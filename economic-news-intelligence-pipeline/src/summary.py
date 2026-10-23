from __future__ import annotations

import html
import os
import re
from typing import Any

import requests
from bs4 import BeautifulSoup


BAD_SUMMARY_PATTERNS = (
    "相关消息",
    "相关动态",
    "该新闻涉及",
    "值得继续关注其市场传导",
    "可能影响行业估值、资金流向和风险偏好",
    "以下是",
)
BAD_MIXED_LANGUAGE_PATTERNS = (
    "表示 it",
    "saying the",
    "react to president",
    "prices are",
    "last year",
    "thwarted",
)
SUMMARY_LABEL_PATTERNS = (
    r"^标题[:：]\s*",
    r"^来源[:：]\s*",
    r"^描述[:：]\s*",
    r"^摘要[:：]\s*",
    r"^概括[:：]\s*",
)
BUCKET_PREFIX_PATTERNS = (
    "国际宏观金融/政策",
    "国际贸易/大宗/能源",
    "国际公司/资本市场",
    "国际、外交",
    "美国、主流新闻",
    "美国、金融",
)


def get_summary_runtime(config: dict[str, Any]) -> dict[str, str | bool]:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    provider = (os.getenv("SUMMARY_PROVIDER") or config.get("summary_provider") or "").strip().lower()
    ollama_model = (os.getenv("OLLAMA_MODEL") or os.getenv("SUMMARY_MODEL") or config.get("summary_model") or "").strip()
    enabled = bool(config.get("enable_llm_summary"))
    if provider == "openai":
        llm_enabled = bool(api_key and enabled)
        reason = None if llm_enabled else "no_openai_api_key"
    elif provider == "ollama":
        llm_enabled = bool(enabled and ollama_model)
        reason = None if llm_enabled else "no_ollama_model"
    else:
        llm_enabled = False
        reason = "unsupported_or_missing_provider"
    return {
        "llm_summary_enabled": llm_enabled,
        "provider_detected": provider if provider else ("openai" if api_key else "none"),
        "summary_mode": "auto_generated" if llm_enabled else "manual_required",
        "reason": None if llm_enabled else reason,
    }


