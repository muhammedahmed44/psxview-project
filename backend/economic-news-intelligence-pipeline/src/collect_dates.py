from __future__ import annotations

import re
from datetime import date, datetime
from time import struct_time
from typing import Any
from zoneinfo import ZoneInfo

from .utils import parse_datetime

def parse_entry_published_datetime(
    entry: Any,
    link: str,
    title: str,
    summary: str,
    source_timezone: str,
) -> tuple[datetime | None, str | None, set[str]]:
    """
    Extract the most reliable published datetime from a feed entry.

    Tries multiple common feed date fields in order of preference.
    Returns (datetime, raw_value, set_of_fields_considered).
    """
    candidates = [
        ("published", entry.get("published")),
        ("pubDate", entry.get("pubDate")),
        ("updated", entry.get("updated")),
        ("dc_date", entry.get("dc_date") or entry.get("dc:date")),
        ("datePublished", entry.get("datePublished")),
        ("published_at", entry.get("published_at")),
        ("date", entry.get("date")),
    ]

    fields: set[str] = set()

    # Prefer explicit publication dates over update dates.
    for field, value in candidates:
        if not value:
            continue

        parsed = parse_datetime(value, source_timezone)
        if parsed:
            fields.add(field)
            return parsed, str(value), fields

    # Feedparser exposes parsed dates separately from date strings.
    for field in ("published_parsed", "updated_parsed"):
        value = entry.get(field)
        if not value:
            continue

        try:
            if isinstance(value, struct_time):
                parts = value
            else:
                parts = value

            parsed = datetime(
                *parts[:6],
                tzinfo=ZoneInfo(source_timezone),
            )
            fields.add(field)
            return parsed, str(value), fields
        except (TypeError, ValueError, IndexError):
            continue

    # Do not infer publication time from a URL, headline, or summary. These
    # commonly contain dates for events or older stories, which can corrupt
    # target-date filtering. A missing feed publication date stays missing.
    return None, None, fields

def parse_date_from_text(text: str) -> date | None:
    """
    Try to find a calendar date embedded in arbitrary text.

    Useful for detecting old story republication from URLs or headlines.
    Returns None if no valid date is found.
    """
    import re

    patterns = [
        # YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
        r"(?<!\d)((?:19|20)\d{2})[-/.]([01]?\d)[-/.]([0-3]?\d)(?!\d)",

        # Chinese: YYYY年M月D日
        r"(?<!\d)((?:19|20)\d{2})年([01]?\d)月([0-3]?\d)日",

        # Compact: YYYYMMDD
        r"(?<!\d)((?:19|20)\d{2})([01]\d)([0-3]\d)(?!\d)",
        # Common Pakistan/English news formats: 21 October 2026 / Oct 21, 2026
        r"(?i)\b([0-3]?\d)\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?[,]?\s+((?:19|20)\d{2})\b",
        r"(?i)\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+([0-3]?\d),?\s+((?:19|20)\d{2})\b",
    ]

    month_numbers = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    for index, pattern in enumerate(patterns):
        for match in re.finditer(pattern, text):
            try:
                if index <= 2:
                    year, month, day = map(int, match.groups())
                elif index == 3:
                    day, month_name, year = match.groups()
                    month = month_numbers[month_name[:3].casefold()]
                    day, year = int(day), int(year)
                else:
                    month_name, day, year = match.groups()
                    month = month_numbers[month_name[:3].casefold()]
                    day, year = int(day), int(year)
                return date(year, month, day)
            except (ValueError, KeyError):
                continue

    return None


def item_dates(
    published: datetime | None,
    source_timezone: str,
    target_timezone: str,
) -> tuple[date | None, date | None]:
    """
    Convert a published datetime into both source-timezone and target-timezone dates.

    Returns (source_date, target_date), or (None, None) if published is missing.
    """
    if not published:
        return None, None
    source_dt = published.astimezone(ZoneInfo(source_timezone))
    target_dt = published.astimezone(ZoneInfo(target_timezone))
    return source_dt.date(), target_dt.date()


def possible_republished_old_story(
    url: str,
    title: str,
    summary: str,
    published_date: date | None,
) -> bool:
    """
    Detect whether an article might be a republication of an older story.

    Compares the feed's published_date with any date found in the URL or title.
    If the embedded date is more than 2 days earlier than the published date,
    the story is likely recycled.
    """
    if not published_date:
        return False
    embedded_date = parse_date_from_text(f"{url} {title}")
    if not embedded_date:
        return False
    return (published_date - embedded_date).days > 2