from __future__ import annotations

import json
from subprocess import CompletedProcess
import urllib.request

import news_service


def test_gemini_news_evaluation_uses_generate_content(monkeypatch):
    expected = {
        "dir": "up",
        "sentiment": "Positive",
        "strength": 2,
        "summary": "Demand improves",
        "detail": "Higher demand can support sector earnings.",
        "confidence": 82,
    }
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            body = {
                "candidates": [{
                    "content": {"parts": [{"text": json.dumps(expected)}]},
                }],
            }
            return json.dumps(body).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["api_key"] = request.get_header("X-goog-api-key")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = news_service._evaluate_llm(
        "Industrial demand rises",
        "Sales increased during the quarter.",
        "LUCK",
        "Cement",
        "test-api-key",
        provider="gemini",
    )

    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-test-model:generateContent"
    )
    assert captured["api_key"] == "test-api-key"
    assert captured["payload"]["contents"][0]["parts"][0]["text"]
    assert captured["payload"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["timeout"] == 8
    assert result == {**expected, "evaluator": "llm"}


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
