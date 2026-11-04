"""Prevent regressions to JavaScript-readable bearer credentials in the ERP UI.

Frontend authentication must use same-origin HttpOnly cookies, CSRF and the
central API client. Legacy token removal is allowed; reading or storing JWTs
in local/session storage is not.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "apps" / "frontend" / "src"
FORBIDDEN = [
    re.compile(r"(?:localStorage|sessionStorage)\.(?:setItem|getItem)\s*\(\s*['\"](?:access_token|refresh_token)['\"]"),
    re.compile(r"Authorization\s*:\s*['\`\"]Bearer\b", re.IGNORECASE),
    re.compile(r"headers\.set\s*\(\s*['\"]Authorization['\"]\s*,", re.IGNORECASE),
]
exceptions = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path.suffix not in (".ts", ".tsx", ".js", ".jsx"):
        continue
    source = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(source.splitlines(), 1):
        for pattern in FORBIDDEN:
            if pattern.search(line):
                exceptions.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()[:160]}")

if exceptions:
    raise SystemExit("JavaScript-readable auth credentials forbidden:\n" + "\n".join(exceptions))
print("PASS: no local/sessionStorage JWT storage or frontend Bearer header issuance")
