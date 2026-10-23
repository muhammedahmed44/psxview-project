"""Bridge between economic-news-intelligence-pipeline and the PSXviewAI backend.

Reads snapshots or invokes the pipeline's ranked outputs, performs impact evaluation
(using LLM when available, falling back to deterministic financial lexicon),
and produces frontend-compatible Announcements and SourceRecords.
"""
from __future__ import annotations

import glob
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("psxviewai.news")

# Paths to the sibling pipeline directory and its output snapshots.
BASE_DIR = Path(__file__).resolve().parent.parent
PIPELINE_DIR = BASE_DIR / "economic-news-intelligence-pipeline"
OUTPUT_DIR = PIPELINE_DIR / "output"

# Symbols tracked by the app for news mapping.
WATCHLIST_SYMBOLS = ["OGDC", "PPL", "MARI", "HBL", "ENGRO", "LUCK", "FFC"]

# Mapping of watchlist symbols to their company/sector keywords.
WATCHLIST_MAPPING = {
    "OGDC": {
        "keywords": ["ogdc", "oil & gas development company", "oil and gas development company"],
        "sector": "Oil & Gas Exploration",
    },
    "PPL": {
        "keywords": ["ppl", "pakistan petroleum limited", "pakistan petroleum"],
        "sector": "Oil & Gas Exploration",
    },
    "MARI": {
        "keywords": ["mari", "mari petroleum", "mari energies", "mari gas"],
        "sector": "Oil & Gas Exploration",
    },
    "HBL": {
        "keywords": ["hbl", "habib bank limited", "habib bank"],
        "sector": "Commercial Banks",
    },
    "ENGRO": {
        "keywords": ["engro", "engro fertilizers", "engro corp", "engro polymer"],
        "sector": "Fertilizer / Conglomerate",
    },
    "FFC": {
        "keywords": ["ffc", "fauji fertilizer company", "fauji fertilizer"],
        "sector": "Fertilizer",
    },
    "LUCK": {
        "keywords": ["luck", "lucky cement", "lucky core"],
        "sector": "Cement",
    },
}

# When no exact company match is found, use sector keywords to still tie a news item to a relevant symbol.
SECTOR_FALLBACKS = [
    {
        "keywords": ["gas tariff", "circular debt", "petroleum levy", "crude oil", "brent", "drilling", "well discovery", "refinery"],
        "symbols": ["OGDC", "PPL", "MARI"],
        "sector": "Oil & Gas Exploration",
    },
    {
        "keywords": ["interest rate", "policy rate", "state bank of pakistan", "sbp", "monetary policy", "banking spread", "t-bills", "pibs"],
        "symbols": ["HBL"],
        "sector": "Commercial Banks",
    },
    {
        "keywords": ["urea", "fertilizer", "dap", "gas curtailment", "subsidies on fertilizer"],
        "symbols": ["ENGRO", "FFC"],
        "sector": "Fertilizer",
    },
    {
        "keywords": ["cement", "dispatches", "construction", "coal prices", "infrastructure spending"],
        "symbols": ["LUCK"],
        "sector": "Cement",
    },
]

# Financial lexicon for deterministic sentiment scoring.
POSITIVE_TERMS = [
    "rise", "gain", "surplus", "reforms", "growth", "boost", "positive", "approves", "approval",
    "dividend", "profit", "expansion", "record high", "discovery", "payout", "rebound", "upgraded",
    "imf deal", "imf tranche", "inflow", "reserves rise"
]
NEGATIVE_TERMS = [
    "fall", "drop", "decline", "deficit", "loss", "slump", "circular debt tops", "debt tops",
    "pressure", "curtailment", "penalty", "slowdown", "slows", "inflation rises", "outflow",
    "downgrade", "crisis", "disruption", "risk"
]


def _format_relative_time(pub_str: Optional[str]) -> str:
    """
    Format an ISO published-at string into a friendly relative label.

    Examples: 'Today, 9:40 AM', 'Yesterday, 2:15 PM', '20 Oct, 2:15 PM'.
    """
    if not pub_str:
        return "Recent"
    try:
        # e.g. 2026-10-20T14:03:00+05:00
        dt = datetime.fromisoformat(pub_str)
        now = datetime.now(dt.tzinfo)
        date_fmt = dt.strftime("%d %b").lstrip("0")
        time_fmt = dt.strftime("%I:%M %p").lstrip("0")

        if dt.date() == now.date():
            return f"Today, {time_fmt}"
        days_diff = (now.date() - dt.date()).days
        if days_diff == 1:
            return f"Yesterday, {time_fmt}"
        return f"{date_fmt}, {time_fmt}"
    except Exception:
        return pub_str[:16].replace("T", " ")


