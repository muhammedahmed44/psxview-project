from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Any

from .pipeline_config import get_config_section
from .source_quality import is_low_quality_title


ROUNDUP_PATTERNS = (
    "things you missed",
    "what you missed",
    "news you missed",
    "biggest news you missed",
    "weekend rundown",
    "morning briefing",
    "daily briefing",
    "evening briefing",
    "live updates",
    "live blog",
    "recap",
    "roundup",
    "newsletter",
    "photos",
    "watch live",
    "opinion",
    "analysis",
    "explainer",
    "in pictures",
    "quiz",
    "podcast",
    "here's what to know",
    "what to know",
    "here's who",
    "a history of",
    "timeline of",
    "background",
    "how .* works",
    "everything you need to know",
)
CHINESE_ROUNDUP_PATTERNS = (
    "一图读懂",
    "图解",
    "海报",
    "组图",
    "直播",
    "滚动",
    "综述",
    "述评",
    "评论",
    "快评",
    "观察",
    "特写",
    "探访",
    "走进",
    "文化中国行",
    "薪火相传",
    "看见",
    "浪漫",
    "想象空间",
    "带你看",
    "Vlog",
    "微视频",
)
SOFT_NEWS_PATTERNS = (
    "青少年比赛",
    "选拔赛",
    "大赛举行",
    "文化活动",
    "文旅",
    "非遗",
    "展览",
    "旅游",
    "走进",
    "探访",
    "故事",
    "暖新闻",
    "人物",
    "生活方式",
    "娱乐",
    "体育花边",
    "科普活动",
    "校园活动",
    "文艺演出",
    "自然保护区",
    "野生动物",
    "生机勃勃",
    "开园",
    "以虫治虫",
    "生态根基",
    "faith and family",
    "family",
    "comedian",
    "singer",
    "celebrity",
    "face-lift",
    "approval ratings",
    "实时行情",
    "走势图",
    "财报",
    "股票股价",
    "obesity drugs",
    "world cup",
    "soccer",
    "sports",
    "nba",
    "ufc",
)
ECONOMIC_QUALITY_KEYWORDS = (
    "央行", "人民银行", "社融", "金融统计", "人民币", "外汇", "银行", "信贷", "财政",
    "商务部", "海关", "关税", "贸易", "进出口", "出口管制", "制裁", "供应链", "外资",
    "期货", "大宗商品", "商品", "农产品", "粮食", "玉米", "大豆", "棕榈油", "棉花",
    "有色金属", "铜", "铝", "锌", "镍", "铁矿石", "钢铁", "原油", "天然气", "能源",
    "航运", "油轮", "港口", "cpi", "ppi", "fed", "federal reserve", "inflation", "rates",
    "tariff", "trade", "sanctions", "export controls", "oil", "natural gas", "shipping",
    "tanker", "ipo", "nasdaq", "nyse", "market debut", "shares", "valuation", "market cap",
)
GENERAL_NEWS_KEYWORDS = (
    "通报",
    "会议",
    "召开",
    "举行",
    "发展",
    "建设",
    "增长",
    "上线",
    "创新",
    "首个",
    "首次",
    "新规",
    "规范",
    "治理",
    "保护",
    "调整",
    "数据",
    "报告",
    "回应",
    "部署",
    "推进",
    "启动",
    "完成",
    "突破",
)
HARD_NEWS_KEYWORDS = (
    "发布",
    "出台",
    "修订",
    "批准",
    "调查",
    "制裁",
    "禁令",
    "清单",
    "关税",
    "会谈",
    "访问",
    "签署",
    "声明",
    "预警",
    "灾害",
    "事故",
    "冲突",
    "袭击",
    "战争",
    "停火",
    "央行",
    "利率",
    "通胀",
    "金融统计",
    "贸易",
    "进出口",
    "海关",
    "外汇",
    "人民币",
    "监管",
    "AI监管",
    "芯片",
    "半导体",
    "产业政策",
    "重大突破",
    "国家级",
    "国务院",
    "商务部",
    "发改委",
    "人民银行",
    "海关总署",
    "网信办",
    "工信部",
    "财政部",
    "announces",
    "approves",
    "sanctions",
    "tariff",
    "trade",
    "ceasefire",
    "strike",
    "attack",
    "war",
    "conflict",
    "Fed",
    "inflation",
    "rates",
    "economy",
    "market",
    "export controls",
    "visa",
    "immigration",
    "policy",
    "regulation",
    "investigation",
    "ban",
    "warning",
    "disaster",
    "crash",
    "summit",
    "agreement",
    "military",
    "central bank",
    "IPO",
    "initial public offering",
    "public offering",
    "listing",
    "listed",
    "market debut",
    "Nasdaq debut",
    "NYSE debut",
    "shares",
    "stock debut",
    "priced",
    "valuation",
    "raises",
    "record IPO",
    "largest IPO",
    "oversubscribed",
    "order book",
    "market cap",
    "trading debut",
    "surges",
    "falls in debut",
    "ticker",
    "chipmaker",
    "semiconductor",
    "AI company",
    "aerospace",
    "space company",
    "satellite",
    "上市",
    "挂牌",
    "纳斯达克",
    "纽交所",
    "首日交易",
    "发行价",
    "募资",
    "估值",
    "市值",
    "股票",
    "股价",
    "科技股",
    "航天",
    "卫星",
    "星链",
    "马斯克",
    "英伟达",
    "特斯拉",
    "苹果",
    "微软",
    "谷歌",
    "亚马逊",
    "半导体",
)
LIVE_PAGE_PATTERNS = ("live updates", "live blog")
EXPLAINER_BACKGROUND_PATTERNS = (
    "a history of",
    "what to know",
    "timeline of",
    "explainer",
    "analysis",
    "background",
    "how ",
    "everything you need to know",
    "history of",
)
POLITICAL_SANCTIONS_PERSON_PATTERNS = (
    "priest",
    "confessor",
    "religious",
    "bishop",
    "politician",
    "lawmaker",
    "official",
    "figure",
    "person",
)
SANCTIONS_ECONOMIC_LINK_PATTERNS = (
    "oil",
    "energy",
    "trade",
    "tariff",
    "export controls",
    "bank",
    "banking",
    "finance",
    "financial",
    "market",
    "company",
    "shipping",
    "tanker",
    "port",
    "commodity",
    "commodities",
    "dollar",
    "supply",
)
REASON_LABELS = {
    "关税": "trade_policy",
    "贸易": "trade_policy",
    "进出口": "trade_policy",
    "海关": "customs_trade",
    "预警": "public_safety_warning",
    "灾害": "public_safety_warning",
    "事故": "public_safety_event",
    "央行": "central_bank",
    "人民银行": "central_bank",
    "金融统计": "financial_data",
    "美联储": "fed_policy",
    "Fed": "fed_policy",
    "芯片": "tech_industry",
    "半导体": "tech_industry",
    "AI监管": "AI_regulation",
    "网信办": "AI_regulation",
    "制裁": "sanctions",
    "清单": "sanctions",
    "war": "geopolitics",
    "conflict": "geopolitics",
    "ceasefire": "geopolitics",
    "strike": "geopolitics",
    "tariff": "trade_policy",
    "trade": "trade_policy",
    "visa": "policy",
    "policy": "policy",
    "IPO": "business_market_hard_news",
    "initial public offering": "business_market_hard_news",
    "market debut": "business_market_hard_news",
    "Nasdaq debut": "business_market_hard_news",
    "NYSE debut": "business_market_hard_news",
    "trading debut": "business_market_hard_news",
}


