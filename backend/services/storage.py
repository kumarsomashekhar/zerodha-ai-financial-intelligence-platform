"""Permanent storage in a small SQLite database file (no setup needed)."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_FILE = Path(__file__).resolve().parents[2] / "data" / "app.db"


def _connect() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                portfolio_id TEXT,
                status TEXT,
                created_at TEXT,
                public_json TEXT,
                audit_json TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                card_id TEXT,
                helpful INTEGER,
                note TEXT,
                at TEXT
            )"""
        )

def _ensure_snapshots(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS snapshots (
            job_id TEXT PRIMARY KEY,
            portfolio_id TEXT,
            taken_at TEXT,
            holdings_json TEXT
        )"""
    )


def save_snapshot(job_id: str, portfolio_id: str, holdings_json: str) -> None:
    """Keep the exact holdings and prices that one analysis was based on."""
    with _connect() as conn:
        _ensure_snapshots(conn)
        conn.execute(
            "INSERT OR REPLACE INTO snapshots (job_id, portfolio_id, taken_at, holdings_json) VALUES (?, ?, ?, ?)",
            (job_id, portfolio_id, datetime.now(timezone.utc).isoformat(), holdings_json),
        )


def get_snapshot(job_id: str) -> dict | None:
    with _connect() as conn:
        _ensure_snapshots(conn)
        row = conn.execute("SELECT * FROM snapshots WHERE job_id = ?", (job_id,)).fetchone()
    if not row:
        return None
    return {
        "job_id": row["job_id"],
        "portfolio_id": row["portfolio_id"],
        "taken_at": row["taken_at"],
        "holdings": json.loads(row["holdings_json"]),
    }

def save_job(job: dict) -> None:
    """Insert or update one insight job. The audit trail is stored separately."""
    public = {k: v for k, v in job.items() if k != "audit"}
    audit = job.get("audit", {})
    portfolio_id = (job.get("request") or {}).get("portfolio_id")
    with _connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO jobs
               (job_id, portfolio_id, status, created_at, public_json, audit_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                job["job_id"],
                portfolio_id,
                job.get("status"),
                job.get("created_at"),
                json.dumps(public, default=str),
                json.dumps(audit, default=str),
            ),
        )


def get_job(job_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT public_json FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return json.loads(row["public_json"]) if row else None


def get_audit(job_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT public_json, audit_json FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
    if not row:
        return None
    stages = json.loads(row["public_json"]).get("stages", [])
    return {"job_id": job_id, "stages": stages, **json.loads(row["audit_json"])}


def job_exists(job_id: str) -> bool:
    with _connect() as conn:
        return conn.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone() is not None


def save_feedback(entry: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO feedback (job_id, card_id, helpful, note, at) VALUES (?, ?, ?, ?, ?)",
            (
                entry["job_id"],
                entry["card_id"],
                1 if entry["helpful"] else 0,
                entry.get("note", ""),
                entry.get("at") or datetime.now(timezone.utc).isoformat(),
            ),
        )


def list_feedback(job_id: str | None = None) -> list[dict]:
    with _connect() as conn:
        if job_id:
            rows = conn.execute("SELECT * FROM feedback WHERE job_id = ? ORDER BY id", (job_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM feedback ORDER BY id").fetchall()
    return [dict(r) | {"helpful": bool(r["helpful"])} for r in rows]

def _ensure_quality(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS quality_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT,
            metrics_json TEXT,
            flags_json TEXT,
            report_text TEXT
        )"""
    )


def save_quality_run(metrics: dict, flags: list, report_text: str) -> None:
    with _connect() as conn:
        _ensure_quality(conn)
        conn.execute(
            "INSERT INTO quality_runs (run_at, metrics_json, flags_json, report_text) VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                json.dumps(metrics),
                json.dumps(flags),
                report_text,
            ),
        )


def latest_quality_run() -> dict | None:
    with _connect() as conn:
        _ensure_quality(conn)
        row = conn.execute("SELECT * FROM quality_runs ORDER BY id DESC LIMIT 1").fetchone()
        total = conn.execute("SELECT COUNT(*) FROM quality_runs").fetchone()[0]
    if not row:
        return None
    return {
        "run_at": row["run_at"],
        "runs_saved": total,
        "metrics": json.loads(row["metrics_json"]),
        "flags": json.loads(row["flags_json"]),
        "report_text": row["report_text"],
    }

