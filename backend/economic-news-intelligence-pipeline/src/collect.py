from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests

from .collect_dates import item_dates, parse_date_from_text, parse_entry_published_datetime, possible_republished_old_story
from .collect_http import get_with_http_fallback
from .links import validate_item_link
from .pipeline_config import get_config_section
from .source_quality import enrich_source_metadata, extract_original_source
from .utils import canonicalize_url, derive_tags, is_paid_domain, normalize_url, parse_datetime


HTML_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/120 Safari/537.36"
)
NAV_TITLES = {
    "首页",
    "新闻",
    "国内",
    "国际",
    "财经",
    "更多",
    "更多>>",
    "English",
    "关于我们",
    "联系我们",
    "网站地图",
    "RSS",
    "频道地图",
    "设为首页",
    "登录",
    "客户端",
    "分享",
    "视频",
    "图片",
    "财经首页",
    "栏目页",
    "关于我们",
    "联系我们",
    "广告服务",
    "版权声明",
    "隐私政策",
    "订阅",
    "newsletter",
    "Home",
    "Video",
    "Photos",
    "Podcasts",
    "Newsletter",
    "Subscribe",
    "Sign In",
    "Login",
    "Live TV",
    "Watch",
    "About",
    "Contact",
    "Privacy",
    "Terms",
    "Advertisement",
}
NOISE_TITLE_KEYWORDS = {
    "首页",
    "English",
    "English Version",
    "机构设置",
    "新闻发布",
    "政务公开",
    "政策法规",
    "互动交流",
    "司局负责人发布",
    "专题",
    "学习贯彻",
    "学习宣传贯彻",
    "党的二十大",
    "主题教育",
    "网站工作年度报表",
    "更多",
    "返回",
    "网站地图",
}
DETAIL_URL_HINTS = (
    "art",
    "article",
    "content",
    "detail",
    "news",
    "xinwen",
    "xwfb",
    "goutongjiaoliu",
    "302249",
    "302330",
    "2480148",
)
RSS_INDEX_KEYWORDS = (
    "财经要闻",
    "国内财经",
    "国际财经",
    "期货",
    "外汇",
    "股市",
    "Top Stories",
    "U.S.",
    "Politics",
    "World",
    "MoneyWatch",
    "焦点新闻",
    "期货要闻",
    "外汇",
    "美股快报",
)
_COLLECT_KEYWORDS = get_config_section("keywords", {}).get("collect", {})
_COLLECT_THRESHOLDS = get_config_section("thresholds", {}).get("collection", {})
DOMESTIC_ECONOMIC_KEYWORDS = tuple(_COLLECT_KEYWORDS.get("domestic_economic_keywords", ()))
INTERNATIONAL_ECONOMIC_KEYWORDS = tuple(_COLLECT_KEYWORDS.get("international_economic_keywords", ()))


def collect_news(config: dict[str, Any], target_date: date) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    sources = _iter_sources(config)
    core_sources = [source for source in sources if source.get("source_type", "core") == "core"]
    optional_sources = sorted(
        [source for source in sources if source.get("source_type") == "optional"],
        key=_optional_source_priority,
    )
    bing_fallback_sources = [source for source in sources if source.get("source_type") == "bing_fallback"]

    for source in core_sources:
        try:
            items.extend(_collect_source(source, config, target_date))
        except Exception as exc:
            logging.warning("Source failed [%s - %s]: %s", source.get("category"), source.get("name"), exc)

    category_counts = _category_counts(items)
    for source in optional_sources:
        if _should_skip_optional_source(source, items, category_counts, target_date):
            continue
        try:
            new_items = _collect_source(source, config, target_date)
            items.extend(new_items)
            category_counts = _category_counts(items)
        except Exception as exc:
            logging.warning("Optional source failed [%s - %s]: %s", source.get("category"), source.get("name"), exc)

    fallback_needed = {
        "domestic": _category_target_date_count(items, target_date, "domestic") < 8,
        "international": _category_target_date_count(items, target_date, "international") < 8,
    }
    topic_fallback_needed = {
        "domestic": _source_group_target_date_count(items, target_date, "google_topic") < int(_COLLECT_THRESHOLDS.get("domestic_topic_fallback_trigger", 8)),
        "international": _source_group_target_date_count(items, target_date, "google_topic_intl") < int(_COLLECT_THRESHOLDS.get("international_topic_fallback_trigger", 8)),
    }
    for category, needed in fallback_needed.items():
        if not (needed or topic_fallback_needed.get(category)):
            continue
        for source in [source for source in bing_fallback_sources if source.get("category") == category]:
            try:
                items.extend(_collect_source(source, config, target_date))
            except Exception as exc:
                logging.warning("Bing fallback source failed [%s - %s]: %s", source.get("category"), source.get("name"), exc)

    category_counts = _category_counts(items)
    if min(category_counts.get("domestic", 0), category_counts.get("international", 0)) < 6:
        items.extend(_collect_newsapi(config, target_date))
        items.extend(_collect_gdelt(config, target_date))
    return items


def probe_domestic_sources(config: dict[str, Any], target_date: date) -> list[dict[str, Any]]:
    return probe_sources(config, target_date, category="domestic")


