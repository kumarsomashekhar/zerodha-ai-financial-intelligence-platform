"""Checks that no secret value from backend/.env appears in any file Git will upload.
Prints file names only, never the secrets themselves."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
env_file = ROOT / "backend" / ".env"

secrets = []
for line in env_file.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        name, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if name.strip().upper().endswith(("KEY", "SECRET", "TOKEN")) and len(value) >= 8:
            secrets.append(value)

files = subprocess.run(
    ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
).stdout.splitlines()

hits = []
for name in files:
    path = ROOT / name
    if path.suffix.lower() in (".png", ".jpg", ".ico", ".db"):
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    if any(s in text for s in secrets):
        hits.append(name)

print(f"Checked {len(files)} files that Git would upload against {len(secrets)} secret values.")
if hits:
    print("FOUND secret values in these files. Do NOT upload yet:")
    for h in hits:
        print(" -", h)
else:
    print("OK: no secret values found in any file Git would upload.")