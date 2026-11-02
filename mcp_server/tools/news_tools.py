"""News tools: read the downloaded news file."""
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[2] / "data" / "processed"


def get_recent_news(symbol: str, limit: int = 5) -> dict:
    """Recent news headlines about one stock, newest first, with source, date and link. Dates are publication dates, not the moment the stock reacted."""
    file = PROC / "news_all_stocks.csv"
    if not file.exists():
        return {"error": "No news file found. Run scripts/download_news_all.py first"}
    news = pd.read_csv(file)
    name = symbol.upper().replace(".NS", "")
    news = news[(news["symbol"] == name) & (news["mentions_company"].astype(str).str.lower() == "true")]
    if news.empty:
        return {"error": f"No news saved for '{symbol}'"}
    limit = max(1, min(int(limit), 10))
    news = news.sort_values("published_at", ascending=False).head(limit)
    return {
        "symbol": name,
        "articles": [
            {
                "title": str(r["title"]),
                "source": str(r["source"]),
                "published_at": str(r["published_at"]),
                "url": str(r["url"]),
            }
            for _, r in news.iterrows()
        ],
    }