def probe_international_sources(config: dict[str, Any], target_date: date) -> list[dict[str, Any]]:
    return probe_sources(config, target_date, category="international")


def probe_sources(config: dict[str, Any], target_date: date, category: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for source in [source for source in _iter_sources(config) if source.get("category") == category]:
        result = {
            "name": source.get("name"),
            "source_group": source.get("source_group"),
            "method": source.get("method"),
            "source_type": source.get("source_type", "core"),
            "raw_count": 0,
            "date_parse_success_count": 0,
            "target_date_count": 0,
            "economic_keyword_count": 0,
            "selected_candidate_count": 0,
            "target_date_missing_count": 0,
            "bucket_guess_counts": {},
            "source_quality": None,
            "accepted_count": 0,
            "excluded_broker_count": 0,
            "excluded_low_quality_count": 0,
            "excluded_unknown_count": 0,
            "sample_target_titles": [],
            "status": "failed",
            "sample_titles": [],
            "sample_rejected_titles": [],
            "sample_descriptions": [],
            "error": None,
        }
        try:
            items = _collect_source(source, config, target_date, health_check=True)
            result["raw_count"] = len(items)
            result["date_parse_success_count"] = sum(1 for item in items if item.get("published_date"))
            result["target_date_count"] = sum(1 for item in items if item.get("published_date") == target_date.isoformat())
            result["target_date_missing_count"] = sum(1 for item in items if not item.get("published_date"))
            result["economic_keyword_count"] = sum(1 for item in items if _has_economic_keyword(item, category))
            result["selected_candidate_count"] = sum(
                1
                for item in items
                if item.get("published_date") == target_date.isoformat() and _has_economic_keyword(item, category)
            )
            result["bucket_guess_counts"] = _probe_bucket_counts(items)
            result["source_quality"] = _probe_primary_source_quality(items)
            result["accepted_count"] = sum(1 for item in items if item.get("source_quality_allowed"))
            result["excluded_broker_count"] = sum(1 for item in items if item.get("source_quality") == "broker_or_trading_platform")
            result["excluded_low_quality_count"] = sum(1 for item in items if item.get("source_quality") in {"low_quality_finance", "content_farm"})
            result["excluded_unknown_count"] = sum(1 for item in items if item.get("source_quality") == "unknown")
            result["sample_titles"] = [item.get("title") for item in items[:3]]
            result["sample_target_titles"] = [item.get("title") for item in items if item.get("published_date") == target_date.isoformat()][:3]
            result["sample_rejected_titles"] = [item.get("title") for item in items if not item.get("source_quality_allowed")][:3]
            result["sample_descriptions"] = [item.get("summary") for item in items if item.get("summary")][:3]
            result["status"] = "ok" if result["raw_count"] else "empty"
        except Exception as exc:
            result["error"] = str(exc)
        results.append(result)
    return sorted(results, key=lambda item: (item["selected_candidate_count"], item["target_date_count"], item["raw_count"]), reverse=True)


def check_sources(config: dict[str, Any], target_date: date) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for source in _iter_sources(config):
        result = {
            "name": source.get("name"),
            "category": source.get("category"),
            "method": source.get("method") or source.get("type"),
            "source_type": source.get("source_type", "core"),
            "source_group": source.get("source_group"),
            "primary_url": source.get("url"),
            "final_url_used": None,
            "status": "failed",
            "item_count": 0,
            "sample_titles": [],
            "latest_date": None,
            "latest_date_shanghai": None,
            "error": None,
            "note": None,
            "date_fields_detected": [],
        }
        try:
            items = _collect_source(source, config, target_date, health_check=True)
            result["item_count"] = len(items)
            result["sample_titles"] = [item["title"] for item in items[:3]]
            result["sample_links"] = _sample_link_checks(source, items)
            result["final_url_used"] = source.get("_final_url_used") or source.get("url")
            result["note"] = source.get("_fetch_note")
            latest_date = _latest_item_date(items)
            result["latest_date"] = latest_date.isoformat() if latest_date else None
            result["latest_date_shanghai"] = latest_date.isoformat() if latest_date else None
            result["date_fields_detected"] = sorted(source.get("_date_fields_detected", []))
            if not items:
                result["status"] = "empty"
            elif latest_date and (target_date - latest_date).days > 30:
                result["status"] = "stale"
                result["note"] = _merge_note(result["note"], "rss_stale_do_not_rank")
            else:
                result["status"] = "ok"
            if items and latest_date is None:
                result["note"] = _merge_note(result["note"], "missing_date_unusable_for_ranking")
        except Exception as exc:
            result["error"] = str(exc)
            result["final_url_used"] = source.get("_final_url_used")
            result["note"] = source.get("_fetch_note")
        results.append(result)
    return results


def _sample_link_checks(source: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, str | None]]:
    if source.get("source_group") != "chinanews":
        return []
    samples: list[dict[str, str | None]] = []
    for item in items[:3]:
        checked = validate_item_link(dict(item), timeout=4)
        samples.append(
            {
                "original_url": checked.get("original_url"),
                "normalized_url": checked.get("normalized_url"),
                "final_url_used": checked.get("final_url_used"),
                "link_status": checked.get("link_status"),
                "link_note": checked.get("link_note"),
            }
        )
    return samples


