"""Data pipeline, part 5: build the data-quality report (Check 5)."""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REPORT = PROC / "data_quality_report.txt"

holdings = pd.read_csv(PROC / "portfolio_holdings_clean.csv")
prices = pd.read_csv(PROC / "stock_prices_clean.csv", parse_dates=["Date"])
bench = pd.read_csv(PROC / "benchmark_prices_clean.csv", parse_dates=["Date"])
news = pd.read_csv(PROC / "financial_news_clean.csv")

# Words that show a headline is really about the company
KEYWORDS = {
    "INFY": ["infosys", "infy"],
    "TCS": ["tcs", "tata consultancy"],
    "WIPRO": ["wipro"],
    "HDFCBANK": ["hdfc bank", "hdfcbank"],
    "ITC": ["itc"],
}

def names_company(title, symbol):
    words = KEYWORDS.get(symbol, [symbol.lower()])
    pattern = r"\b(" + "|".join(re.escape(w) for w in words) + r")\b"
    return bool(re.search(pattern, str(title).lower()))

lines, flags = [], []
add = lines.append

add("DATA QUALITY REPORT")
add("=" * 60)

add("\n1. PORTFOLIO HOLDINGS")
add(f"Holdings: {len(holdings)}   Missing values: {int(holdings.isna().sum().sum())}")

add("\n2. STOCK PRICES")
add(f"Date range: {prices['Date'].min().date()} to {prices['Date'].max().date()}")
for sym in holdings["symbol"]:
    sub = prices[prices["symbol"] == sym]
    add(f"  {sym:9s} rows: {len(sub):4d}   missing Close: {int(sub['Close'].isna().sum())}")
    if sub.empty:
        flags.append(f"{sym}: no price data at all (check the ticker or the source)")
counts = prices.groupby("symbol").size()
if counts.max() - counts.min() > 5:
    flags.append("Stocks have very different numbers of price rows")

add("\n3. BENCHMARK (^NSEI)")
add(f"Rows: {len(bench)}   Date range: {bench['Date'].min().date()} to {bench['Date'].max().date()}")
overlap = bench["Date"].isin(prices["Date"]).sum()
add(f"Dates shared with stock prices: {overlap} of {len(bench)}")
if overlap < len(bench) * 0.95:
    flags.append("Benchmark dates do not line up well with the stock dates")

add("\n4. FINANCIAL NEWS")
add(f"Total articles: {len(news)}   Date range: "
    f"{pd.to_datetime(news['published_at'], utc=True).min().date()} to "
    f"{pd.to_datetime(news['published_at'], utc=True).max().date()}")
for sym in holdings["symbol"]:
    sub = news[news["symbol"] == sym]
    if sub.empty:
        add(f"  {sym:9s} articles: 0")
        flags.append(f"{sym}: no news articles")
        continue
    named = int(sub["mentions_company"].sum())
    add(f"  {sym:9s} articles: {len(sub):3d}   articles mentioning the company: {named} of {len(sub)}")
    if len(sub) < 5:
        flags.append(f"{sym}: only {len(sub)} news articles (low count)")
    if named < len(sub) / 2:
        flags.append(f"{sym}: fewer than half the headlines name the company; review manually")

shared = news.groupby("title")["symbol"].nunique()
shared = shared[shared > 1]
if len(shared):
    flags.append(f"{len(shared)} headline(s) appear under more than one stock")

add("\n5. THINGS TO REVIEW")
if flags:
    for f in flags:
        add(f"  - {f}")
else:
    add("  Nothing flagged.")
add("\nNote: a news publication date is not the moment a stock first reacted to it.")

text = "\n".join(lines)
REPORT.write_text(text, encoding="utf-8")


import sys

sys.path.insert(0, str(ROOT))
from backend.services import storage  # noqa: E402

storage.save_quality_run(
    {
        "price_rows": int(len(prices)),
        "benchmark_rows": int(len(bench)),
        "news_articles": int(len(news)),
        "flag_count": len(flags),
    },
    flags,
    text,
)

print(text)
print(f"\nSaved to: {REPORT}")