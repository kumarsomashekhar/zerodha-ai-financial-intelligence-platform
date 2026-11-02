"""Analytics tools: read the per-portfolio benchmark results."""
from pathlib import Path

import pandas as pd

PORTFOLIOS = Path(__file__).resolve().parents[2] / "data" / "processed" / "portfolios"


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    return int(f) if f.is_integer() else f


def get_benchmark_comparison(portfolio_id: str) -> dict:
    """One-year return, volatility and maximum drawdown of a sample portfolio versus the Nifty 50, using real downloaded market prices."""
    if not portfolio_id.replace("_", "").replace("-", "").isalnum():
        return {"error": "Invalid portfolio name"}
    kpi_file = PORTFOLIOS / portfolio_id / "portfolio_kpis.csv"
    if not kpi_file.exists():
        return {"error": f"Benchmark analysis is not available for '{portfolio_id}' yet"}
    raw = pd.read_csv(kpi_file, index_col=0)["value"].to_dict()
    return {"portfolio_id": portfolio_id, "kpis": {k: _num(v) for k, v in raw.items()}}