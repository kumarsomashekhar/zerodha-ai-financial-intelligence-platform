# Architecture

The platform turns a portfolio into plain-language insights. Code computes every number, an AI model only explains them, and every explanation is checked, stored and open to human review.

## Components

| Layer | What it does | Where it lives |
|---|---|---|
| Data sources | Sample portfolios (CSV), live holdings (Zerodha Kite Connect), prices and the Nifty 50 (Yahoo Finance), headlines (GNews) | `data/`, `backend/services/kite_client.py`, `scripts/` |
| Analytics engine | Weights, sector exposure, concentration, diversification, volatility, drawdown, benchmark comparison | `backend/services/analytics.py`, `scripts/run_all_portfolios.py` |
| LLM analysis layer | Builds the context, asks Gemini or Claude for an explanation, falls back to a template | `backend/services/llm.py` |
| Validation | Rejects invented numbers, advice and prediction language | `backend/services/validation.py` |
| Recommendation engine | Turns metrics, alerts and the explanation into insight cards | `backend/services/recommendation.py` |
| Backend services | FastAPI routes, jobs, feedback, snapshots, audit, compliance, operations | `backend/main.py`, `storage.py`, `compliance_service.py` |
| Data store | SQLite file `data/app.db` | `backend/services/storage.py` |
| MCP server | Six read-only tools for MCP-compatible AI apps | `mcp_server/` |
| Dashboards | Investor screen, operations dashboard, compliance panel | `frontend-files/` (Next.js) |

## Flow of one analysis

1. The investor picks a portfolio and clicks **Analyse portfolio**. The frontend calls `POST /api/portfolio-analysis`.
2. **data_load:** the portfolio is read from the sample file, or from Zerodha for `LIVE`. The exact holdings are saved as a **snapshot**.
3. **analytics:** metrics and rule-based risk alerts are computed in code.
4. **llm_analysis:** the AI is given the metrics and alerts and asked for a short explanation as JSON.
5. **validation:** the explanation is rejected if it contains a number that is not in the analytics data, or advice or prediction language. A rejected answer is replaced by a template and marked `fallback_used`.
6. **recommendation:** insight cards are built from the result.
7. The job is saved, with its audit trail (AI provider, prompt version, validation result and issues, stage timings). The stage timings are shown on the screen.

The benchmark section works separately. `scripts/run_all_portfolios.py` downloads real prices once and writes one-year return, volatility, maximum drawdown and three charts per portfolio into `data/processed/portfolios/<name>/`. The backend serves those files and asks the AI to explain them, with recent headlines as background. The same number check applies.

## Stored data (SQLite)

| Table | Holds |
|---|---|
| `jobs` | Every analysis: status, public result, and a separate audit trail |
| `snapshots` | The exact holdings and prices each analysis used |
| `feedback` | "Was this useful?" clicks |
| `quality_runs` | Every data-quality report run, with metrics and flags (a growing history) |
| `reviews` | Compliance decisions. Every review is kept, and the newest one is the current status |

## How the AI is kept honest

- The AI never computes. Its prompt says to use only the supplied figures, and the validator checks each digit in its answer against the analytics data.
- Advice and prediction words (buy, sell, guaranteed, "will rise") are rejected.
- Headlines are treated as untrusted text. The AI is told never to follow instructions inside them, never to copy numbers from them, and never to claim the news caused a price move.
- If anything fails (no key, a network error, a rejected answer), a plain template is shown, so the app never shows an unchecked answer and never crashes.
- Every fallback is visible on the operations dashboard and as a policy flag in the compliance panel.

## Key design decisions

- **Code computes, AI explains.** This keeps every figure reproducible and checkable.
- **A template fallback.** A safe, boring answer is better than an unchecked clever one.
- **SQLite for storage.** It needs no setup and stores everything permanently in one file. The table design carries over to PostgreSQL or Supabase later.
- **MCP over stdio.** The server runs as a local process that an MCP client starts, and it is read-only.
- **Two price sources, labelled on screen.** Sample portfolios use fixed prices stored in the CSV file. The benchmark section uses real downloaded prices. The two are labelled so a reader is not misled.

## Mapping to the planned architecture

| Planned component | Status |
|---|---|
| Portfolio, market data and news sources | Built |
| Analytics engine | Built (exposure, concentration, volatility, drawdown, benchmark). Sector drift is not built |
| LLM analysis layer and recommendation engine | Built |
| MCP server | Built (six read-only tools, generated registry) |
| Backend services | Built |
| Data stores | Built with SQLite. PostgreSQL or Supabase is not used |
| Investor dashboard, operations dashboard, compliance panel | Built |
| Validation, model-output checks, fallback behavior | Built |
| Audit logs and source traceability | Built (audit trail, snapshots, headline links) |
| API gateway (authentication, rate limits) | Not built. The backend has no login and is for local use only |
| Structured logging and permission controls | Not built |
| Scenario framing, corporate actions | Not built |

## Differences from the planned folder layout

- Analytics, AI and validation code sits in `backend/services/` and not in separate top-level `analytics/` and `ai_workflows/` folders.
- The frontend source is in `frontend-files/` and is copied into a Next.js project to run.
- Data-pipeline scripts live in `scripts/`.
- The sample portfolio file also carries stored prices and volatility, so there is no separate sample market data file.