def ops_summary() -> dict:
    """Numbers for the operations dashboard: job health, adoption, output quality, open exceptions."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT job_id, portfolio_id, status, created_at, public_json, audit_json "
            "FROM jobs WHERE job_id != 'selftest' ORDER BY rowid DESC"  # 'selftest' is our test row
        ).fetchall()
        fb = conn.execute("SELECT helpful FROM feedback").fetchall()

    by_status, by_portfolio, providers, validation = {}, {}, {}, {}
    stage_totals, stage_counts = {}, {}
    recent, exceptions = [], []

    for r in rows:
        public = json.loads(r["public_json"])
        audit = json.loads(r["audit_json"] or "{}")
        status = r["status"] or "unknown"
        provider = audit.get("provider")
        vstatus = audit.get("validation_status")
        stages = public.get("stages", [])
        total_ms = round(sum(s.get("ms", 0) for s in stages), 1)

        by_status[status] = by_status.get(status, 0) + 1
        by_portfolio[r["portfolio_id"]] = by_portfolio.get(r["portfolio_id"], 0) + 1
        if provider:
            providers[provider] = providers.get(provider, 0) + 1
        if vstatus:
            validation[vstatus] = validation.get(vstatus, 0) + 1
        if status == "completed":
            for s in stages:
                stage_totals[s["stage"]] = stage_totals.get(s["stage"], 0) + s.get("ms", 0)
                stage_counts[s["stage"]] = stage_counts.get(s["stage"], 0) + 1

        if len(recent) < 10:
            recent.append({
                "job_id": r["job_id"],
                "portfolio_id": r["portfolio_id"],
                "status": status,
                "created_at": r["created_at"],
                "provider": provider,
                "validation_status": vstatus,
                "total_ms": total_ms,
            })
        if len(exceptions) < 20:
            if status == "failed":
                exceptions.append({"type": "failed_job", "ref": r["job_id"],
                                   "detail": f"{r['portfolio_id']}: {public.get('error', 'unknown error')}"})
            elif vstatus == "fallback_used":
                exceptions.append({"type": "ai_output_rejected", "ref": r["job_id"],
                                   "detail": "; ".join(audit.get("validation_issues", [])) or "validation failed"})

    quality = latest_quality_run()
    if quality:
        for flag in quality["flags"]:
            exceptions.append({"type": "data_quality_flag", "ref": quality["run_at"], "detail": flag})

    total = len(rows)
    helpful = sum(1 for f in fb if f["helpful"])
    checked = sum(validation.values())
    return {
        "job_health": {
            "total_jobs": total,
            "by_status": by_status,
            "avg_stage_ms": {k: round(stage_totals[k] / stage_counts[k], 1) for k in stage_totals},
        },
        "adoption": {
            "jobs_by_portfolio": by_portfolio,
            "feedback_count": len(fb),
        },
        "output_quality": {
            "ai_provider_mix": providers,
            "validation": validation,
            "validation_pass_rate_pct": round(validation.get("passed", 0) / checked * 100, 1) if checked else None,
            "helpful_rate_pct": round(helpful / len(fb) * 100, 1) if fb else None,
        },
        "exceptions": exceptions,
        "recent_jobs": recent,
        "latest_quality_run": None if not quality else {
            "run_at": quality["run_at"], "runs_saved": quality["runs_saved"], "metrics": quality["metrics"],
        },
    }

def list_audit_rows(limit: int = 25) -> list[dict]:
    """The newest analyses with the audit details a compliance reviewer needs."""
    with _connect() as conn:
        _ensure_snapshots(conn)
        rows = conn.execute(
            "SELECT j.job_id, j.portfolio_id, j.status, j.created_at, j.public_json, j.audit_json, "
            "(SELECT COUNT(*) FROM snapshots s WHERE s.job_id = j.job_id) AS has_snapshot "
            "FROM jobs j WHERE j.job_id != 'selftest' ORDER BY j.rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        public = json.loads(r["public_json"])
        audit = json.loads(r["audit_json"] or "{}")
        out.append({
            "job_id": r["job_id"],
            "portfolio_id": r["portfolio_id"],
            "status": r["status"],
            "created_at": r["created_at"],
            "error": public.get("error"),
            "provider": audit.get("provider"),
            "prompt_version": audit.get("prompt_version"),
            "validation_status": audit.get("validation_status"),
            "validation_issues": audit.get("validation_issues", []),
            "has_snapshot": bool(r["has_snapshot"]),
        })
    return out


def _ensure_reviews(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            decision TEXT,
            note TEXT,
            reviewer TEXT,
            at TEXT
        )"""
    )


def save_review(job_id: str, decision: str, note: str, reviewer: str) -> None:
    """Every review is kept; the newest one for a job is its current status."""
    with _connect() as conn:
        _ensure_reviews(conn)
        conn.execute(
            "INSERT INTO reviews (job_id, decision, note, reviewer, at) VALUES (?, ?, ?, ?, ?)",
            (job_id, decision, note, reviewer, datetime.now(timezone.utc).isoformat()),
        )


def latest_reviews() -> dict:
    with _connect() as conn:
        _ensure_reviews(conn)
        rows = conn.execute("SELECT * FROM reviews ORDER BY id").fetchall()
    return {
        r["job_id"]: {"decision": r["decision"], "note": r["note"], "reviewer": r["reviewer"], "at": r["at"]}
        for r in rows
    }