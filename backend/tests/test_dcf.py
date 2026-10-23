import dcf


def test_matches_html_tool():
    r = dcf.required_return(0.11, 0.06, 1.0)
    assert round(dcf.solve_implied_growth(97.42, 22.1, r, 5) * 100, 1) == -10.5    # KOHC
    assert round(dcf.solve_implied_growth(212.74, 26.08, r, 5) * 100, 1) == 5.1    # DGKC
    assert round(dcf.dcf_value(22.1, 0.08, r, 0.035, 5)) == 201
    assert round(dcf.dcf_value(26.08, 0.08, r, 0.035, 5)) == 237


def test_absurd_price_returns_none():
    assert dcf.solve_implied_growth(1_000_000, 1.0, 0.17, 5) is None


def test_sensitivity_has_19_points():
    s = dcf.sensitivity(22.1, 97.42, 0.17, 0.035, 5)
    assert len(s["growth_pct"]) == len(s["upside_pct"]) == 19