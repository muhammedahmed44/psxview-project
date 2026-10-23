from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from .pipeline_config import get_config_section
from .utils import canonicalize_url


# Stopwords removed from titles so event signatures focus on meaningful words.
CHINESE_STOPWORDS = {"的", "了", "和", "就", "在", "对", "与", "及", "等", "称", "表示", "公布", "发布", "举行", "进行", "记者", "报道", "最新"}
ENGLISH_STOPWORDS = {"the", "a", "an", "of", "in", "on", "to", "for", "with", "and", "says", "said", "report", "reports", "new", "latest", "update"}
# Tokens that are too generic to identify a specific event.
GENERIC_ENTITY_TOKENS = {"china", "chinese", "us", "u_s", "u.s", "america", "united_states", "states", "market", "markets", "government"}
# Verbs/actions that strongly signal a discrete market-moving event.
EVENT_ACTION_KEYWORDS = {
    "发布", "出台", "修订", "批准", "调查", "制裁", "禁令", "清单", "关税", "会谈", "签署", "声明", "预警",
    "事故", "冲突", "袭击", "停火", "利率", "通胀", "监管", "上市", "挂牌", "募资", "估值", "市值",
    "announces", "approves", "sanctions", "tariff", "trade", "ceasefire", "strike", "attack", "war", "conflict",
    "policy", "regulation", "investigation", "ban", "warning", "agreement", "ipo", "listing", "shares", "valuation",
    "market debut", "priced", "raises", "market cap", "trading debut",
}

# Load similarity thresholds from pipeline configuration.
_DEDUPE_THRESHOLDS = get_config_section("thresholds", {}).get("dedupe", {})


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicate news items, keeping the highest-quality representative.

    Returns only the kept items.
    """
    return dedupe_items_with_report(items)[0]


def dedupe_items_with_report(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Remove duplicates and also produce a diagnostic report.

    Returns (kept_items, report) where report contains stats and example duplicates.
    """
    kept: list[dict[str, Any]] = []
    duplicate_records: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()

    # Sort items so the best representative of each event is processed first.
    for item in sorted(items, key=_best_key, reverse=True):
        _annotate_item(item)
        duplicate = _find_duplicate(item, kept)
        if duplicate is None:
            item["duplicate_group_id"] = item["event_cluster_key"]
            item["duplicate_count"] = 1
            kept.append(item)
            continue

        kept_item, reason = duplicate
        stats[reason] += 1
        kept_item["duplicate_count"] = int(kept_item.get("duplicate_count", 1)) + 1
        item["dedupe_reason"] = reason
        duplicate_records.append(
            {
                "kept": _dedupe_snapshot(kept_item),
                "dropped": _dedupe_snapshot(item),
                "reason": reason,
                "fingerprint": item.get("event_fingerprint"),
            }
        )

    report = {
        "stats": {
            "exact_url": stats.get("exact_url", 0),
            "title_similarity": stats.get("title_similarity", 0),
            "event_fingerprint": stats.get("event_fingerprint", 0),
            "fuzzy_event_similarity": stats.get("fuzzy_event_similarity", 0),
        },
        "duplicates": duplicate_records,
        "examples": duplicate_records[:5],
    }
    return kept, report


