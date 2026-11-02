"""AI output tests: the benchmark explanation's number check and its safe template."""
from backend.services import llm

BENCH = {
    "kpis": {
        "Start date": "2025-10-29",
        "End date": "2026-10-29",
        "Portfolio return (%)": -23.4,
        "Nifty 50 return (%)": -12.2,
        "Return versus Nifty 50 (percentage points)": -11.2,
        "Portfolio volatility (% a year)": 25.4,
        "Nifty 50 volatility (% a year)": 13.8,
        "Portfolio max drawdown (%)": -39.5,
        "Nifty 50 max drawdown (%)": -15.6,
    },
    "sector_weights_pct": {"IT": 91.5, "FMCG": 4.8},
}


def test_template_has_the_three_expected_parts():
    out = llm.benchmark_template(BENCH)
    assert set(out) == {"summary", "key_drivers", "risk_note"}
    assert isinstance(out["key_drivers"], list) and out["key_drivers"]


def test_template_only_uses_numbers_from_the_data():
    out = llm.benchmark_template(BENCH)
    assert llm._numbers_ok(out, BENCH)


def test_an_invented_number_is_caught():
    fake = {"summary": "The portfolio fell 99.9% over the year.", "key_drivers": [], "risk_note": ""}
    assert not llm._numbers_ok(fake, BENCH)


def test_template_says_behind_when_the_portfolio_trails():
    assert "behind" in llm.benchmark_template(BENCH)["summary"]


def test_template_says_ahead_when_the_portfolio_leads():
    bench = {**BENCH, "kpis": {**BENCH["kpis"], "Return versus Nifty 50 (percentage points)": 3.0}}
    assert "ahead of" in llm.benchmark_template(bench)["summary"]