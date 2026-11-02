"""Compliance panel logic: disclosures, audit trail, policy flags and reviewer status."""
from backend.services import storage

DISCLOSURES = [
    "Educational information only. Nothing here is investment advice, a recommendation to buy, sell or hold, or a prediction of future returns.",
    "Past prices are not a guide to future results. Benchmark figures are a what-if view using assumed quantities, not real trading history.",
    "Numbers come from deterministic analytics code. An AI model only explains them. Every AI answer is checked: it is rejected if it invents a number or uses advice or prediction language, and a safe template is used instead.",
    "Market prices come from Yahoo Finance, news from GNews, and live holdings from the user's own Zerodha account through Kite Connect. Sample portfolios use fixed sample prices stored with the portfolio.",
    "News publication dates are not the moment a stock reacted to the news, so no cause is claimed.",
    "Sector labels for the LIVE portfolio are not available yet, and the sample portfolios are illustrative.",
]


def summary(limit: int = 25) -> dict:
    rows = storage.list_audit_rows(limit)
    reviews = storage.latest_reviews()

    flags = []
    for r in rows:
        reasons = []
        if r["status"] == "failed":
            reasons.append(f"Job failed: {r['error'] or 'unknown error'}")
        if r["validation_status"] == "fallback_used":
            detail = "; ".join(r["validation_issues"]) or "no detail recorded"
            reasons.append(f"AI answer rejected by validation ({detail}); safe template used instead")
        if reasons:
            flags.append({
                "job_id": r["job_id"],
                "portfolio_id": r["portfolio_id"],
                "created_at": r["created_at"],
                "reasons": reasons,
                "review": reviews.get(r["job_id"]),
            })

    for r in rows:
        r["review"] = reviews.get(r["job_id"])

    quality = storage.latest_quality_run()
    return {
        "disclosures": DISCLOSURES,
        "counts": {
            "analyses_audited": len(rows),
            "flagged": len(flags),
            "awaiting_review": sum(1 for f in flags if not f["review"]),
            "reviewed": sum(1 for f in flags if f["review"]),
        },
        "flags": flags,
        "data_flags": quality["flags"] if quality else [],
        "audit_trail": rows,
    }