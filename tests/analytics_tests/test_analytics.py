from backend.services import analytics, llm, validation


def _run(pid):
    m = analytics.compute_metrics(analytics.load_portfolio(pid))
    return m, analytics.risk_alerts(m)


def test_diversified_has_no_alerts():
    _, alerts = _run("diversified")
    assert alerts == []


def test_concentrated_flags_sector_and_stock():
    _, alerts = _run("concentrated_it")
    types = {a["type"] for a in alerts}
    assert {"sector_concentration", "single_stock_concentration"} <= types


def test_volatile_flags_volatility():
    _, alerts = _run("volatile_smallcap")
    assert "high_volatility" in {a["type"] for a in alerts}


def test_stale_data_flagged():
    _, alerts = _run("stale_data")
    assert "stale_data" in {a["type"] for a in alerts}


def test_limited_holdings_flagged():
    _, alerts = _run("limited_holdings")
    assert "low_diversification" in {a["type"] for a in alerts}


def test_unknown_portfolio_raises():
    try:
        analytics.load_portfolio("nope")
        assert False
    except KeyError:
        pass


def test_validation_accepts_template_and_rejects_invented_numbers():
    m, alerts = _run("concentrated_it")
    ctx = {"metrics": m, "alerts": alerts, "alert_count": len(alerts)}
    good = llm.template_explanation(ctx)
    assert validation.validate(good, ctx)[0]
    bad = dict(good, summary="Your portfolio will double and you should buy more. Return is 999.9%.")
    ok, issues = validation.validate(bad, ctx)
    assert not ok and len(issues) >= 2
