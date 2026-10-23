"""Basic smoke tests for authenticator registration and login."""
from __future__ import annotations

import uuid

import pyotp
from fastapi.testclient import TestClient

from main import app


def test_register_and_authenticator_flow():
    client = TestClient(app)
    email = f"{uuid.uuid4().hex[:8]}@example.com"

    registered = client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": "password1"},
    )
    assert registered.status_code == 201
    body = registered.json()
    code = pyotp.TOTP(body["setup"]["manual_key"]).now()

    verified = client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": body["challenge_token"], "code": code},
    )
    assert verified.status_code == 200
    assert verified.json()["email"] == email
    assert client.get("/api/auth/me").json()["email"] == email


def test_me_requires_auth():
    assert TestClient(app).get("/api/auth/me").status_code == 401
