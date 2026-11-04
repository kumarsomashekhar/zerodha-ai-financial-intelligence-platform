"""Searches the whole Git history for the real secret values in backend/.env.
Prints key names and counts only, never the secrets themselves."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

secrets = {}
for line in (ROOT / "backend" / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        name, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if name.strip().upper().endswith(("KEY", "SECRET", "TOKEN")) and len(value) >= 8:
            secrets[name.strip()] = value

commits = subprocess.run(
    ["git", "rev-list", "--all", "--count"], cwd=ROOT, capture_output=True, text=True
).stdout.strip()
print(f"Searching {commits} commits of history for {len(secrets)} secret values.")

found = False
for name, value in secrets.items():
    hits = subprocess.run(
        ["git", "log", "--all", "--oneline", "-S", value],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout.strip()
    if hits:
        found = True
        print(f"FOUND: {name} appears in {len(hits.splitlines())} commit(s).")

if found:
    print("Do NOT make the repository public. Tell Claude what this printed.")
else:
    print("OK: none of the secret values appears anywhere in the history.")