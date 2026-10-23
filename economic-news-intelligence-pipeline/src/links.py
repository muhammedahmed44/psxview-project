from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

from .utils import normalize_url


HEADERS = {"User-Agent": "KaraNewsAgent/1.0 (+local link check)"}


def validate_items_links(items: list[dict[str, Any]], timeout: int = 5) -> list[dict[str, Any]]:
    for item in items:
        validate_item_link(item, timeout=timeout)
    return items


def validate_item_link(item: dict[str, Any], timeout: int = 5) -> dict[str, Any]:
    original_url = item.get("original_url") or item.get("url")
    normalized_url = normalize_url(item.get("normalized_url") or original_url)
    candidates = _candidate_urls(original_url, normalized_url)

    item["original_url"] = original_url
    item["normalized_url"] = normalized_url
    for candidate in candidates:
        resolved_url = _url_ok(candidate, timeout=timeout)
        if resolved_url:
            item["final_url_used"] = resolved_url
            item["url"] = resolved_url
            if resolved_url != original_url:
                item["link_status"] = "fixed"
                item["link_note"] = _link_note(original_url, resolved_url)
            else:
                item["link_status"] = "ok"
                item["link_note"] = None
            return item

    item["final_url_used"] = normalized_url
    item["url"] = normalized_url
    item["link_status"] = "failed"
    item["link_note"] = "all_link_validation_attempts_failed"
    logging.warning("Link validation failed for %s", original_url)
    return item


def _candidate_urls(original_url: str, normalized_url: str) -> list[str]:
    candidates: list[str] = []
    for url in (normalized_url, original_url):
        if url and url not in candidates:
            candidates.append(url)

    for url in list(candidates):
        parsed = urlparse(url)
        if parsed.scheme == "https":
            alternate = urlunparse(("http", parsed.netloc, parsed.path, "", parsed.query, ""))
        elif parsed.scheme == "http":
            alternate = urlunparse(("https", parsed.netloc, parsed.path, "", parsed.query, ""))
        else:
            continue
        if alternate not in candidates:
            candidates.append(alternate)
    return candidates


def _url_ok(url: str, timeout: int) -> str | None:
    try:
        response = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if response.status_code < 400:
            return str(response.url)
        if response.status_code not in {403, 405, 406}:
            return None
    except requests.RequestException:
        pass

    try:
        with requests.get(url, headers=HEADERS, timeout=timeout, stream=True, allow_redirects=True) as response:
            if response.status_code >= 400:
                return None
            next(response.iter_content(chunk_size=256), b"")
            return str(response.url)
    except requests.RequestException:
        return None


def _link_note(original_url: str, final_url: str) -> str:
    original_host = urlparse(original_url).netloc.lower()
    final_host = urlparse(final_url).netloc.lower()
    if original_host == "chinanews.com.cn" and final_host == "www.chinanews.com.cn":
        return "added_www_for_chinanews"
    if urlparse(original_url).scheme != urlparse(final_url).scheme:
        return "scheme_fallback"
    return "normalized_url"
