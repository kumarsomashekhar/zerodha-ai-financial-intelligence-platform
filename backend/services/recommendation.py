"""Turns analytics + validated explanation into reviewable cards. No buy/sell language."""
DISCLAIMER = "Educational information based on the data snapshot shown. Not investment advice."

REVIEW_TEXT = {
    "sector_concentration": "Review how much of your portfolio depends on one sector.",
    "single_stock_concentration": "Review whether one holding is a larger share than you intended.",
    "low_diversification": "Review whether the number of holdings matches your risk preference.",
    "high_volatility": "Review whether the level of price swings fits your comfort with risk.",
    "stale_data": "Refresh market data before relying on these figures.",
}


def confidence_level(m: dict) -> str:
    if m["data_age_days"] > 3:
        return "low"
    if m["holdings_count"] < 5:
        return "medium"
    return "high"


def build_cards(m: dict, alerts: list[dict], explanation: dict) -> list[dict]:
    freshness = {"age_days": m["data_age_days"], "stale": m["data_age_days"] > 3}
    conf = confidence_level(m)
    cards = [{
        "id": "summary",
        "category": "educational_insight",
        "title": "Portfolio summary",
        "rationale": explanation["summary"],
        "details": explanation["key_drivers"] + [explanation["risk_note"]],
        "metrics": {"total_pnl_pct": m["total_pnl_pct"], "holdings": m["holdings_count"]},
        "freshness": freshness, "confidence": conf, "disclaimer": DISCLAIMER,
    }]
    for i, a in enumerate(alerts):
        cards.append({
            "id": f"alert-{i}",
            "category": "risk_alert",
            "title": a["type"].replace("_", " ").title(),
            "rationale": f"{a['metric']} is {a['value']} against a review threshold of {a['threshold']}.",
            "details": [REVIEW_TEXT.get(a["type"], "Review this item.")],
            "metrics": {"value": a["value"], "threshold": a["threshold"], "severity": a["severity"]},
            "freshness": freshness, "confidence": conf, "disclaimer": DISCLAIMER,
        })
    return cards
