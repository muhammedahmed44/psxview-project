from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Any

from .pipeline_config import get_config_section
from .utils import parse_datetime, target_day_bounds


HEADLINE_KEYWORDS = (
    "习近平", "国务院", "中央", "外交", "会谈", "峰会", "战争", "冲突", "袭击", "制裁",
    "重大", "政策", "央行", "利率", "通胀", "G7", "G20", "WTO", "IMF", "Fed", "Federal Reserve",
    "美国", "中国", "欧盟", "市场", "暴跌", "暴涨", "灾害", "事故", "坠机", "安全",
    "AI", "人工智能", "芯片", "半导体", "新能源", "监管",
)
INDUSTRY_KEYWORDS = (
    "关税", "贸易", "进出口", "海关", "期货", "商品", "大宗商品", "农产品", "粮食", "玉米",
    "大豆", "棕榈油", "糖", "棉花", "有色金属", "铜", "铝", "锌", "镍", "铁矿石", "钢铁",
    "银行", "信用证", "贸易融资", "外汇", "人民币", "央行", "发改委", "商务部", "美联储",
    "美元", "航运", "能源", "石油", "天然气", "地缘政治",
)
TECH_KEYWORDS = (
    "科技", "AI", "人工智能", "大模型", "芯片", "半导体", "算力", "数据中心", "云计算",
    "机器人", "低空经济", "新能源", "智能汽车", "电动车", "自动驾驶", "航天", "卫星",
    "量子", "互联网", "平台经济", "国产替代", "科创", "数字经济",
    "ai company", "aerospace", "space company", "satellite",
)
FINANCE_KEYWORDS = (
    "财经", "宏观", "贸易", "进出口", "央行", "银行", "人民币", "外汇", "金融", "市场",
    "关税", "商务部", "发改委", "财政", "利率",
)
COMMODITY_KEYWORDS = (
    "期货", "商品", "大宗商品", "农产品", "有色金属", "能源", "航运", "石油", "天然气",
    "铜", "铝", "锌", "镍", "铁矿石", "钢铁", "玉米", "大豆", "棕榈油", "棉花", "糖",
)
US_ECONOMY_KEYWORDS = (
    "fed", "federal reserve", "inflation", "cpi", "ppi", "rates", "rate cut", "rate hike",
    "unemployment", "jobs", "payrolls", "dollar", "treasury yields", "gdp", "fiscal", "deficit",
    "tax", "budget", "consumer spending", "retail sales", "economy", "trade policy", "tariff",
)
GLOBAL_MACRO_FINANCE_KEYWORDS = (
    "ecb", "european central bank", "bank of england", "bank of japan", "imf", "world bank",
    "treasury", "treasury yields", "bond yields", "dollar", "euro", "yen", "currency",
    "central bank", "sovereign debt", "fiscal",
)
BUSINESS_KEYWORDS = ("business", "company", "stock", "shares", "earnings", "market", "finance")
BUSINESS_MARKET_HARD_NEWS_KEYWORDS = (
    "ipo", "initial public offering", "public offering", "listing", "listed", "market debut",
    "nasdaq debut", "nyse debut", "shares", "stock debut", "priced", "valuation", "raises",
    "record ipo", "largest ipo", "oversubscribed", "order book", "market cap", "trading debut",
    "surges", "falls in debut", "ticker", "chipmaker", "semiconductor", "ai company", "aerospace", "space company",
    "satellite", "上市", "挂牌", "纳斯达克", "纽交所", "首日交易", "发行价", "募资",
    "估值", "市值", "股票", "股价", "科技股", "航天", "卫星", "半导体", "芯片",
)
ENERGY_GEO_KEYWORDS = ("energy", "oil", "gas", "commodity", "commodities", "war", "conflict", "geopolitical", "shipping")
ECONOMIC_PRIORITY_KEYWORDS = (
    "央行", "人民银行", "fed", "federal reserve", "利率", "降息", "加息", "通胀", "cpi", "ppi",
    "就业", "社融", "金融统计", "汇率", "人民币", "美元", "外汇", "银行", "信贷",
    "trade", "tariff", "关税", "贸易", "进出口", "海关", "出口管制", "export controls",
    "供应链", "外资", "商务部", "ustr", "wto", "贸易谈判",
)
TRADE_COMMODITY_PRIORITY_KEYWORDS = (
    "期货", "大宗商品", "商品", "农产品", "粮食", "玉米", "大豆", "棕榈油", "糖", "棉花",
    "有色金属", "铜", "铝", "锌", "镍", "铁矿石", "钢铁", "原油", "天然气", "能源",
    "航运", "油轮", "港口", "霍尔木兹海峡", "红海", "futures", "commodity", "commodities",
    "grain", "corn", "soybean", "copper", "aluminum", "zinc", "nickel", "iron ore", "steel",
    "oil", "crude", "natural gas", "energy", "shipping", "tanker", "port", "strait of hormuz",
    "red sea",
)
MARKET_IMPACT_KEYWORDS = (
    "股市", "债券", "ipo", "上市", "挂牌", "nasdaq", "nyse", "市值", "估值", "募资",
    "首日交易", "股票", "market debut", "listing", "shares", "valuation", "market cap",
    "stock", "bond", "yield", "s&p 500", "dow", "index", "ticker",
)
ECONOMIC_TECH_KEYWORDS = (
    "ai", "人工智能", "大模型", "芯片", "半导体", "算力", "数据中心", "新能源", "机器人",
    "智能汽车", "自动驾驶", "航天", "卫星",
)
PUBLIC_SAFETY_KEYWORDS = ("预警", "灾害", "事故", "袭击", "坠机", "地震", "洪水", "storm", "disaster", "crash", "attack")
GEO_MARKET_IMPACT_KEYWORDS = (
    "iran", "伊朗", "strait of hormuz", "霍尔木兹海峡", "red sea", "红海", "russia", "ukraine",
    "俄乌", "sanctions", "制裁", "g7", "summit", "oil", "能源", "shipping", "航运", "tanker", "油轮",
    "port", "港口", "supply", "供应", "trade", "贸易", "market", "dollar", "commodity", "export", "tariff",
)
NON_ECONOMIC_SOFT_KEYWORDS = (
    "文化", "文旅", "非遗", "体育", "娱乐", "人物", "访谈", "生活方式", "健康科普",
    "青少年比赛", "活动举行", "展览", "故事", "暖新闻", "soft", "newsletter", "roundup",
    "opinion", "analysis", "explainer", "sports", "entertainment", "lifestyle", "health",
)
INTERNATIONAL_POLITICAL_ONLY_KEYWORDS = (
    "priest", "confessor", "religious", "bishop", "church", "historian", "crime", "criminal",
    "人物", "牧师", "宗教", "人物背景",
)
SANCTIONS_PERSON_ONLY_KEYWORDS = (
    "priest", "confessor", "religious", "bishop", "church", "politician", "lawmaker", "official",
    "figure", "person", "牧师", "宗教", "人物",
)


