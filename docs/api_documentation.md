# API documentation

Base address when running locally: `http://localhost:8000`. The backend also serves an interactive version of this page at `/docs` (every route with a "Try it out" button) and a machine-readable description at `/openapi.json`.

There is no login system. Recording a compliance review needs a reviewer key, and everything else is open, so the API suits sample data and local use only.. Cross-origin access is limited to the addresses in the `ALLOWED_ORIGINS` setting, which defaults to `http://localhost:3000`.

Error responses have the form `{"detail": "message"}`.

## Health and portfolios

| Method and path | Purpose | Returns |
|---|---|---|
| `GET /health` | Check the backend is running | `{"status": "ok"}` |
| `GET /api/portfolios` | Portfolio names (`LIVE` is always first) | `{"portfolios": ["LIVE", "concentrated_it", ...]}` |

## Analysis jobs

### `POST /api/portfolio-analysis`

Runs one analysis and saves the job, its audit trail and a snapshot of the holdings.

Request body:

```json
{"portfolio_id": "diversified", "timeframe": "1M", "insight_type": "summary"}
```

Only `portfolio_id` is required. `timeframe` and `insight_type` are accepted for future use.

Response: the job, without its audit trail.

| Field | Meaning |
|---|---|
| `job_id`, `status`, `created_at`, `request` | Identity and state of the job (`completed` or `failed`) |
| `stages` | Time in milliseconds for `data_load`, `analytics`, `llm_analysis`, `validation`, `recommendation` |
| `metrics` | Totals, sector weights, top holding, concentration index and the per-holding table |
| `alerts` | Rule-based risk alerts, each with a type, severity, value and threshold |
| `cards` | Insight cards, each with an explanation, a confidence level and source details |

Errors: `404` for an unknown portfolio, `422` for unusable data (for example `LIVE` when not logged in to Zerodha, or a portfolio worth zero). Failed jobs are still saved.

PowerShell example:

```
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/portfolio-analysis -ContentType "application/json" -Body '{"portfolio_id":"diversified"}'
```

### Reading saved results

| Method and path | Returns |
|---|---|
| `GET /api/insights/{job_id}` | The saved job, as returned when it was created |
| `GET /api/audit/{job_id}` | `stages`, `provider` (`gemini`, `anthropic`, `template` or `template_fallback`), `prompt_version`, `validation_status` (`passed` or `fallback_used`), `validation_issues` and the `data_snapshot` the AI was given |
| `GET /api/snapshot/{job_id}` | `portfolio_id`, `taken_at` and the exact `holdings` the analysis used |

All three return `404` for an unknown job. Snapshots exist only for jobs run after snapshots were added.

## Feedback

| Method and path | Purpose |
|---|---|
| `POST /api/feedback` | Save a "Was this useful?" click. Body: `{"job_id": "...", "card_id": "summary", "helpful": true, "note": ""}`. Returns `{"saved": true}`, or `404` for an unknown job |
| `GET /api/feedback` | All saved feedback: `{"feedback": [{"id": 1, "job_id": "...", "card_id": "summary", "helpful": true, "note": "", "at": "..."}]}` |

## Benchmark analysis

These routes read the results written by `scripts/run_all_portfolios.py`, which uses real prices downloaded from Yahoo Finance.

| Method and path | Returns |
|---|---|
| `GET /api/benchmark/{portfolio_id}` | `portfolio_id`, `kpis` and the addresses of three `graphs` |
| `GET /api/benchmark/{portfolio_id}/explanation` | `explanation` (`summary`, `key_drivers`, `risk_note`) and the `provider` that wrote it |
| `GET /portfolio-graphs/{portfolio_id}/{file}.png` | A chart image, served as a static file (so it is not listed on `/docs`): `portfolio_vs_nifty`, `stock_returns` or `sector_weights` |

Errors: `400` for an invalid name, `404` when no analysis exists yet for that portfolio (for example `LIVE`, or `volatile_smallcap`, whose placeholder stocks have no market prices).

Example `kpis` for `diversified`:

```json
{
  "Start date": "2025-10-29",
  "End date": "2026-10-29",
  "Portfolio return (%)": -18.3,
  "Nifty 50 return (%)": -12.2,
  "Return versus Nifty 50 (percentage points)": -6,
  "Portfolio volatility (% a year)": 13.7,
  "Nifty 50 volatility (% a year)": 13.8,
  "Portfolio max drawdown (%)": -23.9,
  "Nifty 50 max drawdown (%)": -15.6,
  "Stocks analysed": 8,
  "Stocks skipped (no price data)": "none"
}
```

The explanation is checked: any number the AI writes must exist in the figures it was given, otherwise a template is used and `provider` is `template`. Recent headlines are given to the AI as background only.

Older routes `GET /api/benchmark-analysis` and `GET /api/benchmark-explanation`, and the static `/graphs/...` files, serve only the first sample portfolio.

## Zerodha (Kite Connect)

| Method and path | Purpose |
|---|---|
| `GET /api/kite/login` | Redirects to Zerodha's login page. Needed once per day, and again after every backend restart |
| `GET /api/kite/callback` | Where Zerodha sends the browser back. It must match the Redirect URL set in the Kite developer console. Redirects to the frontend, or returns `400` if the login did not complete |
| `GET /api/kite/status` | `{"logged_in": true}` or `false` |
| `GET /api/kite/holdings` | `{"holdings": [...]}` straight from Zerodha. Returns `401` when not logged in |

The access token is kept in memory only. The free Kite "Personal" plan returns holdings but no price history.

## Quality, operations and compliance

| Method and path | Returns |
|---|---|
| `GET /api/quality` | The latest data-quality run: `run_at`, `runs_saved`, `metrics`, `flags` and the full `report_text`. `404` if none has been saved |
| `GET /api/ops/summary` | `job_health` (counts by status, average time per stage), `adoption`, `output_quality` (AI provider mix, validation pass rate, helpful rate), open `exceptions`, `recent_jobs` and the `latest_quality_run` |
| `GET /api/compliance/summary` | `disclosures`, `counts`, policy `flags` (failed jobs and rejected AI answers, each with its review status), `data_flags` and the `audit_trail` |
| `POST /api/compliance/review` | Record a reviewer decision. Body: `{"job_id": "...", "decision": "approved", "note": "...", "reviewer": "name"}`. Header `x-review-key` must hold the reviewer key. `decision` must be `approved` or `needs_follow_up` (otherwise `422`). Returns `{"saved": true}`, or `404` for an unknown job |

Every review is kept, and the newest one for a job is its current status. Recording a review also needs the reviewer key in the `x-review-key` request header. A missing or wrong key returns `403`, and so does any review on a server running in demo mode with no key configured. A job named `selftest` (used in development) is ignored by the operations and compliance summaries.