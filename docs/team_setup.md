# Team setup: run the project on your own laptop

This guide gets the full project running on your computer, including the `LIVE` portfolio with **your own** Zerodha holdings. Each person uses their own Zerodha account and their own keys. Never share keys, and never commit them to Git.

If you only want to look, you do not need any of this. Read the code on GitHub, or open the online demo (see the README). The online demo has no `LIVE` portfolio, on purpose.

## What you need

- A **Zerodha trading account** (needed for `LIVE` only)
- **Git**, **Python 3.10 or newer**, and a current **Node.js** (LTS)
- **VS Code** is optional but makes things easier
- A **Gemini API key** from Google AI Studio is optional. Without it the app uses a safe template instead of AI-written text

## 1. Get the code

The project is two repositories: the backend (this one) and the website.

```
git clone https://github.com/kumarsomashekhar/zerodha-ai-financial-intelligence-platform.git
git clone https://github.com/kumarsomashekhar/zerodha-frontend.git
```

If the folder you clone into has an `&` in its path, quote paths in PowerShell, for example `cd "C:\path\with&ampersand"`.

## 2. Backend setup

From inside the backend folder:

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

On macOS or Linux, activate with `source .venv/bin/activate` instead. If PowerShell refuses to run the activation script, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` and try again.

The prices, news and benchmark results are already included in the repository, so you do **not** need to run the data scripts.

## 3. Create your own Kite Connect app (for LIVE)

1. Log in at the Kite developer site (developers.kite.trade) with your Zerodha account and create an app. Choose the free **Personal** plan.
2. Set the app's **Redirect URL** to exactly:

```
http://localhost:8000/api/kite/callback
```

3. Copy the app's **API key** and **API secret**. These belong to you and your account only.

The free Personal plan returns your holdings but no price history, so `LIVE` has no benchmark analysis and shows its sectors as "Unclassified". Check the developer site for the plans on offer, because they can change.

## 4. Your keys file

Copy the template and fill it in:

```
Copy-Item .env.example backend\.env
```

Open `backend\.env` and set these (no quote marks, no spaces around `=`):

```
KITE_API_KEY=your key
KITE_API_SECRET=your secret
DEMO_MODE=false
GEMINI_API_KEY=your Gemini key (optional)
GEMINI_MODEL=gemini-3.5-flash-lite
```

`DEMO_MODE` must be `false`, or `LIVE` stays hidden. `backend/.env` is ignored by Git, so it stays on your machine. Edits to it take effect only after you restart the backend.

## 5. Website setup

From inside the website folder:

```
npm install
```

Create a file named `.env.local` in that folder containing one line:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 6. Run it

Use two terminals.

```
# Terminal 1: in the backend folder, with the virtual environment active
uvicorn backend.main:app --reload

# Terminal 2: in the website folder
npm run dev
```

The backend must be started **from the backend project's root folder**, or Python says `No module named 'backend'`.

Open `http://localhost:3000`.

## 7. See your own holdings

1. Open `http://localhost:8000/api/kite/login` and log in to **your** Zerodha account.
2. Zerodha sends you back to the website. The backend keeps the login in memory, so **repeat this once a day and after every backend restart**.
3. Choose **LIVE** in the dropdown and click **Analyse portfolio**.

## Working together

- Never commit `backend/.env`. Before pushing, run `pytest` and `python scripts/check_secrets.py`. The second command searches every file Git would upload for the real values in your `.env` and prints only file names.
- Work on a branch, not on `main`. Pushes to `main` redeploy the live demo.

```
git checkout -b my-change
git add -A
git commit -m "Describe the change"
git push -u origin my-change
```

Then open a **pull request** on GitHub for review. If you are not a collaborator, fork the repository first and open the pull request from your fork.

## Problems and fixes

| Symptom | Cause and fix |
|---|---|
| Screen says "Not logged in to Zerodha" | Open `http://localhost:8000/api/kite/login` and log in. Needed daily |
| Zerodha complains about the redirect address | The Redirect URL in your Kite app must be exactly `http://localhost:8000/api/kite/callback`, and the backend must run on port 8000 |
| `LIVE` is missing from the dropdown | `DEMO_MODE` is `true`, or the backend was not restarted after editing `.env` |
| Dropdown empty, "Cannot reach the backend" | The backend is not running, or `.env.local` has the wrong address. Restart the website after editing it |
| `No module named 'backend'` | Start `uvicorn` from the backend project's root folder |
| Insight box says "Standard summary" | No AI answer was used. Check `GEMINI_API_KEY` and `GEMINI_MODEL`, then read the backend terminal for a line starting `[LLM]` |
| `mcp` errors about `FastMCP` | Version 2 of the package is installed. Run `pip install "mcp[cli]<2"` |
| Port already in use | Another copy is still running. Close it, or stop it with Ctrl + C |