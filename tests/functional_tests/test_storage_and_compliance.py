"""Functional tests: storage, compliance flags and operations numbers.
Every test uses a temporary database, so the real data/app.db is never touched."""
import json

import pytest

from backend.services import compliance_service, storage


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_FILE", tmp_path / "test.db")
    storage.init_db()
    return tmp_path


def make_job(job_id, portfolio="diversified", status="completed", provider="gemini",
             vstatus="passed", issues=None, error=None):
    job = {
        "job_id": job_id,
        "status": status,
        "created_at": "2026-10-29T10:00:00+00:00",
        "request": {"portfolio_id": portfolio},
        "stages": [{"stage": "llm_analysis", "ms": 10.0}] if status == "completed" else [],
    }
    if error:
        job["error"] = error
    if status == "completed":
        job["audit"] = {
            "provider": provider,
            "prompt_version": "v2",
            "validation_status": vstatus,
            "validation_issues": issues or [],
        }
    return job


def test_job_round_trip(db):
    storage.save_job(make_job("j1"))
    job = storage.get_job("j1")
    assert job["status"] == "completed"
    assert "audit" not in job  # the audit trail is kept apart from the public result
    audit = storage.get_audit("j1")
    assert audit["provider"] == "gemini"
    assert audit["stages"][0]["stage"] == "llm_analysis"
    assert storage.get_job("missing") is None


def test_job_exists(db):
    storage.save_job(make_job("j1"))
    assert storage.job_exists("j1")
    assert not storage.job_exists("nope")


def test_feedback_round_trip(db):
    storage.save_feedback({"job_id": "j1", "card_id": "summary", "helpful": True, "note": "", "at": "now"})
    rows = storage.list_feedback()
    assert len(rows) == 1
    assert rows[0]["helpful"] is True
    assert rows[0]["card_id"] == "summary"


def test_snapshot_round_trip(db):
    storage.save_snapshot("j1", "diversified", json.dumps([{"symbol": "INFY", "quantity": 65}]))
    snap = storage.get_snapshot("j1")
    assert snap["portfolio_id"] == "diversified"
    assert snap["holdings"][0]["symbol"] == "INFY"
    assert storage.get_snapshot("none") is None


def test_audit_row_shows_snapshot_flag(db):
    storage.save_job(make_job("j1"))
    storage.save_job(make_job("j2"))
    storage.save_snapshot("j1", "diversified", "[]")
    rows = {r["job_id"]: r for r in storage.list_audit_rows()}
    assert rows["j1"]["has_snapshot"] is True
    assert rows["j2"]["has_snapshot"] is False


def test_quality_history_grows(db):
    assert storage.latest_quality_run() is None
    storage.save_quality_run({"price_rows": 10}, ["flag a"], "report text")
    storage.save_quality_run({"price_rows": 12}, ["flag a"], "report text")
    run = storage.latest_quality_run()
    assert run["runs_saved"] == 2
    assert run["flags"] == ["flag a"]
    assert run["metrics"]["price_rows"] == 12


def test_latest_review_wins(db):
    storage.save_job(make_job("j1"))
    storage.save_review("j1", "needs_follow_up", "check this", "alice")
    storage.save_review("j1", "approved", "all fine", "bob")
    review = storage.latest_reviews()["j1"]
    assert review["decision"] == "approved"
    assert review["reviewer"] == "bob"


def test_compliance_flags_and_review_counts(db):
    storage.save_job(make_job("ok"))
    storage.save_job(make_job("bad", status="failed", error="Not logged in"))
    storage.save_job(make_job("rej", vstatus="fallback_used", provider="template_fallback",
                              issues=["number 88 not found in analytics data"]))

    summary = compliance_service.summary()
    assert summary["counts"]["analyses_audited"] == 3
    assert summary["counts"]["flagged"] == 2
    assert summary["counts"]["awaiting_review"] == 2
    assert summary["counts"]["reviewed"] == 0
    assert {f["job_id"] for f in summary["flags"]} == {"bad", "rej"}
    reasons = [r for f in summary["flags"] for r in f["reasons"]]
    assert any("Job failed" in r for r in reasons)
    assert any("rejected" in r for r in reasons)
    assert summary["disclosures"]

    storage.save_review("bad", "approved", "expected during testing", "reviewer")
    after = compliance_service.summary()["counts"]
    assert after["awaiting_review"] == 1
    assert after["reviewed"] == 1


def test_selftest_row_is_ignored(db):
    storage.save_job(make_job("selftest", portfolio="demo"))
    storage.save_job(make_job("j1"))
    assert compliance_service.summary()["counts"]["analyses_audited"] == 1
    assert storage.ops_summary()["job_health"]["total_jobs"] == 1


def test_ops_summary_numbers(db):
    storage.save_job(make_job("ok"))
    storage.save_job(make_job("bad", status="failed", error="Not logged in"))
    storage.save_job(make_job("rej", vstatus="fallback_used", provider="template_fallback",
                              issues=["number 88 not found in analytics data"]))
    storage.save_feedback({"job_id": "ok", "card_id": "summary", "helpful": True, "note": "", "at": "now"})
    storage.save_feedback({"job_id": "rej", "card_id": "summary", "helpful": False, "note": "", "at": "now"})

    ops = storage.ops_summary()
    assert ops["job_health"]["total_jobs"] == 3
    assert ops["job_health"]["by_status"] == {"completed": 2, "failed": 1}
    assert ops["job_health"]["avg_stage_ms"]["llm_analysis"] == 10.0
    assert ops["output_quality"]["validation"] == {"passed": 1, "fallback_used": 1}
    assert ops["output_quality"]["validation_pass_rate_pct"] == 50.0
    assert ops["output_quality"]["helpful_rate_pct"] == 50.0
    assert ops["adoption"]["feedback_count"] == 2
    types = {e["type"] for e in ops["exceptions"]}
    assert {"failed_job", "ai_output_rejected"} <= types


def test_ops_summary_with_no_data(db):
    ops = storage.ops_summary()
    assert ops["job_health"]["total_jobs"] == 0
    assert ops["output_quality"]["validation_pass_rate_pct"] is None
    assert ops["output_quality"]["helpful_rate_pct"] is None
    assert ops["exceptions"] == []