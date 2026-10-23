"""Regression tests for the source-grounded research assistant."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import assistant
import main


def test_ask_matches_individual_headline_words(monkeypatch):
    monkeypatch.setattr(main, "get_companies", lambda: [])
    monkeypatch.setattr(
        main,
        "get_news",
        lambda: ([{
            "symbol": "OGDC",
            "headline": "Oil production rises",
            "time": "2026-10-22",
            "detail": "Output increased.",
        }], []),
    )

    app = FastAPI()
    app.include_router(assistant.router)
    response = TestClient(app).post("/api/research/ask", json={"question": "What happened to oil?"})

    assert response.status_code == 200
    assert "Oil production rises" in response.json()["answer"]
