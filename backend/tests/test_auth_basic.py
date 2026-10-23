"""Basic tests for auth flows: register, login, OTP, and /me."""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_register_and_login_flow(monkeypatch):
    # Ensure email sending does not require real SMTP.
    import emailer

    sent = {}

    def fake_send(email: str, code: str) -> None:
        sent.setdefault(email, []).append(code)

    monkeypatch.setattr(emailer, "send_otp_email", fake_send)

    # Register
    r = client.post("/api/auth/register", json={"email": "user@example.com", "password": "secret"})
    assert r.status_code == 200
    challenge = r.json()["challenge_token"]
    assert sent["user@example.com"]
    code = sent["user@example.com"][0]

    # Verify OTP to establish session
    r = client.post("/api/auth/verify-otp", json={"token": challenge, "code": code})
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"

    # /me should now work with session cookie
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"


def test_me_requires_auth():
    r = client.get("/api/auth/me")
    assert r.status_code == 401
