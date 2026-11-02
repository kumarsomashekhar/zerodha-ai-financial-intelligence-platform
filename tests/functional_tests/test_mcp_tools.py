"""MCP tool tests. File-reading tools use small temporary files, so they don't depend on data/processed."""
import pandas as pd

from mcp_server.tools import analytics_tools, market_tools, news_tools, portfolio_tools

TODAY = pd.Timestamp.today().normalize()


# ---- portfolio tools (read the real sample file, read-only) ----
def test_list_portfolios_includes_live_and_samples():
    names = portfolio_tools.list_portfolios()
    assert "LIVE" in names
    assert "concentrated_it" in names


def test_metrics_for_unknown_portfolio_returns_an_error_message():
    result = portfolio_tools.get_portfolio_metrics("does_not_exist")
    assert "error" in result


def test_risk_alerts_for_a_known_portfolio():
    result = portfolio_tools.get_risk_alerts("concentrated_it")
    assert result["alert_count"] == len(result["alerts"])
    assert "sector_concentration" in {a["type"] for a in result["alerts"]}


def test_risk_alerts_for_unknown_portfolio_returns_an_error_message():
    assert "error" in portfolio_tools.get_risk_alerts("does_not_exist")


# ---- market tools ----
def write_prices(tmp_path, last_date):
    first_date = last_date - pd.Timedelta(days=365)
    pd.DataFrame({
        "Date": [str(first_date.date()), str(last_date.date())],
        "symbol": ["INFY", "INFY"],
        "Close": [100.0, 110.0],
    }).to_csv(tmp_path / "stock_prices_clean.csv", index=False)


def test_fresh_price_is_ok_and_symbol_is_normalised(tmp_path, monkeypatch):
    monkeypatch.setattr(market_tools, "PROC", tmp_path)
    write_prices(tmp_path, TODAY)
    result = market_tools.get_stock_price_summary("infy.ns")
    assert result["symbol"] == "INFY"
    assert result["latest_close"] == 110.0
    assert result["one_year_return_pct"] == 10.0
    assert result["price_age_days"] == 0
    assert result["freshness"] == "ok"


def test_stale_price_is_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(market_tools, "PROC", tmp_path)
    write_prices(tmp_path, TODAY - pd.Timedelta(days=10))
    result = market_tools.get_stock_price_summary("INFY")
    assert result["price_age_days"] == 10
    assert result["freshness"].startswith("stale")


def test_unknown_symbol_lists_what_is_available(tmp_path, monkeypatch):
    monkeypatch.setattr(market_tools, "PROC", tmp_path)
    write_prices(tmp_path, TODAY)
    result = market_tools.get_stock_price_summary("ZZZ")
    assert "error" in result
    assert "INFY" in result["error"]


# ---- news tools ----
def write_news(tmp_path):
    pd.DataFrame({
        "symbol": ["TCS", "TCS", "TCS", "INFY"],
        "mentions_company": [True, True, False, True],
        "published_at": ["2026-10-01", "2026-10-05", "2026-10-09", "2026-10-02"],
        "title": ["older", "newer", "unrelated", "other company"],
        "source": ["s", "s", "s", "s"],
        "url": ["https://a", "https://b", "https://c", "https://d"],
    }).to_csv(tmp_path / "news_all_stocks.csv", index=False)


def test_news_is_filtered_and_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(news_tools, "PROC", tmp_path)
    write_news(tmp_path)
    result = news_tools.get_recent_news("tcs")
    assert [a["title"] for a in result["articles"]] == ["newer", "older"]


def test_news_for_unknown_symbol_returns_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(news_tools, "PROC", tmp_path)
    write_news(tmp_path)
    assert "error" in news_tools.get_recent_news("ZZZ")


def test_news_limit_is_kept_in_range(tmp_path, monkeypatch):
    monkeypatch.setattr(news_tools, "PROC", tmp_path)
    write_news(tmp_path)
    assert len(news_tools.get_recent_news("TCS", limit=0)["articles"]) == 1


# ---- analytics tools ----
def test_benchmark_rejects_a_name_that_tries_to_leave_the_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics_tools, "PORTFOLIOS", tmp_path)
    result = analytics_tools.get_benchmark_comparison("../secret")
    assert result["error"] == "Invalid portfolio name"


def test_benchmark_for_a_missing_portfolio_returns_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics_tools, "PORTFOLIOS", tmp_path)
    assert "not available" in analytics_tools.get_benchmark_comparison("volatile_smallcap")["error"]


def test_benchmark_returns_the_saved_figures_with_whole_numbers_as_integers(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics_tools, "PORTFOLIOS", tmp_path)
    folder = tmp_path / "diversified"
    folder.mkdir()
    pd.Series({"Portfolio return (%)": -18.3, "Stocks analysed": 8.0}).to_csv(
        folder / "portfolio_kpis.csv", header=["value"]
    )
    kpis = analytics_tools.get_benchmark_comparison("diversified")["kpis"]
    assert kpis["Portfolio return (%)"] == -18.3
    assert kpis["Stocks analysed"] == 8
    assert isinstance(kpis["Stocks analysed"], int)