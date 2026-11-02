"""Data pipeline, part 2: download historical prices and run Check 2."""
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
HOLDINGS = ROOT / "data" / "processed" / "portfolio_holdings_clean.csv"
OUTPUT = ROOT / "data" / "processed" / "stock_prices_clean.csv"

holdings = pd.read_csv(HOLDINGS)
frames, failed = [], []

for _, row in holdings.iterrows():
    symbol, yahoo = row["symbol"], row["yahoo_symbol"]
    try:
        hist = yf.Ticker(yahoo).history(period="1y", auto_adjust=False)
    except Exception as e:
        print(f"Download failed for {yahoo}: {e}")
        hist = pd.DataFrame()
    if hist.empty:
        failed.append(symbol)
        continue
    idx = hist.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    frame = pd.DataFrame({
        "Date": idx.normalize(),
        "symbol": symbol,
        "Open": hist["Open"].values,
        "High": hist["High"].values,
        "Low": hist["Low"].values,
        "Close": hist["Close"].values,
        "Volume": hist["Volume"].values,
    })
    frames.append(frame)

if not frames:
    raise SystemExit("No prices were downloaded for any stock. Check your internet connection.")

prices = pd.concat(frames, ignore_index=True)
prices = prices.dropna(subset=["Close"]).drop_duplicates(subset=["Date", "symbol"])
prices = prices.sort_values(["symbol", "Date"])
prices.to_csv(OUTPUT, index=False)

# ---- Check 2 ----
rows_per_stock = prices.groupby("symbol").size()
close_numeric = pd.to_numeric(prices["Close"], errors="coerce").notna().all()
dates_valid = prices["Date"].notna().all() and (prices["Date"] <= pd.Timestamp.today()).all()
high_ok = bool((prices["High"] >= prices["Low"]).all())
symbols_match = set(prices["symbol"]) == set(holdings["symbol"])

print("\nRows downloaded per stock:")
print(rows_per_stock.to_string())
print(f"\nDate range: {prices['Date'].min().date()} to {prices['Date'].max().date()}")
if failed:
    print("\nNo data for:", ", ".join(failed))

print()
checks = {
    "Multiple dates for every downloaded stock": bool((rows_per_stock > 1).all()),
    "Close column is numeric": bool(close_numeric),
    "Dates are valid": bool(dates_valid),
    "High prices are not lower than Low prices": high_ok,
    "Stock symbols match the portfolio": symbols_match,
}
for name, passed in checks.items():
    print(("PASS  " if passed else "FAIL  ") + name)
print(f"\nSaved to: {OUTPUT}")