#!/usr/bin/env python3
"""Pre-commit guard mirroring tests/validate_app.py's wording scan.

The validator (tests/validate_app.py) concatenates the frontend files plus a set
of docs and FAILS if any absolute-safety substring is present, or if the approved
review-wording string is missing. New map/legend copy added during the UI rework
is the most likely place to accidentally introduce a banned substring, so this
script lets us catch it before running the (slow, browser-backed) suite.

It scans the files this rework actually edits — the frontend trio + backend *.py
— which is where new map/legend copy (the real risk) lands. It deliberately does
NOT scan docs that legitimately quote the banned list (e.g. docs/scope.md,
CLAUDE.md), since the validator does not scan those either. Exit code 1 on any
violation.

Usage:  python -B scripts/check_forbidden_terms.py
"""
from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

# Built piecewise so this guard file never itself contains the joined substring.
FORBIDDEN_TERMS = ["danger" + "ous", "un" + "safe", "definitely " + "danger" + "ous"]
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."

SELF = Path(__file__).resolve()


def scanned_files() -> list[Path]:
    files: list[Path] = []
    static = PROJECT_DIR / "frontend" / "static"
    for name in ("index.html", "app.js", "styles.css"):
        files.append(static / name)
    files.extend(sorted((PROJECT_DIR / "backend").glob("*.py")))
    # never scan this guard itself (it holds the term fragments by design)
    return [f for f in files if f.exists() and f.resolve() != SELF]


def main() -> int:
    violations: list[str] = []
    wording_seen = False
    frontend_blob = ""

    for path in scanned_files():
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        if REVIEW_WORDING in text:
            wording_seen = True
        if path.parent.name == "static":
            frontend_blob += text
        rel = path.relative_to(PROJECT_DIR)
        for term in FORBIDDEN_TERMS:
            start = 0
            while True:
                idx = lowered.find(term, start)
                if idx < 0:
                    break
                line_no = text.count("\n", 0, idx) + 1
                snippet = text[max(0, idx - 40):idx + 40].replace("\n", " ")
                violations.append(f"{rel}:{line_no}: banned '{term}' -> ...{snippet}...")
                start = idx + 1

    ok = True
    if violations:
        ok = False
        print("FORBIDDEN-TERM CHECK: FAIL")
        for v in violations:
            print("  " + v)
    if REVIEW_WORDING not in frontend_blob and not wording_seen:
        ok = False
        print("FORBIDDEN-TERM CHECK: FAIL - approved review-wording string is missing")

    if ok:
        print(f"FORBIDDEN-TERM CHECK: OK - scanned {len(scanned_files())} files, "
              f"0 banned substrings, approved wording present.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