def _find_duplicate(candidate: dict[str, Any], kept_items: list[dict[str, Any]]) -> tuple[dict[str, Any], str] | None:
    """
    Check whether candidate is a duplicate of any already-kept item.

    Uses progressively fuzzier matching: exact URL, title similarity, event fingerprint,
    and token overlap with shared entities/actions.
    """
    candidate_url = canonicalize_url(candidate["url"])
    candidate_title = candidate["normalized_title"]
    candidate_tokens = set(candidate["event_tokens"])
    candidate_entities = set(candidate["strong_entities"])
    candidate_actions = set(candidate["action_tokens"])

    for kept in kept_items:
        if candidate_url == canonicalize_url(kept["url"]):
            return kept, "exact_url"

        kept_title = kept["normalized_title"]
        title_similarity = SequenceMatcher(None, candidate_title, kept_title).ratio()
        if candidate_title == kept_title or title_similarity >= float(_DEDUPE_THRESHOLDS.get("title_similarity_strict", 0.9)):
            return kept, "title_similarity"

        if _informative_fingerprint(candidate.get("event_fingerprint")) and candidate.get("event_fingerprint") == kept.get("event_fingerprint"):
            return kept, "event_fingerprint"

        kept_tokens = set(kept.get("event_tokens", ()))
        kept_entities = set(kept.get("strong_entities", ()))
        kept_actions = set(kept.get("action_tokens", ()))
        shared_entities = _distinctive_shared_entities(candidate_entities, kept_entities)
        shared_tokens = candidate_tokens & kept_tokens
        token_similarity = _token_similarity(candidate_tokens, kept_tokens)

        # Fuzzy event matching: high title similarity with decent token overlap.
        if title_similarity >= float(_DEDUPE_THRESHOLDS.get("title_similarity_high", 0.82)) and token_similarity >= 0.5:
            return kept, "fuzzy_event_similarity"
        # Same day + enough shared tokens.
        if candidate.get("published_date") == kept.get("published_date") and len(shared_tokens) >= 3 and token_similarity >= 0.5:
            return kept, "fuzzy_event_similarity"
        # Shared distinctive entities and strong token overlap.
        if shared_entities and token_similarity >= float(_DEDUPE_THRESHOLDS.get("token_similarity_shared_entities", 0.72)):
            return kept, "fuzzy_event_similarity"
        # Shared entities + shared action + moderate token overlap.
        if shared_entities and candidate_actions & kept_actions and token_similarity >= float(_DEDUPE_THRESHOLDS.get("fuzzy_token_similarity_min", 0.55)):
            return kept, "fuzzy_event_similarity"
        # Same action with very high token overlap.
        if candidate_actions & kept_actions and token_similarity >= float(_DEDUPE_THRESHOLDS.get("token_similarity_action_overlap", 0.85)):
            return kept, "fuzzy_event_similarity"
    return None


def _annotate_item(item: dict[str, Any]) -> None:
    """
    Add normalized fields used for deduplication to the item in place.

    Computes normalized title, strong entities, action tokens, event tokens,
    fingerprint, and cluster keys.
    """
    normalized_title = normalize_title_for_event(item.get("title", ""))
    strong_entities = _strong_entities(item.get("title", ""))
    action_tokens = _action_tokens(item.get("title", ""))
    event_tokens = _event_tokens(item.get("title", ""), normalized_title, strong_entities, action_tokens)
    event_fingerprint = _event_fingerprint(item, strong_entities, action_tokens, event_tokens)

    item["normalized_title"] = normalized_title
    item["strong_entities"] = strong_entities
    item["action_tokens"] = action_tokens
    item["event_tokens"] = event_tokens
    item["event_fingerprint"] = event_fingerprint
    item["event_group_key"] = event_fingerprint
    item["event_cluster_key"] = event_fingerprint


def normalize_title_for_event(title: str) -> str:
    """
    Clean a title into a comparable normalized form.

    Strips leading labels, removes trailing source tags, removes punctuation,
    and drops English stopwords.
    """
    lowered = title.casefold()
    lowered = re.sub(r"^[\[\(（【].*?[\]\)）】]\s*", "", lowered)
    lowered = re.sub(r"\s+[-—–]\s+[\w\s.\u4e00-\u9fff]+$", "", lowered)
    lowered = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    tokens = [token for token in lowered.split() if token not in ENGLISH_STOPWORDS]
    return " ".join(tokens) if tokens else lowered


def _action_tokens(title: str) -> list[str]:
    """
    Extract event-action keywords found in the title.

    Actions are normalized to snake_case so they compare cleanly.
    """
    raw = title.casefold()
    actions: list[str] = []
    for action in EVENT_ACTION_KEYWORDS:
        normalized = action.casefold().replace(" ", "_")
        if action.casefold() in raw and normalized not in actions:
            actions.append(normalized)
    return actions


def _strong_entities(title: str) -> list[str]:
    """
    Extract named entities from a title.

    Looks for capitalized English phrases, Chinese phrases with optional numbers,
    and acronyms. Filters out stopwords and overly generic terms.
    """
    entities: list[str] = []
    entities.extend(_append_matches(title, r"[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3}"))
    entities.extend(_append_matches(title, r"[\u4e00-\u9fff]{2,8}\d{0,4}"))
    entities.extend(_append_matches(title, r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})?\b"))

    normalized_entities: list[str] = []
    for entity in entities:
        normalized = entity.casefold().replace(" ", "_")
        if len(normalized) < 3 or normalized in CHINESE_STOPWORDS or normalized in ENGLISH_STOPWORDS:
            continue
        if normalized in GENERIC_ENTITY_TOKENS:
            continue
        if normalized not in normalized_entities:
            normalized_entities.append(normalized)
    return normalized_entities[: int(_DEDUPE_THRESHOLDS.get("max_strong_entities", 8))]


