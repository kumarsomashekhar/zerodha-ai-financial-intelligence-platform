"""Turns analytics + validated explanation into reviewable cards. No buy/sell language.

Three distinct categories:
  educational_insight  the plain-language summary
  risk_alert           one card per rule-based alert
  review_prompt        neutral prompts to review something: diversification, watchlist, follow-up

Every card carries its freshness, a rule-based confidence (level and score), the source of its
data, and the result of a policy check on its text.
"""
from backend.services.validation import BANNED

DISCLAIMER = "Educational information based on the data snapshot shown. Not investment advice."

REVIEW_TEXT = {
    "sector_concentration": "Review how much of your portfolio depends on one sector.",
    "single_stock_concentration": "Review whether one holding is a larger share than you intended.",
    "low_diversification": "Review whether the number of holdings matches your risk preference.",
    "high_volatility": "Review whether the level of price swings fits your comfort with risk.",
    "stale_data": "Refresh market data before relying on these figures.",
}

# Rule-based, not statistically calibrated: the score simply mirrors the level.
CONFIDENCE_SCORE = {"low": 0.3, "medium": 0.6, "high": 0.9}

DIVERSIFICATION_TYPES = {"sector_concentration", "single_stock_concentration", "low_diversification"}

SAFE_TEXT = "This item was withheld by a content policy check. Please review the underlying figures."


def confidence_level(m: dict) -> str:
    if m["data_age_days"] > 3:
        return "low"
    if m["holdings_count"] < 5:
        return "medium"
    return "high"


def _policy_check(card: dict) -> dict:
    """Last check before a card reaches the dashboard: advice or prediction wording is replaced."""
    text = " ".join([card["title"], card["rationale"], *map(str, card["details"])])
    if BANNED.search(text):
        card["rationale"] = SAFE_TEXT
        card["details"] = []
        card["policy_check"] = "replaced"
    else:
        card["policy_check"] = "passed"
    return card


def build_cards(m: dict, alerts: list[dict], explanation: dict, source: dict | None = None) -> list[dict]:
    source = source or {}
    freshness = {"age_days": m["data_age_days"], "stale": m["data_age_days"] > 3}
    conf = confidence_level(m)
    base = {
        "freshness": freshness,
        "confidence": conf,
        "confidence_score": CONFIDENCE_SCORE[conf],
        "source": source,
        "disclaimer": DISCLAIMER,
    }

    cards = [{
        "id": "summary",
        "category": "educational_insight",
        "title": "Portfolio summary",
        "rationale": explanation["summary"],
        "details": explanation["key_drivers"] + [explanation["risk_note"]],
        "metrics": {"total_pnl_pct": m["total_pnl_pct"], "holdings": m["holdings_count"]},
        **base,
    }]

    for i, a in enumerate(alerts):
        cards.append({
            "id": f"alert-{i}",
            "category": "risk_alert",
            "title": a["type"].replace("_", " ").title(),
            "rationale": f"{a['metric']} is {a['value']} against a review threshold of {a['threshold']}.",
            "details": [REVIEW_TEXT.get(a["type"], "Review this item.")],
            "metrics": {"value": a["value"], "threshold": a["threshold"], "severity": a["severity"]},
            **base,
        })

    top_sector, top_sector_pct = next(iter(m["sector_pct"].items()))

    # Review prompt 1: diversification review, only when a concentration or diversification flag exists
    flagged = [a for a in alerts if a["type"] in DIVERSIFICATION_TYPES]
    if flagged:
        cards.append({
            "id": "review-diversification",
            "category": "review_prompt",
            "title": "Diversification review",
            "rationale": f"{len(flagged)} concentration or diversification flag(s) were raised for this snapshot.",
            "details": [REVIEW_TEXT[a["type"]] for a in flagged],
            "metrics": {
                "flags": len(flagged),
                "top_holding": m["top_holding"]["symbol"],
                "top_holding_weight_pct": m["top_holding"]["weight_pct"],
                "top_sector": top_sector,
                "top_sector_pct": top_sector_pct,
            },
            **base,
        })

    # Review prompt 2: watchlist monitoring, naming the two holdings that contributed least to return
    weakest = sorted(m["holdings"], key=lambda h: h["contribution_pct"])[:2]
    if weakest:
        any_loss = any(h["contribution_pct"] < 0 for h in weakest)
        cards.append({
            "id": "review-watchlist",
            "category": "review_prompt",
            "title": "Watchlist monitoring",
            "rationale": (
                "These holdings reduced the portfolio's return the most in this snapshot."
                if any_loss
                else "No holding lost money in this snapshot. These contributed the least to the portfolio's return."
            ),
            "details": [
                f"{h['symbol']}: {h['contribution_pct']}% contribution to return, "
                f"{h['weight_pct']}% of the portfolio"
                for h in weakest
            ] + ["Review whether you want to monitor these holdings more closely."],
            "metrics": {
                "symbols": [h["symbol"] for h in weakest],
                "contributions_pct": [h["contribution_pct"] for h in weakest],
            },
            **base,
        })

    # Review prompt 3: summary follow-up, always present
    cards.append({
        "id": "review-followup",
        "category": "review_prompt",
        "title": "Summary follow-up",
        "rationale": f"This summary reflects data that was {m['data_age_days']} day(s) old when it was analysed.",
        "details": ["Run the analysis again after your next data refresh and compare the total return "
                    "and the largest sector weight shown here."],
        "metrics": {
            "total_pnl_pct": m["total_pnl_pct"],
            "top_sector": top_sector,
            "top_sector_pct": top_sector_pct,
            "data_age_days": m["data_age_days"],
        },
        **base,
    })

    return [_policy_check(c) for c in cards]