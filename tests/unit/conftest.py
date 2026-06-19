"""Make the stdlib-only backend and scripts importable for unit tests.

These unit tests are deliberately dependency-free and need no analysis_output
data store, so they run in CI (unlike the two integration suites in tests/).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("backend", "scripts"):
    path = str(ROOT / sub)
    if path not in sys.path:
        sys.path.insert(0, path)
