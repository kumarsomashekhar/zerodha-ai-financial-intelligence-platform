"""Prints the ID of the most recently saved analysis job (ignores the test row)."""
import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "data" / "app.db"
row = sqlite3.connect(db).execute(
    "SELECT job_id, portfolio_id FROM jobs WHERE job_id != 'selftest' ORDER BY rowid DESC LIMIT 1"
).fetchone()
print(row[0] if row else "No analysis jobs saved yet")