def collect_html_source(
    source: dict[str, Any],
    target_date: date,
    lookback_days: int = 3,
    config: dict[str, Any] | None = None,
    url_override: str | None = None,
) -> list[dict[str, Any]]:
    from bs4 import BeautifulSoup

    runtime_config = config or {}
    request_url = url_override or source["url"]
    response, final_url, note = _get_with_http_fallback(request_url, source, timeout=_source_timeout(source))
    source["_final_url_used"] = final_url
    source["_fetch_note"] = note
    response.encoding = response.apparent_encoding or response.encoding

    soup = BeautifulSoup(response.text, "html.parser")
    items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    article_date_fetch_limit = max(0, int(source.get("article_date_fetch_limit", 10)))
    article_date_fetches = 0

    for anchor in soup.find_all("a"):
        title = _clean_title(anchor.get_text(" ", strip=True))
        if not _is_probable_news_title(title):
            continue

        href = (anchor.get("href") or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "#")):
            continue

        absolute_url = urljoin(final_url, href)
        parsed_url = urlparse(absolute_url)
        if parsed_url.scheme not in {"http", "https"}:
            continue
        if _is_noise_url(absolute_url):
            continue
        if not _is_probable_detail_url(absolute_url, source["url"], title):
            continue
        if runtime_config and is_paid_domain(absolute_url, runtime_config.get("paid_domains", [])):
            continue

        canonical_url = canonicalize_url(absolute_url)
        if canonical_url in seen_urls:
            continue

        published_date = _extract_nearby_date(anchor, source.get("url", ""))
        date_fields = ["listing_page_date"] if published_date else []
        published_at = None
        # Listing pages often omit dates; inspect a bounded number of article
        # pages for authoritative publication metadata instead of guessing from
        # the listing URL or headline.
        if (published_date is None and source.get("fetch_article_dates", True)
                and article_date_fetches < article_date_fetch_limit):
            article_date_fetches += 1
            article_date, article_published_at, article_date_field = _extract_article_publication_date(
                absolute_url, source, config=runtime_config
            )
            if article_date:
                published_date = article_date
                published_at = article_published_at
                date_fields = [article_date_field] if article_date_field else ["article_metadata"]
        seen_urls.add(canonical_url)
        items.append(
            _build_item(
                title=title,
                url=absolute_url,
                source=source,
                category=source["category"],
                published_date=published_date,
                source_timezone_date=published_date,
                published_at=published_at,
                date_parse_fields=date_fields,
                summary="",
                config=runtime_config,
            )
        )

    return items


def _collect_source(source: dict[str, Any], config: dict[str, Any], target_date: date, health_check: bool = False) -> list[dict[str, Any]]:
    method = (source.get("method") or source.get("type") or "rss").lower()
    if method == "rss":
        return _fetch_rss_source(source, config, target_date, include_old=health_check)
    if method == "google_news_rss":
        return _collect_google_news_rss(source, config, target_date, include_old=health_check)
    if method == "bing_news_rss":
        return _collect_bing_news_rss(source, config, target_date, include_old=health_check)
    if method == "opml_discovery":
        return _collect_opml_discovery(source, config, target_date, include_old=health_check)
    if method == "rss_list":
        return _collect_rss_list(source, config, target_date, include_old=health_check)
    if method == "rss_index":
        return _collect_rss_index(source, config, target_date, include_old=health_check)
    if method == "rss_index_or_rss":
        items = _collect_rss_index(source, config, target_date, include_old=health_check)
        if items:
            return items
        return _fetch_rss_source(source, config, target_date, include_old=health_check)
    if method == "rss_or_html":
        try:
            items = _fetch_rss_source(source, config, target_date, include_old=health_check)
            if items:
                return items
        except Exception as exc:
            logging.warning("RSS primary failed [%s]: %s", source.get("name"), exc)
        return collect_html_source(source, target_date, lookback_days=365 if health_check else 0, config=config)
    if method == "html_or_rss_index":
        items = collect_html_source(source, target_date, lookback_days=365 if health_check else 0, config=config)
        if items:
            return items
        return _collect_rss_index(source, config, target_date, include_old=health_check)
    if method == "html_or_rss":
        items = collect_html_source(source, target_date, lookback_days=365 if health_check else 0, config=config)
        if items:
            return items
        return _fetch_rss_source(source, config, target_date, include_old=health_check)
    if method == "html":
        return collect_html_source(source, target_date, lookback_days=365 if health_check else 0, config=config)
    raise ValueError(f"Unsupported source method: {method}")


def _collect_google_news_rss(source: dict[str, Any], config: dict[str, Any], target_date: date, include_old: bool = False) -> list[dict[str, Any]]:
    query = source.get("query") or source.get("q") or ""
    dated_query = f"{query} after:{target_date.isoformat()} before:{(target_date + timedelta(days=1)).isoformat()}"
    locale = source.get("google_news_locale") or config.get("google_news_locale") or "en-PK"
    country = source.get("google_news_country") or config.get("google_news_country") or "PK"
    language = locale.split("-")[0]
    url = ("https://news.google.com/rss/search?q=" + quote_plus(dated_query)
           + f"&hl={language}-{country}&gl={country}&ceid={country}:{language}")
    feed_source = dict(source)
    feed_source["url"] = url
    feed_source["timezone"] = source.get("timezone") or config.get("timezone", "Asia/Karachi")
    feed_source["method"] = "google_news_rss"
    return _fetch_rss_source(feed_source, config, target_date, include_old=include_old)[: int(source.get("max_items", 20))]


