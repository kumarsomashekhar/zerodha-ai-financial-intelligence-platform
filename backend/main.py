"""FastAPI app. Run from the project root:  uvicorn backend.main:app --reload"""
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.services import analytics, compliance_service, kite_client, llm, recommendation, storage, validation

load_dotenv("backend/.env")

app = FastAPI(title="Zerodha AI Financial Intelligence Platform", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

DEMO_MODE = os.getenv("DEMO_MODE", "").strip().lower() in ("1", "true", "yes")


@app.middleware("http")
async def demo_mode_guard(request, call_next):
    """In demo mode the real Zerodha account is unreachable: every Kite route is refused."""
    if DEMO_MODE and request.url.path.startswith("/api/kite"):
        return JSONResponse({"detail": "Not available in demo mode"}, status_code=404)
    return await call_next(request)

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))  # 0 switches the limit off
_REQUEST_LOG: dict = defaultdict(deque)


def _limited_path(path: str) -> bool:
    return path == "/api/portfolio-analysis" or path.endswith("/explanation")


@app.middleware("http")
async def rate_limit_guard(request, call_next):
    """Give each visitor a limited number of analysis and AI-explanation requests per minute."""
    if RATE_LIMIT_PER_MINUTE > 0 and _limited_path(request.url.path):
        forwarded = request.headers.get("x-forwarded-for", "")
        visitor = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
        now = time.time()
        recent = _REQUEST_LOG[visitor]
        while recent and now - recent[0] > 60:
            recent.popleft()
        if len(recent) >= RATE_LIMIT_PER_MINUTE:
            allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
            origin = request.headers.get("origin", "")
            headers = {"Access-Control-Allow-Origin": origin} if origin in allowed else {}
            return JSONResponse(
                {"detail": "Too many requests. Please wait a minute and try again."},
                status_code=429,
                headers=headers,
            )
        recent.append(now)
    return await call_next(request)

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
app.mount("/graphs", StaticFiles(directory=PROC / "graphs"), name="graphs")

storage.init_db()

class AnalysisRequest(BaseModel):
    portfolio_id: str
    timeframe: str = "1M"
    insight_type: str = "summary"


class FeedbackRequest(BaseModel):
    job_id: str
    card_id: str
    helpful: bool
    note: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/kite/login")
def kite_login():
    return RedirectResponse(kite_client.login_url())


@app.get("/api/kite/callback")
def kite_callback(request_token: str = "", status: str = ""):
    if status != "success" or not request_token:
        raise HTTPException(400, "Zerodha login did not complete")
    kite_client.complete_login(request_token)
    return RedirectResponse("http://localhost:3000")


@app.get("/api/kite/status")
def kite_status():
    return {"logged_in": kite_client.is_logged_in()}

@app.get("/api/kite/holdings")
def kite_holdings():
    if not kite_client.is_logged_in():
        raise HTTPException(401, "Log in first at /api/kite/login")
    return {"holdings": kite_client.get_holdings()}


@app.get("/api/portfolios")
def portfolios():
    names = analytics.list_portfolios()
    if DEMO_MODE:
        names = [n for n in names if n != "LIVE"]
    return {"portfolios": names}


def _stage(job: dict, name: str, started: float):
    job["stages"].append({"stage": name, "ms": round((time.time() - started) * 1000, 1)})


