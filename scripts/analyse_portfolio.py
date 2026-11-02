"""Analysis: portfolio KPIs versus the Nifty 50, plus graphs."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files, no pop-up windows
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
GRAPHS = PROC / "graphs"
GRAPHS.mkdir(parents=True, exist_ok=True)

holdings = pd.read_csv(PROC / "portfolio_holdings_clean.csv")
prices = pd.read_csv(PROC / "stock_prices_clean.csv", parse_dates=["Date"])
bench = pd.read_csv(PROC / "benchmark_prices_clean.csv", parse_dates=["Date"])

info = holdings.set_index("symbol")
qty = info["quantity"]

# One column of closing prices per stock, only on dates the benchmark also has
close = prices.pivot(index="Date", columns="symbol", values="Close").sort_index()
bench_close = bench.set_index("Date")["Close"].sort_index()
dates = close.index.intersection(bench_close.index)
close = close.loc[dates].ffill()[qty.index]
bench_close = bench_close.loc[dates]

values = close * qty            # value of each stock on each day
portfolio = values.sum(axis=1)  # total portfolio value on each day


def total_return(s):
    return (s.iloc[-1] / s.iloc[0] - 1) * 100


def volatility(s):
    return s.pct_change().std() * np.sqrt(252) * 100


def max_drawdown(s):
    return (s / s.cummax() - 1).min() * 100


# ---- Portfolio-level KPIs ----
kpis = {
    "Start date": dates.min().date(),
    "End date": dates.max().date(),
    "Portfolio value at start (Rs)": round(portfolio.iloc[0]),
    "Portfolio value at end (Rs)": round(portfolio.iloc[-1]),
    "Portfolio return (%)": round(total_return(portfolio), 1),
    "Nifty 50 return (%)": round(total_return(bench_close), 1),
    "Return versus Nifty 50 (percentage points)": round(total_return(portfolio) - total_return(bench_close), 1),
    "Portfolio volatility (% a year)": round(volatility(portfolio), 1),
    "Nifty 50 volatility (% a year)": round(volatility(bench_close), 1),
    "Portfolio max drawdown (%)": round(max_drawdown(portfolio), 1),
    "Nifty 50 max drawdown (%)": round(max_drawdown(bench_close), 1),
}

# ---- Per-stock table ----
last_values = values.iloc[-1]
stocks = pd.DataFrame({
    "sector": info["sector"],
    "quantity": qty,
    "last_close": close.iloc[-1],
    "value": last_values,
    "weight_pct": last_values / last_values.sum() * 100,
    "return_1y_pct": (close.iloc[-1] / close.iloc[0] - 1) * 100,
    "vs_purchase_price_pct": (close.iloc[-1] / info["assumed_purchase_price"] - 1) * 100,
}).round(1)
sectors = stocks.groupby("sector")["weight_pct"].sum().sort_values(ascending=False).round(1)

pd.Series(kpis).to_csv(PROC / "portfolio_kpis.csv", header=["value"])
stocks.to_csv(PROC / "stock_kpis.csv")

# ---- Graphs ----
# 1. Portfolio versus Nifty 50, both starting at 100
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(portfolio.index, portfolio / portfolio.iloc[0] * 100, label="Your portfolio", linewidth=2)
ax.plot(bench_close.index, bench_close / bench_close.iloc[0] * 100, label="Nifty 50", linewidth=2)
ax.axhline(100, color="grey", linewidth=0.8, linestyle="--")
ax.set_title("Portfolio versus Nifty 50 (both start at 100)")
ax.set_ylabel("Index value")
ax.legend()
fig.tight_layout()
fig.savefig(GRAPHS / "portfolio_vs_nifty.png", dpi=150)
plt.close(fig)

# 2. One-year return of each stock
fig, ax = plt.subplots(figsize=(8, 5))
ordered = stocks["return_1y_pct"].sort_values()
ax.barh(ordered.index, ordered.values, color=["#c0392b" if v < 0 else "#27ae60" for v in ordered.values])
ax.set_title("One-year return by stock (%)")
ax.axvline(0, color="black", linewidth=0.8)
fig.tight_layout()
fig.savefig(GRAPHS / "stock_returns.png", dpi=150)
plt.close(fig)

# 3. Sector weights
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(sectors.index, sectors.values, color="#2c6fbb")
ax.set_title("Sector weights (% of portfolio value)")
ax.set_ylabel("%")
fig.tight_layout()
fig.savefig(GRAPHS / "sector_weights.png", dpi=150)
plt.close(fig)

# ---- Print a summary ----
print("PORTFOLIO KPIs")
for k, v in kpis.items():
    print(f"  {k}: {v}")
print("\nPER-STOCK KPIs")
print(stocks.to_string())
print("\nSECTOR WEIGHTS (%)")
print(sectors.to_string())
print(f"\nGraphs saved in: {GRAPHS}")