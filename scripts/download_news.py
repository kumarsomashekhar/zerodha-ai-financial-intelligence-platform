"""Data pipeline, part 4: download financial news and run Check 4."""
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")

HOLDINGS = ROOT / "data" / "processed" / "portfolio_holdings_clean.csv"
OUTPUT = ROOT / "data" / "processed" / "financial_news_clean.csv"

API_KEY = os.getenv("GNEWS_API_KEY")
if not API_KEY:
    raise SystemExit("GNEWS_API_KEY was not found in backend/.env. Check the line is saved.")

# Search by company name, because news articles rarely use the stock symbol
COMPANY_NAMES = {
    "INFY": "Infosys",
    "TCS": "Tata Consultancy Services",
    "WIPRO": "Wipro",
    "HDFCBANK": "HDFC Bank",
    "ITC": "ITC Ltd",
}

# Words that show an article is really about the company
KEYWORDS = {
    "INFY": ["infosys", "infy"],
    "TCS": ["tcs", "tata consultancy"],
    "WIPRO": ["wipro"],
    "HDFCBANK": ["hdfc bank", "hdfcbank"],
    "ITC": ["itc"],
}


def names_company(text, symbol):
    words = KEYWORDS.get(symbol, [symbol.lower()])
    pattern = r"\b(" + "|".join(re.escape(w) for w in words) + r")\b"
    return bool(re.search(pattern, str(text).lower()))


holdings = pd.read_csv(HOLDINGS)
rows, no_articles, errors = [], [], []

for symbol in holdings["symbol"]:
    company = COMPANY_NAMES.get(symbol, symbol)
    params = {
        "q": f'"{company}"',
        "lang": "en",
        "country": "in",
        "max": 10,
        "apikey": API_KEY,
    }
    try:
        resp = requests.get("https://gnews.io/api/v4/search", params=params, timeout=30)
    except requests.RequestException as e:
        errors.append(f"{symbol}: network problem ({type(e).__name__})")
        continue
    if resp.status_code != 200:
        errors.append(f"{symbol}: GNews returned status {resp.status_code}: {resp.text[:300]}")
        continue
    articles = resp.json().get("articles", [])
    if not articles:
        no_articles.append(symbol)
    for a in articles:
        rows.append({
            "symbol": symbol,
            "search_query": company,
            "published_at": a.get("publishedAt"),
            "title": a.get("title"),
            "description": a.get("description"),
            "source": (a.get("source") or {}).get("name"),
            "url": a.get("url"),
        })
    time.sleep(1.5)  # be gentle with the free plan

columns = ["symbol", "search_query", "published_at", "title", "description", "source", "url"]
news = pd.DataFrame(rows, columns=columns)

if not news.empty:
    news["published_at"] = pd.to_datetime(news["published_at"], errors="coerce", utc=True)
    news = news.drop_duplicates(subset=["url"]).sort_values(
        ["symbol", "published_at"], ascending=[True, False]
    )
    news["mentions_company"] = [
        names_company(f"{t} {d}", s)
        for t, d, s in zip(news["title"], news["description"], news["symbol"])
    ]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
news.to_csv(OUTPUT, index=False)

# ---- Check 4 ----
print("Articles per stock (and how many really mention the company):")
if news.empty:
    print("(none)")
else:
    summary = news.groupby("symbol").agg(
        articles=("url", "count"), mention_company=("mentions_company", "sum")
    )
    print(summary.to_string())
if no_articles:
    print("\nNo articles returned for:", ", ".join(no_articles))
if errors:
    print("\nProblems:")
    for e in errors:
        print(" -", e)

print()
if news.empty:
    print("FAIL  Headlines are present")
    print("No articles were saved. Paste the messages above and we will work out why.")
else:
    titles_ok = bool(news["title"].notna().all() and (news["title"].str.strip() != "").all())
    dates_ok = bool(news["published_at"].notna().all())
    urls_ok = bool(news["url"].astype(str).str.startswith(("http://", "https://")).all())
    symbols_ok = set(news["symbol"]).issubset(set(holdings["symbol"]))
    print(("PASS  " if titles_ok else "FAIL  ") + "Headlines are present")
    print(("PASS  " if dates_ok else "FAIL  ") + "Publication dates are parseable")
    print(("PASS  " if urls_ok else "FAIL  ") + "URLs look like web links")
    print(("PASS  " if symbols_ok else "FAIL  ") + "Stock symbols match the portfolio")
    print(f"\nSaved to: {OUTPUT}")