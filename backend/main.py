"""PSXviewAI FastAPI backend — live data from psxdata package.

Start:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from data import ANNOUNCEMENTS as MOCK_ANNOUNCEMENTS, SOURCES as MOCK_SOURCES, build_companies
from news_service import process_pipeline_news
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import auth
import config
import valuation
from assistant import router as research_router
from portfolio import router as portfolio_router
from academy import router as academy_router
from db import init_db

# Set up basic logging so server events are visible in the console.
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("psxviewai")

# Create the FastAPI application instance.
app = FastAPI(title="PSXviewAI API", version="0.2.0")


# Allow the frontend dev servers (Vite) to call this backend with credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Simple TTL cache: refresh companies every 15 min (live quotes are cached by
# psxdata itself for 15 min on disk, so this is just an extra in-process layer)
# ---------------------------------------------------------------------------
_CACHE: Dict[str, Any] = {
    "companies": [],       # cached list of company dicts
    "announcements": [],   # cached list of news announcements
    "sources": [],         # cached list of source evidence
    "ts": 0.0,             # timestamp of last company refresh
    "news_ts": 0.0,        # timestamp of last news refresh
    "market_source": "unavailable",
    "news_source": "unavailable",
}
CACHE_TTL = 15 * 60        # seconds: how long company data stays cached
NEWS_CACHE_TTL = 10 * 60   # seconds: how long news stays cached


def get_companies() -> List[Dict]:
    """
    Return cached company data, refreshing from psxdata if stale or empty.

    This is a synchronous function called in an executor thread.
    """
    now = time.time()
    if not _CACHE["companies"] or now - _CACHE["ts"] > CACHE_TTL:
        log.info("Refreshing company data from psxdata …")
        companies = build_companies()
        _CACHE["companies"] = companies
        _CACHE["market_source"] = "psxdata_or_fallback"
        _CACHE["ts"] = now
        log.info("Done — %d companies loaded", len(companies))
    return _CACHE["companies"]


def get_news() -> Tuple[List[Dict], List[Dict]]:
    """
    Return cached news + sources, refreshing from pipeline if stale or empty.

    Falls back to mock data if the pipeline returns no items.
    """
    now = time.time()
    if not _CACHE["announcements"] or now - _CACHE["news_ts"] > NEWS_CACHE_TTL:
        log.info("Refreshing news from economic pipeline …")
        announcements, sources = process_pipeline_news()
        if not announcements:
            log.warning("No pipeline news items loaded; using prototype mock news (source=mock).")
            announcements, sources = MOCK_ANNOUNCEMENTS, MOCK_SOURCES
            news_source = "mock"
        else:
            news_source = "pipeline"
        _CACHE["announcements"] = announcements
        _CACHE["sources"] = sources
        _CACHE["news_source"] = news_source
        _CACHE["news_ts"] = now
        log.info("Loaded %d announcements (source=%s)", len(announcements), news_source)
    return _CACHE["announcements"], _CACHE["sources"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def _warmup():
    """
    Pre-fetch data on startup so the first user request isn't slow.

    Runs init_db() to create tables, then warms both caches in a thread pool.
    Failures are logged but do not crash startup; they retry on the first request.
    """
    import asyncio
    init_db()  # create database tables if they do not exist yet
    loop = asyncio.get_event_loop()
    for fn in (get_companies, get_news):
        try:
            await loop.run_in_executor(None, fn)
        except Exception:
            log.exception("Warmup of %s failed; will retry on first request", fn.__name__)


# Include the auth and valuation route modules under their prefixes.
app.include_router(auth.router)
app.include_router(valuation.router)
app.include_router(research_router)
app.include_router(portfolio_router)
app.include_router(academy_router)


@app.get("/api/health")
def health():
    """
    Basic health + cache status endpoint.

    Useful for monitoring and confirming the server is alive and data is loaded.
    """
    return {
        "status": "ok",
        "cached_at": _CACHE["ts"],
        "news_cached_at": _CACHE["news_ts"],
        "news_count": len(_CACHE["announcements"]),
        "market_source": _CACHE["market_source"],
        "news_source": _CACHE["news_source"],
    }


@app.get("/api/companies")
def companies():
    """Return the cached list of companies with live price/volume/series data."""
    return get_companies()


@app.get("/api/announcements")
def announcements():
    """Return the cached list of announcements/news items."""
    ann, _ = get_news()
    return ann


@app.get("/api/sources")
def sources():
    """Return the cached list of source evidence linked to announcements."""
    _, src = get_news()
    return src


@app.post("/api/news/refresh")
def refresh_news():
    """
    Manually invalidate news cache and re-read pipeline snapshots.

    Returns the number of announcements after refresh.
    """
    _CACHE["news_ts"] = 0.0
    ann, src = get_news()
    return {"refreshed": True, "count": len(ann)}


@app.get("/api/market")
def market():
    """
    Single round-trip bundle the frontend uses on initial load.

    Combines companies, announcements, sources, and a representative asOf date.
    """
    companies = get_companies()
    announcements, sources = get_news()
    as_of = next((c.get("asOf") for c in companies if c.get("asOf")), "")
    return {
        "companies": companies,
        "announcements": announcements,
        "sources": sources,
        "asOf": as_of,
        "provenance": {
            "market": _CACHE["market_source"],
            "news": _CACHE["news_source"],
        },
    }


# The production image builds React into /app/dist. Mounting after all API
# routes keeps /api and the interactive API docs reachable while serving the
# frontend and its assets from the same origin (important for session cookies).
_default_frontend = Path(__file__).resolve().parent.parent / "dist"
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(_default_frontend)))
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    log.info("Frontend build not found at %s; API-only mode enabled", FRONTEND_DIST)


if __name__ == "__main__":
    # Entry point for running the server directly with `python main.py`.
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
