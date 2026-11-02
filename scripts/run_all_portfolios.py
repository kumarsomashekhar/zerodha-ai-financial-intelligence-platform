"""Analyse every sample portfolio against the Nifty 50 and save results per portfolio."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "sample_portfolios.csv"
OUT = ROOT / "data" / "processed" / "portfolios"
OUT.mkdir(parents=True, exist_ok=True)


def clean_index(idx):
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def to_series(hist, name):
    s = pd.Series(hist["Close"].values, index=clean_index(hist.index), name=name)
    return s[~s.index.duplicated()].dropna()


def download_close(symbol):
    """Closing prices for one stock. Tries the NSE name (.NS), then the BSE name (.BO)."""
    base = symbol.replace(".NS", "").replace(".BO", "")
    for suffix in (".NS", ".BO"):
        try:
            hist = yf.Ticker(base + suffix).history(period="1y", auto_adjust=False)
        except Exception:
            continue
        if not hist.empty:
            return to_series(hist, symbol)
    return None


def total_return(s):
    return (s.iloc[-1] / s.iloc[0] - 1) * 100


def volatility(s):
    return s.pct_change().std() * np.sqrt(252) * 100


def max_drawdown(s):
    return (s / s.cummax() - 1).min() * 100


# ---- Benchmark, downloaded once ----
bench_hist = yf.Ticker("^NSEI").history(period="1y", auto_adjust=False)
if bench_hist.empty:
    raise SystemExit("Could not download the Nifty 50 benchmark. Check your internet connection.")
bench_all = to_series(bench_hist, "^NSEI")

df = pd.read_csv(SOURCE)
cache = {}
summary = []

for pid, group in df.groupby("portfolio_id"):
    group = group.drop_duplicates("symbol")
    series, skipped = {}, []
    for sym in group["symbol"]:
        if sym not in cache:
            cache[sym] = download_close(sym)
        if cache[sym] is None:
            skipped.append(sym)
        else:
            series[sym] = cache[sym]

    if not series:
        summary.append((pid, "FAILED: no price data for any stock", ", ".join(skipped), "", ""))
        continue

    used = group[group["symbol"].isin(series)].set_index("symbol")
    close = pd.concat(series, axis=1)[used.index].sort_index().ffill()
    dates = close.dropna().index.intersection(bench_all.index)
    if len(dates) < 2:
        summary.append((pid, "FAILED: too few shared dates", ", ".join(skipped), "", ""))
        continue
    close = close.loc[dates]
    bench = bench_all.loc[dates]

    qty = used["quantity"]
    values = close * qty
    portfolio = values.sum(axis=1)

    kpis = {
        "Start date": dates.min().date(),
        "End date": dates.max().date(),
        "Portfolio value at start (Rs)": round(portfolio.iloc[0]),
        "Portfolio value at end (Rs)": round(portfolio.iloc[-1]),
        "Portfolio return (%)": round(total_return(portfolio), 1),
        "Nifty 50 return (%)": round(total_return(bench), 1),
        "Return versus Nifty 50 (percentage points)": round(total_return(portfolio) - total_return(bench), 1),
        "Portfolio volatility (% a year)": round(volatility(portfolio), 1),
        "Nifty 50 volatility (% a year)": round(volatility(bench), 1),
        "Portfolio max drawdown (%)": round(max_drawdown(portfolio), 1),
        "Nifty 50 max drawdown (%)": round(max_drawdown(bench), 1),
        "Stocks analysed": len(used),
        "Stocks skipped (no price data)": ", ".join(skipped) if skipped else "none",
    }

    last_values = values.iloc[-1]
    stocks = pd.DataFrame({
        "sector": used["sector"],
        "quantity": qty,
        "last_close": close.iloc[-1],
        "value": last_values,
        "weight_pct": last_values / last_values.sum() * 100,
        "return_1y_pct": (close.iloc[-1] / close.iloc[0] - 1) * 100,
        "vs_purchase_price_pct": (close.iloc[-1] / used["avg_price"] - 1) * 100,
    }).round(1)
    stocks.index.name = "symbol"
    sectors = stocks.groupby("sector")["weight_pct"].sum().sort_values(ascending=False).round(1)

    folder = OUT / pid
    folder.mkdir(parents=True, exist_ok=True)
    pd.Series(kpis).to_csv(folder / "portfolio_kpis.csv", header=["value"])
    stocks.to_csv(folder / "stock_kpis.csv")

    # Graph 1: portfolio versus Nifty 50, both starting at 100
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(portfolio.index, portfolio / portfolio.iloc[0] * 100, label="Your portfolio", linewidth=2)
    ax.plot(bench.index, bench / bench.iloc[0] * 100, label="Nifty 50", linewidth=2)
    ax.axhline(100, color="grey", linewidth=0.8, linestyle="--")
    ax.set_title(f"{pid}: portfolio versus Nifty 50 (both start at 100)")
    ax.set_ylabel("Index value")
    ax.legend()
    fig.tight_layout()
    fig.savefig(folder / "portfolio_vs_nifty.png", dpi=150)
    plt.close(fig)

    # Graph 2: one-year return of each stock
    fig, ax = plt.subplots(figsize=(8, 5))
    ordered = stocks["return_1y_pct"].sort_values()
    ax.barh(ordered.index, ordered.values,
            color=["#c0392b" if v < 0 else "#27ae60" for v in ordered.values])
    ax.set_title(f"{pid}: one-year return by stock (%)")
    ax.axvline(0, color="black", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(folder / "stock_returns.png", dpi=150)
    plt.close(fig)

    # Graph 3: sector weights
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(sectors.index, sectors.values, color="#2c6fbb")
    ax.set_title(f"{pid}: sector weights (% of portfolio value)")
    ax.set_ylabel("%")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(folder / "sector_weights.png", dpi=150)
    plt.close(fig)

    summary.append((pid, "ok", ", ".join(skipped) if skipped else "none",
                    kpis["Portfolio return (%)"], kpis["Nifty 50 return (%)"]))

print("\nSUMMARY")
print(pd.DataFrame(summary, columns=["portfolio", "status", "skipped stocks",
                                     "portfolio return %", "nifty return %"]).to_string(index=False))
print(f"\nResults saved in: {OUT}")