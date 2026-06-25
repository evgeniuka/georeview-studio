from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
FRONTEND_STATIC_DIR = PROJECT_DIR / "frontend" / "static"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
FORBIDDEN_TERMS = ["danger" + "ous", "un" + "safe", "definitely " + "danger" + "ous"]

# Core product + analysis modules that must exist (the tight, post-subtraction surface).
REQUIRED_MODULES = [
    "app.py", "generic_safe_access_mapper.py", "route_network_analyzer.py",
    "transit_access_analyzer.py", "park_playground_access_analyzer.py",
    "scoring_rules.py", "osm_tag_quality.py", "analysis_profiles.py", "analysis_runs.py",
    "analysis_workflow.py", "profile_dashboard.py", "pilot_area_catalog.py",
    "workspace_runner.py", "run_job_manager.py", "preflight.py", "local_intake.py",
    "source_onboarding.py", "review_decisions.py", "portfolio_report_builder.py",
]
REQUIRED_FILES = [
    PROJECT_DIR / "README.md",
    PROJECT_DIR / "project_manifest.json",
    PROJECT_DIR / "config" / "scoring_rules_v001.json",
    FRONTEND_STATIC_DIR / "index.html",
    FRONTEND_STATIC_DIR / "app.js",
    FRONTEND_STATIC_DIR / "styles.css",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def get(base_url: str, path: str, timeout: int = 120) -> tuple[int, object]:
    try:
        with urlopen(Request(base_url + path, method="GET"), timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            ctype = resp.headers.get("Content-Type", "")
            return resp.status, (json.loads(body) if "json" in ctype else body)
    except HTTPError as exc:
        return exc.code, None


def main() -> None:
    # 1. Required files / the tight module surface.
    for mod in REQUIRED_MODULES:
        if not (BACKEND_DIR / mod).exists():
            fail(f"required module missing: {mod}")
    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"required file missing: {path}")

    # 2. Forbidden-term guard (delegates to the canonical scanner).
    scan = subprocess.run(
        [sys.executable, "-B", str(PROJECT_DIR / "scripts" / "check_forbidden_terms.py")],
        capture_output=True, text=True,
    )
    if scan.returncode != 0:
        fail(f"forbidden-term scan failed:\n{scan.stdout}\n{scan.stderr}")

    # 3. Boot the app (full mode) and check the product + analysis surface.
    sys.path.insert(0, str(BACKEND_DIR))
    import app  # noqa: PLC0415

    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    ws = app.WORKSPACE_ID
    summary: dict[str, object] = {}
    try:
        status, body = get(base_url, "/")
        if status != 200 or "GeoReview" not in body or "mapCanvas" not in body:
            fail("index.html did not render the expected app shell")

        checks = [
            ("/api/health", lambda p: p.get("ok") and p.get("app_version") == "v083"),
            ("/api/project-manifest", lambda p: bool(p.get("version"))),
            ("/api/scoring-rules", lambda p: p.get("profile_count", 0) >= 1),
            ("/api/osm-tag-quality", lambda p: isinstance(p, dict)),
            ("/api/pilot-areas", lambda p: isinstance(p, list) and len(p) >= 1),
            ("/api/profile-dashboard", lambda p: p.get("implemented_profile_count", 0) >= 3),
            (f"/api/workspaces/{ws}/summary", lambda p: bool(p.get("counts"))),
            (f"/api/workspaces/{ws}/candidates", lambda p: isinstance(p, list) and len(p) >= 1),
            (f"/api/workspaces/{ws}/map-features", lambda p: isinstance(p, dict)),
        ]
        for path, ok in checks:
            status, payload = get(base_url, path)
            if status != 200 or not ok(payload):
                fail(f"endpoint contract failed: {path} (status {status})")

        candidate_count = len(get(base_url, f"/api/workspaces/{ws}/candidates")[1])
        if candidate_count < 1:
            fail("no review candidates produced")

        # 4. Product-mode gate hides tooling, serves the product (function-level check).
        if app.served_in_product_mode("/api/release-readiness"):
            fail("product gate should hide archived tooling endpoints")
        for product_path in ("/api/health", "/api/scoring-rules", "/api/pilot-areas"):
            if not app.served_in_product_mode(product_path):
                fail(f"product gate should serve {product_path}")

        # 5. Review-worklist export (CSV + GeoJSON), the field-handoff artifact.
        workspaces = get(base_url, "/api/dashboard-workspaces")[1]
        if not (isinstance(workspaces, list) and workspaces):
            fail("no dashboard workspaces to export")
        export_ws = ""
        for entry in workspaces:
            wid = entry.get("workspace_id", "")
            rows = get(base_url, f"/api/dashboard-workspaces/{wid}/candidates?limit=1")[1]
            if isinstance(rows, list) and rows:
                export_ws = wid
                break
        if not export_ws:
            fail("no dashboard workspace with review candidates to export")
        csv_status, csv_body = get(base_url, f"/api/dashboard-workspaces/{export_ws}/candidates-export?format=csv&limit=5")
        if csv_status != 200 or "rank,generator_id" not in csv_body or "reviewed on-site" not in csv_body:
            fail("CSV worklist export failed")
        gj_status, gj_body = get(base_url, f"/api/dashboard-workspaces/{export_ws}/candidates-export?format=geojson&limit=5")
        gj = json.loads(gj_body) if isinstance(gj_body, str) else gj_body
        if gj_status != 200 or gj.get("type") != "FeatureCollection" or not gj.get("note", "").startswith("This location"):
            fail("GeoJSON worklist export failed")

        summary = {
            "passed": True,
            "app_version": "v083",
            "required_modules": len(REQUIRED_MODULES),
            "backend_module_count": len(list(BACKEND_DIR.glob("*.py"))),
            "candidate_count": candidate_count,
            "forbidden_terms_clean": True,
        }
        (PROJECT_DIR / "validation_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("VALIDATION: passed")
    finally:
        server.shutdown()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
