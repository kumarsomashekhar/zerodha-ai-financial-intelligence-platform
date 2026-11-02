"""Data pipeline, part 3: download the Nifty 50 benchmark and run Check 3."""
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / "data" / "processed" / "stock_prices_clean.csv"
OUTPUT = ROOT / "data" / "processed" / "benchmark_prices_clean.csv"

SYMBOL = "^NSEI"

# Use the same date range as the stock prices so the comparison is fair
stock_dates = pd.read_csv(PRICES, parse_dates=["Date"])["Date"]
start, end = stock_dates.min(), stock_dates.max() + pd.Timedelta(days=1)

try:
    hist = yf.Ticker(SYMBOL).history(start=start, end=end, auto_adjust=False)
except Exception as e:
    print(f"Download failed for {SYMBOL}: {e}")
    hist = pd.DataFrame()

if hist.empty:
    raise SystemExit(
        "No benchmark records were returned. As your brief says, we must "
        "resolve this before comparing against the benchmark."
    )

idx = hist.index
if getattr(idx, "tz", None) is not None:
    idx = idx.tz_localize(None)

bench = pd.DataFrame({
    "Date": idx.normalize(),
    "symbol": SYMBOL,
    "Open": hist["Open"].values,
    "High": hist["High"].values,
    "Low": hist["Low"].values,
    "Close": hist["Close"].values,
})
bench = bench.dropna(subset=["Close"]).drop_duplicates(subset=["Date"]).sort_values("Date")
bench.to_csv(OUTPUT, index=False)

# ---- Check 3 ----
print(f"Rows downloaded: {len(bench)}")
print(f"Date range: {bench['Date'].min().date()} to {bench['Date'].max().date()}")
print(f"Overlapping dates with your stocks: {bench['Date'].isin(stock_dates).sum()}")
print()
checks = {
    "File contains the ^NSEI symbol": bool((bench["symbol"] == SYMBOL).all() and len(bench) > 0),
    "Close column is numeric": bool(pd.to_numeric(bench["Close"], errors="coerce").notna().all()),
    "Multiple dates exist": len(bench) > 1,
}
for name, passed in checks.items():
    print(("PASS  " if passed else "FAIL  ") + name)
print(f"\nSaved to: {OUTPUT}")