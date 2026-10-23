"""Live PSX data via the `psxdata` package.

For each symbol we pull the last 90 trading-day closes from the historical
OHLCV endpoint (used both as the sparkline graph and the displayed close
price / day volume) and the P/E ratio from the live screener.  EPS is derived
as price / P/E so the frontend's ``price / eps`` round-trips back to the live
P/E.  Falls back to a last-resort stub only when a fetch fails entirely, so
the API always returns 7 companies — but in normal operation every number is
live from psxdata, not hard-coded.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("psxviewai")

# Hard-coded announcements and sources stay as prototype data (AI layer TBD).
# These are the seven PSX symbols tracked by the app.
SYMBOLS = ["OGDC", "PPL", "MARI", "HBL", "ENGRO", "LUCK", "FFC"]

# PSX appends a corporate-action suffix to screener symbols (e.g. "OGDC" ->
# "OGDCXD" for ex-dividend), so an exact quote() lookup misses.  We try the
# plain symbol first, then these suffixes, to still resolve the live P/E.
_CROP_SUFFIXES = ("XD", "XR", "XB")


# ---------------------------------------------------------------------------
# psxdata helpers
# ---------------------------------------------------------------------------

def _safe_float(val: Any, default: float = 0.0) -> float:
    """
    Convert a value to float safely.

    Returns the default if the value is missing, non-numeric, or NaN.
    """
    try:
        v = float(val)
        # NaN check (NaN != NaN)
        return default if v != v else v
    except (TypeError, ValueError):
        return default


def _fmt_volume(v: float) -> str:
    """
    Format a raw volume number into a human-readable string.

    Examples: 1_250_000 -> "1.25M", 3_400 -> "3.4K".
    """
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return str(int(v)) if v else "—"


def _fmt_date(val: Any) -> str:
    """Format a pandas Timestamp / datetime as '21 Oct 2026' (no leading zero)."""
    try:
        return f"{int(val.day)} {val.strftime('%b')} {int(val.year)}"
    except Exception:
        return str(val)


def _screener_row(symbol: str, screener_df: Any) -> Optional[Any]:
    """
    Find a symbol's row in the screener, tolerating XD/XR/XB suffixes.

    Returns None if the symbol cannot be found at all.
    """
    if screener_df is None or getattr(screener_df, "empty", True):
        return None
    if "symbol" not in screener_df.columns:
        return None
    syms = screener_df["symbol"]
    m = screener_df[syms == symbol]
    if m.empty:
        for suf in _CROP_SUFFIXES:
            m = screener_df[syms == symbol + suf]
            if not m.empty:
                break
    return None if m.empty else m.iloc[0]


def fetch_company(symbol: str, screener_df: Any = None) -> Optional[Dict]:
    """
    Return a live company dict (price, volume, 90-point series, eps, asOf).

    Price, volume, and the 90-day close series come from ``psxdata.stocks``;
    the P/E (and thus EPS) comes from the live screener via ``_screener_row``.
    Returns None only if the historical fetch fails entirely.
    """
    try:
        import psxdata

        # psxdata returns ALL history in a single POST and only filters the
        # date range in memory, so requesting the full series costs the same
        # network round-trip as a narrow window.  We fetch everything and take
        # the last 90 trading days after sorting — this also covers symbols
        # whose most recent available data is older than a fixed recent window
        # (e.g. ENGRO, whose history currently stops in early 2025).
        df = psxdata.stocks(symbol)

        if df is None or df.empty:
            log.warning("%s: empty historical dataframe", symbol)
            return None

        # Normalize column names to lowercase so lookups are case-insensitive.
        df.columns = [c.lower() for c in df.columns]
        close_col = next(
            (c for c in ("close", "ldcp", "last") if c in df.columns), None
        )
        if close_col is None:
            log.warning("%s: no close column in %s", symbol, list(df.columns))
            return None

        # Rows are NOT chronologically ordered — sort ascending so the last
        # row is the most recent session.
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)

        closes = [_safe_float(v) for v in df[close_col].dropna().tolist()]
        if not closes:
            return None

        # Latest session's close + volume + date (all from the same row).
        last_row = df.iloc[-1]
        price = round(_safe_float(last_row[close_col]), 2)
        volume = _safe_float(last_row["volume"]) if "volume" in df.columns else 0.0
        as_of = _fmt_date(last_row["date"]) if "date" in df.columns else ""

        # P/E from the live screener -> EPS = price / P/E.  When P/E is 0 or
        # unavailable (e.g. ENGRO today), eps stays 0 and the frontend shows N/A.
        pe = 0.0
        row = _screener_row(symbol, screener_df)
        if row is not None and "pe_ratio" in row.index:
            pe = _safe_float(row["pe_ratio"])
        eps = round(price / pe, 2) if pe > 0 else 0.0

        # Exactly 90 points (left-pad if a symbol has shorter history) so the
        # frontend's fixed indices (series[59], series[88], series[89]) work.
        series = closes[-90:]
        if len(series) < 90:
            series = [series[0]] * (90 - len(series)) + series

        return {
            "symbol": symbol,
            "price": price,
            "volume": _fmt_volume(volume),
            "series": [round(v, 4) for v in series],
            "eps": eps,
            "asOf": as_of,
        }

    except Exception as exc:
        log.error("%s: fetch failed — %s", symbol, exc)
        return None


def build_companies() -> List[Dict]:
    """
    Fetch live data for all symbols; fall back to a stub only on failure.

    The screener is fetched once and reused for every P/E lookup.
    psxdata caches it on disk for 15 min, so this is one network round-trip for 7 symbols.
    """
    screener_df = None
    try:
        import psxdata

        screener_df = psxdata.screener()
        if screener_df is not None and not screener_df.empty:
            screener_df.columns = [c.lower() for c in screener_df.columns]
    except Exception as exc:
        log.warning("screener fetch failed — %s", exc)

    results: List[Dict] = []
    for symbol in SYMBOLS:
        company = fetch_company(symbol, screener_df)
        results.append(company if company else _stub(symbol))
    return results


def _stub(symbol: str) -> Dict:
    """
    Last-resort fallback so the UI never breaks on a total fetch failure.

    Uses hard-coded price, volume, and EPS to build a 90-point synthetic series.
    """
    stubs = {
        "OGDC":  (312.4,  "1.24M", 39.05),
        "PPL":   (241.8,  "2.1M",  24.93),
        "MARI":  (684.2,  "0.42M", 60.02),
        "HBL":   (189.5,  "1.8M",  14.47),
        "ENGRO": (356.9,  "0.9M",  28.96),
        "LUCK":  (921.3,  "0.31M", 77.42),
        "FFC":   (428.6,  "1.1M",  47.96),
    }
    price, volume, eps = stubs.get(symbol, (100.0, "—", 10.0))
    series = [round(price * (1 + (i - 45) * 0.001), 4) for i in range(90)]
    return {"symbol": symbol, "price": price, "volume": volume,
            "series": series, "eps": eps, "asOf": ""}


# ---------------------------------------------------------------------------
# Announcements + Sources (prototype / AI layer — unchanged)
# ---------------------------------------------------------------------------

ANNOUNCEMENTS: List[Dict] = [
    {
        "symbol": "OGDC", "time": "Today, 9:40 AM",
        "headline": "Board approves interim cash dividend for the quarter",
        "dir": "up", "sentiment": "Positive", "strength": 3,
        "summary": "Dividend support",
        "detail": "Payout is in line with last year, so buyers may step in. Expect a modest move up, not a big jump.",
    },
    {
        "symbol": "PPL", "time": "Today, 8:15 AM",
        "headline": "Gas price notification revised by regulator",
        "dir": "neu", "sentiment": "Neutral", "strength": 1,
        "summary": "Limited effect",
        "detail": "Revision is small and margins stay mostly flat. Sector circular debt news can still add short-term swings.",
    },
    {
        "symbol": "HBL", "time": "Yesterday, 4:50 PM",
        "headline": "Central bank announces policy rate decision",
        "dir": "down", "sentiment": "Negative", "strength": 2,
        "summary": "Margin pressure",
        "detail": "A lower rate can squeeze interest margins in the coming quarters. Watch guidance in the next results.",
    },
    {
        "symbol": "ENGRO", "time": "Yesterday, 11:20 AM",
        "headline": "Fertilizer plant completes scheduled maintenance",
        "dir": "up", "sentiment": "Positive", "strength": 2,
        "summary": "Output back early",
        "detail": "Production resumes earlier than planned, which supports volumes and quarterly earnings.",
    },
    {
        "symbol": "LUCK", "time": "19 Oct, 2:05 PM",
        "headline": "Monthly cement dispatches reported",
        "dir": "neu", "sentiment": "Neutral", "strength": 1,
        "summary": "Mixed numbers",
        "detail": "Local sales rose while exports slipped. Net effect on earnings should be small.",
    },
    {
        "symbol": "MARI", "time": "18 Oct, 5:30 PM",
        "headline": "New gas well enters production",
        "dir": "up", "sentiment": "Positive", "strength": 3,
        "summary": "Higher output",
        "detail": "Added production lifts expected revenue. Market may price this in over the next few sessions.",
    },
    {
        "symbol": "FFC", "time": "18 Oct, 1:10 PM",
        "headline": "Urea offtake slows during the month",
        "dir": "down", "sentiment": "Negative", "strength": 1,
        "summary": "Slight softness",
        "detail": "Lower offtake may trim next quarter sales a little. Impact stays small unless it continues.",
    },
]

# Sources are shown when the user opens the "Sources" view for an announcement.
# Each entry links to an official or authoritative page for the reader to verify.
SOURCES: List[Dict] = [
    {"confidence": 86, "sources": [
        {"title": "OGDC announcements on PSX", "type": "Official", "time": "Official company record", "text": "Open the PSX company page to review OGDC announcements, financial results and payout records.", "url": "https://dps.psx.com.pk/company/OGDC"},
    ]},
    {"confidence": 72, "sources": [
        {"title": "PPL announcements on PSX", "type": "Official", "time": "Official company record", "text": "Open the PSX company page to review PPL filings and regulatory announcements.", "url": "https://dps.psx.com.pk/company/PPL"},
    ]},
    {"confidence": 78, "sources": [
        {"title": "State Bank monetary policy statements", "type": "Official", "time": "Official central-bank record", "text": "Review the original monetary policy statements and supporting documents from the State Bank of Pakistan.", "url": "https://www.sbp.org.pk/our-operations/publications/monetary-policy-statements/501"},
    ]},
    {"confidence": 81, "sources": [
        {"title": "ENGRO announcements on PSX", "type": "Official", "time": "Official company record", "text": "Open the PSX company page to review ENGRO announcements and operational updates.", "url": "https://dps.psx.com.pk/company/ENGRO"},
    ]},
    {"confidence": 68, "sources": [
        {"title": "LUCK announcements on PSX", "type": "Official", "time": "Official company record", "text": "Open the PSX company page to review Lucky Cement announcements, reports and financial results.", "url": "https://dps.psx.com.pk/company/LUCK"},
    ]},
    {"confidence": 84, "sources": [
        {"title": "MARI announcements on PSX", "type": "Official", "time": "Official company record", "text": "Open the PSX company page to review Mari Energies announcements and production updates.", "url": "https://dps.psx.com.pk/company/MARI"},
    ]},
    {"confidence": 70, "sources": [
        {"title": "NFDC fertilizer statistics", "type": "Data", "time": "Official industry data", "text": "Review fertilizer production, availability and offtake statistics from the National Fertilizer Development Centre.", "url": "https://nfdc.gov.pk/stat.html"},
    ]},
]