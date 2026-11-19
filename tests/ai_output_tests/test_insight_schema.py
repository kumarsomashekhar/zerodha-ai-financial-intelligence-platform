"""AI output tests: real analysis results must match data/insight_schema.json."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from backend.services import analytics, llm, recommendation, validation

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[2] / "data" / "insight_schema.json").read_text(encoding="utf-8")
)
PORTFOLIOS = ["concentrated_it", "diversified", "limited_holdings", "stale_data", "volatile_smallcap"]


def build_job(portfolio_id):
    """Runs the same steps as the analysis route, without the database or the AI."""
    df = analytics.load_portfolio(portfolio_id)
    metrics = analytics.compute_metrics(df)
    alerts = analytics.risk_alerts(metrics)
    ctx = {"metrics": metrics, "alerts": alerts, "alert_count": len(alerts), "timeframe": "1M"}
    explanation = llm.template_explanation(ctx)
    ok, issues = validation.validate(explanation, ctx)
    assert ok, issues  # the fallback template must itself pass the validator
    cards = recommendation.build_cards(
        metrics, alerts, explanation,
        source={"portfolio_id": portfolio_id, "snapshot": "/api/snapshot/test",
                "price_source": "sample portfolio file (fixed prices)", "explanation_by": "template"},
    )
    job = {
        "job_id": "test",
        "status": "completed",
        "created_at": "2026-11-05T10:00:00+00:00",
        "request": {"portfolio_id": portfolio_id, "timeframe": "1M", "insight_type": "summary"},
        "stages": [{"stage": "data_load", "ms": 1.0}, {"stage": "recommendation", "ms": 0.3}],
        "metrics": metrics,
        "alerts": alerts,
        "cards": cards,
    }
    return explanation, job


def problems(instance, validator):
    return [e.message for e in validator.iter_errors(instance)]


def test_the_schema_file_is_itself_valid():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("portfolio_id", PORTFOLIOS)
def test_a_real_job_and_its_explanation_match_the_schema(portfolio_id):
    explanation, job = build_job(portfolio_id)
    assert problems(job, Draft202012Validator(SCHEMA)) == []
    explanation_schema = {"$ref": "#/$defs/explanation", "$defs": SCHEMA["$defs"]}
    assert problems(explanation, Draft202012Validator(explanation_schema)) == []


def test_the_schema_rejects_an_unknown_card_category():
    _, job = build_job("diversified")
    job["cards"][0]["category"] = "buy_recommendation"
    assert problems(job, Draft202012Validator(SCHEMA))


def test_the_schema_rejects_a_card_without_a_disclaimer():
    _, job = build_job("diversified")
    del job["cards"][0]["disclaimer"]
    assert problems(job, Draft202012Validator(SCHEMA))