PAKISTAN_ECONOMIC_KEYWORDS = (
    "state bank of pakistan", "sbp", "ministry of finance",
    "finance division", "federal board of revenue", "fbr",
    "pakistan bureau of statistics", "pbs", "pakistan stock exchange", "psx",
    "kse-100", "kse 100", "pakistan rupee", "pakistani rupee", "pkr",
    "rupee", "current account", "trade deficit", "fiscal deficit",
    "foreign exchange reserves", "foreign reserves", "remittances",
    "tax collection", "tax revenue", "policy rate", "monetary policy",
    "large-scale manufacturing", "lsm", "consumer price index", "sensitive price indicator",
    "circular debt", "petroleum levy", "electricity tariff", "gas tariff",
    "power tariff", "textile exports", "rice exports", "cotton", "fertiliser",
    "fertilizer", "wheat support price", "imf programme", "imf program",
    "imf review", "imf tranche", "sovereign debt", "eurobond",
    "اسٹیٹ بینک", "مہنگائی", "شرح سود", "روپیہ", "بجٹ", "ٹیکس",
    "برآمدات", "درآمدات", "ترسیلات زر", "زرمبادلہ", "کرنٹ اکاؤنٹ",
    "تجارتی خسارہ", "آئی ایم ایف", "توانائی", "پیٹرولیم لیوی",
)
PAKISTAN_EXTERNAL_IMPACT_KEYWORDS = (
    "brent crude", "crude oil", "oil prices", "lng", "liquefied natural gas",
    "gulf shipping", "strait of hormuz", "red sea", "freight rates",
    "shipping disruption", "global food prices", "commodity prices",
    "federal reserve", "fed rate", "us treasury yields", "dollar index",
    "global interest rates", "oil import bill", "energy imports",
)