def _append_matches(title: str, pattern: str) -> list[str]:
    """Return all non-empty regex matches in the title."""
    return [match.group(0).strip() for match in re.finditer(pattern, title) if match.group(0).strip()]


def _event_tokens(title: str, normalized_title: str, strong_entities: list[str], action_tokens: list[str]) -> list[str]:
    """
    Build the full token set representing an event.

    Combines entities, actions, English words, and Chinese/number phrases.
    """
    tokens: list[str] = []
    tokens.extend(strong_entities)
    tokens.extend(action_tokens)
    tokens.extend(re.findall(r"[a-z][a-z0-9-]{2,}", normalized_title))
    tokens.extend(re.findall(r"[\u4e00-\u9fff]{2,}\d*|\d+人|\d+[a-z]*", title))

    cleaned: list[str] = []
    for token in tokens:
        if token in ENGLISH_STOPWORDS or token in CHINESE_STOPWORDS:
            continue
        if token not in cleaned:
            cleaned.append(token)
    return cleaned[: int(_DEDUPE_THRESHOLDS.get("max_event_tokens", 12))]


def _event_fingerprint(item: dict[str, Any], entities: list[str], action_tokens: list[str], event_tokens: list[str]) -> str:
    """
    Create a stable fingerprint string that groups the same news event.

    Uses publication date plus the most distinctive entities, actions, and tokens.
    """
    date_part = item.get("published_date") or ""
    entity_core = [entity for entity in entities if entity not in GENERIC_ENTITY_TOKENS]
    core = list(dict.fromkeys(entity_core + action_tokens + event_tokens))
    if len(core) < 3:
        core = list(dict.fromkeys(action_tokens + event_tokens))
    return "|".join([date_part] + core[: int(_DEDUPE_THRESHOLDS.get("max_fingerprint_terms", 6))])


def _distinctive_shared_entities(left_entities: set[str], right_entities: set[str]) -> set[str]:
    """Return shared entities that are not considered generic."""
    return {
        entity
        for entity in (left_entities & right_entities)
        if entity not in GENERIC_ENTITY_TOKENS
    }


def _informative_fingerprint(fingerprint: str | None) -> bool:
    """
    Decide whether a fingerprint is informative enough to trust for exact deduplication.

    Requires at least 3 parts and at least 2 non-generic informative parts.
    """
    if not fingerprint:
        return False
    parts = [part for part in fingerprint.split("|") if part]
    if len(parts) < 3:
        return False
    informative_parts = [part for part in parts[1:] if part not in GENERIC_ENTITY_TOKENS]
    return len(informative_parts) >= 2


def _token_similarity(left: set[str], right: set[str]) -> float:
    """
    Compute a normalized similarity score between two token sets.

    Uses Dice coefficient: 2 * intersection / (size_left + size_right).
    """
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    return (2 * intersection) / (len(left) + len(right))


def _best_key(item: dict[str, Any]) -> tuple[float, float, int, int, str]:
    """
    Return a sort key so the highest-quality item is kept as the duplicate representative.

    Prefers higher quality score, higher source weight, numeric specificity, link status,
    and more recent publication time.
    """
    link_bonus = 1 if item.get("link_status") in {"ok", "fixed", "unchecked"} else 0
    numeric_specificity = len(re.findall(r"\d+", item.get("title", "")))
    return (
        float(item.get("quality_score", 0)),
        float(item.get("source_weight", 0)),
        numeric_specificity,
        link_bonus,
        item.get("published_at") or "",
    )


def _dedupe_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a small summary of an item for duplicate-reporting purposes.
    """
    return {
        "title": item.get("title"),
        "source": item.get("source"),
        "source_group": item.get("source_group"),
        "url": item.get("url"),
        "published_date": item.get("published_date"),
        "quality_score": item.get("quality_score"),
        "source_weight": item.get("source_weight"),
        "event_fingerprint": item.get("event_fingerprint"),
    }