@app.post("/api/portfolio-analysis")
def create_analysis(req: AnalysisRequest):
    if DEMO_MODE and req.portfolio_id == "LIVE":
        raise HTTPException(404, "The LIVE portfolio is not available in demo mode")
    job_id = uuid.uuid4().hex[:12]
    job = {"job_id": job_id, "status": "running", "stages": [],
           "created_at": datetime.now(timezone.utc).isoformat(), "request": req.model_dump()}
    storage.save_job(job)
    try:
        t = time.time()
        df = analytics.load_portfolio(req.portfolio_id)
        storage.save_snapshot(job_id, req.portfolio_id, df.to_json(orient="records"))
        _stage(job, "data_load", t)

        t = time.time()
        metrics = analytics.compute_metrics(df)
        alerts = analytics.risk_alerts(metrics)
        ctx = {"metrics": metrics, "alerts": alerts, "alert_count": len(alerts), "timeframe": req.timeframe}
        _stage(job, "analytics", t)

        t = time.time()
        explanation, provider = llm.explain(ctx)
        _stage(job, "llm_analysis", t)

        t = time.time()
        ok, issues = validation.validate(explanation, ctx)
        validation_status = "passed"
        if not ok:  # fail safe: fall back to the template explanation
            explanation, provider = llm.template_explanation(ctx), "template_fallback"
            validation_status = "fallback_used"
        _stage(job, "validation", t)

        t = time.time()
        cards = recommendation.build_cards(metrics, alerts, explanation)
        _stage(job, "recommendation", t)

        job.update(status="completed", metrics=metrics, alerts=alerts, cards=cards,
                   audit={"provider": provider, "prompt_version": llm.PROMPT_VERSION,
                          "validation_status": validation_status, "validation_issues": issues,
                          "data_snapshot": ctx})
    except KeyError as e:
        job.update(status="failed", error=str(e))
        storage.save_job(job)
        raise HTTPException(404, str(e))
    except ValueError as e:
        job.update(status="failed", error=str(e))
        storage.save_job(job)
        raise HTTPException(422, str(e))
    storage.save_job(job)
    return {k: v for k, v in job.items() if k != "audit"}