PAKISTAN_DIRECT_KEYWORDS = (
    "state bank of pakistan", "sbp", "ministry of finance",
    "finance division", "federal board of revenue", "fbr",
    "pakistan bureau of statistics", "pbs", "pakistan stock exchange", "psx",
    "kse-100", "kse 100", "pakistan rupee", "pakistani rupee", "pkr",
    "current account", "trade deficit", "fiscal deficit", "foreign exchange reserves",
    "remittances", "tax collection", "policy rate", "monetary policy",
    "circular debt", "petroleum levy", "electricity tariff", "gas tariff",
    "imf programme", "imf program", "imf review", "imf tranche",
    "اسٹیٹ بینک", "مہنگائی", "شرح سود", "روپیہ", "بجٹ", "ٹیکس",
    "برآمدات", "درآمدات", "ترسیلات زر", "زرمبادلہ", "کرنٹ اکاؤنٹ",
    "تجارتی خسارہ", "آئی ایم ایف", "توانائی", "پیٹرولیم لیوی",
)
PAKISTAN_EXTERNAL_IMPACT_KEYWORDS = (
    "brent crude", "crude oil", "oil prices", "lng", "liquefied natural gas",
    "strait of hormuz", "red sea", "gulf shipping", "freight rates",
    "shipping disruption", "global food prices", "commodity prices",
    "federal reserve", "fed rate", "us treasury yields", "dollar index",
    "global interest rates", "energy imports", "oil import bill",
)

