"""Download news for every real stock in the sample portfolios (Check 4 files stay untouched)."""
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")

SOURCE = ROOT / "data" / "sample_portfolios.csv"
OUTPUT = ROOT / "data" / "processed" / "news_all_stocks.csv"

API_KEY = os.getenv("GNEWS_API_KEY")
if not API_KEY:
    raise SystemExit("GNEWS_API_KEY was not found in backend/.env. Check the line is saved.")

# symbol: (name to search for, words that show an article is really about the company)
COMPANIES = {
    "INFY": ("Infosys", ["infosys", "infy"]),
    "TCS": ("Tata Consultancy Services", ["tcs", "tata consultancy"]),
    "WIPRO": ("Wipro", ["wipro"]),
    "HDFCBANK": ("HDFC Bank", ["hdfc bank", "hdfcbank"]),
    "ITC": ("ITC Ltd", ["itc"]),
    "RELIANCE": ("Reliance Industries", ["reliance"]),
    "LT": ("Larsen & Toubro", ["larsen", "l&t"]),
    "SUNPHARMA": ("Sun Pharma", ["sun pharma", "sunpharma"]),
    "MARUTI": ("Maruti Suzuki", ["maruti"]),
    "BHARTIARTL": ("Bharti Airtel", ["airtel", "bharti"]),
}


def names_company(text, symbol):
    words = COMPANIES[symbol][1]
    pattern = r"\b(" + "|".join(re.escape(w) for w in words) + r")\b"
    return bool(re.search(pattern, str(text).lower()))


symbols = sorted(pd.read_csv(SOURCE)["symbol"].str.replace(".NS", "", regex=False).unique())
unmapped = [s for s in symbols if s not in COMPANIES]
todo = [s for s in symbols if s in COMPANIES]

rows, errors = [], []
for symbol in todo:
    name = COMPANIES[symbol][0]
    params = {"q": f'"{name}"', "lang": "en", "country": "in", "max": 10, "apikey": API_KEY}
    try:
        resp = requests.get("https://gnews.io/api/v4/search", params=params, timeout=30)
    except requests.RequestException as e:
        errors.append(f"{symbol}: network problem ({type(e).__name__})")
        continue
    if resp.status_code != 200:
        errors.append(f"{symbol}: GNews returned status {resp.status_code}: {resp.text[:300]}")
        continue
    for a in resp.json().get("articles", []):
        rows.append({
            "symbol": symbol,
            "search_query": name,
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
    news = news.drop_duplicates(subset=["symbol", "url"]).sort_values(
        ["symbol", "published_at"], ascending=[True, False]
    )
    news["mentions_company"] = [
        names_company(f"{t} {d}", s)
        for t, d, s in zip(news["title"], news["description"], news["symbol"])
    ]
news.to_csv(OUTPUT, index=False)

print("Articles per stock (and how many really mention the company):")
if news.empty:
    print("(none)")
else:
    print(news.groupby("symbol").agg(
        articles=("url", "count"), mention_company=("mentions_company", "sum")
    ).to_string())
if unmapped:
    print("\nNo company name set up yet for:", ", ".join(unmapped))
if errors:
    print("\nProblems:")
    for e in errors:
        print(" -", e)
print(f"\nSaved to: {OUTPUT}")