"""Basic tests for auth flows: register, login, OTP, and /me."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from main import app


def test_register_and_login_flow(monkeypatch):
    # Ensure email sending does not require real SMTP.
    import emailer

    sent = {}

    def fake_send(email: str, code: str) -> None:
        sent.setdefault(email, []).append(code)

    monkeypatch.setattr(emailer, "send_otp", fake_send)

    client = TestClient(app)
    email = f"{uuid.uuid4().hex[:8]}@example.com"

    # Register
    r = client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": "password1"},
    )
    assert r.status_code == 201
    challenge = r.json()["challenge_token"]
    assert sent[email]
    code = sent[email][0]

    # Verify OTP to establish session
    r = client.post(
        "/api/auth/verify-otp",
        json={"challenge_token": challenge, "code": code},
    )
    assert r.status_code == 200
    assert r.json()["email"] == email

    # /me should now work with session cookie
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == email


def test_me_requires_auth():
    client = TestClient(app)
    r = client.get("/api/auth/me")
    assert r.status_code == 401
