import time
import uuid

import pyotp
from fastapi.testclient import TestClient


def _registration(client: TestClient, email: str):
    response = client.post(
        "/api/auth/register",
        json={"name": "Ada", "email": email, "password": "password1"},
    )
    assert response.status_code == 201
    return response.json()


def test_register_then_authenticator_setup_then_me(app):
    client = TestClient(app)
    email = f"ada-{uuid.uuid4().hex[:8]}@example.com"
    registration = _registration(client, email)

    assert registration["requires_setup"] is True
    assert registration["setup"]["qr_code_data_url"].startswith("data:image/svg+xml;base64,")
    assert client.get("/api/auth/me").status_code == 401

    challenge = registration["challenge_token"]
    secret = registration["setup"]["manual_key"]
    real_code = pyotp.TOTP(secret).now()
    wrong_code = "000000" if real_code != "000000" else "111111"
    assert client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": challenge, "code": wrong_code},
    ).status_code == 400

    verified = client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": challenge, "code": real_code},
    )
    assert verified.status_code == 200
    assert verified.json()["email"] == email
    assert len(verified.json()["recovery_codes"]) == 8
    assert client.get("/api/auth/me").json()["name"] == "Ada"
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_email_and_bad_password(app):
    client = TestClient(app)
    email = f"duplicate-{uuid.uuid4().hex[:8]}@example.com"
    _registration(client, email)
    assert client.post(
        "/api/auth/register",
        json={"name": "A", "email": email, "password": "password1"},
    ).status_code == 409
    assert client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrong"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
    ).status_code == 401
    assert client.post(
        "/api/auth/register",
        json={"name": "A", "email": f"new-{uuid.uuid4().hex}@example.com", "password": "short"},
    ).status_code == 422


def test_login_with_next_authenticator_code(app, monkeypatch):
    import security

    client = TestClient(app)
    email = f"login-{uuid.uuid4().hex[:8]}@example.com"
    start = int(time.time())
    monkeypatch.setattr(security.time, "time", lambda: start)
    registration = _registration(client, email)
    secret = registration["setup"]["manual_key"]
    first_code = pyotp.TOTP(secret).at(start)
    assert client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": registration["challenge_token"], "code": first_code},
    ).status_code == 200
    client.post("/api/auth/logout")

    monkeypatch.setattr(security.time, "time", lambda: start + 30)
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password1"},
    )
    assert login.status_code == 200
    assert login.json()["requires_setup"] is False
    assert login.json()["setup"] is None
    next_code = pyotp.TOTP(secret).at(start + 30)
    assert client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": login.json()["challenge_token"], "code": next_code},
    ).status_code == 200


def test_authenticator_lockout_after_five_wrong_codes(app):
    client = TestClient(app)
    email = f"lockout-{uuid.uuid4().hex[:8]}@example.com"
    registration = _registration(client, email)
    challenge = registration["challenge_token"]
    real_code = pyotp.TOTP(registration["setup"]["manual_key"]).now()
    wrong_code = "000000" if real_code != "000000" else "111111"
    for _ in range(5):
        assert client.post(
            "/api/auth/verify-totp",
            json={"challenge_token": challenge, "code": wrong_code},
        ).status_code == 400
    assert client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": challenge, "code": real_code},
    ).status_code == 429


def test_recovery_code_is_one_time(app):
    client = TestClient(app)
    email = f"recovery-{uuid.uuid4().hex[:8]}@example.com"
    registration = _registration(client, email)
    setup_code = pyotp.TOTP(registration["setup"]["manual_key"]).now()
    setup_result = client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": registration["challenge_token"], "code": setup_code},
    )
    recovery_codes = setup_result.json()["recovery_codes"]
    client.post("/api/auth/logout")

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password1"},
    ).json()
    used_code = recovery_codes[0]
    assert client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": login["challenge_token"], "code": used_code},
    ).status_code == 200
    client.post("/api/auth/logout")

    second_login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password1"},
    ).json()
    reused = client.post(
        "/api/auth/verify-totp",
        json={"challenge_token": second_login["challenge_token"], "code": used_code},
    )
    assert reused.status_code == 400
    assert reused.json()["detail"] == "Invalid or already-used recovery code"


def test_session_token_is_not_a_challenge_token(app, make_user):
    client, _ = make_user()
    session = client.cookies.get("psx_session")
    response = TestClient(app).post(
        "/api/auth/verify-totp",
        json={"challenge_token": session, "code": "123456"},
    )
    assert response.status_code == 401
