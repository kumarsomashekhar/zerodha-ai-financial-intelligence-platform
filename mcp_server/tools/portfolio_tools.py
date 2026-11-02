"""Portfolio tools exposed through the MCP server. They reuse the existing analytics code."""
from backend.services import analytics


def list_portfolios() -> list[str]:
    """List the portfolio IDs that can be analysed. LIVE is the real Zerodha account and only works after logging in through the app."""
    return analytics.list_portfolios()


def get_portfolio_metrics(portfolio_id: str) -> dict:
    """Return holdings, weights, sector exposure and totals for one portfolio, computed from stored data."""
    try:
        return analytics.compute_metrics(analytics.load_portfolio(portfolio_id))
    except (KeyError, ValueError) as e:
        return {"error": str(e)}


def get_risk_alerts(portfolio_id: str) -> dict:
    """Return the rule-based risk alerts for one portfolio: sector and single-stock concentration, low diversification, high volatility and stale data."""
    try:
        metrics = analytics.compute_metrics(analytics.load_portfolio(portfolio_id))
    except (KeyError, ValueError) as e:
        return {"error": str(e)}
    alerts = analytics.risk_alerts(metrics)
    return {"portfolio_id": portfolio_id, "alert_count": len(alerts), "alerts": alerts}