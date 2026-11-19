"""Functional tests: recommendation cards have distinct categories, full context and a policy check."""
from backend.services import recommendation

EXPLANATION = {"summary": "Your portfolio fell.", "key_drivers": ["IT dominates."], "risk_note": "Educational only."}
ALERT = {"type": "sector_concentration", "severity": "high",
         "metric": "IT sector weight", "value": 70.0, "threshold": 40.0}


def metrics(**over):
    m = {
        "holdings_count": 6,
        "total_pnl_pct": -4.2,
        "data_age_days": 0,
        "top_holding": {"symbol": "INFY", "weight_pct": 40.0},
        "sector_pct": {"IT": 70.0, "FMCG": 30.0},
        "holdings": [
            {"symbol": "INFY", "sector": "IT", "weight_pct": 40.0, "pnl_pct": -8.0, "contribution_pct": -3.5},
            {"symbol": "TCS", "sector": "IT", "weight_pct": 30.0, "pnl_pct": -6.0, "contribution_pct": -2.0},
            {"symbol": "ITC", "sector": "FMCG", "weight_pct": 30.0, "pnl_pct": 5.0, "contribution_pct": 1.3},
        ],
    }
    m.update(over)
    return m


def ids(cards):
    return {c["id"] for c in cards}


def test_three_distinct_categories_are_produced():
    cards = recommendation.build_cards(metrics(), [ALERT], EXPLANATION)
    assert {c["category"] for c in cards} == {"educational_insight", "risk_alert", "review_prompt"}


def test_every_card_carries_full_context():
    cards = recommendation.build_cards(metrics(), [ALERT], EXPLANATION, source={"portfolio_id": "demo"})
    for card in cards:
        for field in ("rationale", "details", "metrics", "freshness", "confidence",
                      "confidence_score", "source", "disclaimer", "policy_check"):
            assert field in card, f"{card['id']} is missing {field}"
        assert card["rationale"]
        assert card["source"] == {"portfolio_id": "demo"}
        assert card["policy_check"] == "passed"


def test_diversification_prompt_appears_only_when_flagged():
    assert "review-diversification" not in ids(recommendation.build_cards(metrics(), [], EXPLANATION))
    assert "review-diversification" in ids(recommendation.build_cards(metrics(), [ALERT], EXPLANATION))


def test_watchlist_prompt_names_the_largest_losers():
    cards = recommendation.build_cards(metrics(), [], EXPLANATION)
    watch = next(c for c in cards if c["id"] == "review-watchlist")
    assert watch["metrics"]["symbols"] == ["INFY", "TCS"]


def test_watchlist_prompt_still_appears_when_nothing_lost_money():
    holdings = [
        {"symbol": "A", "sector": "S", "weight_pct": 60.0, "pnl_pct": 2.0, "contribution_pct": 1.0},
        {"symbol": "B", "sector": "S", "weight_pct": 40.0, "pnl_pct": 9.0, "contribution_pct": 4.0},
    ]
    cards = recommendation.build_cards(metrics(holdings=holdings), [], EXPLANATION)
    watch = next(c for c in cards if c["id"] == "review-watchlist")
    assert watch["metrics"]["symbols"] == ["A", "B"]
    assert "No holding lost money" in watch["rationale"]
    assert "review-followup" in ids(cards)


def test_stale_data_lowers_confidence_and_marks_freshness():
    cards = recommendation.build_cards(metrics(data_age_days=5), [], EXPLANATION)
    summary = cards[0]
    assert summary["confidence"] == "low"
    assert summary["confidence_score"] == 0.3
    assert summary["freshness"]["stale"] is True


def test_policy_check_replaces_advice_language():
    bad = {**EXPLANATION, "summary": "You should buy more shares."}
    summary = recommendation.build_cards(metrics(), [], bad)[0]
    assert summary["policy_check"] == "replaced"
    assert summary["rationale"] == recommendation.SAFE_TEXT
    assert summary["details"] == []