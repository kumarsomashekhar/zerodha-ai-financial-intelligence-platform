"""Edge cases: awkward inputs must give clear errors or the right alerts, never a crash or a silent wrong answer."""
import pandas as pd
import pytest

from backend.services import analytics


def make_df(pairs, price=100, qty=10, **extra):
    df = pd.DataFrame({
        "symbol": [s for s, _ in pairs],
        "sector": [x for _, x in pairs],
        "quantity": qty,
        "avg_price": price,
        "current_price": price,
    })
    for key, value in extra.items():
        df[key] = value
    return df


BALANCED = [("A", "S1"), ("B", "S2"), ("C", "S3"), ("D", "S4"), ("E", "S5"), ("F", "S6")]


def alert_types(df):
    metrics = analytics.compute_metrics(df)
    return {a["type"] for a in analytics.risk_alerts(metrics)}


def test_unknown_portfolio_raises_key_error():
    with pytest.raises(KeyError):
        analytics.load_portfolio("does_not_exist")


def test_missing_column_gives_a_clear_error(tmp_path, monkeypatch):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"portfolio_id": ["p"], "symbol": ["INFY"]}).to_csv(bad, index=False)
    monkeypatch.setattr(analytics, "DATA_FILE", bad)
    with pytest.raises(ValueError, match="missing columns"):
        analytics.load_portfolio("p")


def test_portfolio_worth_zero_is_refused():
    df = make_df(BALANCED)
    df["current_price"] = 0
    with pytest.raises(ValueError, match="no positive value"):
        analytics.compute_metrics(df)


def test_single_holding_triggers_the_three_concentration_alerts():
    assert alert_types(make_df([("INFY", "IT")])) == {
        "sector_concentration",
        "single_stock_concentration",
        "low_diversification",
    }


def test_balanced_portfolio_has_no_alerts():
    assert alert_types(make_df(BALANCED)) == set()


def test_stale_data_is_flagged():
    assert alert_types(make_df(BALANCED, data_age_days=5)) == {"stale_data"}


def test_high_volatility_is_flagged():
    assert "high_volatility" in alert_types(make_df(BALANCED, vol_30d_pct=50))


def test_weights_add_up_to_one_hundred():
    metrics = analytics.compute_metrics(make_df(BALANCED))
    total = sum(h["weight_pct"] for h in metrics["holdings"])
    assert total == pytest.approx(100, abs=0.5)