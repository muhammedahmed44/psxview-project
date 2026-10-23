"""Run the economic-news pipeline and persist a backend-readable snapshot.

The web API invokes this script with ``--dry-run``.  Dry-run skips the DOCX
report, but deliberately still writes the JSON snapshot consumed by
``backend/news_service.py``.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from src.collect import collect_news
from src.dedupe import dedupe_items_with_report
from src.links import validate_items_links
from src.quality import filter_quality_items_with_report
from src.rank import rank_items, select_top_items, summarize_selection
from src.render_docx import render_daily_docx
from src.summary import enrich_items_with_summary_zh, get_summary_runtime
from src.utils import (
    build_snapshot_path,
    ensure_directory,
    get_target_date,
    load_runtime_config,
    setup_logging,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and rank daily economic news")
    parser.add_argument("date", nargs="?", help="Target date in YYYY-MM-DD format")
    parser.add_argument("--date", dest="date_option", help="Target date in YYYY-MM-DD format")
    parser.add_argument("--dry-run", action="store_true", help="Write JSON only; skip DOCX")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing DOCX")
    return parser.parse_args()


def _json_safe(value: Any) -> Any:
    """Convert the few non-JSON scalar types emitted by pipeline helpers."""
    if isinstance(value, (date, Path)):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def run_pipeline(
    target_date_arg: str | None = None,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> tuple[Path, int]:
    """Run one collection cycle and return ``(snapshot_path, item_count)``."""
    config = load_runtime_config()
    target_date = get_target_date(target_date_arg, config["timezone"])

    output_dir = Path(config["output_dir"])
    temp_output_dir = Path(config["temp_output_dir"])
    log_path = Path(config["log_file"])
    ensure_directory(output_dir)
    ensure_directory(temp_output_dir)
    ensure_directory(log_path.parent)
    setup_logging(log_path)

    logging.info("Collecting economic news for %s", target_date.isoformat())
    collected_items = collect_news(config, target_date)

    quality_items, quality_stats, quality_excluded = filter_quality_items_with_report(
        collected_items,
        target_date,
        config=config,
    )
    deduped_items, duplicate_report = dedupe_items_with_report(quality_items)
    ranked_items = rank_items(deduped_items, config, target_date)
    domestic_items, international_items, selection_diagnostics = select_top_items(
        ranked_items,
        limit=int(config.get("top_n_per_section", 10)),
    )

    selected_items = domestic_items + international_items
    if selected_items:
        validated_items = validate_items_links(
            selected_items,
            timeout=min(int(config.get("http_timeout", 15)), 5),
        )
        enriched_items = enrich_items_with_summary_zh(validated_items, config)
        domestic_count = len(domestic_items)
        domestic_items = enriched_items[:domestic_count]
        international_items = enriched_items[domestic_count:]

    snapshot_path = build_snapshot_path(temp_output_dir, target_date)
    snapshot_payload = {
        "target_date": target_date.isoformat(),
        "generated_at": date.today().isoformat(),
        "domestic_items": domestic_items,
        "international_items": international_items,
        "diagnostics": {
            "collected_count": len(collected_items),
            "quality_retained_count": len(quality_items),
            "deduplicated_count": len(deduped_items),
            "selected_count": len(domestic_items) + len(international_items),
            "quality_stats": quality_stats,
            "quality_excluded": quality_excluded,
            "duplicate_report": duplicate_report,
            "selection": selection_diagnostics,
            "selection_summary": summarize_selection(domestic_items + international_items),
            "summary_runtime": get_summary_runtime(config),
        },
    }
    snapshot_path.write_text(
        json.dumps(_json_safe(snapshot_payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    selected_count = len(domestic_items) + len(international_items)
    logging.info(
        "Pipeline snapshot written to %s (%d selected from %d collected)",
        snapshot_path,
        selected_count,
        len(collected_items),
    )

    if not dry_run:
        report_path = render_daily_docx(
            config,
            target_date,
            domestic_items,
            international_items,
            overwrite=overwrite,
        )
        logging.info("DOCX report written to %s", report_path)

    return snapshot_path, selected_count


def main() -> int:
    args = _parse_args()
    target_date_arg = args.date_option or args.date
    try:
        _snapshot_path, selected_count = run_pipeline(
            target_date_arg,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
    except Exception:
        logging.exception("Economic-news pipeline failed")
        return 1

    # A technically successful run with no usable items should be treated as a
    # failed refresh by the web service so it retains its last good data.
    return 0 if selected_count > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