_RANK_KEYWORDS = get_config_section("keywords", {}).get("rank", {})
_RANK_THRESHOLDS = get_config_section("thresholds", {}).get("ranking", {})
_SELECTION_THRESHOLDS = get_config_section("thresholds", {}).get("selection", {})
HEADLINE_KEYWORDS = tuple(_RANK_KEYWORDS.get("headline_keywords", HEADLINE_KEYWORDS))
INDUSTRY_KEYWORDS = tuple(_RANK_KEYWORDS.get("industry_keywords", INDUSTRY_KEYWORDS))
TECH_KEYWORDS = tuple(_RANK_KEYWORDS.get("tech_keywords", TECH_KEYWORDS))
FINANCE_KEYWORDS = tuple(_RANK_KEYWORDS.get("finance_keywords", FINANCE_KEYWORDS))
BUSINESS_KEYWORDS = tuple(_RANK_KEYWORDS.get("business_keywords", BUSINESS_KEYWORDS))
BUSINESS_MARKET_HARD_NEWS_KEYWORDS = tuple(_RANK_KEYWORDS.get("business_market_hard_news_keywords", BUSINESS_MARKET_HARD_NEWS_KEYWORDS))
ECONOMIC_PRIORITY_KEYWORDS = tuple(_RANK_KEYWORDS.get("economic_priority_keywords", ECONOMIC_PRIORITY_KEYWORDS))
TRADE_COMMODITY_PRIORITY_KEYWORDS = tuple(_RANK_KEYWORDS.get("trade_commodity_priority_keywords", TRADE_COMMODITY_PRIORITY_KEYWORDS))
MARKET_IMPACT_KEYWORDS = tuple(_RANK_KEYWORDS.get("market_impact_keywords", MARKET_IMPACT_KEYWORDS))
ECONOMIC_TECH_KEYWORDS = tuple(_RANK_KEYWORDS.get("economic_tech_keywords", ECONOMIC_TECH_KEYWORDS))
PUBLIC_SAFETY_KEYWORDS = tuple(_RANK_KEYWORDS.get("public_safety_keywords", PUBLIC_SAFETY_KEYWORDS))
GLOBAL_MACRO_FINANCE_KEYWORDS = tuple(_RANK_KEYWORDS.get("global_macro_finance_keywords", GLOBAL_MACRO_FINANCE_KEYWORDS))
US_ECONOMY_KEYWORDS = tuple(_RANK_KEYWORDS.get("us_economy_keywords", US_ECONOMY_KEYWORDS))
NON_ECONOMIC_SOFT_KEYWORDS = tuple(_RANK_KEYWORDS.get("non_economic_soft_keywords", NON_ECONOMIC_SOFT_KEYWORDS))
INTERNATIONAL_POLITICAL_ONLY_KEYWORDS = tuple(_RANK_KEYWORDS.get("international_political_only_keywords", INTERNATIONAL_POLITICAL_ONLY_KEYWORDS))
SANCTIONS_PERSON_ONLY_KEYWORDS = tuple(_RANK_KEYWORDS.get("sanctions_person_only_keywords", SANCTIONS_PERSON_ONLY_KEYWORDS))
ECONOMIC_PRIORITY_KEYWORDS = tuple(dict.fromkeys(ECONOMIC_PRIORITY_KEYWORDS + PAKISTAN_DIRECT_KEYWORDS))
FINANCE_KEYWORDS = tuple(dict.fromkeys(FINANCE_KEYWORDS + PAKISTAN_DIRECT_KEYWORDS))
INDUSTRY_KEYWORDS = tuple(dict.fromkeys(INDUSTRY_KEYWORDS + PAKISTAN_DIRECT_KEYWORDS))
TRADE_COMMODITY_PRIORITY_KEYWORDS = tuple(dict.fromkeys(
    TRADE_COMMODITY_PRIORITY_KEYWORDS + PAKISTAN_EXTERNAL_IMPACT_KEYWORDS
))


