"""Email-provider routing tests."""

import config
import emailer

REAL_SEND_OTP = emailer.send_otp


def test_resend_uses_https_api(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(config, "RESEND_API_KEY", "re_test")
    monkeypatch.setattr(config, "RESEND_FROM", "PSXviewAI <onboarding@resend.dev>")
    monkeypatch.setattr(config, "SMTP_HOST", "")
    monkeypatch.setattr(emailer.httpx, "post", fake_post)
    monkeypatch.setattr(emailer, "send_otp", REAL_SEND_OTP)

    emailer.send_otp("reader@example.com", "123456")

    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer re_test"
    assert captured["json"]["to"] == ["reader@example.com"]
    assert "123456" in captured["json"]["text"]
