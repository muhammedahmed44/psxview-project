from fastapi.testclient import TestClient




def test_protected_routes_reject_anonymous(app):
    c = TestClient(app)
    assert c.get("/api/auth/me").status_code == 401


def test_register_then_2fa_then_me(app, codes):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"name": "Ada", "email": "Ada@x.com", "password": "password1"})
    assert r.status_code == 201
    ch = r.json()["challenge_token"]
    assert c.get("/api/auth/me").status_code == 401                      # password alone is not enough
    wrong = "000000" if codes[-1] != "000000" else "111111"
    assert c.post("/api/auth/verify-otp", json={"challenge_token": ch, "code": wrong}).status_code == 400
    ok = c.post("/api/auth/verify-otp", json={"challenge_token": ch, "code": codes[-1]})
    assert ok.status_code == 200 and ok.json()["email"] == "ada@x.com"   # email lower-cased
    assert c.get("/api/auth/me").json()["name"] == "Ada"
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401


def test_duplicate_email_and_bad_password(app):
    c = TestClient(app)
    assert c.post("/api/auth/register", json={"name": "A", "email": "ada@x.com", "password": "password1"}).status_code == 409
    assert c.post("/api/auth/login", json={"email": "ada@x.com", "password": "wrong"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "nobody@x.com", "password": "wrong"}).status_code == 401
    assert c.post("/api/auth/register", json={"name": "A", "email": "new@x.com", "password": "short"}).status_code == 422


def test_login_flow_and_lockout(app, codes):
    c = TestClient(app)
    ch = c.post("/api/auth/login", json={"email": "ada@x.com", "password": "password1"}).json()["challenge_token"]
    real = codes[-1]
    bad = "000000" if real != "000000" else "111111"
    for _ in range(5):
        assert c.post("/api/auth/verify-otp", json={"challenge_token": ch, "code": bad}).status_code == 400
    # 6th try is blocked even with the right code
    assert c.post("/api/auth/verify-otp", json={"challenge_token": ch, "code": real}).status_code == 429


def test_session_token_is_not_a_challenge_token(app, make_user):
    c, _ = make_user()
    session = c.cookies.get("psx_session")
    r = TestClient(app).post("/api/auth/verify-otp", json={"challenge_token": session, "code": "123456"})
    assert r.status_code == 401