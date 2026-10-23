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
    assert response.json()["provenance"]["answer"] == "fallback"


def test_ask_uses_gemini_with_numbered_grounding(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_companies",
        lambda: [{
            "symbol": "OGDC",
            "name": "Oil & Gas Development Company",
            "sector": "Oil & Gas Exploration",
            "price": 298.45,
            "volume": "633.2K",
            "eps": 56.4,
            "asOf": "23 Oct 2026",
        }],
    )
    monkeypatch.setattr(main, "get_news", lambda: ([], []))
    captured = {}

    def fake_generate(prompt, fallback, **kwargs):
        captured["prompt"] = prompt
        captured["fallback"] = fallback
        captured["kwargs"] = kwargs
        return {"text": "OGDC is priced at Rs 298.45 [1]. Educational only, not investment advice.", "source": "gemini"}

    monkeypatch.setattr(assistant.ai, "generate_text", fake_generate)

    app = FastAPI()
    app.include_router(assistant.router)
    response = TestClient(app).post("/api/research/ask", json={"question": "Explain OGDC"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["answer"] == "gemini"
    assert payload["answer"].endswith("Educational only, not investment advice.")
    assert '"citation": 1' in captured["prompt"]
    assert '"price_pkr": 298.45' in captured["prompt"]
    assert captured["kwargs"]["purpose"] == "research answer"
