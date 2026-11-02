# Demo script (about 10 minutes)

This walk-through shows every feature of the platform. Figures shift slightly as the one-year window moves forward. The sample portfolios' own prices are fixed, so those figures stay the same.

## Before you start

Run each of these in its own terminal.

```
# Backend (project root, with the virtual environment active)
uvicorn backend.main:app --reload

# Frontend (the Next.js project folder)
npm run dev
```

Wait for "Application startup complete" in the first terminal and "Ready" in the second.

## 1. Analyse a diversified portfolio

1. Open `http://localhost:3000`.
2. Choose **diversified** and click **Analyse portfolio**.
3. **Expect:** an insight card with a plain-English summary, then a sector chart and a holdings table. Under **Insights**, a grey note explains that these prices come from the portfolio data itself.
4. Scroll to **Benchmark analysis**. **Expect:** a table of return, volatility and maximum drawdown for the portfolio against the Nifty 50, an AI-written explanation labelled "numbers checked", and three charts. The diversified portfolio's one-year return is about -18%, against about -12% for the Nifty 50.

**Why it matters:** the numbers come from code, and the AI only explains them.

## 2. See concentration risk

1. Choose **concentrated_it** and click **Analyse portfolio**.
2. **Expect:** risk flags for a very high IT share and a large single-stock weight. The benchmark section shows a deeper loss and higher volatility than the diversified portfolio.

**Why it matters:** the app turns raw holdings into risk signals a non-expert can read.

## 3. Try the awkward portfolios

1. Choose **limited_holdings**, then **stale_data**, and click **Analyse portfolio** for each.
2. **Expect:** a low-diversification flag for the first, and a stale-data flag for the second, because its prices are marked as several days old.
3. Choose **volatile_smallcap**. **Expect:** an analysis from its stored prices, but the benchmark section says benchmark analysis is not available. Its stocks are placeholder names, so Yahoo Finance has no prices for them.

**Why it matters:** missing or old data is reported plainly and never hidden.

## 4. Give feedback

Click **Yes** or **No** under "Was this useful?" on an insight card. It is saved permanently.

## 5. Real holdings (optional)

1. Open `http://localhost:8000/api/kite/login` and log in to Zerodha. This shows a real account, so skip this step when presenting publicly.
2. Back at `http://localhost:3000`, choose **LIVE** and click **Analyse portfolio**.
3. **Expect:** your real holdings analysed, with sectors shown as "Unclassified". The benchmark section says it is not available, because the free Kite plan has no price history.

If you choose LIVE without logging in, the app shows "Not logged in to Zerodha". This is expected, and it appears later as a failed job on the dashboards.

## 6. Operations dashboard

1. Click **Operations dashboard**.
2. **Expect:** job counts by status, average time per stage (the AI step dominates), analyses per portfolio, how often AI answers passed validation, the share marked helpful, and a list of open exceptions.

**Why it matters:** an operator can see job health and output quality at a glance.

## 7. Compliance panel

1. Click **Compliance panel**.
2. **Expect:** disclosures, counts of flagged analyses, and a list of flags: failed jobs and AI answers that were rejected and replaced by the safe template. The audit trail below lists every analysis with its AI provider, prompt version, validation result and a **snapshot** link.
3. On a flag, type a note and click **Approve** or **Needs follow-up**. Refresh the page. **Expect:** the decision is still there, and the counts have changed.
4. Click a **snapshot** link. **Expect:** the exact holdings and prices behind that analysis.

**Why it matters:** every insight can be traced back to its data, and a person signs off on exceptions.

## 8. MCP server

In a third terminal, from the project root:

```
python scripts/test_mcp_server.py
```

**Expect:** six tools listed, then sample results: a stock's latest price with a freshness check, a benchmark comparison, recent headlines, and a clear "not available" message for `volatile_smallcap`.

## 9. Backend documentation page

Open `http://localhost:8000/docs`. **Expect:** every backend route listed, each with a "Try it out" button.

## 10. Automated tests

```
pytest
```

**Expect:** 56 tests passing. They cover the analytics, the AI-output checks, edge cases, the MCP tools, storage and the compliance logic.

## What to point out

- The AI never computes numbers, and its answers are rejected if they contain an invented number or advice language.
- Rejected answers are replaced by a template and logged for human review.
- Gaps are shown honestly: LIVE has no benchmark, ITC has little news, and sample prices differ from market prices.