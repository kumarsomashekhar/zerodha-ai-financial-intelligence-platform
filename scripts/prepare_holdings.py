"""Data pipeline, part 1: clean the portfolio holdings and run Check 1."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "sample_portfolios.csv"
OUTPUT = ROOT / "data" / "processed" / "portfolio_holdings_clean.csv"

df = pd.read_csv(SOURCE)

# Pick the first sample portfolio that has exactly five holdings
counts = df.groupby("portfolio_id")["symbol"].count()
five = counts[counts == 5]
if five.empty:
    raise SystemExit("No sample portfolio has exactly 5 holdings. Tell me what you see below:\n" + counts.to_string())
portfolio_id = five.index[0]

holdings = df[df["portfolio_id"] == portfolio_id][
    ["portfolio_id", "symbol", "sector", "quantity", "avg_price"]
].copy()
holdings = holdings.rename(columns={"avg_price": "assumed_purchase_price"})

# Yahoo Finance needs ".NS" after Indian stock names (for example TCS.NS)
holdings["yahoo_symbol"] = holdings["symbol"].apply(
    lambda s: s if s.endswith(".NS") else s + ".NS"
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
holdings.to_csv(OUTPUT, index=False)

# ---- Check 1 ----
checks = {
    "Five holdings are present": len(holdings) == 5,
    "Each symbol is unique": holdings["symbol"].is_unique,
    "All quantities are positive": bool((holdings["quantity"] > 0).all()),
    "All purchase prices are positive": bool((holdings["assumed_purchase_price"] > 0).all()),
    "Each holding has a sector": bool(holdings["sector"].notna().all()
                                      and (holdings["sector"].astype(str).str.strip() != "").all()),
}

print(f"Portfolio used: {portfolio_id}")
print(holdings.to_string(index=False))
print()
for name, passed in checks.items():
    print(("PASS  " if passed else "FAIL  ") + name)
print(f"\nSaved to: {OUTPUT}")