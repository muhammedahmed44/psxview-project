from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse
from zoneinfo import ZoneInfo

import yaml
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional during lightweight test runs
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False

from .pipeline_config import PROJECT_ROOT, load_repository_config


def load_runtime_config() -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    config = load_repository_config()

    config["http_timeout"] = int(os.getenv("HTTP_TIMEOUT", "15"))
    config["user_agent"] = os.getenv("USER_AGENT", "KaraNewsAgent/1.0 (+local)")
    config["newsapi_key"] = os.getenv("NEWSAPI_KEY", "").strip()
    config["gdelt_api_key"] = os.getenv("GDELT_API_KEY", "").strip()
    config["enable_llm_summary"] = os.getenv("ENABLE_LLM_SUMMARY", "false").strip().lower() in {"1", "true", "yes", "on"}
    config["summary_provider"] = os.getenv("SUMMARY_PROVIDER", "").strip().lower()
    config["summary_model"] = os.getenv("SUMMARY_MODEL", "").strip()
    config["allow_low_quality_sources"] = os.getenv("ALLOW_LOW_QUALITY_SOURCES", "false").strip().lower() in {"1", "true", "yes", "on"}
    config["output_dir"] = os.getenv("OUTPUT_DIR", str((PROJECT_ROOT / config.get("output_dir", "output/reports")).resolve()))
    config["temp_output_dir"] = os.getenv("TEMP_OUTPUT_DIR", str((PROJECT_ROOT / config.get("temp_output_dir", "output")).resolve()))
    config["log_file"] = os.getenv("LOG_FILE", str((PROJECT_ROOT / config.get("log_file", "logs/daily_news.log")).resolve()))
    return config


def setup_logging(log_path: Path) -> None:
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_target_date(date_arg: str | None, timezone_name: str) -> date:
    timezone = ZoneInfo(timezone_name)
    if date_arg:
        return datetime.strptime(date_arg, "%Y-%m-%d").date()

    local_now = datetime.now(timezone)
    return (local_now - timedelta(days=1)).date()


def build_snapshot_path(temp_output_dir: Path, target_date: date) -> Path:
    return temp_output_dir / f"{target_date.isoformat()}_snapshot.json"


def parse_datetime(value: str | None, fallback_timezone: str) -> datetime | None:
    if not value:
        return None

    timezone = ZoneInfo(fallback_timezone)
    cleaned = value.strip()
    cleaned = cleaned.replace("Z", "+00:00")
    candidates = [
        cleaned,
        cleaned.split(" GMT")[0],
    ]

    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone)
            return parsed.astimezone(timezone)
        except ValueError:
            pass

    known_formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y%m%dT%H%M%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in known_formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone)
            return parsed.astimezone(timezone)
        except ValueError:
            continue
    return None


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    hostname = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{hostname}{path}"


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    hostname = parsed.netloc.lower()
    if hostname == "chinanews.com.cn":
        hostname = "www.chinanews.com.cn"
    scheme = parsed.scheme.lower() or "https"
    path = parsed.path or "/"
    return urlunparse((scheme, hostname, path, "", parsed.query, ""))


def is_paid_domain(url: str, paid_domains: list[str]) -> bool:
    hostname = urlparse(url).netloc.lower().replace("www.", "")
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in paid_domains)


def normalize_title(title: str) -> str:
    lowered = title.casefold()
    lowered = re.sub(r"\s+", " ", lowered)
    lowered = re.sub(r"[\|\-_:：丨]+.*$", "", lowered)
    lowered = re.sub(r"[^\w\s\u4e00-\u9fff]", "", lowered)
    return lowered.strip()


def derive_tags(title: str, config: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    title_casefold = title.casefold()
    for keyword in config.get("fallback_topics", []):
        if keyword.casefold() in title_casefold:
            tags.append(keyword)
    return tags[:4]


def target_day_bounds(target_date: date, timezone_name: str) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(timezone_name)
    start = datetime.combine(target_date, time.min, tzinfo=timezone)
    end = datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=timezone)
    return start, end