_QUALITY_KEYWORDS = get_config_section("keywords", {}).get("quality", {})
_QUALITY_THRESHOLDS = get_config_section("thresholds", {}).get("quality", {})
DOMESTIC_ANCHOR_KEYWORDS = tuple(dict.fromkeys(
    tuple(_QUALITY_KEYWORDS.get("domestic_anchor_keywords", ()))
    + PAKISTAN_ECONOMIC_KEYWORDS
    + ("pakistan", "islamabad", "karachi", "lahore", "pakistani")
))
ROUNDUP_PATTERNS = tuple(_QUALITY_KEYWORDS.get("roundup_patterns", ROUNDUP_PATTERNS))
CHINESE_ROUNDUP_PATTERNS = tuple(_QUALITY_KEYWORDS.get("chinese_roundup_patterns", CHINESE_ROUNDUP_PATTERNS))
SOFT_NEWS_PATTERNS = tuple(_QUALITY_KEYWORDS.get("soft_news_patterns", SOFT_NEWS_PATTERNS))
ECONOMIC_QUALITY_KEYWORDS = tuple(_QUALITY_KEYWORDS.get("economic_quality_keywords", ECONOMIC_QUALITY_KEYWORDS))
GENERAL_NEWS_KEYWORDS = tuple(_QUALITY_KEYWORDS.get("general_news_keywords", GENERAL_NEWS_KEYWORDS))
HARD_NEWS_KEYWORDS = tuple(_QUALITY_KEYWORDS.get("hard_news_keywords", HARD_NEWS_KEYWORDS))
LIVE_PAGE_PATTERNS = tuple(_QUALITY_KEYWORDS.get("live_page_patterns", LIVE_PAGE_PATTERNS))
EXPLAINER_BACKGROUND_PATTERNS = tuple(_QUALITY_KEYWORDS.get("explainer_background_patterns", EXPLAINER_BACKGROUND_PATTERNS))
POLITICAL_SANCTIONS_PERSON_PATTERNS = tuple(_QUALITY_KEYWORDS.get("political_sanctions_person_patterns", POLITICAL_SANCTIONS_PERSON_PATTERNS))
SANCTIONS_ECONOMIC_LINK_PATTERNS = tuple(_QUALITY_KEYWORDS.get("sanctions_economic_link_patterns", SANCTIONS_ECONOMIC_LINK_PATTERNS))
REASON_LABELS = {str(key): str(value) for key, value in _QUALITY_KEYWORDS.get("reason_labels", REASON_LABELS).items()}
# Add Pakistan-focused terms after configuration overrides, so both defaults and
# configured keyword lists retain the Pakistan coverage.
ECONOMIC_QUALITY_KEYWORDS = tuple(dict.fromkeys(ECONOMIC_QUALITY_KEYWORDS + PAKISTAN_ECONOMIC_KEYWORDS))
HARD_NEWS_KEYWORDS = tuple(dict.fromkeys(HARD_NEWS_KEYWORDS + PAKISTAN_ECONOMIC_KEYWORDS))

REASON_LABELS.update({
    "state bank of pakistan": "pakistan_monetary_policy",
    "sbp": "pakistan_monetary_policy",
    "policy rate": "pakistan_monetary_policy",
    "monetary policy": "pakistan_monetary_policy",
    "consumer price index": "pakistan_inflation_data",
    "sensitive price indicator": "pakistan_inflation_data",
    "fbr": "pakistan_fiscal_policy",
    "tax collection": "pakistan_fiscal_policy",
    "foreign exchange reserves": "pakistan_external_financing",
    "remittances": "pakistan_external_flows",
    "imf tranche": "pakistan_external_financing",
})


