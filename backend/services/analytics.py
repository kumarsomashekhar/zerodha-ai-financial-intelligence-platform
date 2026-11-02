"""Deterministic portfolio analytics. The LLM never computes numbers; this module does."""
from pathlib import Path

import pandas as pd
from backend.services import kite_client

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "sample_portfolios.csv"

# Alert thresholds (make these configurable later, e.g. from an admin console)
SECTOR_LIMIT_PCT = 40.0
STOCK_LIMIT_PCT = 25.0
MIN_HOLDINGS = 5
STALE_DAYS = 3
VOLATILITY_LIMIT_PCT = 35.0

REQUIRED = ["portfolio_id", "symbol", "sector", "quantity", "avg_price", "current_price"]


def list_portfolios() -> list[str]:
    ids = sorted(pd.read_csv(DATA_FILE)["portfolio_id"].unique().tolist())
    return ["LIVE"] + ids


def _load_live_portfolio() -> pd.DataFrame:
    if not kite_client.is_logged_in():
        raise ValueError("Not logged in to Zerodha. Open http://localhost:8000/api/kite/login first")
    rows = kite_client.get_holdings()
    if not rows:
        raise ValueError("Your Zerodha account has no holdings to analyse")
    return pd.DataFrame({
        "portfolio_id": "LIVE",
        "symbol": [r["tradingsymbol"] for r in rows],
        "sector": "Unclassified",
        "quantity": [r["quantity"] for r in rows],
        "avg_price": [r["average_price"] for r in rows],
        "current_price": [r["last_price"] for r in rows],
    })


def load_portfolio(portfolio_id: str) -> pd.DataFrame:
    if portfolio_id == "LIVE":
        return _load_live_portfolio()
    df = pd.read_csv(DATA_FILE)
    missing = [c for c in REQUIRED if c not in df.columns]
    df = pd.read_csv(DATA_FILE)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Portfolio file is missing columns: {missing}")
    df = df[df["portfolio_id"] == portfolio_id].copy()
    if df.empty:
        raise KeyError(f"Portfolio '{portfolio_id}' not found")
    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["invested"] = df["quantity"] * df["avg_price"]
    df["value"] = df["quantity"] * df["current_price"]
    df["pnl"] = df["value"] - df["invested"]

    total_value = float(df["value"].sum())
    total_invested = float(df["invested"].sum())
    if total_value <= 0 or total_invested <= 0:
        raise ValueError("Portfolio has no positive value; cannot analyse")

    df["weight_pct"] = df["value"] / total_value * 100
    df["pnl_pct"] = df["pnl"] / df["invested"] * 100
    df["contribution_pct"] = df["pnl"] / total_invested * 100  # contribution to portfolio return

    sector_pct = (df.groupby("sector")["value"].sum() / total_value * 100).sort_values(ascending=False)
    hhi = float(((df["weight_pct"] / 100) ** 2).sum())  # 1/N for equal weights, 1.0 for one stock

    vol_proxy = None
    if "vol_30d_pct" in df.columns:
        vol_proxy = float((df["weight_pct"] / 100 * df["vol_30d_pct"]).sum())

    top = df.sort_values("weight_pct", ascending=False).iloc[0]
    age = int(df["data_age_days"].max()) if "data_age_days" in df.columns else 0

    return {
        "holdings_count": int(len(df)),
        "total_value": round(total_value, 0),
        "total_invested": round(total_invested, 0),
        "total_pnl_pct": round((total_value / total_invested - 1) * 100, 1),
        "top_holding": {"symbol": str(top["symbol"]), "weight_pct": round(float(top["weight_pct"]), 1)},
        "sector_pct": {k: round(float(v), 1) for k, v in sector_pct.items()},
        "hhi": round(hhi, 2),
        "weighted_volatility_pct": None if vol_proxy is None else round(vol_proxy, 1),
        "data_age_days": age,
        "holdings": [
            {
                "symbol": r["symbol"],
                "sector": r["sector"],
                "weight_pct": round(float(r["weight_pct"]), 1),
                "pnl_pct": round(float(r["pnl_pct"]), 1),
                "contribution_pct": round(float(r["contribution_pct"]), 1),
            }
            for _, r in df.sort_values("weight_pct", ascending=False).iterrows()
        ],
    }


def risk_alerts(m: dict) -> list[dict]:
    alerts = []
    top_sector, top_sector_pct = next(iter(m["sector_pct"].items()))
    if top_sector_pct > SECTOR_LIMIT_PCT:
        alerts.append({"type": "sector_concentration", "severity": "high",
                       "metric": f"{top_sector} sector weight", "value": top_sector_pct,
                       "threshold": SECTOR_LIMIT_PCT})
    if m["top_holding"]["weight_pct"] > STOCK_LIMIT_PCT:
        alerts.append({"type": "single_stock_concentration", "severity": "medium",
                       "metric": f"{m['top_holding']['symbol']} weight",
                       "value": m["top_holding"]["weight_pct"], "threshold": STOCK_LIMIT_PCT})
    if m["holdings_count"] < MIN_HOLDINGS:
        alerts.append({"type": "low_diversification", "severity": "medium",
                       "metric": "number of holdings", "value": m["holdings_count"],
                       "threshold": MIN_HOLDINGS})
    vol = m["weighted_volatility_pct"]
    if vol is not None and vol > VOLATILITY_LIMIT_PCT:
        alerts.append({"type": "high_volatility", "severity": "medium",
                       "metric": "weighted 30-day volatility", "value": vol,
                       "threshold": VOLATILITY_LIMIT_PCT})
    if m["data_age_days"] > STALE_DAYS:
        alerts.append({"type": "stale_data", "severity": "high",
                       "metric": "data age (days)", "value": m["data_age_days"],
                       "threshold": STALE_DAYS})
    return alerts
