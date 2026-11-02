# MCP tooling

The MCP (Model Context Protocol) server offers the platform's abilities as named tools that any MCP-compatible AI app can call. It reuses the same analytics code and data files as the web app, so an AI app sees the same numbers an investor sees.

All six tools are **read-only**. None of them writes data, places an order or changes an account.

## Run and test

Run from the project root, with the virtual environment active:

```
python -m mcp_server.server
```

The server talks over standard input and output (`stdio`) and is normally started by the MCP client, not by hand. Nothing in the server code may print to the screen, because that output channel carries the protocol.

To test it the way an AI app would, run:

```
python scripts/test_mcp_server.py
```

This starts the server, lists the tools and calls several of them.

It needs `mcp[cli]<2`. Version 2 of the package renamed `FastMCP`, so the code is written for version 1.

## The tools

| Tool | Inputs | Returns | Data it reads |
|---|---|---|---|
| `list_portfolios` | none | Portfolio names. `LIVE` is the real Zerodha account | `data/sample_portfolios.csv` |
| `get_portfolio_metrics` | `portfolio_id` | Holdings, weights, sector exposure, totals and profit or loss for one portfolio | `data/sample_portfolios.csv` |
| `get_risk_alerts` | `portfolio_id` | Rule-based alerts: sector or single-stock concentration, low diversification, high volatility, stale data | `data/sample_portfolios.csv` |
| `get_stock_price_summary` | `symbol` | Latest close, price date, one-year return, age of the latest price in days, and a freshness verdict | `data/processed/stock_prices_clean.csv` |
| `get_recent_news` | `symbol`, `limit` (1 to 10, default 5) | Recent headlines with source, publication date and link, newest first | `data/processed/news_all_stocks.csv` |
| `get_benchmark_comparison` | `portfolio_id` | One-year return, volatility and maximum drawdown against the Nifty 50, using real market prices | `data/processed/portfolios/<name>/portfolio_kpis.csv` |

Each tool's description, input schema and implementing file are in `mcp_server/tool_registry.json`. That file is generated from the running server by `scripts/build_tool_registry.py`, so it always matches the code. Do not edit it by hand.

### Example results

`get_risk_alerts` for `concentrated_it`:

```json
{
  "portfolio_id": "concentrated_it",
  "alert_count": 2,
  "alerts": [
    {"type": "sector_concentration", "severity": "high", "metric": "IT sector weight", "value": 88.4, "threshold": 40.0},
    {"type": "single_stock_concentration", "severity": "medium", "metric": "TCS weight", "value": 38.3, "threshold": 25.0}
  ]
}
```

`get_stock_price_summary` for `INFY`:

```json
{
  "symbol": "INFY",
  "latest_close": 1129.1,
  "latest_price_date": "2026-10-29",
  "first_price_date": "2025-10-29",
  "one_year_return_pct": -25.2,
  "price_age_days": 0,
  "freshness": "ok"
}
```

When a price is more than 3 days old, `freshness` says `stale: do not present this as a current price`. This guards against showing an old price as if it were live.

## Behaviour to know about

- **Errors are returned, not raised.** An unknown name gives `{"error": "..."}` with a readable message, so an AI app can explain it to the user.
- **Symbols are tidied.** `infy.ns` and `INFY` both mean INFY.
- **Stored prices versus market prices.** `get_portfolio_metrics` and `get_risk_alerts` use the prices stored with each sample portfolio, so their figures can differ from `get_benchmark_comparison`, which uses real downloaded prices. For example, `concentrated_it` shows IT at 88.4% from stored prices and about 91.5% from market prices.
- **Limited coverage:** `get_stock_price_summary` covers the five stocks in the cleaned price file (INFY, TCS, WIPRO, HDFCBANK, ITC). `get_recent_news` covers the ten real stocks in the sample portfolios.
- **`LIVE`:** the Zerodha login lives in the web backend's memory, so through the MCP server `LIVE` returns a "not logged in" error. It has no benchmark analysis either, because the free Kite plan has no price history.
- **Data must exist first.** The file-based tools need the pipeline scripts to have been run (see the README). A missing file gives an error that names the script to run.
- **Name checks.** The benchmark tool accepts only letters, numbers, underscores and hyphens in a portfolio name, so a name cannot point outside the data folder.
- **News dates** are publication dates, not the moment a stock reacted.

## Connecting an MCP client

Add the server to the client's MCP settings. This is the usual shape for desktop MCP apps. Check your app's documentation for where the settings file lives.

```json
{
  "mcpServers": {
    "zerodha-portfolio-intelligence": {
      "command": "C:\\path\\to\\project\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "env": {"PYTHONPATH": "C:\\path\\to\\project"}
    }
  }
}
```

Replace `C:\\path\\to\\project` with the full path of the project folder, keeping the double backslashes. The `PYTHONPATH` entry lets Python find the `mcp_server` and `backend` packages. Restart the client after saving.

Then try questions such as "which portfolios can you analyse?", "what risk alerts does the concentrated_it portfolio have?" or "how did the diversified portfolio do against the Nifty 50?".

## Adding a tool

1. Write a plain function in a file under `mcp_server/tools/`. Give it type hints and a clear docstring, because the docstring becomes the description an AI app sees.
2. Register it in `mcp_server/server.py` with `mcp.tool()(module.function)`.
3. Run `python scripts/build_tool_registry.py` to update `tool_registry.json`.
4. Add a test in `tests/functional_tests/test_mcp_tools.py`.

## Safety

- The tools are read-only and make no network calls when they run. They read files already on disk.
- They return facts and figures, never advice. Disclosures and the number-checking safeguards belong to the web app's AI layer, so an AI app using these tools should keep the same rule: explain the figures, never recommend buying or selling.
- The server has no authentication, because it runs as a local process started by the client. Do not expose it on a network as it stands.