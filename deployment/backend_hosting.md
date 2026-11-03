# Backend hosting (Render, free plan)

The backend runs as a Render **Web Service** built from the project's GitHub repository. Plan details below were checked in November 2026. Free-plan limits change, so check Render's pricing and free-tier pages before relying on them.

## Settings

| Field | Value |
|---|---|
| Repository | The backend project, on branch `main` |
| Language | Python 3 |
| Root Directory | empty (the app is started from the project root) |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |
| Environment variables | See `environment_setup.md` |

Render rebuilds and restarts automatically on every push to `main`.

## What the free plan means for the demo

- **Sleep:** a free service stops after 15 minutes without visitors, and wakes on the next request in about a minute. Open the site and run one analysis a few minutes before a demo.
- **No lasting files:** the filesystem is temporary. The SQLite database (`data/app.db`) is wiped whenever the service restarts, redeploys or sleeps. After that, jobs, feedback, snapshots, quality runs and compliance reviews start empty and refill as people use the site. Everything the app reads from the repository (the sample portfolios, news, results and charts) comes back with every deploy.
- **Hours:** there is a monthly allowance of free instance hours, which is ample for a demo.
- **Upgrade path:** to keep data, move storage to a hosted database (PostgreSQL or Supabase). The table layout in `storage.py` carries over. Free Render PostgreSQL databases expire after 30 days, so they are not a fix for a long-lived demo.

## Safety on a public server

- `DEMO_MODE=true` hides `LIVE` and makes every `/api/kite` route answer "Not available in demo mode".
- Verify this after every deploy by opening `/api/kite/status`. If it returns `{"logged_in":false}`, demo mode is **off**: do not leave the server public.
- There is no login on the API. Public data only: sample portfolios, downloaded prices and news.
- The per-visitor limit and the explanation cache protect the AI quota. Both live in memory and reset on restart. They are a speed bump, not a replacement for an API gateway.

## Updating the data

Prices, news and benchmark results are produced locally and committed to the repository:

1. Run the scripts in the README (`download_news_all.py`, `run_all_portfolios.py`, and so on).
2. Run `pytest` and `python scripts/check_secrets.py`.
3. `git add -A`, `git commit -m "Refresh data"`, `git push`. Render redeploys.

## After a deploy: checks

| Address | Expected |
|---|---|
| `/health` | `{"status":"ok"}` |
| `/api/portfolios` | The portfolios, **without** `LIVE` |
| `/api/kite/status` | `{"detail":"Not available in demo mode"}` |
| `/api/benchmark/diversified` | Benchmark figures |
| `/api/benchmark/concentrated_it/explanation` | `"provider":"gemini"` |

## Problems met during the first deployment

| Symptom | Cause and fix |
|---|---|
| Insight box says "Standard summary" and the backend log shows `Gemini returned status 404` | The model name does not exist. Set `GEMINI_MODEL` to a current name |
| `[LLM] ... status 400` or `403` | The key is wrong, or was copied with a space or quote mark |
| Very slow first request | The free service was asleep. Wait a minute and refresh |
| Dashboards empty after a quiet period | The temporary database was wiped, as described above |
| Browser Console says "blocked by CORS policy" | `ALLOWED_ORIGINS` is missing or does not match the website address exactly |