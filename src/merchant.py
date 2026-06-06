"""Best-effort merchant extraction and a stable key for rule matching."""
import re

_NUMERIC_RUN = re.compile(r"\d{3,}")


def extract_merchant(description: str) -> str:
    s = description.strip()
    if s.upper().startswith("SQ *"):
        s = s[4:].strip()
    m = _NUMERIC_RUN.search(s)
    if m:
        s = s[:m.start()].strip()
    return re.sub(r"\s+", " ", s).strip()


def match_key(merchant: str) -> str:
    tokens = re.sub(r"\s+", " ", merchant.strip()).upper().split(" ")
    return " ".join(tokens[:3])
