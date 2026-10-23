BODY = {"symbol": "kohc", "eps": 22.1, "price": 97.42, "growth_pct": 8, "terminal_pct": 3.5}


def test_anonymous_blocked(app):
    from fastapi.testclient import TestClient
    c = TestClient(app)
    assert c.post("/api/valuation/calculate", json=BODY).status_code == 401
    assert c.get("/api/valuation/saved").status_code == 401


def test_calculate_matches_reference(make_user):
    c, _ = make_user()
    r = c.post("/api/valuation/calculate", json=BODY).json()
    assert round(r["implied_growth_pct"], 1) == -10.5
    assert round(r["fair_value"]) == 201
    assert len(r["sensitivity"]["growth_pct"]) == 19


def test_bad_inputs_rejected(make_user):
    c, _ = make_user()
    assert c.post("/api/valuation/calculate", json={**BODY, "years": 7}).status_code == 422
    assert c.post("/api/valuation/calculate", json={**BODY, "eps": -1}).status_code == 422
    # required return (5.6%) not above terminal growth (8%) -> math would break
    bad = {**BODY, "rf_pct": 5, "erp_pct": 2, "beta": 0.3, "terminal_pct": 8}
    assert c.post("/api/valuation/calculate", json=bad).status_code == 422


def test_save_list_delete_and_isolation(make_user):
    a, _ = make_user()
    b, _ = make_user()
    sid = a.post("/api/valuation/saved", json=BODY).json()["id"]
    assert [x["symbol"] for x in a.get("/api/valuation/saved").json()] == ["KOHC"]
    assert b.get("/api/valuation/saved").json() == []                    # B cannot see A's rows
    assert b.delete(f"/api/valuation/saved/{sid}").status_code == 404    # ... or delete them
    assert a.delete(f"/api/valuation/saved/{sid}").status_code == 200
    assert a.get("/api/valuation/saved").json() == []


def test_explain_falls_back_without_ai_key(make_user):
    c, _ = make_user()
    r = c.post("/api/valuation/explain", json=BODY).json()
    assert r["source"] == "fallback" and "Educational only" in r["text"]