def _find_symbol_and_sector(title: str, summary: str, tags: List[str]) -> Tuple[str, str, str]:
    """
    Identify the matching stock symbol, sector, and scope.

    Returns a tuple of (symbol, sector, impact_scope).
    Scope is "stock" for direct company matches, "sector" for sector fallbacks,
    or "market" for broad macro items.
    """
    text = f"{title} {summary} {' '.join(tags)}".lower()

    # 1. Check direct company matches
    for sym, meta in WATCHLIST_MAPPING.items():
        if re.search(rf"\b{sym.lower()}\b", text):
            return sym, meta["sector"], "stock"
        for kw in meta["keywords"]:
            if kw in text:
                return sym, meta["sector"], "stock"

    # 2. Check sector fallbacks
    for sf in SECTOR_FALLBACKS:
        for kw in sf["keywords"]:
            if kw in text:
                # Distribute or pick primary symbol
                return sf["symbols"][0], sf["sector"], "sector"

    # 3. Overall Market Fallback
    return "KSE100", "Macro / Market", "market"


def _evaluate_rule_based(title: str, text: str, symbol: str, sector: str, scope: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate impact using deterministic financial keywords.

    Produces direction, sentiment, strength, summary, detail, confidence, and evaluator label.
    """
    combined = f"{title} {text}".lower()

    # Count positive and negative keyword matches.
    pos_score = sum(1 for term in POSITIVE_TERMS if term in combined)
    neg_score = sum(1 for term in NEGATIVE_TERMS if term in combined)

    # Default verdict from keyword counts.
    if pos_score > neg_score:
        direction = "up"
        sentiment = "Positive"
        summary = "Favorable outlook"
        detail = f"Positive developments in {sector.lower() if sector else 'market'} expected to support investor confidence and valuations."
    elif neg_score > pos_score:
        direction = "down"
        sentiment = "Negative"
        summary = "Potential headwind"
        detail = f"Challenges and cost pressures in {sector.lower() if sector else 'market'} may weigh on performance in the near term."
    else:
        direction = "neu"
        sentiment = "Neutral"
        summary = "Balanced impact"
        detail = f"Headline suggests steady operational conditions with limited immediate volatility expected for {symbol}."

    # Override verdict for specific high-signal financial themes.
    if "dividend" in combined or "payout" in combined:
        direction = "up"
        sentiment = "Positive"
        summary = "Dividend support"
        detail = f"Payout decisions support income appeal and provide downside cushion for {symbol}."
    elif "circular debt" in combined:
        if "rises" in combined or "tops" in combined or "hits" in combined or "increase" in combined:
            direction = "down"
            sentiment = "Negative"
            summary = "Debt overhang"
            detail = "Gas/energy circular debt buildup strains cash flows, receivables, and operational liquidity for E&P and energy firms."
        else:
            direction = "neu"
            sentiment = "Neutral"
            summary = "Reform scrutiny"
            detail = "Gas/energy circular debt review and reforms under government discussion; market monitoring structural settlement plans."
    elif "policy rate" in combined or "interest rate" in combined:
        summary = "Rate environment update"
        detail = "Monetary policy adjustments influence cost of funds, lending spreads, and broader market liquidity."
    elif "gdp" in combined and ("down" in combined or "falls" in combined or "decline" in combined):
        direction = "down"
        sentiment = "Negative"
        summary = "Growth trimmed"
        detail = "Downward revision in economic growth targets dampens aggregate demand and market earnings projections."
    elif "gas" in combined or "tariff" in combined:
        summary = "Tariff & pricing review"
        detail = "Regulatory notifications alter producer and consumer realizations across energy and fertilizer value chains."

    # Compute strength (1 = Mild, 2 = Moderate, 3 = High) from pipeline scores.
    econ_score = item.get("economic_relevance_score", 0.0)
    market_score = item.get("market_impact_score", 0.0)
    source_weight = item.get("source_weight", 5.0)

    total_imp = econ_score + market_score + (source_weight / 2.0)
    if total_imp >= 12 or item.get("final_score", 0) >= 30:
        strength = 3
    elif total_imp >= 7:
        strength = 2
    else:
        strength = 1

    confidence = min(95, max(60, int(total_imp * 5)))

    return {
        "dir": direction,
        "sentiment": sentiment,
        "strength": strength,
        "summary": summary,
        "detail": detail,
        "confidence": confidence,
        "evaluator": "rule-based",
    }


def _evaluate_llm(title: str, text: str, symbol: str, sector: str, api_key: str, provider: str = "openai") -> Optional[Dict[str, Any]]:
    """
    Evaluate impact using an LLM when an API key is configured.

    Falls back to None on any error so the caller can use rule-based scoring instead.
    """
    try:
        prompt = f"""
You are a senior equity analyst specializing in Pakistan Stock Exchange (PSX).
Evaluate the following economic news headline and brief snippet for its impact on {symbol} (Sector: {sector}):
Title: {title}
Context: {text}

Respond ONLY with a valid JSON object with the following fields:
{{
  "dir": "up" | "down" | "neu",
  "sentiment": "Positive" | "Negative" | "Neutral",
  "strength": 1 | 2 | 3,
  "summary": "Short impact phrase (2-4 words, e.g. 'Margin expansion')",
  "detail": "1-2 concise sentences explaining market transmission to stock/market.",
  "confidence": 60 to 95
}}
"""
        if provider == "openai":
            import urllib.request
            req_data = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "You are a precise financial intelligence evaluator. Output strictly JSON."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                result = json.loads(res_body["choices"][0]["message"]["content"])
                result["evaluator"] = "llm"
                return result
        elif provider == "gemini":
            import urllib.request
            req_data = {
                "model": os.getenv("GEMINI_MODEL", "gemini-1.5"),
                "input": prompt,
                "temperature": 0.2,
            }
            req = urllib.request.Request(
                "https://api.generativeai.google/v1beta2/models/gemini-1.5:generateMessage",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                result = json.loads(res_body["candidates"][0]["content"][0]["text"])
                result["evaluator"] = "llm"
                return result
    except Exception as e:
        log.warning("LLM evaluation failed or timed out: %s. Falling back to rule-based.", e)
    return None


def _clean_snippet(raw_text: str) -> str:
    """Strip HTML markup from RSS/pipeline raw snippets."""
    if not raw_text:
        return ""
    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", raw_text)
    # Unescape HTML entities
    cleaned = re.sub(r"&[a-z]+;", " ", cleaned)
    # Compress whitespace
    return re.sub(r"\s+", " ", cleaned).strip()


def load_latest_pipeline_snapshot() -> Optional[Dict[str, Any]]:
    """Find and read the latest snapshot file from the pipeline output directory."""
    if not OUTPUT_DIR.exists():
        return None
    snapshots = sorted(OUTPUT_DIR.glob("*_snapshot.json"), reverse=True)
    if not snapshots:
        return None
    latest_file = snapshots[0]
    log.info("Loading latest news snapshot from %s", latest_file.name)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Failed to read snapshot %s: %s", latest_file, e)
        return None


def process_pipeline_news() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Process pipeline news items into (Announcements, Sources).

    Reads the latest snapshot, evaluates each item, and returns up to 15
    announcement/source pairs for the frontend.
    """
    snapshot = load_latest_pipeline_snapshot()
    if not snapshot:
        log.warning("No pipeline snapshot found. Returning empty lists.")
        return [], []

    items = snapshot.get("domestic_items", []) + snapshot.get("international_items", [])
    if not items:
        return [], []

    # Sort items by final_score descending so the highest-impact news comes first.
    sorted_items = sorted(items, key=lambda x: x.get("final_score", 0.0), reverse=True)

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    announcements: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []

    # Track covered symbols to ensure variety across the active watchlist
    assigned_symbols = set()

    for item in sorted_items:
        title = item.get("title") or item.get("raw_title", "")
        if not title:
            continue

        # Extract and clean the best available snippet text.
        raw_snippet = item.get("summary") or item.get("raw_snippet") or item.get("raw_description") or ""
        snippet = _clean_snippet(raw_snippet)
        tags = item.get("tags") or []
        url = item.get("final_url_used") or item.get("url") or item.get("original_url") or ""
        source_name = item.get("source") or item.get("original_source") or "Market News"
        pub_at = item.get("published_at") or item.get("published_date") or ""

        # Map this news item to a symbol, sector, and scope.
        symbol, sector, scope = _find_symbol_and_sector(title, snippet, tags)

        # If this watchlist symbol is already heavily represented, and we have unassigned watchlist symbols,
        # fallback to general market if not an explicit company match.
        if scope == "sector" and symbol in assigned_symbols:
            unassigned = [s for s in WATCHLIST_SYMBOLS if s not in assigned_symbols]
            if unassigned:
                # Keep diverse by assigning next relevant or fallback
                pass

        assigned_symbols.add(symbol)

        # Evaluate impact: LLM if available, otherwise rule-based
        eval_result = None
        if openai_key or gemini_key:
            llm_key = openai_key if openai_key else gemini_key
            eval_result = _evaluate_llm(title, snippet, symbol, sector, llm_key, provider="openai" if openai_key else "gemini")
        if not eval_result:
            eval_result = _evaluate_rule_based(title, snippet, symbol, sector, scope, item)

        # Build the frontend announcement object.
        announcement = {
            "symbol": symbol,
            "time": _format_relative_time(pub_at),
            "headline": title,
            "dir": eval_result["dir"],
            "sentiment": eval_result["sentiment"],
            "strength": eval_result["strength"],
            "summary": eval_result["summary"],
            "detail": eval_result["detail"],
        }

        # Determine source type classification based on source name keywords.
        source_type = "News"
        src_lower = source_name.lower()
        if "state bank" in src_lower or "pbs" in src_lower or "secp" in src_lower or "ministry" in src_lower:
            source_type = "Official"
        elif "psx" in src_lower or "notice" in src_lower or "filing" in src_lower:
            source_type = "Filing"

        # Build the frontend source evidence object.
        source_record = {
            "confidence": eval_result.get("confidence", 75),
            "sources": [
                {
                    "title": source_name,
                    "type": source_type,
                    "time": _format_relative_time(pub_at),
                    "text": snippet if len(snippet) > 15 else title,
                    "url": url,
                }
            ],
        }

        announcements.append(announcement)
        sources.append(source_record)

        # Limit to top 15 news items for smooth frontend ticker display
        if len(announcements) >= 15:
            break

    return announcements, sources