def rank_items(items: list[dict[str, Any]], config: dict[str, Any], target_date: date) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for item in items:
        item["category_bucket"] = _category_bucket(item)
        headline_weight = _headline_importance_weight(item)
        economic_relevance_weight = _economic_relevance_weight(item)
        market_impact_weight = _market_impact_weight(item)
        trade_commodity_weight = _trade_commodity_weight(item)
        keyword_weight = economic_relevance_weight + market_impact_weight + trade_commodity_weight
        pakistan_relevance_weight = _pakistan_relevance_weight(item)
        recency_weight = _recency_weight(item, config, target_date)
        source_weight = float(item.get("source_weight", 0))
        stale_penalty = _stale_penalty(item, config, target_date)
        soft_news_penalty = _soft_news_penalty(item)
        non_economic_penalty = _non_economic_penalty(item)
        duplicate_penalty = _duplicate_penalty(item)
        watchlist_bonus = float(_RANK_THRESHOLDS.get("watchlist_bonus", 6.0)) if item.get("watchlist_hits") else 0.0
        quality_score = float(item.get("quality_score", 0))
        score = (
            source_weight
            + economic_relevance_weight
            + market_impact_weight
            + trade_commodity_weight
            + headline_weight
            + pakistan_relevance_weight
            + recency_weight
            + watchlist_bonus
            + quality_score
            - soft_news_penalty
            - duplicate_penalty
            - stale_penalty
            - non_economic_penalty
        )

        item["headline_importance_weight"] = round(headline_weight, 3)
        item["economic_relevance_score"] = round(economic_relevance_weight, 3)
        item["market_impact_score"] = round(market_impact_weight, 3)
        item["trade_commodity_score"] = round(trade_commodity_weight, 3)
        item["keyword_relevance_weight"] = round(keyword_weight, 3)
        item["pakistan_relevance_weight"] = round(pakistan_relevance_weight, 3)
        item["recency_weight"] = round(recency_weight, 3)
        item["stale_penalty"] = round(stale_penalty, 3)
        item["soft_news_penalty"] = round(soft_news_penalty, 3)
        item["duplicate_penalty"] = round(duplicate_penalty, 3)
        item["non_economic_penalty"] = round(non_economic_penalty, 3)
        item["watchlist_bonus"] = round(watchlist_bonus, 3)
        item["score"] = round(score, 3)
        item["final_score"] = item["score"]
        item["reason"] = _selection_reason(item)
        ranked.append(item)
    return ranked


def select_top_items(items: list[dict[str, Any]], limit: int = 10) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    domestic, domestic_diag = _select_with_quota([item for item in items if item.get("section") == "domestic"], "domestic", limit)
    international, international_diag = _select_with_quota([item for item in items if item.get("section") == "international"], "international", limit)
    return domestic, international, {"domestic": domestic_diag, "international": international_diag}


def summarize_selection(items: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        "category_buckets": dict(Counter(item.get("category_bucket", "unknown") for item in items)),
        "sources": dict(Counter(item.get("source", "unknown") for item in items)),
        "source_groups": dict(Counter(item.get("source_group", "unknown") for item in items)),
    }


