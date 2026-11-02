"""Market data tools: read the cleaned price files."""
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[2] / "data" / "processed"


def get_stock_price_summary(symbol: str) -> dict:
    """Latest closing price, one-year return and how old the latest price is, for a stock whose prices were downloaded (INFY, TCS, WIPRO, HDFCBANK, ITC)."""
    file = PROC / "stock_prices_clean.csv"
    if not file.exists():
        return {"error": "No price file found. Run scripts/download_prices.py first"}
    prices = pd.read_csv(file, parse_dates=["Date"])
    name = symbol.upper().replace(".NS", "")
    sub = prices[prices["symbol"] == name].sort_values("Date")
    if sub.empty:
        return {"error": f"No downloaded prices for '{symbol}'. Available: {sorted(prices['symbol'].unique())}"}
    first, last = sub.iloc[0], sub.iloc[-1]
    age = int((pd.Timestamp.today().normalize() - last["Date"]).days)
    return {
        "symbol": name,
        "latest_close": round(float(last["Close"]), 2),
        "latest_price_date": str(last["Date"].date()),
        "first_price_date": str(first["Date"].date()),
        "one_year_return_pct": round((float(last["Close"]) / float(first["Close"]) - 1) * 100, 1),
        "price_age_days": age,
        "freshness": "ok" if age <= 3 else "stale: do not present this as a current price",
    }