"""Shared test setup. Uses a throw-away SQLite file, never your real database."""
import os
import tempfile
import uuid

# These MUST be set before the app code is imported.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["GEMINI_API_KEY"] = ""          # tests must never call the real AI

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import emailer
import valuation
from db import init_db

CODES: list[str] = []                      # every "emailed" 2FA code lands here


@pytest.fixture(autouse=True)
def capture_codes(monkeypatch):
    monkeypatch.setattr(emailer, "send_otp", lambda to, code: CODES.append(code))


@pytest.fixture(scope="session")
def app():
    init_db()
    a = FastAPI()
    a.include_router(auth.router)
    a.include_router(valuation.router)
    return a


@pytest.fixture
def codes():
    return CODES


@pytest.fixture
def make_user(app):
    """Call make_user() -> (client_with_login_cookie, email). Each call = new user."""
    def _make():
        c = TestClient(app)
        email = f"{uuid.uuid4().hex[:8]}@example.com"
        ch = c.post("/api/auth/register", json={"name": "Test", "email": email, "password": "password1"}).json()["challenge_token"]
        assert c.post("/api/auth/verify-otp", json={"challenge_token": ch, "code": CODES[-1]}).status_code == 200
        return c, email
    return _make