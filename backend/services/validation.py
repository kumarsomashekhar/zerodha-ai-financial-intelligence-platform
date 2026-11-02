"""Guardrails: reject explanations that invent numbers or give advice."""
import re

BANNED = re.compile(r"\b(buy|sell|guarantee[d]?|will (rise|fall|double)|sure[- ]shot)\b", re.I)
NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?")  # ignore digits inside tickers like SMALLCAP1


def _numbers_in(obj, out: set):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers_in(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers_in(v, out)


def validate(explanation: dict, ctx: dict) -> tuple[bool, list[str]]:
    issues = []
    for key in ("summary", "key_drivers", "risk_note"):
        if key not in explanation:
            issues.append(f"missing field: {key}")
    if issues:
        return False, issues

    text = " ".join([explanation["summary"], explanation["risk_note"], *map(str, explanation["key_drivers"])])
    if BANNED.search(text):
        issues.append("contains advice or prediction language")

    allowed: set = set()
    _numbers_in(ctx, allowed)
    allowed |= {abs(a) for a in allowed}  # "a loss of 5.2%" matches -5.2
    text = re.sub(r"(?<=\d),(?=\d)", "", text)  # "790,900" counts as 790900
    for n in NUMBER.findall(text):
        if not any(abs(float(n) - a) <= 0.051 for a in allowed):
            issues.append(f"number {n} not found in analytics data")
    return (not issues), issues