def _select_with_quota(items: list[dict[str, Any]], section: str, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sorted_items = sorted(items, key=lambda item: _selection_key(item, section), reverse=True)
    selected: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    event_buckets: dict[str, set[str]] = {}
    diagnostics = {
        "bucket_skipped_due_cap": Counter(),
        "event_skipped_due_limit": Counter(),
        "selected_event_groups": Counter(),
    }

    quotas = _bucket_quotas(section)
    max_by_bucket = _bucket_max(section)
    for bucket, min_count in quotas.items():
        candidates = [item for item in sorted_items if item.get("category_bucket") == bucket]
        while len([item for item in selected if item.get("category_bucket") == bucket]) < min_count:
            picked = _pick_next(
                candidates, selected, source_counts, group_counts, topic_counts,
                event_counts, event_buckets, max_by_bucket, section, diagnostics,
            )
            if not picked:
                break
            selected.append(picked)
            source_counts[picked.get("source", "")] += 1
            group_counts[picked.get("source_group", picked.get("source", ""))] += 1
            if picked.get("topic_group"):
                topic_counts[picked.get("topic_group", "")] += 1
            _record_selected_event(picked, event_counts, event_buckets, diagnostics)

    while len(selected) < limit:
        picked = _pick_next(
            sorted_items, selected, source_counts, group_counts, topic_counts,
            event_counts, event_buckets, max_by_bucket, section, diagnostics,
        )
        if not picked:
            break
        selected.append(picked)
        source_counts[picked.get("source", "")] += 1
        group_counts[picked.get("source_group", picked.get("source", ""))] += 1
        if picked.get("topic_group"):
            topic_counts[picked.get("topic_group", "")] += 1
        _record_selected_event(picked, event_counts, event_buckets, diagnostics)

    diagnostics["bucket_skipped_due_cap"] = dict(diagnostics["bucket_skipped_due_cap"])
    diagnostics["event_skipped_due_limit"] = dict(diagnostics["event_skipped_due_limit"])
    diagnostics["selected_event_groups"] = dict(diagnostics["selected_event_groups"])
    return selected[:limit], diagnostics


def _pick_next(
    candidates: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    source_counts: Counter[str],
    group_counts: Counter[str],
    topic_counts: Counter[str],
    event_counts: Counter[str],
    event_buckets: dict[str, set[str]],
    max_by_bucket: dict[str, int],
    section: str,
    diagnostics: dict[str, Any],
) -> dict[str, Any] | None:
    selected_urls = {item.get("url") for item in selected}
    bucket_counts = Counter(item.get("category_bucket") for item in selected)
    for item in candidates:
        if item.get("url") in selected_urls:
            continue
        source = item.get("source", "")
        group = item.get("source_group") or source
        bucket = item.get("category_bucket", "unknown")
        if source_counts[source] >= int(_SELECTION_THRESHOLDS.get("per_source_limit", 2)):
            continue
        group_limit = _group_limit(group, section)
        if group_counts[group] >= group_limit:
            continue
        topic_group = item.get("topic_group")
        if topic_group and topic_counts[topic_group] >= int(_SELECTION_THRESHOLDS.get("per_topic_limit", 2)):
            continue
        if bucket_counts[bucket] >= max_by_bucket.get(bucket, 10):
            diagnostics["bucket_skipped_due_cap"][bucket] += 1
            continue
        if not _event_group_allowed(item, event_counts, event_buckets):
            event_group = item.get("event_cluster_key") or item.get("event_group_key") or item.get("event_fingerprint") or "other"
            diagnostics["event_skipped_due_limit"][event_group] += 1
            continue
        return item
    return None


def _group_limit(group: str, section: str) -> int:
    group_limits = _SELECTION_THRESHOLDS.get("group_limits", {}).get(section, {})
    return int(group_limits.get(group, group_limits.get("default", 4 if section == "domestic" else 3)))


def _category_bucket(item: dict[str, Any]) -> str:
    blob = _blob(item)
    section = item.get("section")
    source_group = item.get("source_group")
    if section == "domestic":
        if _contains_any(blob, NON_ECONOMIC_SOFT_KEYWORDS):
            return "soft_news"
        if source_group in {"qhrb", "dce"} or _contains_any(blob, TRADE_COMMODITY_PRIORITY_KEYWORDS):
            return "commodities_logistics"
        if source_group in {"mofcom", "pbc", "ndrc", "sina", "cs", "customs", "stats", "mof", "sbp", "fbr", "pbs", "psx", "finance_division", "finance_ministry", "commerce_division", "pakistan_customs", "pakistan_bureau_statistics"}:
            return "finance_macro_trade"
        if _contains_any(blob, ECONOMIC_PRIORITY_KEYWORDS) or _contains_any(blob, FINANCE_KEYWORDS):
            return "finance_macro_trade"
        if _contains_any(blob, TECH_KEYWORDS) or _contains_any(blob, ECONOMIC_TECH_KEYWORDS):
            return "tech_industry"
        if _contains_any(blob, PUBLIC_SAFETY_KEYWORDS):
            return "public_safety"
        return "general_headline"

    if _contains_any(blob, NON_ECONOMIC_SOFT_KEYWORDS):
        return "soft_news"
    if _is_personal_sanctions_story(blob):
        return "major_headline"
    if source_group in {"fed", "imf", "ecb", "world_bank", "treasury", "boe", "boj"}:
        return "us_economy_policy"
    if _has_us_economy_policy_context(blob) or _contains_any(blob, GLOBAL_MACRO_FINANCE_KEYWORDS):
        return "us_economy_policy"
    if _is_geopolitics_market_item(blob):
        return "geopolitics_market_impact"
    if _contains_any(blob, TRADE_COMMODITY_PRIORITY_KEYWORDS):
        return "trade_commodities_energy"
    if _contains_any(blob, BUSINESS_MARKET_HARD_NEWS_KEYWORDS):
        return "business_market_hard_news"
    if _contains_any(blob, TECH_KEYWORDS) or _contains_any(blob, ECONOMIC_TECH_KEYWORDS):
        return "tech_industry_hard_news"
    if _contains_any(blob, BUSINESS_KEYWORDS):
        return "business_market_hard_news"
    if _contains_any(blob, INTERNATIONAL_POLITICAL_ONLY_KEYWORDS):
        return "major_headline"
    return "major_headline"


def _bucket_quotas(section: str) -> dict[str, int]:
    quotas = _SELECTION_THRESHOLDS.get("bucket_quotas", {}).get(section, {})
    return {str(key): int(value) for key, value in quotas.items()}


def _bucket_max(section: str) -> dict[str, int]:
    limits = _SELECTION_THRESHOLDS.get("bucket_max", {}).get(section, {})
    return {str(key): int(value) for key, value in limits.items()}


def _headline_importance_weight(item: dict[str, Any]) -> float:
    blob = _blob(item)
    hits = sum(1 for keyword in HEADLINE_KEYWORDS if keyword.casefold() in blob)
    return min(5.0, hits * 1.0)


def _economic_relevance_weight(item: dict[str, Any]) -> float:
    blob = _blob(item)
    hits = _count_keyword_hits(blob, ECONOMIC_PRIORITY_KEYWORDS)
    tech_hits = _count_keyword_hits(blob, ECONOMIC_TECH_KEYWORDS)
    bucket_bonus = 2 if item.get("category_bucket") in {"finance_macro_trade", "us_economy_policy"} else 0
    return min(12.0, hits * 2.0 + tech_hits * 1.0 + bucket_bonus)


def _market_impact_weight(item: dict[str, Any]) -> float:
    blob = _blob(item)
    if not _has_capital_market_context(blob):
        return 0.0
    hits = _count_keyword_hits(blob, MARKET_IMPACT_KEYWORDS)
    business_hits = _count_keyword_hits(blob, BUSINESS_MARKET_HARD_NEWS_KEYWORDS)
    bucket_bonus = 2 if item.get("category_bucket") == "business_market_hard_news" else 0
    return min(10.0, hits * 1.8 + business_hits * 1.2 + bucket_bonus)


def _trade_commodity_weight(item: dict[str, Any]) -> float:
    blob = _blob(item)
    hits = _count_keyword_hits(blob, TRADE_COMMODITY_PRIORITY_KEYWORDS)
    bucket_bonus = 2 if item.get("category_bucket") in {"commodities_logistics", "trade_commodities_energy"} else 0
    return min(10.0, hits * 1.8 + bucket_bonus)


def _keyword_relevance_weight(item: dict[str, Any]) -> float:
    blob = _blob(item)
    industry_hits = sum(1 for keyword in INDUSTRY_KEYWORDS if keyword.casefold() in blob)
    tech_hits = sum(1 for keyword in TECH_KEYWORDS if keyword.casefold() in blob)
    business_hits = sum(1 for keyword in BUSINESS_MARKET_HARD_NEWS_KEYWORDS if keyword.casefold() in blob)
    return min(7.0, industry_hits * 0.55 + tech_hits * 0.65 + business_hits * 0.85)



def _pakistan_relevance_weight(item: dict[str, Any]) -> float:
    """Prioritize Pakistani economic developments and global drivers of Pakistan's economy."""
    blob = _blob(item)
    direct_hits = _count_keyword_hits(blob, PAKISTAN_DIRECT_KEYWORDS)
    external_hits = _count_keyword_hits(blob, PAKISTAN_EXTERNAL_IMPACT_KEYWORDS)
    economic_context = _is_economic_or_market_item(item) or _contains_any(
        blob, ("inflation", "interest rate", "central bank", "trade", "oil", "energy", "commodity", "shipping")
    )
    score = min(6.0, direct_hits * 2.0)
    # A generic Pakistan mention is only a relevance signal in economic context.
    if economic_context and _contains_any(blob, ("pakistan", "pakistani")):
        score += 2.0
    if economic_context:
        score += min(3.0, external_hits * 1.0)
    return min(8.0, score)


def _recency_weight(item: dict[str, Any], config: dict[str, Any], target_date: date) -> float:
    published_at = parse_datetime(item.get("published_at"), config["timezone"])
    if published_at is None:
        return float(_RANK_THRESHOLDS.get("missing_published_at_recency_weight", 0.6))

    start, end = target_day_bounds(target_date, config["timezone"])
    if start <= published_at < end:
        return float(_RANK_THRESHOLDS.get("target_day_recency_weight", 4.0))

    hours_from_window = min(abs((published_at - start).total_seconds()), abs((published_at - end).total_seconds())) / 3600
    if hours_from_window <= 24:
        return float(_RANK_THRESHOLDS.get("nearby_day_recency_weight", 2.0))
    if hours_from_window <= 72:
        return float(_RANK_THRESHOLDS.get("stale_recency_weight", 1.0))
    return float(_RANK_THRESHOLDS.get("far_recency_weight", 0.2))


def _stale_penalty(item: dict[str, Any], config: dict[str, Any], target_date: date) -> float:
    published_at = parse_datetime(item.get("published_at"), config["timezone"])
    if not published_at:
        return float(_RANK_THRESHOLDS.get("missing_datetime_stale_penalty", 0.5))
    days_old = abs((published_at.date() - target_date).days)
    if days_old > int(_RANK_THRESHOLDS.get("very_old_story_penalty_days", 30)):
        return float(_RANK_THRESHOLDS.get("very_old_story_penalty", 8.0))
    if days_old > int(_RANK_THRESHOLDS.get("old_story_penalty_days", 3)):
        return float(_RANK_THRESHOLDS.get("old_story_penalty", 2.0))
    return 0.0


def _soft_news_penalty(item: dict[str, Any]) -> float:
    title = item.get("title", "")
    blob = _blob(item)
    penalty = 0.0
    if len(title) < 12:
        penalty += float(_RANK_THRESHOLDS.get("short_title_penalty", 3.0))
    if _contains_any(blob, NON_ECONOMIC_SOFT_KEYWORDS):
        penalty += float(_RANK_THRESHOLDS.get("soft_news_penalty", 8.0))
    if any(token in title.casefold() for token in ("newsletter", "subscribe", "roundup")):
        penalty += float(_RANK_THRESHOLDS.get("roundup_penalty", 8.0))
    if "live updates" in title.casefold() and not item.get("watchlist_hits"):
        penalty += float(_RANK_THRESHOLDS.get("live_updates_penalty", 3.0))
    return penalty


def _duplicate_penalty(item: dict[str, Any]) -> float:
    duplicate_count = int(item.get("duplicate_count", 1) or 1)
    return min(float(_RANK_THRESHOLDS.get("max_duplicate_penalty", 3.0)), max(0, duplicate_count - 1) * float(_RANK_THRESHOLDS.get("duplicate_penalty_step", 0.75)))


def _non_economic_penalty(item: dict[str, Any]) -> float:
    bucket = item.get("category_bucket")
    if bucket == "soft_news":
        return float(_RANK_THRESHOLDS.get("soft_bucket_penalty", 20.0))
    if bucket == "major_headline":
        return 0.0 if _headline_importance_weight(item) >= 2.0 else 2.0
    if bucket in {"general_headline", "public_safety"}:
        return float(_RANK_THRESHOLDS.get("public_safety_penalty", 4.0)) if not _is_economic_or_market_item(item) else 0.0
    return 0.0


def _ranking_key(item: dict[str, Any]) -> tuple[float, float, str]:
    return (
        float(item.get("score", 0)),
        float(item.get("source_weight", 0)),
        item.get("published_at") or "",
    )


def _selection_key(item: dict[str, Any], section: str) -> tuple[float, float, float, str]:
    return (
        float(_bucket_priority(item.get("category_bucket", "unknown"), section)),
        float(item.get("score", 0)),
        float(item.get("source_weight", 0)),
        item.get("published_at") or "",
    )


def _bucket_priority(bucket: str, section: str) -> int:
    priorities = _SELECTION_THRESHOLDS.get("bucket_priority", {}).get(section, {})
    return priorities.get(bucket, 0)


def _contains_any(blob: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        lowered = keyword.casefold()
        if re.search(r"[a-z]", lowered):
            if re.search(rf"\b{re.escape(lowered)}\b", blob):
                return True
        elif lowered in blob:
            return True
    return False


def _count_keyword_hits(blob: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if _contains_any(blob, (keyword,)))


def _is_economic_or_market_item(item: dict[str, Any]) -> bool:
    blob = _blob(item)
    return any(
        _contains_any(blob, keywords)
        for keywords in (
            ECONOMIC_PRIORITY_KEYWORDS,
            TRADE_COMMODITY_PRIORITY_KEYWORDS,
            MARKET_IMPACT_KEYWORDS,
            BUSINESS_MARKET_HARD_NEWS_KEYWORDS,
            ECONOMIC_TECH_KEYWORDS,
            US_ECONOMY_KEYWORDS,
        )
    )


def _has_capital_market_context(blob: str) -> bool:
    return _contains_any(
        blob,
        (
            "ipo", "nasdaq", "nyse", "股票", "股价", "市值", "估值", "募资", "首日交易",
            "发行价", "上市公司", "market debut", "shares", "valuation", "market cap",
            "stock", "ticker", "s&p 500",
        ),
    )


def _selection_reason(item: dict[str, Any]) -> str:
    labels = ["target_date", item.get("category_bucket", "unknown")]
    blob = _blob(item)
    source_group = item.get("source_group")
    if item.get("watchlist_hits"):
        labels.append("watchlist")
    if _contains_any(blob, PAKISTAN_DIRECT_KEYWORDS):
        labels.append("pakistan_economic_relevance")
    elif _contains_any(blob, PAKISTAN_EXTERNAL_IMPACT_KEYWORDS) and _is_economic_or_market_item(item):
        labels.append("global_driver_relevant_to_pakistan")
    if source_group in {"pbc", "fed"} or _contains_any(blob, ("央行", "人民银行", "fed", "federal reserve", "金融统计", "社融")):
        labels.append("central_bank_data")
    if source_group in {"mofcom", "customs", "reuters"} or _contains_any(blob, ("商务部", "海关", "贸易", "关税", "进出口", "tariff", "trade", "export controls", "ustr", "wto")):
        labels.append("trade_policy")
    if _contains_any(blob, ("期货", "商品", "大宗商品", "农产品", "铜", "铝", "铁矿石", "原油", "oil", "natural gas", "shipping", "tanker", "航运", "油轮")):
        labels.append("commodities_energy")
    if _has_capital_market_context(blob) or _contains_any(blob, ("ai company", "chipmaker", "semiconductor", "satellite")):
        labels.append("IPO_watchlist")
    if item.get("category_bucket") == "geopolitics_market_impact":
        labels.append("oil_supply_risk" if _contains_any(blob, ("oil", "原油", "tanker", "shipping", "strait of hormuz", "red sea")) else "market_impact")
    if item.get("category_bucket") in {"tech_industry", "tech_industry_hard_news"}:
        labels.append("industrial_policy_or_capex")
    if item.get("category_bucket") in {"public_safety", "general_headline", "major_headline"} and not _is_economic_or_market_item(item):
        labels.append("major_general_fallback")
    return " + ".join(dict.fromkeys(label for label in labels if label))


def _is_geopolitics_market_item(blob: str) -> bool:
    geo_keywords = ("war", "strike", "conflict", "attack", "iran", "russia", "ukraine", "israel", "hezbollah", "sanctions", "g7", "summit", "战争", "冲突", "袭击", "制裁")
    market_keywords = (
        "oil", "energy", "tanker", "shipping", "trade", "market", "dollar", "supply", "commodity",
        "strait of hormuz", "red sea", "export", "tariff", "power", "electricity", "grid",
        "substation", "outage", "outages", "water facility", "water facilities", "pipeline",
        "refinery", "port", "ports", "原油", "能源", "航运", "油轮", "贸易", "供应",
        "红海", "霍尔木兹海峡", "电力", "电网", "变电站", "停电", "供水", "港口", "炼油",
    )
    if _is_personal_sanctions_story(blob):
        return False
    return _contains_any(blob, geo_keywords) and _contains_any(blob, market_keywords)


def _event_group_allowed(item: dict[str, Any], event_counts: Counter[str], event_buckets: dict[str, set[str]]) -> bool:
    group = item.get("event_cluster_key") or item.get("event_group_key") or item.get("duplicate_group_id") or item.get("event_fingerprint")
    if not group:
        return True
    return event_counts[group] < int(_SELECTION_THRESHOLDS.get("max_items_per_event", 1))


def _record_selected_event(
    item: dict[str, Any],
    event_counts: Counter[str],
    event_buckets: dict[str, set[str]],
    diagnostics: dict[str, Any],
) -> None:
    group = item.get("event_cluster_key") or item.get("event_group_key") or item.get("duplicate_group_id") or item.get("event_fingerprint")
    if not group:
        return
    event_counts[group] += 1
    event_buckets.setdefault(group, set()).add(item.get("category_bucket", "unknown"))
    diagnostics["selected_event_groups"][group] += 1


def _blob(item: dict[str, Any]) -> str:
    return " ".join(
        [
            item.get("title", ""),
            item.get("summary", ""),
            item.get("raw_description", ""),
            item.get("raw_snippet", ""),
            item.get("original_source", ""),
        ]
    ).casefold()


def _has_us_economy_policy_context(blob: str) -> bool:
    return _contains_any(blob, US_ECONOMY_KEYWORDS)


def _is_personal_sanctions_story(blob: str) -> bool:
    has_sanctions = _contains_any(blob, ("sanctions", "sanction", "制裁"))
    if not has_sanctions:
        return False
    if _contains_any(blob, ("oil", "energy", "trade", "export", "tariff", "bank", "finance", "financial", "market", "company", "shipping", "tanker", "port", "commodity", "supply", "原油", "能源", "贸易", "航运")):
        return False
    return _contains_any(blob, SANCTIONS_PERSON_ONLY_KEYWORDS)