def _collect_bing_news_rss(source: dict[str, Any], config: dict[str, Any], target_date: date, include_old: bool = False) -> list[dict[str, Any]]:
    query = source.get("query") or source.get("q") or ""
    dated_query = f"{query} after:{target_date.isoformat()} before:{(target_date + timedelta(days=1)).isoformat()}"
    url = "https://www.bing.com/news/search?q=" + quote_plus(dated_query) + "&format=rss&qft=sortbydate%3d%221%22"
    feed_source = dict(source)
    feed_source["url"] = url
    feed_source["timezone"] = source.get("timezone") or config.get("timezone", "Asia/Karachi")
    feed_source["method"] = "bing_news_rss"
    return _fetch_rss_source(feed_source, config, target_date, include_old=include_old)[: int(source.get("max_items", 10))]


def _collect_opml_discovery(source: dict[str, Any], config: dict[str, Any], target_date: date, include_old: bool = False) -> list[dict[str, Any]]:
    from bs4 import BeautifulSoup

    response, final_url, note = _get_with_http_fallback(source["url"], source, timeout=_source_timeout(source))
    source["_final_url_used"] = final_url
    source["_fetch_note"] = note
    soup = BeautifulSoup(response.content, "xml")
    include_tokens = tuple(source.get("rss_keywords") or ("finance", "politics", "economy", "society", "world", "财经", "经济", "时政", "社会", "国际"))
    exclude_tokens = ("sports", "entertainment", "culture", "video", "photo", "体育", "娱乐", "文化", "视频", "图片")
    feed_urls: list[str] = []
    for outline in soup.find_all("outline"):
        candidate = outline.get("xmlUrl") or outline.get("xmlurl") or outline.get("url")
        text = " ".join(str(outline.get(attr, "")) for attr in ("text", "title", "type"))
        blob = f"{text} {candidate or ''}".casefold()
        if not candidate:
            continue
        if any(token.casefold() in blob for token in exclude_tokens):
            continue
        if include_tokens and not any(token.casefold() in blob for token in include_tokens):
            continue
        if candidate not in feed_urls:
            feed_urls.append(candidate)

    return _collect_discovered_rss_feeds(source, config, target_date, feed_urls[: int(source.get("max_feeds", 8))], include_old)


def _collect_rss_list(source: dict[str, Any], config: dict[str, Any], target_date: date, include_old: bool = False) -> list[dict[str, Any]]:
    feed_urls = list(source.get("feed_urls") or [])
    if not feed_urls:
        from bs4 import BeautifulSoup

        response, final_url, note = _get_with_http_fallback(source["url"], source, timeout=_source_timeout(source))
        source["_final_url_used"] = final_url
        source["_fetch_note"] = note
        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.find_all("a"):
            href = anchor.get("href") or ""
            candidate = urljoin(final_url, href)
            if re.search(r"(rss|xml|feed)", candidate, re.I):
                feed_urls.append(candidate)
    return _collect_discovered_rss_feeds(source, config, target_date, feed_urls[: int(source.get("max_feeds", 8))], include_old)