def filter_quality_items(
    items: list[dict[str, Any]],
    target_date: date,
    min_quality_score: float = 2.0,
    config: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    retained, stats, _excluded = filter_quality_items_with_report(items, target_date, min_quality_score, config)
    return retained, stats


def filter_quality_items_with_report(
    items: list[dict[str, Any]],
    target_date: date,
    min_quality_score: float = 2.0,
    config: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    stats: Counter[str] = Counter()
    retained: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    min_quality_score = float((config or {}).get("thresholds", {}).get("quality", {}).get("min_quality_score", _QUALITY_THRESHOLDS.get("min_quality_score", min_quality_score)))
    watchlist_keywords = tuple((config or {}).get("watchlist_keywords", ()))
    allow_low_quality_sources = bool((config or {}).get("allow_low_quality_sources"))

    for item in items:
        title_blob = f"{item.get('title', '')} {item.get('summary', '')} {item.get('url', '')}"
        watchlist_hits = _matched_keywords(title_blob, watchlist_keywords)
        if watchlist_hits:
            stats["watchlist_candidates"] += 1
            item["watchlist_hits"] = watchlist_hits

        published_date = _parse_item_date(item)
        section = item.get("section", "unknown")
        if published_date is None:
            stats["missing_date"] += 1
            stats[f"{section}_missing_date"] += 1
            _record_exclusion(excluded, item, "missing_date", watchlist_hits, target_date)
            continue
        if published_date > target_date:
            stats["future_date"] += 1
            stats[f"{section}_future_date"] += 1
            _record_exclusion(excluded, item, "future_date", watchlist_hits, target_date)
            continue
        if published_date < target_date:
            stats["non_target_date"] += 1
            stats[f"{section}_non_target_date"] += 1
            _record_exclusion(excluded, item, "non_target_date_due_timezone" if watchlist_hits else "non_target_date", watchlist_hits, target_date)
            continue
        if _is_foreign_story_in_domestic_slot(item):
            stats["foreign_story_in_domestic_slot"] += 1
            stats[f"{section}_foreign_story_in_domestic_slot"] += 1
            _record_exclusion(excluded, item, "foreign_story_in_domestic_slot", watchlist_hits, target_date)
            continue
        if item.get("possible_republished_old_story"):
            stats["possible_republished_old_story"] += 1
            stats[f"{section}_possible_republished_old_story"] += 1
            _record_exclusion(excluded, item, "possible_republished_old_story", watchlist_hits, target_date)
            continue
        source_quality = item.get("source_quality")
        if section == "international" and not allow_low_quality_sources:
            if source_quality == "broker_or_trading_platform":
                stats["excluded_broker_trading_platform"] += 1
                stats[f"{section}_excluded_broker_trading_platform"] += 1
                _record_exclusion(excluded, item, "broker_or_trading_platform", watchlist_hits, target_date)
                continue
            if source_quality in {"low_quality_finance", "content_farm"}:
                stats["excluded_low_quality_finance"] += 1
                stats[f"{section}_excluded_low_quality_finance"] += 1
                _record_exclusion(excluded, item, "low_quality_finance", watchlist_hits, target_date)
                continue
            if is_low_quality_title(item.get("title", ""), item.get("summary", ""), item.get("original_source", "")):
                stats["excluded_low_quality_finance"] += 1
                stats[f"{section}_excluded_low_quality_finance"] += 1
                _record_exclusion(excluded, item, "low_quality_title_pattern", watchlist_hits, target_date)
                continue
            if source_quality == "unknown":
                stats["excluded_unknown_source"] += 1
                stats[f"{section}_excluded_unknown_source"] += 1
                _record_exclusion(excluded, item, "unknown_source", watchlist_hits, target_date)
                continue

        hard_hits = _matched_keywords(title_blob, HARD_NEWS_KEYWORDS)
        live_allowed = bool(watchlist_hits) and _contains_any(title_blob, LIVE_PAGE_PATTERNS)
        is_roundup = _contains_any(title_blob, ROUNDUP_PATTERNS) or _contains_any(title_blob, CHINESE_ROUNDUP_PATTERNS)
        is_live_page = _contains_any(title_blob, LIVE_PAGE_PATTERNS)
        if _is_explainer_or_background(item):
            stats["explainer_history_background"] += 1
            stats[f"{section}_explainer_history_background"] += 1
            _record_exclusion(excluded, item, "explainer_history_background", watchlist_hits, target_date)
            continue
        if is_roundup and not (is_live_page and live_allowed):
            stats["roundup_newsletter"] += 1
            stats[f"{section}_roundup_newsletter"] += 1
            _record_exclusion(excluded, item, "roundup_or_live_page", watchlist_hits, target_date)
            continue
        if _is_general_political_sanctions(item):
            stats["general_political_sanctions"] += 1
            stats[f"{section}_general_political_sanctions"] += 1
            _record_exclusion(excluded, item, "general_political_sanctions", watchlist_hits, target_date)
            continue
        soft_hit = _contains_any(title_blob, SOFT_NEWS_PATTERNS)
        economic_hit = _contains_any(title_blob, ECONOMIC_QUALITY_KEYWORDS)
        if soft_hit and not (watchlist_hits or economic_hit):
            stats["soft_news"] += 1
            stats[f"{section}_soft_news"] += 1
            _record_exclusion(excluded, item, "soft_news", watchlist_hits, target_date)
            continue
        general_hits = _matched_keywords(title_blob, GENERAL_NEWS_KEYWORDS)

        quality_score = _quality_score(item, hard_hits, general_hits, watchlist_hits)
        if quality_score < min_quality_score:
            stats["soft_news"] += 1
            stats[f"{section}_soft_news"] += 1
            _record_exclusion(excluded, item, "quality_score_below_threshold", watchlist_hits, target_date)
            continue

        item["quality_score"] = round(quality_score, 3)
        item["watchlist_hits"] = watchlist_hits
        item["reason"] = _reason(hard_hits, general_hits, watchlist_hits, live_allowed)
        retained.append(item)

    stats["watchlist_excluded"] = len(excluded)
    return retained, dict(stats), excluded


def _parse_item_date(item: dict[str, Any]) -> date | None:
    value = item.get("published_date")
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _quality_score(item: dict[str, Any], hard_hits: list[str], general_hits: list[str], watchlist_hits: list[str]) -> float:
    title = item.get("title", "")
    score = 0.0
    score += min(6.0, len(hard_hits) * 1.5)
    score += min(2.0, len(general_hits) * 0.8)
    score += min(5.0, len(watchlist_hits) * 2.5)
    score += min(2.0, float(item.get("source_weight", 0)) / 5)
    if re.search(r"[。；：:]", title) or len(title) >= 18:
        score += 0.5
    return score


def _reason(hard_hits: list[str], general_hits: list[str], watchlist_hits: list[str], live_allowed: bool = False) -> str:
    labels = ["target_date"]
    if watchlist_hits:
        labels.append("watchlist")
    if hard_hits:
        labels.append("hard_news")
    elif general_hits:
        labels.append("general_news")
    for keyword in hard_hits:
        label = REASON_LABELS.get(keyword)
        if label and label not in labels:
            labels.append(label)
    if any(REASON_LABELS.get(keyword) == "business_market_hard_news" for keyword in hard_hits + watchlist_hits):
        if "business_market_hard_news" not in labels:
            labels.append("business_market_hard_news")
    if live_allowed and "live_page_allowed" not in labels:
        labels.append("live_page_allowed")
    return " + ".join(labels)


def _record_exclusion(
    excluded: list[dict[str, Any]],
    item: dict[str, Any],
    reason: str,
    watchlist_hits: list[str],
    target_date: date,
) -> None:
    if not watchlist_hits:
        return
    excluded.append(
        {
            "title": item.get("title"),
            "source": item.get("source"),
            "raw_pubdate": item.get("original_pubdate"),
            "parsed_date": item.get("published_date"),
            "source_timezone": item.get("source_timezone"),
            "source_timezone_date": item.get("source_timezone_date"),
            "shanghai_date": item.get("shanghai_date"),
            "status": "excluded",
            "exclusion_reason": reason,
            "target_date": target_date.isoformat(),
            "watchlist_hits": watchlist_hits,
            "url": item.get("url"),
        }
    )


def _is_foreign_story_in_domestic_slot(item: dict[str, Any]) -> bool:
    if item.get("section") != "domestic":
        return False
    if item.get("source_group") not in {"google_topic", "bing_topic"}:
        return False
    blob = f"{item.get('title', '')} {item.get('summary', '')} {item.get('raw_description', '')} {item.get('raw_snippet', '')}".casefold()
    return not _contains_any(blob, DOMESTIC_ANCHOR_KEYWORDS)


def _is_explainer_or_background(item: dict[str, Any]) -> bool:
    blob = f"{item.get('title', '')} {item.get('summary', '')}".casefold()
    if "how " in blob and "works" in blob:
        return True
    return any(pattern in blob for pattern in EXPLAINER_BACKGROUND_PATTERNS)


def _is_general_political_sanctions(item: dict[str, Any]) -> bool:
    if item.get("section") != "international":
        return False
    blob = f"{item.get('title', '')} {item.get('summary', '')}".casefold()
    if "sanction" not in blob and "制裁" not in blob:
        return False
    if any(pattern in blob for pattern in SANCTIONS_ECONOMIC_LINK_PATTERNS):
        return False
    return any(pattern in blob for pattern in POLITICAL_SANCTIONS_PERSON_PATTERNS) or "eu sanctions" in blob


def _matched_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    blob = text.casefold()
    matches: list[str] = []
    for keyword in keywords:
        lowered = keyword.casefold()
        if re.search(r"[a-z]", lowered):
            if re.search(rf"\b{re.escape(lowered)}\b", blob):
                matches.append(keyword)
        elif lowered in blob:
            matches.append(keyword)
    return matches


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    blob = text.casefold()
    return any(pattern.casefold() in blob for pattern in patterns)
