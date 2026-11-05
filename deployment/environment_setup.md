# Environment setup

Every setting the project uses, and where it lives. Keys are never committed to Git. `.env.example` at the project root is the template.

## Local backend: `backend/.env`

Create the file by hand. It is listed in `.gitignore`. Changes to `.env` are read only when the backend starts, so restart `uvicorn` after editing it (`--reload` only watches code files).

| Setting | Purpose | Example or note |
|---|---|---|
| `KITE_API_KEY`, `KITE_API_SECRET` | Zerodha Kite Connect app credentials for the `LIVE` portfolio | **Local only. Never put these on a public server** |
| `GNEWS_API_KEY` | News download scripts | Local only. Used by `scripts/download_news*.py`, not by the running backend |
| `GEMINI_API_KEY` | AI explanations through Gemini | Optional. Without any AI key the app uses the template explanation |
| `GEMINI_MODEL` | Gemini model name | `gemini-3.5-flash-lite`. Google retires model names, so update it if the AI stops answering (a "404" in the backend log means the name no longer exists) |
| `ANTHROPIC_API_KEY`, `LLM_MODEL` | AI explanations through Claude | Optional alternative |
| `LLM_PROVIDER` | Force a provider | `gemini`, `anthropic` or `template`. Otherwise chosen from the keys present |
| `DEMO_MODE` | Hide `LIVE` and refuse every `/api/kite` route | `false` locally, `true` on any public server |
| `ALLOWED_ORIGINS` | Website addresses allowed to call the backend | Comma separated, no trailing slash. Default `http://localhost:3000` |
| `RATE_LIMIT_PER_MINUTE` | Analysis and AI requests per visitor per minute | Default `20`. `0` switches the limit off |
| `REVIEW_KEY` | Key required to record compliance reviews | Anyone holding it can approve flags, so share it only with reviewers. On a public server with no key set, reviews are refused |

## Hosted backend (Render)

Entered on the service's **Environment** page. `backend/.env` is not uploaded.

| Setting | Value |
|---|---|
| `DEMO_MODE` | `true` |
| `PYTHON_VERSION` | `3.12.3` |
| `GEMINI_API_KEY` | Your Gemini key |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` |
| `ALLOWED_ORIGINS` | The website address, for example `https://your-site.vercel.app`, with **no `/` at the end** |
| `REVIEW_KEY` | The same reviewer key as in your local `.env` |

Do **not** add the Kite or GNews keys to a public server. Demo mode does not need them, and leaving them out means the real Zerodha account cannot be reached from the internet.

## Hosted frontend (Vercel)

| Setting | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | The backend address, for example `https://your-backend.onrender.com`, with **no `/` at the end** |

- Save it as a **Config** setting, not a Secret. Anything starting with `NEXT_PUBLIC_` is built into the website and visible to every visitor's browser, and Vercel refuses to keep it as a Secret.
- The value is fixed into the site when it is built. After changing it, **redeploy** from the Deployments page.
- Locally, `.env.local` holds the same setting (`http://localhost:8000`) and is not committed.

## Before every upload to GitHub

```
pytest
python scripts/check_secrets.py
```

`check_secrets.py` searches every file Git would upload for the real key values in `backend/.env` and prints only file names. If a key ever reaches a public place, treat it as exposed and replace it at its provider.
