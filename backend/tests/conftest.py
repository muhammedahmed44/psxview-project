"""Shared test setup. Uses a throw-away SQLite file, never the real database."""
import os
import tempfile
import uuid

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["GEMINI_API_KEY"] = ""
os.environ["COOKIE_SECURE"] = "0"

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import valuation
from db import init_db


@pytest.fixture(scope="session")
def app():
    init_db()
    test_app = FastAPI()
    test_app.include_router(auth.router)
    test_app.include_router(valuation.router)
    return test_app


@pytest.fixture
def make_user(app):
    """Call make_user() -> (logged-in client, email)."""
    def _make():
        client = TestClient(app)
        email = f"{uuid.uuid4().hex[:8]}@example.com"
        registered = client.post(
            "/api/auth/register",
            json={"name": "Test", "email": email, "password": "password1"},
        )
        assert registered.status_code == 201
        body = registered.json()
        code = pyotp.TOTP(body["setup"]["manual_key"]).now()
        verified = client.post(
            "/api/auth/verify-totp",
            json={"challenge_token": body["challenge_token"], "code": code},
        )
        assert verified.status_code == 200
        return client, email

    return _make
