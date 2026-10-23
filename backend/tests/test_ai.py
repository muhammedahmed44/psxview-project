from __future__ import annotations

import ai


class _GeminiResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "candidates": [{
                "content": {
                    "parts": [
                        {"text": "Grounded answer "},
                        {"text": "with citation [1]."},
                    ]
                }
            }]
        }


def test_generate_text_calls_gemini_and_joins_text_parts(monkeypatch):
    monkeypatch.setattr(ai.config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(ai.config, "GEMINI_MODEL", "test-model")
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _GeminiResponse()

    monkeypatch.setattr(ai.httpx, "post", fake_post)

    result = ai.generate_text(
        "Use evidence [1]",
        "Fallback",
        max_output_tokens=1600,
        purpose="research answer",
    )

    assert result == {"text": "Grounded answer with citation [1].", "source": "gemini"}
    assert captured["url"].endswith("/models/test-model:generateContent")
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["json"]["contents"][0]["parts"][0]["text"] == "Use evidence [1]"
    assert captured["json"]["generationConfig"]["maxOutputTokens"] == 1600
    assert captured["json"]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}


def test_generate_text_falls_back_without_api_key(monkeypatch):
    monkeypatch.setattr(ai.config, "GEMINI_API_KEY", "")

    assert ai.generate_text("Prompt", "Safe fallback") == {
        "text": "Safe fallback",
        "source": "fallback",
    }