def _collect_discovered_rss_feeds(
    source: dict[str, Any],
    config: dict[str, Any],
    target_date: date,
    feed_urls: list[str],
    include_old: bool,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for feed_url in feed_urls:
        feed_source = dict(source)
        feed_source["url"] = feed_url
        feed_source["method"] = "rss"
        try:
            feed_items = _fetch_rss_source(feed_source, config, target_date, include_old=include_old)
        except Exception as exc:
            logging.warning("Discovered RSS failed [%s - %s]: %s", source.get("name"), feed_url, exc)
            continue
        if _latest_item_date(feed_items) and (target_date - _latest_item_date(feed_items)).days > int(source.get("stale_days", 2)):
            logging.warning("Discovered RSS stale [%s - %s]", source.get("name"), feed_url)
            continue
        items.extend(feed_items)
    return items


def _fetch_rss_source(source: dict[str, Any], config: dict[str, Any], target_date: date, include_old: bool = False) -> list[dict[str, Any]]:
    headers = {"User-Agent": config["user_agent"]}
    response, final_url, note = _get_with_http_fallback(source["url"], source, timeout=_source_timeout(source), headers=headers)
    source["_final_url_used"] = final_url
    source["_fetch_note"] = note
    feed = feedparser.parse(response.content)
    items: list[dict[str, Any]] = []
    category = source["category"]

    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            continue
        if not _is_probable_news_title(title) or _is_noise_url(link):
            continue
        if is_paid_domain(link, config["paid_domains"]):
            continue

        published, original_pubdate, date_fields = _entry_published_datetime(entry, link, title, entry.get("summary") or "", config, source)
        _record_date_fields(source, date_fields)

        summary = (entry.get("summary") or "").strip()
        item_source = _entry_source_override(source, entry, title=title, link=link)
        source_timezone = _source_timezone(source, config)
        source_date, target_date_value = item_dates(published, source_timezone, config["timezone"])
        built_item = _build_item(
            title=title,
            url=link,
            source=item_source,
            category=category,
            published_date=target_date_value,
            source_timezone_date=source_date,
            published_at=published.isoformat() if published else None,
            original_pubdate=original_pubdate,
            date_parse_fields=sorted(date_fields),
            summary=summary,
            config=config,
        )
        enrich_source_metadata(built_item, entry_source_title=item_source.get("_entry_source_title"))
        items.append(built_item)
    return items


def _entry_source_override(source: dict[str, Any], entry: Any, title: str = "", link: str = "") -> dict[str, Any]:
    if source.get("method") not in {"google_news_rss", "bing_news_rss"}:
        return source
    entry_source = entry.get("source") or {}
    source_title = ""
    if isinstance(entry_source, dict):
        source_title = entry_source.get("title") or ""
    if not source_title:
        source_title = extract_original_source(title=title, current_source=source.get("name", ""), url=link)
    item_source = dict(source)
    item_source["name"] = source_title
    item_source["source_group"] = source.get("source_group")
    item_source["topic_group"] = source.get("topic_group") or source.get("source_group")
    item_source["_entry_source_title"] = source_title
    return item_source


def _collect_rss_index(source: dict[str, Any], config: dict[str, Any], target_date: date, include_old: bool = False) -> list[dict[str, Any]]:
    response, final_url, note = _get_with_http_fallback(source["url"], source, timeout=_source_timeout(source))
    source["_final_url_used"] = final_url
    source["_fetch_note"] = note

    from bs4 import BeautifulSoup

    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")
    keywords = tuple(source.get("rss_keywords") or RSS_INDEX_KEYWORDS)
    feed_urls: list[str] = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href") or ""
        text = anchor.get_text(" ", strip=True)
        candidate = urljoin(final_url, href)
        if not any(token in f"{text} {candidate}" for token in keywords):
            continue
        if not re.search(r"(rss|xml|feed)", candidate, re.I):
            continue
        if candidate not in feed_urls:
            feed_urls.append(candidate)

    items: list[dict[str, Any]] = []
    for feed_url in feed_urls[:6]:
        feed_source = dict(source)
        feed_source["url"] = feed_url
        try:
            items.extend(_fetch_rss_source(feed_source, config, target_date, include_old=include_old))
        except Exception as exc:
            logging.warning("RSS index feed failed [%s - %s]: %s", source.get("name"), feed_url, exc)

    if not items:
        for fallback_url in source.get("fallback_urls", []):
            try:
                items.extend(collect_html_source(source, target_date, lookback_days=365 if include_old else 0, config=config, url_override=fallback_url))
            except Exception as exc:
                logging.warning("RSS index HTML fallback failed [%s - %s]: %s", source.get("name"), fallback_url, exc)
    return items


def _collect_newsapi(config: dict[str, Any], target_date: date) -> list[dict[str, Any]]:
    api_config = config.get("apis", {}).get("newsapi", {})
    api_key = config.get("newsapi_key")
    if not api_config.get("enabled") or not api_key:
        return []

    queries = config.get("newsapi_queries") or [
        ("domestic", '(Pakistan OR Islamabad OR "State Bank of Pakistan" OR SBP OR SECP OR budget OR inflation OR exports)'),
        ("international", '(trade OR tariff OR commodities OR "Federal Reserve" OR shipping OR geopolitics OR IMF OR World Bank)'),
    ]
    items: list[dict[str, Any]] = []
    for category, query in queries:
        params = {
            "q": query,
            "from": target_date.isoformat(),
            "to": target_date.isoformat(),
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": api_config.get("page_size", 20),
            "apiKey": api_key,
        }
        try:
            response = requests.get(
                api_config["endpoint"],
                params=params,
                headers={"User-Agent": config["user_agent"]},
                timeout=config["http_timeout"],
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logging.warning("NewsAPI request failed for %s: %s", category, exc)
            continue

        for article in payload.get("articles", []):
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url or not _is_probable_news_title(title) or _is_noise_url(url) or is_paid_domain(url, config["paid_domains"]):
                continue
            published = parse_datetime(article.get("publishedAt"), config["timezone"])
            if published and published.date() != target_date:
                continue
            source_name = article.get("source", {}).get("name") or "NewsAPI"
            source = {"name": source_name, "source_weight": 6.0, "method": "api", "category": category, "timezone": _default_source_timezone(category, source_name)}
            source_timezone = _source_timezone(source, config)
            source_date, target_date_value = item_dates(published, source_timezone, config["timezone"])
            items.append(
                enrich_source_metadata(_build_item(
                    title=title,
                    url=url,
                    source=source,
                    category=category,
                    published_date=target_date_value,
                    source_timezone_date=source_date,
                    published_at=published.isoformat() if published else article.get("publishedAt"),
                    summary=(article.get("description") or "").strip(),
                    date_parse_fields=["publishedAt"] if published else [],
                    config=config,
                ))
            )
    return items


def _collect_gdelt(config: dict[str, Any], target_date: date) -> list[dict[str, Any]]:
    api_config = config.get("apis", {}).get("gdelt", {})
    if not api_config.get("enabled"):
        return []

    queries = config.get("gdelt_queries") or [
        ("domestic", 'Pakistan OR Islamabad OR "State Bank of Pakistan" OR SBP OR SECP OR inflation OR exports OR budget'),
        ("international", 'trade OR tariff OR commodities OR "Federal Reserve" OR shipping OR geopolitics OR IMF OR "World Bank"'),
    ]
    items: list[dict[str, Any]] = []
    for category, query in queries:
        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": api_config.get("max_records", 20),
            "format": "json",
            "sort": "DateDesc",
            "startdatetime": f"{target_date.strftime('%Y%m%d')}000000",
            "enddatetime": f"{target_date.strftime('%Y%m%d')}235959",
        }
        try:
            response = requests.get(
                api_config["endpoint"],
                params=params,
                headers={"User-Agent": config["user_agent"]},
                timeout=config["http_timeout"],
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logging.warning("GDELT request failed for %s: %s", category, exc)
            continue

        for article in payload.get("articles", []):
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url or not _is_probable_news_title(title) or _is_noise_url(url) or is_paid_domain(url, config["paid_domains"]):
                continue
            published = parse_datetime(article.get("seendate"), config["timezone"])
            if published and published.date() != target_date:
                continue
            source = {"name": article.get("domain", "GDELT"), "source_weight": 5.0, "method": "api", "category": category, "timezone": _default_source_timezone(category, article.get("domain", "GDELT"))}
            source_timezone = _source_timezone(source, config)
            source_date, target_date_value = item_dates(published, source_timezone, config["timezone"])
            items.append(
                enrich_source_metadata(_build_item(
                    title=title,
                    url=url,
                    source=source,
                    category=category,
                    published_date=target_date_value,
                    source_timezone_date=source_date,
                    published_at=published.isoformat() if published else article.get("seendate"),
                    summary="",
                    date_parse_fields=["seendate"] if published else [],
                    config=config,
                ))
            )
    return items


def _build_item(
    title: str,
    url: str,
    source: dict[str, Any],
    category: str,
    published_date: date | None,
    source_timezone_date: date | None,
    config: dict[str, Any],
    summary: str = "",
    published_at: str | None = None,
    original_pubdate: str | None = None,
    date_parse_fields: list[str] | None = None,
) -> dict[str, Any]:
    item = {
        "title": title,
        "raw_title": title,
        "original_url": url,
        "normalized_url": normalize_url(url),
        "url": normalize_url(url),
        "final_url_used": normalize_url(url),
        "link_status": "unchecked",
        "link_note": None,
        "source": source["name"],
        "original_source": source["name"],
        "source_weight": float(source.get("source_weight", 0)),
        "section": category,
        "category": category,
        "method": source.get("method") or source.get("type"),
        "source_group": source.get("source_group"),
        "topic_group": source.get("topic_group"),
        "source_type": source.get("source_type", "core"),
        "source_timezone": _source_timezone(source, config),
        "published_date": published_date.isoformat() if published_date else None,
        "source_timezone_date": source_timezone_date.isoformat() if source_timezone_date else None,
        "target_timezone_date": _datetime_date_in_timezone(published_at, config.get("timezone", "Asia/Karachi")),
        "published_at": published_at or (datetime.combine(published_date, datetime.min.time()).isoformat() if published_date else None),
        "original_pubdate": original_pubdate,
        "date_parse_fields": date_parse_fields or [],
        "possible_republished_old_story": possible_republished_old_story(url, title, summary, published_date),
        "summary": summary,
        "raw_description": summary,
        "raw_snippet": summary,
        "meta_description": "",
        "tags": _merge_tags(source.get("tags", []), derive_tags(f"{title} {summary}", config) if config else []),
    }
    return enrich_source_metadata(item)


def _iter_sources(config: dict[str, Any]) -> list[dict[str, Any]]:
    sources = config.get("sources", [])
    if isinstance(sources, list):
        return [source for source in sources if source.get("enabled", True)]

    flattened: list[dict[str, Any]] = []
    for category, category_sources in sources.items():
        for source in category_sources:
            source = dict(source)
            source["category"] = source.get("category", category)
            source["method"] = source.get("method") or source.get("type", "rss")
            if source.get("enabled", True):
                flattened.append(source)
    return flattened


def _clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip(" -_:：|[]【】\t\r\n")


def _is_probable_news_title(title: str) -> bool:
    if not title:
        return False
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", title)
    english_chars = re.findall(r"[A-Za-z]", title)
    if chinese_chars and len(chinese_chars) < 8:
        return False
    if not chinese_chars and len(english_chars) < 15:
        return False
    if title in NAV_TITLES:
        return False
    if any(keyword.casefold() in title.casefold() for keyword in NOISE_TITLE_KEYWORDS):
        return False
    if len(title) <= 10 and any(word in title for word in NAV_TITLES):
        return False
    if re.fullmatch(r"[\d\s./年月日:-]+", title):
        return False
    return True


def _is_noise_url(url: str) -> bool:
    lowered = url.casefold()
    return any(
        token in lowered
        for token in (
            "/video/",
            "/videos/",
            "/photo/",
            "/photos/",
            "/live-tv",
            "/newsletter",
            "/podcast",
            "/podcasts/",
            "tv.cctv.com",
        )
    )


def _is_probable_detail_url(url: str, source_url: str, title: str) -> bool:
    parsed = urlparse(url)
    source_parsed = urlparse(source_url)
    path = parsed.path.rstrip("/")
    source_path = source_parsed.path.rstrip("/")
    if not path or path == source_path:
        return False
    has_long_numeric_segment = bool(re.search(r"/\d{8,}/", path))
    if path.endswith(("/index", "/index.htm", "/index.html")) and not has_long_numeric_segment:
        return False
    if any(noise.casefold() in url.casefold() or noise.casefold() in title.casefold() for noise in ("zt", "zhuanti", "special", "专题")):
        return False
    basename = path.rsplit("/", 1)[-1]
    has_detail_shape = (
        basename.endswith((".html", ".htm", ".shtml"))
        and (re.search(r"\d{4,}", basename) or any(hint in path.casefold() for hint in DETAIL_URL_HINTS))
    )
    has_date_path = re.search(r"/20\d{2}[-_/]?\d{0,2}[-_/]?\d{0,2}/", path)
    return bool(has_detail_shape or has_date_path)


def _extract_article_publication_date(
    url: str,
    source: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> tuple[date | None, str | None, str | None]:
    """Read publication metadata from an article page, never infer from its URL."""
    from bs4 import BeautifulSoup

    runtime_config = config or {}
    try:
        response, _final_url, _note = _get_with_http_fallback(
            url, source, timeout=int(source.get("article_date_timeout", min(_source_timeout(source), 5)))
        )
        response.encoding = response.apparent_encoding or response.encoding
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        logging.debug("Article date lookup failed [%s]: %s", url, exc)
        return None, None, None

    candidates: list[tuple[str, str]] = []
    for key in ("article:published_time", "article:modified_time", "og:published_time", "datePublished", "dateCreated", "pubdate", "publishdate", "timestamp"):
        for tag in soup.find_all("meta", attrs={"property": key}) + soup.find_all("meta", attrs={"name": key}):
            value = tag.get("content") or tag.get("value")
            if value:
                candidates.append((key, value.strip()))
    for tag in soup.find_all("time"):
        value = tag.get("datetime") or tag.get_text(" ", strip=True)
        if value:
            candidates.append(("time_datetime", value.strip()))
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            continue
        stack = payload if isinstance(payload, list) else [payload]
        while stack:
            node = stack.pop(0)
            if isinstance(node, dict):
                for key in ("datePublished", "dateCreated"):
                    value = node.get(key)
                    if isinstance(value, str) and value.strip():
                        candidates.append((key, value.strip()))
                graph = node.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)

    timezone_name = source.get("timezone") or runtime_config.get("timezone", "Asia/Karachi")
    for field, value in candidates:
        parsed = parse_datetime(value, timezone_name)
        if parsed:
            return parsed.astimezone(ZoneInfo(timezone_name)).date(), parsed.isoformat(), field
        parsed_date = parse_date_from_text(value)
        if parsed_date:
            return parsed_date, None, field
    return None, None, None


def _extract_nearby_date(anchor: Any, base_url: str = "") -> date | None:
    # Prefer explicit machine-readable dates and tightly scoped listing cards.
    card = anchor.find_parent(["article", "li", "tr"])
    time_tag = card.find("time") if card else None
    if time_tag is None:
        time_tag = anchor.find("time")
    time_value = (time_tag.get("datetime") or time_tag.get_text(" ", strip=True)) if time_tag else ""
    parent = anchor.parent
    text_candidates = [
        time_value,
        card.get_text(" ", strip=True) if card else "",
        parent.get_text(" ", strip=True) if parent else "",
        anchor.get_text(" ", strip=True),
    ]
    for text in text_candidates:
        extracted = _parse_date_from_text(text)
        if extracted:
            return extracted
    return None


def _parse_date_from_text(text: str) -> date | None:
    return parse_date_from_text(text)


def _entry_published_datetime(
    entry: Any,
    link: str,
    title: str,
    summary: str,
    config: dict[str, Any],
    source: dict[str, Any],
) -> tuple[datetime | None, str | None, set[str]]:
    return parse_entry_published_datetime(entry, link, title, summary, _source_timezone(source, config))


def _source_timezone(source: dict[str, Any], config: dict[str, Any]) -> str:
    return source.get("timezone") or _default_source_timezone(source.get("category"), source.get("name") or source.get("source_group"))


def _default_source_timezone(category: str | None, source_name: str | None = None) -> str:
    # Source-level timezone always takes precedence. These defaults suit the
    # Pakistan-focused pipeline while keeping major international feeds UTC.
    if category == "domestic":
        return "Asia/Karachi"
    source_blob = (source_name or "").casefold()
    if any(token in source_blob for token in ("bbc", "reuters", "world bank", "imf", "eia", "ft", "financial times")):
        return "UTC"
    return "UTC"


def _item_filter_date(published: datetime | None, source: dict[str, Any], config: dict[str, Any]) -> date | None:
    if not published:
        return None
    _source_date, target_date_value = item_dates(published, _source_timezone(source, config), config["timezone"])
    return target_date_value


def _datetime_date_in_timezone(value: str | None, timezone_name: str) -> str | None:
    parsed = parse_datetime(value, timezone_name)
    if not parsed:
        return None
    return parsed.date().isoformat()


def _record_date_fields(source: dict[str, Any], fields: set[str]) -> None:
    existing = set(source.get("_date_fields_detected", []))
    existing.update(fields)
    source["_date_fields_detected"] = sorted(existing)


def _latest_item_date(items: list[dict[str, Any]]) -> date | None:
    latest: date | None = None
    for item in items:
        published_date = item.get("published_date")
        if not published_date:
            continue
        try:
            parsed = date.fromisoformat(published_date)
        except ValueError:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    return latest


def _get_with_http_fallback(
    url: str,
    source: dict[str, Any],
    timeout: int,
    headers: dict[str, str] | None = None,
):
    if headers is None:
        source = dict(source)
        source["user_agent"] = HTML_USER_AGENT
    return get_with_http_fallback(url, source, timeout, headers=headers)


def _source_timeout(source: dict[str, Any]) -> int:
    if "timeout" in source:
        return int(source["timeout"])

    method = source.get("method", "")
    source_type = source.get("source_type", "core")
    if method == "google_news_rss":
        return 6 if source_type == "core" else 5
    if method == "bing_news_rss":
        return 5 if source_type == "bing_fallback" else 6
    if source_type == "optional":
        if method == "html":
            return 4
        if method in {"html_or_rss", "html_or_rss_index", "rss_or_html"}:
            return 5
        return 6
    if method == "html":
        return 6
    return 10


def _optional_source_priority(source: dict[str, Any]) -> tuple[int, float, str]:
    method = source.get("method", "")
    if method in {"rss", "rss_index", "rss_index_or_rss", "opml_discovery", "rss_list", "google_news_rss", "bing_news_rss"}:
        method_priority = 0
    elif method in {"rss_or_html", "html_or_rss", "html_or_rss_index"}:
        method_priority = 1
    else:
        method_priority = 2
    return (
        method_priority,
        -float(source.get("source_weight", 0)),
        source.get("name", ""),
    )


def _should_skip_optional_source(
    source: dict[str, Any],
    items: list[dict[str, Any]],
    category_counts: dict[str, int],
    target_date: date,
) -> bool:
    category = source.get("category")
    method = source.get("method", "")
    target_date_count = _category_target_date_count(items, target_date, category)
    if category == "domestic":
        if target_date_count >= 10:
            return True
        if method == "html" and target_date_count >= 8:
            return True
        return False

    if category_counts.get(category, 0) >= 10:
        return True
    if target_date_count >= 10:
        return True
    if method == "html" and target_date_count >= 8:
        return True
    return False


def _category_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        category = item.get("category") or item.get("section")
        counts[category] = counts.get(category, 0) + 1
    return counts


def _domestic_target_date_count(items: list[dict[str, Any]], target_date: date) -> int:
    return _category_target_date_count(items, target_date, "domestic")


def _category_target_date_count(items: list[dict[str, Any]], target_date: date, category: str) -> int:
    target = target_date.isoformat()
    return sum(1 for item in items if item.get("section") == category and item.get("published_date") == target)


def _source_group_target_date_count(items: list[dict[str, Any]], target_date: date, source_group: str) -> int:
    target = target_date.isoformat()
    return sum(
        1
        for item in items
        if item.get("source_group") == source_group and item.get("published_date") == target
    )


def _has_domestic_economic_keyword(item: dict[str, Any]) -> bool:
    blob = f"{item.get('title', '')} {item.get('summary', '')} {' '.join(item.get('tags', []))}".casefold()
    return any(keyword.casefold() in blob for keyword in DOMESTIC_ECONOMIC_KEYWORDS)


def _has_international_economic_keyword(item: dict[str, Any]) -> bool:
    blob = f"{item.get('title', '')} {item.get('summary', '')} {' '.join(item.get('tags', []))}".casefold()
    return any(keyword.casefold() in blob for keyword in INTERNATIONAL_ECONOMIC_KEYWORDS)


def _has_economic_keyword(item: dict[str, Any], category: str) -> bool:
    if category == "international":
        return _has_international_economic_keyword(item)
    return _has_domestic_economic_keyword(item)


def _probe_bucket_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        bucket = item.get("topic_group") or item.get("source_group") or item.get("source") or "unknown"
        counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items(), key=lambda entry: entry[1], reverse=True))


def _probe_primary_source_quality(items: list[dict[str, Any]]) -> str | None:
    for item in items:
        if item.get("source_quality"):
            return item.get("source_quality")
    return None


def _merge_note(existing: str | None, note: str) -> str:
    if not existing:
        return note
    if note in existing.split(","):
        return existing
    return f"{existing},{note}"


def _merge_tags(*tag_lists: list[str]) -> list[str]:
    merged: list[str] = []
    for tags in tag_lists:
        for tag in tags:
            if tag and tag not in merged:
                merged.append(tag)
    return merged[:8]