def enrich_items_with_summary_zh(items: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    runtime = get_summary_runtime(config)
    for item in items:
        item["summary_mode"] = runtime["summary_mode"]
        item["summary_reason"] = runtime["reason"]
        item["summary_source"] = "none"
        item["summary_confidence"] = "none"
        item["summary_validation"] = "skipped"
        item["bad_summary_reason"] = None
        item["summary_zh"] = ""
        if not runtime["llm_summary_enabled"]:
            continue

        generated = _generate_llm_summary(item, config=config)
        if not generated:
            item["summary_mode"] = "manual_required"
            item["summary_reason"] = "llm_generation_failed"
            continue

        verdict = validate_summary_zh(generated, item)
        if verdict != "ok":
            regenerated = _generate_llm_summary(item, config=config)
            if regenerated:
                regenerated_verdict = validate_summary_zh(regenerated, item)
                if regenerated_verdict == "ok":
                    item["summary_zh"] = regenerated
                    item["summary_source"] = "llm"
                    item["summary_confidence"] = "high"
                    item["summary_validation"] = "regenerated"
                    item["bad_summary_reason"] = verdict
                    item["summary_reason"] = None
                    continue
            item["summary_mode"] = "manual_required"
            item["summary_reason"] = "bad_summary_validation_failed"
            item["summary_validation"] = "regenerated"
            item["bad_summary_reason"] = verdict
            continue

        item["summary_zh"] = generated
        item["summary_source"] = "llm"
        item["summary_confidence"] = "high"
        item["summary_validation"] = "ok"
        item["bad_summary_reason"] = None
        item["summary_reason"] = None
    return items


def validate_summary_zh(summary: str, item: dict[str, Any]) -> str:
    if _looks_like_list_output(summary):
        return "list_like_output"
    text = _normalize_generated_summary(summary)
    if not text:
        return "empty"
    if _english_ratio(text) > 0.55:
        return "english_ratio_too_high"
    if any(prefix in text for prefix in BUCKET_PREFIX_PATTERNS):
        return "bucket_prefix_leaked"
    if _has_repeated_chinese_token(text):
        return "repeated_chinese_keyword"
    if re.search(r"[A-Za-z][A-Za-z\s\-]{4,}$", text):
        return "ends_with_english_fragment"
    if any(pattern in text for pattern in BAD_SUMMARY_PATTERNS):
        return "template_like_summary"
    if any(pattern in text.casefold() for pattern in BAD_MIXED_LANGUAGE_PATTERNS):
        return "mixed_language_fragment"
    if any(name.casefold() in text.casefold() for name in _source_name_variants(item.get("original_source") or item.get("source", ""))):
        if item.get("original_source") and item.get("original_source") not in {"Reuters", "Bloomberg", "CNBC", "Federal Reserve"}:
            return "source_name_as_subject"
    if _chinese_char_count(text) < 20:
        return "too_short"
    if _chinese_char_count(text) > 160:
        return "too_long"
    if _has_mixed_language(text):
        return "mixed_language"
    return "ok"


def _generate_llm_summary(item: dict[str, Any], config: dict[str, Any]) -> str | None:
    if not _has_summary_context(item):
        return None
    provider = (os.getenv("SUMMARY_PROVIDER") or config.get("summary_provider") or "").strip().lower()
    prompt = _summary_prompt(item)
    if provider == "openai":
        return _generate_openai_summary(prompt, config)
    if provider == "ollama":
        return _generate_ollama_summary(prompt, config)
    return None


def _summary_prompt(item: dict[str, Any]) -> str:
    return (
        "请根据提供的正文线索，用中文写一个自然段概括这条新闻。"
        "不要使用标题、来源、描述、摘要等标签，不要使用1. 2. 3.、项目符号或分点，不要逐字改写标题。"
        "如果信息不足以支持可靠概括，就不要补充不存在的细节。"
        "可以用1到2句，连成一个段落。不要做投资建议。\n\n"
        f"title: {_clean_text(item.get('raw_title') or item.get('title', ''))}\n"
        f"source: {_clean_text(item.get('original_source') or item.get('source', ''))}\n"
        f"description: {_clean_text(item.get('raw_description') or '')}\n"
        f"snippet: {_clean_text(item.get('raw_snippet') or '')}\n"
        f"meta_description: {_clean_text(item.get('meta_description') or '')}"
    )


def _generate_openai_summary(prompt: str, config: dict[str, Any]) -> str | None:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    payload = {
        "model": os.getenv("SUMMARY_MODEL", config.get("summary_model") or "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": "你是一个新闻摘要助手。输出简洁、准确、中文、无投资建议。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 180,
    }
    endpoint = os.getenv("SUMMARY_API_BASE", "https://api.openai.com/v1/chat/completions")
    try:
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _normalize_generated_summary(content)
    except Exception:
        return None


def _generate_ollama_summary(prompt: str, config: dict[str, Any]) -> str | None:
    model = (os.getenv("OLLAMA_MODEL") or os.getenv("SUMMARY_MODEL") or config.get("summary_model") or "").strip()
    if not model:
        return None
    endpoint = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/api/generate")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }
    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return _normalize_generated_summary(data.get("response", ""))
    except Exception:
        return None


def _clean_text(value: str) -> str:
    if not value:
        return ""
    text = BeautifulSoup(html.unescape(value), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -|:：;；")


def _normalize_generated_summary(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    text = re.sub(r"(?:标题|来源|描述|摘要|概括)[:：]\s*", "", text)
    text = re.sub(r"(?:新闻|片段|内容)[:：]\s*", "", text)
    for pattern in SUMMARY_LABEL_PATTERNS:
        text = re.sub(pattern, "", text)
    text = re.sub(r"(?:^|\s)(?:[-*•]+|\d+[.)、])\s*", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"([。！？])\1+", r"\1", text)
    return text.strip()


def _english_ratio(text: str) -> float:
    letters = re.findall(r"[A-Za-z]", text)
    visible = re.findall(r"[\u4e00-\u9fffA-Za-z]", text)
    return len(letters) / len(visible) if visible else 0.0


def _chinese_char_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def _has_mixed_language(text: str) -> bool:
    lowered = text.casefold()
    if any(pattern in lowered for pattern in BAD_MIXED_LANGUAGE_PATTERNS):
        return True
    return bool(re.search(r"[\u4e00-\u9fff]{2,}\s+[A-Za-z]{3,}", text))


def _source_name_variants(name: str) -> list[str]:
    cleaned = _clean_text(name)
    if not cleaned:
        return []
    return [cleaned, cleaned.casefold()]


def _has_repeated_chinese_token(text: str) -> bool:
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    counts: dict[str, int] = {}
    for term in chinese_terms:
        if term in {"经济", "金融", "市场", "贸易", "中国", "美国", "公司", "新闻", "表示"}:
            continue
        counts[term] = counts.get(term, 0) + 1
        if counts[term] >= 3 and len(term) >= 3:
            return True
    return False


def _has_summary_context(item: dict[str, Any]) -> bool:
    title = _clean_text(item.get("raw_title") or item.get("title", ""))
    context_parts = [
        _clean_text(item.get("raw_description") or ""),
        _clean_text(item.get("raw_snippet") or ""),
        _clean_text(item.get("meta_description") or ""),
        _clean_text(item.get("summary") or ""),
    ]
    informative_parts: list[str] = []
    title_casefold = title.casefold()
    for part in context_parts:
        if not part:
            continue
        if part.casefold() == title_casefold:
            continue
        if title and part.casefold().startswith(title_casefold) and len(part) - len(title) < 20:
            continue
        informative_parts.append(part)
    if not informative_parts:
        return False
    longest = max(len(part) for part in informative_parts)
    chinese_chars = max(_chinese_char_count(part) for part in informative_parts)
    return longest >= 40 or chinese_chars >= 18


def _looks_like_list_output(text: str) -> bool:
    return bool(re.search(r"(?:^|\s)(?:[-*•]+|\d+[.)、])\s*\S+", text))
