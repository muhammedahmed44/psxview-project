from __future__ import annotations

import json
from subprocess import CompletedProcess

import news_service


def test_load_latest_snapshot_skips_newer_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(news_service, "OUTPUT_DIR", tmp_path)
    (tmp_path / "2026-10-23_snapshot.json").write_text(
        json.dumps({"domestic_items": [], "international_items": []}),
        encoding="utf-8",
    )
    (tmp_path / "2026-10-22_snapshot.json").write_text(
        json.dumps({"domestic_items": [{"title": "Usable"}], "international_items": []}),
        encoding="utf-8",
    )

    snapshot = news_service.load_latest_pipeline_snapshot()

    assert snapshot is not None
    assert snapshot["domestic_items"][0]["title"] == "Usable"


def test_run_pipeline_once_accepts_non_empty_snapshot(tmp_path, monkeypatch):
    runner = tmp_path / "run_daily_news.py"
    runner.write_text("# test runner", encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(news_service, "PIPELINE_RUNNER", runner)
    monkeypatch.setattr(news_service, "PIPELINE_DIR", tmp_path)
    monkeypatch.setattr(news_service, "OUTPUT_DIR", output_dir)

    def fake_run(command, **_kwargs):
        target_date = command[command.index("--date") + 1]
        (output_dir / f"{target_date}_snapshot.json").write_text(
            json.dumps({"domestic_items": [{"title": "Live item"}], "international_items": []}),
            encoding="utf-8",
        )
        return CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(news_service.subprocess, "run", fake_run)

    assert news_service.run_pipeline_once(timeout_seconds=60) is True
    status = news_service.get_pipeline_status()
    assert status["running"] is False
    assert status["last_item_count"] == 1
    assert status["last_error"] is None


def test_run_pipeline_once_falls_back_when_today_is_empty(tmp_path, monkeypatch):
    runner = tmp_path / "run_daily_news.py"
    runner.write_text("# test runner", encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(news_service, "PIPELINE_RUNNER", runner)
    monkeypatch.setattr(news_service, "PIPELINE_DIR", tmp_path)
    monkeypatch.setattr(news_service, "OUTPUT_DIR", output_dir)
    attempted_dates = []

    def fake_run(command, **_kwargs):
        target_date = command[command.index("--date") + 1]
        attempted_dates.append(target_date)
        items = [] if len(attempted_dates) == 1 else [{"title": "Previous-day item"}]
        (output_dir / f"{target_date}_snapshot.json").write_text(
            json.dumps({"domestic_items": items, "international_items": []}),
            encoding="utf-8",
        )
        return CompletedProcess(command, 2 if not items else 0, stdout="", stderr="")

    monkeypatch.setattr(news_service.subprocess, "run", fake_run)

    assert news_service.run_pipeline_once(timeout_seconds=60) is True
    assert len(attempted_dates) == 2
    assert attempted_dates[0] > attempted_dates[1]