@app.get("/api/insights/{job_id}")
def get_insights(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@app.get("/api/audit/{job_id}")
def get_audit(job_id: str):
    audit = storage.get_audit(job_id)
    if not audit:
        raise HTTPException(404, "job not found")
    return audit

@app.get("/api/snapshot/{job_id}")
def get_snapshot(job_id: str):
    snap = storage.get_snapshot(job_id)
    if not snap:
        raise HTTPException(404, "snapshot not found")
    return snap


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    if not storage.job_exists(req.job_id):
        raise HTTPException(404, "job not found")
    storage.save_feedback(req.model_dump() | {"at": datetime.now(timezone.utc).isoformat()})
    return {"saved": True}


@app.get("/api/feedback")
def list_feedback():
    return {"feedback": storage.list_feedback()}

def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    return int(f) if f.is_integer() else f


@app.get("/api/benchmark-analysis")
def benchmark_analysis():
    kpi_file = PROC / "portfolio_kpis.csv"
    stock_file = PROC / "stock_kpis.csv"
    if not kpi_file.exists() or not stock_file.exists():
        raise HTTPException(404, "Run scripts/analyse_portfolio.py first")
    raw = pd.read_csv(kpi_file, index_col=0)["value"].to_dict()
    return {
        "kpis": {k: _num(v) for k, v in raw.items()},
        "stocks": pd.read_csv(stock_file).to_dict(orient="records"),
        "graphs": {
            "portfolio_vs_nifty": "/graphs/portfolio_vs_nifty.png",
            "stock_returns": "/graphs/stock_returns.png",
            "sector_weights": "/graphs/sector_weights.png",
        },
    }

@app.get("/api/benchmark-explanation")
def benchmark_explanation():
    kpi_file = PROC / "portfolio_kpis.csv"
    stock_file = PROC / "stock_kpis.csv"
    if not kpi_file.exists() or not stock_file.exists():
        raise HTTPException(404, "Run scripts/analyse_portfolio.py first")
    raw = pd.read_csv(kpi_file, index_col=0)["value"].to_dict()
    stocks = pd.read_csv(stock_file)
    sectors = stocks.groupby("sector")["weight_pct"].sum().round(1).sort_values(ascending=False)
    bench = {
        "kpis": {k: _num(v) for k, v in raw.items()},
        "sector_weights_pct": sectors.to_dict(),
        "stocks": stocks[["symbol", "weight_pct", "return_1y_pct"]].to_dict(orient="records"),
    }
    explanation, provider = llm.explain_benchmark(bench)
    return {"explanation": explanation, "provider": provider}

PORTFOLIO_DIR = PROC / "portfolios"
app.mount(
    "/portfolio-graphs",
    StaticFiles(directory=PORTFOLIO_DIR, check_dir=False),
    name="portfolio-graphs",
)


def _load_benchmark(portfolio_id: str) -> dict:
    if not portfolio_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Invalid portfolio name")
    folder = PORTFOLIO_DIR / portfolio_id
    kpi_file = folder / "portfolio_kpis.csv"
    stock_file = folder / "stock_kpis.csv"
    if not kpi_file.exists() or not stock_file.exists():
        raise HTTPException(404, f"Benchmark analysis is not available for '{portfolio_id}' yet")
    raw = pd.read_csv(kpi_file, index_col=0)["value"].to_dict()
    stocks = pd.read_csv(stock_file)
    sectors = stocks.groupby("sector")["weight_pct"].sum().round(1).sort_values(ascending=False)
    return {
        "kpis": {k: _num(v) for k, v in raw.items()},
        "sector_weights_pct": sectors.to_dict(),
        "stocks": stocks[["symbol", "weight_pct", "return_1y_pct"]].to_dict(orient="records"),
    }


@app.get("/api/benchmark/{portfolio_id}")
def benchmark_for_portfolio(portfolio_id: str):
    bench = _load_benchmark(portfolio_id)
    base = f"/portfolio-graphs/{portfolio_id}"
    return {
        "portfolio_id": portfolio_id,
        "kpis": bench["kpis"],
        "graphs": {
            "portfolio_vs_nifty": f"{base}/portfolio_vs_nifty.png",
            "stock_returns": f"{base}/stock_returns.png",
            "sector_weights": f"{base}/sector_weights.png",
        },
    }


EXPLANATION_CACHE: dict = {}
EXPLANATION_TTL_SECONDS = 6 * 3600   # keep an AI-written answer for 6 hours
FALLBACK_TTL_SECONDS = 10 * 60       # keep a template answer for only 10 minutes


@app.get("/api/benchmark/{portfolio_id}/explanation")
def benchmark_explanation_for_portfolio(portfolio_id: str):
    bench = _load_benchmark(portfolio_id)
    # The key includes the file's save time, so re-running the analysis script refreshes the answer
    kpi_file = PORTFOLIO_DIR / portfolio_id / "portfolio_kpis.csv"
    key = (portfolio_id, kpi_file.stat().st_mtime)
    cached = EXPLANATION_CACHE.get(key)
    if cached and time.time() - cached["at"] < cached["ttl"]:
        return cached["value"]

    headlines = _headlines_for([s["symbol"] for s in bench["stocks"]])
    explanation, provider = llm.explain_benchmark(bench, headlines)
    value = {"explanation": explanation, "provider": provider}
    ttl = FALLBACK_TTL_SECONDS if provider == "template" else EXPLANATION_TTL_SECONDS
    EXPLANATION_CACHE[key] = {"at": time.time(), "ttl": ttl, "value": value}
    return value

@app.get("/api/quality")
def quality():
    run = storage.latest_quality_run()
    if not run:
        raise HTTPException(404, "No quality report saved yet. Run scripts/build_quality_report.py")
    return run

def _headlines_for(symbols: list, per_stock: int = 2) -> list:
    news_file = PROC / "news_all_stocks.csv"
    if not news_file.exists():
        return []
    news = pd.read_csv(news_file)
    news = news[news["mentions_company"].astype(str).str.lower() == "true"]
    out = []
    for sym in symbols:
        sub = news[news["symbol"] == sym].sort_values("published_at", ascending=False).head(per_stock)
        out += [{"symbol": sym, "headline": str(t)} for t in sub["title"]]
    return out

@app.get("/api/ops/summary")
def ops_summary():
    return storage.ops_summary()

class ReviewRequest(BaseModel):
    job_id: str
    decision: str  # "approved" or "needs_follow_up"
    note: str = ""
    reviewer: str = "reviewer"


@app.get("/api/compliance/summary")
def compliance_summary():
    return compliance_service.summary()


@app.post("/api/compliance/review")
def compliance_review(req: ReviewRequest):
    if req.decision not in ("approved", "needs_follow_up"):
        raise HTTPException(422, "decision must be 'approved' or 'needs_follow_up'")
    if not storage.job_exists(req.job_id):
        raise HTTPException(404, "job not found")
    storage.save_review(req.job_id, req.decision, req.note.strip()[:500], req.reviewer.strip()[:60] or "reviewer")
    return {"saved": True}