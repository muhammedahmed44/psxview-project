from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from .pipeline_config import get_config_section


def _source_quality_config() -> dict[str, Any]:
    return get_config_section("source_quality", {})


def _sources_for(group: str) -> set[str]:
    return set(_source_quality_config().get(group, {}).get("sources", ()))


def _domains_for(group: str) -> set[str]:
    return set(_source_quality_config().get(group, {}).get("domains", ()))


def _patterns(name: str) -> tuple[str, ...]:
    return tuple(_source_quality_config().get(name, ()))


def enrich_source_metadata(item: dict[str, Any], entry_source_title: str | None = None) -> dict[str, Any]:
    original_source = extract_original_source(
        title=item.get("title", ""),
        current_source=item.get("source", ""),
        entry_source_title=entry_source_title,
        url=item.get("url", ""),
    )
    source_quality = classify_source_quality(
        original_source,
        item.get("url", ""),
        item.get("title", ""),
        item.get("summary", ""),
    )
    item["original_source"] = original_source
    item["source"] = original_source or item.get("source")
    item["source_quality"] = source_quality
    item["source_quality_allowed"] = source_quality in {
        "official",
        "tier1_media",
        "financial_media",
        "acceptable_media",
    }
    return item


def extract_original_source(title: str, current_source: str, entry_source_title: str | None = None, url: str = "") -> str:
    candidates = [
        entry_source_title or "",
        _title_suffix_source(title),
        current_source or "",
        _domain_source(url),
    ]
    for candidate in candidates:
        normalized = normalize_source_name(candidate)
        if normalized and normalized != "Unknown":
            return normalized
    return normalize_source_name(current_source) or "Unknown"


def normalize_source_name(name: str) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"\s+", " ", name).strip(" -|:：")
    cleaned = re.sub(r"\s+(news|finance|business|markets)$", "", cleaned, flags=re.I)
    lowered = cleaned.casefold()
    replacements = {
        "cnbc.com": "CNBC",
        "reuters.com": "Reuters",
        "reuters markets": "Reuters",
        "reuters business": "Reuters",
        "bloomberg.com": "Bloomberg",
        "abc news": "ABC News",
        "nbc news": "NBC News",
        "cbs news": "CBS News",
        "cbs moneywatch": "CBS MoneyWatch",
        "ap news": "AP News",
        "associated press": "AP News",
        "yahoo finance": "Yahoo Finance",
        "wall street journal": "Wall Street Journal",
        "financial times": "Financial Times",
        "the economist": "The Economist",
        "the motley fool": "Motley Fool",
        "motley fool": "Motley Fool",
        "forexlive": "ForexLive",
    }
    for source, target in replacements.items():
        if lowered == source or lowered.endswith(source):
            return target
    if cleaned.lower() == "google news":
        return "Google News"
    if cleaned.lower() == "bing news":
        return "Bing News"
    if cleaned.lower() == "newsapi":
        return "NewsAPI"
    if cleaned.lower() == "gdelt":
        return "GDELT"
    return cleaned or "Unknown"


def classify_source_quality(source_name: str, url: str, title: str, summary: str) -> str:
    lowered = source_name.casefold()
    hostname = _hostname(url)
    blob = f"{title} {summary} {url} {source_name}".casefold()
    if any(token in lowered for token in _sources_for("official")) or _hostname_matches(hostname, _domains_for("official")):
        return "official"
    if any(token in lowered for token in _sources_for("tier1_media")) or _hostname_matches(hostname, _domains_for("tier1_media")):
        return "tier1_media"
    if any(token in lowered for token in _sources_for("financial_media")) or _hostname_matches(hostname, _domains_for("financial_media")):
        return "financial_media"
    if any(token in lowered for token in _sources_for("acceptable_media")) or _hostname_matches(hostname, _domains_for("acceptable_media")):
        return "acceptable_media"
    if any(token in lowered for token in _sources_for("denylist")) or _hostname_matches(hostname, _domains_for("denylist")):
        return "broker_or_trading_platform"
    if any(pattern in blob for pattern in _patterns("low_quality_finance_patterns")):
        return "low_quality_finance"
    if any(pattern in blob for pattern in _patterns("content_farm_patterns")):
        return "content_farm"
    if lowered in {"google news", "bing news", "newsapi", "gdelt", "unknown"}:
        return "unknown"
    return "unknown"


def is_low_quality_title(title: str, summary: str = "", source_name: str = "") -> bool:
    blob = f"{title} {summary} {source_name}".casefold()
    return any(pattern in blob for pattern in _patterns("low_quality_title_patterns"))


def _title_suffix_source(title: str) -> str:
    match = re.search(r"\s[-|:]\s([A-Za-z][A-Za-z0-9&'.\s-]{1,50})$", title.strip())
    return match.group(1).strip() if match else ""


def _domain_source(url: str) -> str:
    hostname = _hostname(url).replace("www.", "")
    if not hostname:
        return ""
    parts = hostname.split(".")
    if len(parts) >= 2:
        return parts[0]
    return hostname


def _hostname(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def _hostname_matches(hostname: str, domains: set[str]) -> bool:
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains)
