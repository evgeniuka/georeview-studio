from __future__ import annotations

import io
import json
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"


def infer_maps_root(project_dir: Path) -> Path:
    for parent in project_dir.parents:
        if parent.name == "analysis_output":
            return parent.parent
    return project_dir.parent


MAPS_ROOT = infer_maps_root(PROJECT_DIR)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def request_json(base_url: str, path: str, method: str = "GET", body: str | None = None, timeout: int = 120) -> tuple[int, object]:
    data = body.encode("utf-8") if body is not None else None
    request = Request(
        base_url + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload)
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return exc.code, json.loads(payload)


def request_bytes(base_url: str, path: str, timeout: int = 120) -> tuple[int, bytes, str]:
    request = Request(base_url + path, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), response.headers.get("Content-Type", "")
    except HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("Content-Type", "")


def main() -> None:
    sys.path.insert(0, str(BACKEND_DIR))
    import app  # noqa: PLC0415

    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, payload = request_json(base_url, "/api/health")
        if status != 200 or payload.get("app_version") != "v083":
            fail("health endpoint contract failed")

        status, payload = request_json(base_url, "/api/project-manifest")
        if status != 200 or payload.get("version") != "v083_2026-06-01":
            fail("project manifest endpoint contract failed")

        status, payload = request_json(base_url, "/api/product-architecture")
        if status != 200 or payload.get("recommended_variant_id") != "universal_gis_review_studio":
            fail("product architecture endpoint contract failed")
        if payload.get("current_evidence", {}).get("implemented_profile_count", 0) < 3:
            fail("product architecture should expose implemented profile count")
        product_architecture_version = payload.get("product_architecture_version")

        status, payload = request_json(base_url, "/api/product-architecture/variants")
        if status != 200 or len(payload.get("variants", [])) != 3:
            fail("product architecture variants endpoint contract failed")

        status, payload = request_json(base_url, "/api/product-architecture/roadmap")
        if status != 200 or not any(item.get("release") == "v083" and item.get("status") == "current" for item in payload.get("roadmap", [])):
            fail("product architecture roadmap endpoint contract failed")

        status, payload = request_json(base_url, "/api/product-architecture/implementation-plan", method="POST", body=json.dumps({"target_version": "v083"}))
        if status != 200 or payload.get("target_version") != "v083" or payload.get("focus") != "figma_aligned_dashboard_polish" or len(payload.get("milestones", [])) < 4:
            fail("product architecture implementation plan endpoint contract failed")

        status, payload = request_json(base_url, "/api/release-readiness")
        if status != 200 or payload.get("release_readiness_version") != "release_readiness_dashboard_v001" or payload.get("summary", {}).get("failed_gate_count", 0) != 0:
            fail("release readiness overview endpoint contract failed")
        release_readiness_gate_count = payload.get("summary", {}).get("gate_count", 0)

        status, payload = request_json(base_url, "/api/release-readiness/gates")
        if status != 200 or payload.get("gate_count") != release_readiness_gate_count or payload.get("failed_gate_count") != 0:
            fail("release readiness gates endpoint contract failed")

        status, payload = request_json(base_url, "/api/release-readiness/snapshot", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract readiness snapshot."}))
        if status != 200 or not payload.get("ok") or not payload.get("snapshot", {}).get("snapshot_id") or payload.get("snapshot", {}).get("mutates_config") is not False:
            fail("release readiness snapshot endpoint contract failed")
        release_readiness_snapshot_id = payload.get("snapshot", {}).get("snapshot_id")

        status, payload = request_json(base_url, "/api/release-readiness/snapshots?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("snapshot_id") == release_readiness_snapshot_id for row in payload):
            fail("release readiness snapshots list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/release-readiness/snapshots/{release_readiness_snapshot_id}")
        if status != 200 or payload.get("snapshot_id") != release_readiness_snapshot_id:
            fail("release readiness snapshot detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-demo")
        if status != 200 or payload.get("portfolio_demo_version") != "portfolio_demo_walkthrough_v001" or payload.get("step_count", 0) < 7:
            fail("portfolio demo overview endpoint contract failed")
        portfolio_demo_step_count = payload.get("step_count", 0)

        status, payload = request_json(base_url, "/api/portfolio-demo/steps")
        if status != 200 or payload.get("step_count") != portfolio_demo_step_count:
            fail("portfolio demo steps endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-demo/snapshot", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract demo snapshot."}))
        if status != 200 or not payload.get("ok") or not payload.get("snapshot", {}).get("snapshot_id") or payload.get("snapshot", {}).get("mutates_config") is not False:
            fail("portfolio demo snapshot endpoint contract failed")
        portfolio_demo_snapshot_id = payload.get("snapshot", {}).get("snapshot_id")

        status, payload = request_json(base_url, "/api/portfolio-demo/snapshots?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("snapshot_id") == portfolio_demo_snapshot_id for row in payload):
            fail("portfolio demo snapshots list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/portfolio-demo/snapshots/{portfolio_demo_snapshot_id}")
        if status != 200 or payload.get("snapshot_id") != portfolio_demo_snapshot_id:
            fail("portfolio demo snapshot detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-evidence-bundle")
        if status != 200 or payload.get("portfolio_evidence_bundle_version") != "portfolio_evidence_bundle_v001":
            fail("portfolio evidence bundle status endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-evidence-bundle/create", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract evidence bundle.", "reuse_latest": True}))
        if status != 200 or not payload.get("ok") or not payload.get("bundle", {}).get("bundle_id") or payload.get("bundle", {}).get("copied_file_count", 0) < 8:
            fail("portfolio evidence bundle create endpoint contract failed")
        portfolio_evidence_bundle_id = payload.get("bundle", {}).get("bundle_id")

        status, payload = request_json(base_url, "/api/portfolio-evidence-bundle/bundles?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("bundle_id") == portfolio_evidence_bundle_id for row in payload):
            fail("portfolio evidence bundle list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/portfolio-evidence-bundle/bundles/{portfolio_evidence_bundle_id}")
        if status != 200 or payload.get("bundle_id") != portfolio_evidence_bundle_id:
            fail("portfolio evidence bundle detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-evidence-bundle/bundles/{portfolio_evidence_bundle_id}/download")
        if status != 200 or len(content) < 500 or "markdown" not in content_type.lower():
            fail("portfolio evidence bundle download endpoint contract failed")

        status, payload = request_json(base_url, "/api/bundle-review-checklist")
        if status != 200 or payload.get("bundle_review_checklist_version") != "bundle_review_checklist_v001":
            fail("bundle review checklist status endpoint contract failed")

        status, payload = request_json(base_url, "/api/bundle-review-checklist/create", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract bundle review checklist.", "create_bundle": True, "reuse_latest": True}))
        if status != 200 or not payload.get("ok") or not payload.get("checklist", {}).get("checklist_id") or payload.get("checklist", {}).get("summary", {}).get("failed_count", 1) != 0:
            fail("bundle review checklist create endpoint contract failed")
        bundle_review_checklist_id = payload.get("checklist", {}).get("checklist_id")

        status, payload = request_json(base_url, "/api/bundle-review-checklist/checklists?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("checklist_id") == bundle_review_checklist_id for row in payload):
            fail("bundle review checklist list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/bundle-review-checklist/checklists/{bundle_review_checklist_id}")
        if status != 200 or payload.get("checklist_id") != bundle_review_checklist_id:
            fail("bundle review checklist detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/bundle-review-checklist/checklists/{bundle_review_checklist_id}/download")
        if status != 200 or len(content) < 500 or "markdown" not in content_type.lower():
            fail("bundle review checklist download endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-narrative-export")
        if status != 200 or payload.get("portfolio_narrative_export_version") != "portfolio_narrative_export_v001":
            fail("portfolio narrative export status endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-narrative-export/create", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract portfolio narrative.", "create_checklist": True, "create_bundle": True, "reuse_latest": True}))
        if status != 200 or not payload.get("ok") or not payload.get("narrative", {}).get("narrative_id") or len(payload.get("narrative", {}).get("sections", [])) < 7:
            fail("portfolio narrative export create endpoint contract failed")
        portfolio_narrative_id = payload.get("narrative", {}).get("narrative_id")

        status, payload = request_json(base_url, "/api/portfolio-narrative-export/narratives?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("narrative_id") == portfolio_narrative_id for row in payload):
            fail("portfolio narrative export list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/portfolio-narrative-export/narratives/{portfolio_narrative_id}")
        if status != 200 or payload.get("narrative_id") != portfolio_narrative_id:
            fail("portfolio narrative export detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-narrative-export/narratives/{portfolio_narrative_id}/download")
        if status != 200 or len(content) < 500 or "markdown" not in content_type.lower():
            fail("portfolio narrative export download endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-handoff-page")
        if status != 200 or payload.get("portfolio_handoff_page_version") != "portfolio_handoff_page_v001":
            fail("portfolio handoff page status endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-handoff-page/create", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract portfolio handoff page.", "create_narrative": True, "create_checklist": True, "create_bundle": True, "reuse_latest": True}))
        if status != 200 or not payload.get("ok") or not payload.get("page", {}).get("page_id"):
            fail("portfolio handoff page create endpoint contract failed")
        portfolio_handoff_page_id = payload.get("page", {}).get("page_id")

        status, payload = request_json(base_url, "/api/portfolio-handoff-page/pages?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("page_id") == portfolio_handoff_page_id for row in payload):
            fail("portfolio handoff page list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/portfolio-handoff-page/pages/{portfolio_handoff_page_id}")
        if status != 200 or payload.get("page_id") != portfolio_handoff_page_id:
            fail("portfolio handoff page detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-handoff-page/pages/{portfolio_handoff_page_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"GeoReview Studio" not in content:
            fail("portfolio handoff page download endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-evidence-gallery")
        if status != 200 or payload.get("portfolio_evidence_gallery_version") != "portfolio_evidence_gallery_v001":
            fail("portfolio evidence gallery status endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-evidence-gallery/create", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract portfolio evidence gallery.", "create_handoff_page": True, "create_narrative": True, "create_checklist": True, "create_bundle": True, "reuse_latest": True}))
        if status != 200 or not payload.get("ok") or not payload.get("gallery", {}).get("gallery_id"):
            fail("portfolio evidence gallery create endpoint contract failed")
        portfolio_evidence_gallery_id = payload.get("gallery", {}).get("gallery_id")

        status, payload = request_json(base_url, "/api/portfolio-evidence-gallery/galleries?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("gallery_id") == portfolio_evidence_gallery_id for row in payload):
            fail("portfolio evidence gallery list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/portfolio-evidence-gallery/galleries/{portfolio_evidence_gallery_id}")
        if status != 200 or payload.get("gallery_id") != portfolio_evidence_gallery_id:
            fail("portfolio evidence gallery detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-evidence-gallery/galleries/{portfolio_evidence_gallery_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Evidence Gallery" not in content:
            fail("portfolio evidence gallery download endpoint contract failed")

        status, payload = request_json(base_url, "/api/multi-pilot-comparison")
        if status != 200 or payload.get("multi_pilot_comparison_version") != "multi_pilot_comparison_v001" or payload.get("ready_pilot_count", 0) < 2:
            fail("multi-pilot comparison status endpoint contract failed")

        status, payload = request_json(base_url, "/api/multi-pilot-comparison/create", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract multi-pilot comparison."}))
        if status != 200 or not payload.get("ok") or not payload.get("comparison", {}).get("comparison_id") or payload.get("comparison", {}).get("comparison_readiness") != "ready_for_multi_pilot_review":
            fail("multi-pilot comparison create endpoint contract failed")
        multi_pilot_comparison_id = payload.get("comparison", {}).get("comparison_id")

        status, payload = request_json(base_url, "/api/multi-pilot-comparison/comparisons?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("comparison_id") == multi_pilot_comparison_id for row in payload):
            fail("multi-pilot comparison list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/multi-pilot-comparison/comparisons/{multi_pilot_comparison_id}")
        if status != 200 or payload.get("comparison_id") != multi_pilot_comparison_id or len(payload.get("comparison_matrix", [])) < 8:
            fail("multi-pilot comparison detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/multi-pilot-comparison/comparisons/{multi_pilot_comparison_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Multi-Pilot Comparison" not in content:
            fail("multi-pilot comparison download endpoint contract failed")

        status, payload = request_json(base_url, "/api/comparison-map-exports")
        if status != 200 or payload.get("comparison_map_exports_version") != "comparison_map_exports_v001" or payload.get("ready_pilot_count", 0) < 2:
            fail("comparison map exports status endpoint contract failed")

        status, payload = request_json(base_url, "/api/comparison-map-exports/create", method="POST", body=json.dumps({"created_by": "api_contract", "notes": "API contract comparison map export.", "top_limit": 20}))
        if status != 200 or not payload.get("ok") or not payload.get("export", {}).get("export_id") or payload.get("export", {}).get("export_readiness") != "ready_for_portfolio_map_review":
            fail("comparison map exports create endpoint contract failed")
        comparison_map_export_id = payload.get("export", {}).get("export_id")

        status, payload = request_json(base_url, "/api/comparison-map-exports/exports?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("export_id") == comparison_map_export_id for row in payload):
            fail("comparison map exports list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/comparison-map-exports/exports/{comparison_map_export_id}")
        if status != 200 or payload.get("export_id") != comparison_map_export_id or len(payload.get("pilot_maps", [])) < 2:
            fail("comparison map exports detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/comparison-map-exports/exports/{comparison_map_export_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Comparison Map Export" not in content:
            fail("comparison map exports download endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-dashboard")
        if status != 200 or payload.get("implemented_profile_count", 0) < 3:
            fail("profile dashboard overview endpoint contract failed")
        profile_dashboard_contract_version = payload.get("contract_version")

        status, payload = request_json(base_url, "/api/profile-dashboard/profiles")
        if status != 200 or len(payload.get("profiles", [])) < 3:
            fail("profile dashboard profiles endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-dashboard/transit_stop_walk_access/summary")
        if status != 200 or payload.get("result_count") != 180:
            fail("profile dashboard transit summary endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-dashboard/park_playground_access/results?limit=3")
        if status != 200 or payload.get("row_count") != 3 or payload.get("rows", [{}])[0].get("profile_id") != "park_playground_access":
            fail("profile dashboard park results endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-dashboard/missing_profile/results")
        if status != 404 or payload.get("error") != "profile_dashboard_profile_not_found":
            fail("missing profile dashboard should return 404")

        status, payload = request_json(base_url, "/api/scoring-rules")
        if status != 200 or payload.get("scoring_rules_version") != "scoring_rules_v001" or payload.get("profile_count") != 3:
            fail("scoring rules overview endpoint contract failed")

        status, payload = request_json(base_url, "/api/scoring-rules/safe_access_pedestrian_review")
        # 9 point-bearing scoring rules in v001 after no_reachable_crossing_on_network_proxy
        # was reclassified to a zero-point context flag; the audit below reconciles config<->actual.
        if status != 200 or len(payload.get("scoring_rules", [])) < 9:
            fail("scoring rules profile endpoint contract failed")

        status, payload = request_json(base_url, "/api/scoring-rules/safe_access_pedestrian_review/audit?limit=3")
        if status != 200 or payload.get("rows_audited") != 391 or payload.get("mismatch_count") != 0 or payload.get("row_count") != 3:
            fail("scoring rules GET audit endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/scoring-rules/transit_stop_walk_access/audit",
            method="POST",
            body=json.dumps({"limit": 2}),
        )
        if status != 200 or payload.get("rows_audited") != 180 or payload.get("mismatch_count") != 0 or payload.get("row_count") != 2:
            fail("scoring rules POST audit endpoint contract failed")

        status, payload = request_json(base_url, "/api/scoring-rules/missing_profile")
        if status != 404 or payload.get("error") != "scoring_profile_not_found":
            fail("missing scoring profile should return 404")

        status, payload = request_json(base_url, "/api/postgis-backend")
        if status != 200 or payload.get("connection_status") != "not_configured":
            fail("PostGIS backend status endpoint contract failed")

        status, payload = request_json(base_url, "/api/postgis-backend/schema")
        if status != 200 or payload.get("table_count", 0) < 10 or "profile_results" not in payload.get("tables", []):
            fail("PostGIS backend schema endpoint contract failed")

        status, payload = request_json(base_url, "/api/postgis-backend/migration-plan?scope=kfar_saba_pilot")
        if status != 200 or len(payload.get("phases", [])) < 5 or payload.get("readiness", {}).get("profile_result_rows", 0) < 716:
            fail("PostGIS backend GET migration plan endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/postgis-backend/migration-plan",
            method="POST",
            body=json.dumps({"scope": "kfar_saba_pilot"}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("plan_id"):
            fail("PostGIS backend POST migration plan endpoint contract failed")
        postgis_plan_id = payload.get("plan_id")

        status, payload = request_json(base_url, "/api/postgis-backend/plans?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("plan_id") == postgis_plan_id for row in payload):
            fail("PostGIS backend plan list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/postgis-backend/{postgis_plan_id}")
        if status != 200 or payload.get("plan_id") != postgis_plan_id:
            fail("PostGIS backend plan detail endpoint contract failed")


        status, payload = request_json(base_url, "/api/profile-mapper")
        if status != 200 or payload.get("contract_count") != 6 or payload.get("validation", {}).get("invalid_contract_count") != 0:
            fail("profile mapper overview endpoint contract failed")
        profile_mapper_contracts_version = payload.get("profile_mapper_contracts_version")

        status, payload = request_json(base_url, "/api/profile-mapper/contracts")
        if status != 200 or len(payload.get("contracts", [])) != 6:
            fail("profile mapper contracts endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-mapper/contracts/safe_access_pedestrian_review")
        if status != 200 or payload.get("contract", {}).get("status") != "implemented":
            fail("profile mapper contract detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-mapper/contracts/missing_profile")
        if status != 404 or payload.get("error") != "profile_mapper_contract_not_found":
            fail("missing profile mapper contract should return 404")

        status, payload = request_json(base_url, "/api/profile-mapper/compatibility?dataset_id=israel-and-palestine-260521-free-shp-zip")
        if status != 200 or payload.get("contract_count") != 6 or payload.get("compatible_contract_count", 0) < 5:
            fail("profile mapper compatibility endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-mapper/plan?profile_id=safe_access_pedestrian_review")
        if status != 200 or not payload.get("ok") or len(payload.get("phases", [])) < 5:
            fail("profile mapper GET plan endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-mapper/plan",
            method="POST",
            body=json.dumps({"profile_id": "safe_access_pedestrian_review", "dataset_id": "israel-and-palestine-260521-free-shp-zip"}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("plan_id"):
            fail("profile mapper POST plan endpoint contract failed")
        profile_mapper_plan_id = payload.get("plan_id")

        status, payload = request_json(base_url, "/api/profile-mapper/plans?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("plan_id") == profile_mapper_plan_id for row in payload):
            fail("profile mapper plan list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-mapper/plans/{profile_mapper_plan_id}")
        if status != 200 or payload.get("plan_id") != profile_mapper_plan_id:
            fail("profile mapper plan detail endpoint contract failed")


        status, payload = request_json(base_url, "/api/contract-execution")
        if status != 200 or payload.get("adapter_count") != 6 or payload.get("executable_now_count") != 4:
            fail("contract execution status endpoint contract failed")

        status, payload = request_json(base_url, "/api/template-authoring")
        if status != 200 or payload.get("blueprint_count", 0) < 4:
            fail("template authoring status endpoint contract failed")

        status, payload = request_json(base_url, "/api/template-authoring/options")
        if status != 200 or len(payload.get("blueprints", [])) < 4:
            fail("template authoring options endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/template-authoring/draft",
            method="POST",
            body=json.dumps({"template_id": "cycling_micromobility_access", "dataset_id": "israel-and-palestine-260521-free-shp-zip"}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("draft_id"):
            fail("template authoring draft endpoint contract failed")
        template_authoring_draft_id = payload.get("draft_id")

        status, payload = request_json(base_url, "/api/template-authoring/drafts?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("draft_id") == template_authoring_draft_id for row in payload):
            fail("template authoring drafts list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/template-authoring/drafts/{template_authoring_draft_id}")
        if status != 200 or payload.get("draft_id") != template_authoring_draft_id:
            fail("template authoring draft detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/authored-profile-runner")
        if status != 200 or payload.get("authored_profile_runner_version") != "authored_profile_runner_v001":
            fail("authored profile runner status endpoint contract failed")

        authored_workspace_id = "authored_profile_api_contract_cycling_v001"
        status, payload = request_json(
            base_url,
            "/api/authored-profile-runner/run",
            method="POST",
            body=json.dumps({"draft_id": template_authoring_draft_id, "workspace_id": authored_workspace_id}),
        )
        if status != 200 or not payload.get("ok") or payload.get("workspace", {}).get("manifest", {}).get("workspace_id") != authored_workspace_id:
            fail("authored profile runner run endpoint contract failed")

        status, payload = request_json(base_url, "/api/authored-profile-runner/workspaces")
        if status != 200 or not isinstance(payload, list) or not any(row.get("workspace_id") == authored_workspace_id for row in payload):
            fail("authored profile runner workspace list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-workspaces/{authored_workspace_id}/summary")
        if status != 200 or payload.get("counts", {}).get("result_rows", 0) < 5:
            fail("authored profile workspace summary endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-workspaces/{authored_workspace_id}/results?limit=3")
        if status != 200 or not isinstance(payload, list) or len(payload) != 3:
            fail("authored profile workspace results endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/profile-workspaces/{authored_workspace_id}/download/authored_profile_results")
        if status != 200 or len(content) < 500 or "csv" not in content_type.lower():
            fail("authored profile workspace download endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-promotion")
        if status != 200 or payload.get("profile_promotion_version") != "profile_promotion_wizard_v001" or payload.get("profile_contract_diff_review_version") != "profile_contract_diff_review_v001" or payload.get("profile_config_apply_proposal_version") != "profile_config_apply_proposal_v001" or payload.get("profile_contract_regression_preview_version") != "profile_contract_regression_preview_v001":
            fail("profile promotion status endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-promotion/candidates?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("workspace_id") == authored_workspace_id for row in payload):
            fail("profile promotion candidates endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-promotion/candidates/{authored_workspace_id}")
        if status != 200 or payload.get("recommendation") != "ready_for_promotion_proposal":
            fail("profile promotion candidate detail endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-promotion/propose",
            method="POST",
            body=json.dumps({"workspace_id": authored_workspace_id}),
        )
        if status != 200 or not payload.get("ok") or payload.get("proposal", {}).get("status") != "ready_for_manual_review":
            fail("profile promotion propose endpoint contract failed")
        profile_promotion_proposal_id = payload.get("proposal", {}).get("proposal_id")

        status, payload = request_json(base_url, "/api/profile-promotion/proposals?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("proposal_id") == profile_promotion_proposal_id for row in payload):
            fail("profile promotion proposals list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-promotion/proposals/{profile_promotion_proposal_id}")
        if status != 200 or payload.get("proposal_id") != profile_promotion_proposal_id or payload.get("mapper_contract_patch_preview", {}).get("mutates_config") is not False:
            fail("profile promotion proposal detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-promotion/diff-candidates?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("proposal_id") == profile_promotion_proposal_id for row in payload):
            fail("profile contract diff candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-promotion/contract-diff",
            method="POST",
            body=json.dumps({"proposal_id": profile_promotion_proposal_id}),
        )
        if status != 200 or payload.get("contract_diff", {}).get("diff_status") != "ready_for_manual_review" or payload.get("contract_diff", {}).get("mutates_config") is not False:
            fail("profile contract diff POST endpoint contract failed")
        profile_contract_diff_id = payload.get("contract_diff", {}).get("diff_id")

        status, payload = request_json(base_url, "/api/profile-promotion/contract-diffs?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("diff_id") == profile_contract_diff_id for row in payload):
            fail("profile contract diffs list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-promotion/contract-diffs/{profile_contract_diff_id}")
        if status != 200 or payload.get("diff_id") != profile_contract_diff_id or payload.get("summary", {}).get("field_count", 0) < 1:
            fail("profile contract diff detail endpoint contract failed")
        status, payload = request_json(base_url, "/api/profile-promotion/review-queue?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("proposal_id") == profile_promotion_proposal_id and row.get("decision_status") == "pending_review" for row in payload):
            fail("profile promotion review queue endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-promotion/proposals/{profile_promotion_proposal_id}/decision")
        if status != 404 or payload.get("error") != "profile_acceptance_decision_not_found":
            fail("profile promotion missing decision endpoint contract failed")

        status, payload = request_json(
            base_url,
            f"/api/profile-promotion/proposals/{profile_promotion_proposal_id}/decision",
            method="POST",
            body=json.dumps({"decision": "approve", "reviewer": "api_contract_reviewer", "notes": "Approved for later guarded implementation planning."}),
        )
        if status != 200 or payload.get("decision", {}).get("decision_status") != "approved" or payload.get("decision", {}).get("mutates_config") is not False:
            fail("profile promotion decision POST endpoint contract failed")
        profile_acceptance_decision_id = payload.get("decision", {}).get("decision_id")

        status, payload = request_json(base_url, "/api/profile-promotion/decisions?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("decision_id") == profile_acceptance_decision_id for row in payload):
            fail("profile promotion decisions list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-promotion/proposals/{profile_promotion_proposal_id}/decision")
        if status != 200 or payload.get("decision_id") != profile_acceptance_decision_id or payload.get("decision_status") != "approved":
            fail("profile promotion latest decision endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-promotion/application-candidates?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("proposal_id") == profile_promotion_proposal_id and row.get("decision_status") == "approved" for row in payload):
            fail("profile application candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-promotion/application-plan",
            method="POST",
            body=json.dumps({"proposal_id": profile_promotion_proposal_id, "decision_id": profile_acceptance_decision_id}),
        )
        if status != 200 or payload.get("application_plan", {}).get("plan_status") != "ready_for_manual_implementation" or payload.get("application_plan", {}).get("mutates_config") is not False:
            fail("profile application plan POST endpoint contract failed")
        profile_application_plan_id = payload.get("application_plan", {}).get("plan_id")

        status, payload = request_json(base_url, "/api/profile-promotion/application-plans?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("plan_id") == profile_application_plan_id for row in payload):
            fail("profile application plans list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-promotion/application-plans/{profile_application_plan_id}")
        if status != 200 or payload.get("plan_id") != profile_application_plan_id or payload.get("config_patch_preview", {}).get("mutates_config") is not False:
            fail("profile application plan detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-promotion/apply-candidates?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("application_plan_id") == profile_application_plan_id for row in payload):
            fail("profile config apply candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-promotion/config-apply-proposal",
            method="POST",
            body=json.dumps({"application_plan_id": profile_application_plan_id, "proposal_id": profile_promotion_proposal_id}),
        )
        if status != 200 or payload.get("config_apply_proposal", {}).get("apply_status") != "ready_for_explicit_approval" or payload.get("config_apply_proposal", {}).get("mutates_config") is not False:
            fail("profile config apply proposal POST endpoint contract failed")
        profile_config_apply_proposal_id = payload.get("config_apply_proposal", {}).get("apply_id")

        status, payload = request_json(base_url, "/api/profile-promotion/config-apply-proposals?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("apply_id") == profile_config_apply_proposal_id for row in payload):
            fail("profile config apply proposals list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-promotion/config-apply-proposals/{profile_config_apply_proposal_id}")
        if status != 200 or payload.get("apply_id") != profile_config_apply_proposal_id or len(str(payload.get("current_config_sha256") or "")) != 64:
            fail("profile config apply proposal detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-promotion/regression-candidates?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("apply_id") == profile_config_apply_proposal_id for row in payload):
            fail("profile contract regression candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-promotion/regression-preview",
            method="POST",
            body=json.dumps({"apply_id": profile_config_apply_proposal_id, "proposal_id": profile_promotion_proposal_id}),
        )
        if status != 200 or payload.get("regression_preview", {}).get("regression_status") != "passed" or payload.get("regression_preview", {}).get("mutates_config") is not False:
            fail("profile contract regression preview POST endpoint contract failed")
        profile_contract_regression_preview_id = payload.get("regression_preview", {}).get("preview_id")

        status, payload = request_json(base_url, "/api/profile-promotion/regression-previews?limit=500")
        if status != 200 or not isinstance(payload, list) or not any(row.get("preview_id") == profile_contract_regression_preview_id for row in payload):
            fail("profile contract regression previews list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-promotion/regression-previews/{profile_contract_regression_preview_id}")
        if status != 200 or payload.get("preview_id") != profile_contract_regression_preview_id or payload.get("failed_check_count") != 0:
            fail("profile contract regression preview detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-dashboard")
        if status != 200 or payload.get("authored_profile_count", 0) < 1 or not any(profile.get("profile_id") == "cycling_micromobility_access" for profile in payload.get("profiles", [])):
            fail("profile dashboard authored overview endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-dashboard/cycling_micromobility_access/summary")
        if status != 200 or payload.get("profile_source") != "authored_profile_workspace" or payload.get("result_count", 0) < 5:
            fail("profile dashboard authored summary endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-dashboard/cycling_micromobility_access/results?limit=3")
        if status != 200 or payload.get("row_count") != 3 or payload.get("rows", [{}])[0].get("profile_id") != "cycling_micromobility_access":
            fail("profile dashboard authored results endpoint contract failed")

        status, payload = request_json(base_url, "/api/execution-queue")
        if status != 200 or payload.get("executable_profile_count", 0) < 4:
            fail("execution queue status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/execution-queue/enqueue",
            method="POST",
            body=json.dumps({"profile_id": "osm_tag_quality", "target_workspace_id": "osm_tag_quality_kfar_saba_v001", "execute_now": True}),
        )
        if status != 200 or payload.get("status") != "succeeded" or payload.get("runner_result", {}).get("workspace_id") != "osm_tag_quality_kfar_saba_v001":
            fail("execution queue enqueue endpoint contract failed")
        execution_queue_job_id = payload.get("job_id")

        status, payload = request_json(base_url, "/api/execution-queue/jobs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("job_id") == execution_queue_job_id for row in payload):
            fail("execution queue jobs list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/execution-queue/jobs/{execution_queue_job_id}")
        if status != 200 or payload.get("job_id") != execution_queue_job_id:
            fail("execution queue job detail endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/execution-queue/enqueue-authored-draft",
            method="POST",
            body=json.dumps({"draft_id": template_authoring_draft_id, "workspace_id": "authored_profile_queue_api_contract_v001", "execute_now": True}),
        )
        if status != 200 or payload.get("status") != "succeeded" or payload.get("runner_result", {}).get("workspace_id") != "authored_profile_queue_api_contract_v001":
            fail("execution queue authored draft endpoint contract failed")
        authored_queue_job_id = payload.get("job_id")

        status, payload = request_json(base_url, "/api/dataset-packages")
        if status != 200 or payload.get("source_count") != 2:
            fail("dataset packages status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/dataset-packages/create",
            method="POST",
            body=json.dumps({
                "dataset_id": "israel-and-palestine-260521-free-shp-zip",
                "template_id": "generic_osm_tag_coverage",
                "queue_profile_id": "osm_tag_quality",
                "target_workspace_id": "osm_tag_quality_kfar_saba_v001",
            }),
        )
        if status != 200 or not payload.get("ok") or payload.get("execution_queue_status") != "succeeded":
            fail("dataset package create endpoint contract failed")
        dataset_package_id = payload.get("package_id")

        status, payload = request_json(base_url, "/api/dataset-packages/packages?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("package_id") == dataset_package_id for row in payload):
            fail("dataset packages list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/dataset-packages/packages/{dataset_package_id}")
        if status != 200 or payload.get("package_id") != dataset_package_id:
            fail("dataset package detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/dataset-packages/packages/{dataset_package_id}/download")
        if status != 200 or len(content) < 500 or "markdown" not in content_type.lower():
            fail("dataset package report download endpoint contract failed")

        status, payload = request_json(base_url, "/api/contract-execution/adapters")
        if status != 200 or len(payload.get("adapters", [])) != 6:
            fail("contract execution adapters endpoint contract failed")

        status, payload = request_json(base_url, "/api/contract-execution/dry-run?profile_id=safe_access_pedestrian_review")
        if status != 200 or payload.get("can_execute_now") is not True or payload.get("dry_run_only") is not True:
            fail("contract execution GET dry-run endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/contract-execution/dry-run",
            method="POST",
            body=json.dumps({"profile_id": "safe_access_pedestrian_review", "dataset_id": "israel-and-palestine-260521-free-shp-zip"}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("dry_run_id"):
            fail("contract execution POST dry-run endpoint contract failed")
        contract_execution_dry_run_id = payload.get("dry_run_id")

        status, payload = request_json(base_url, "/api/contract-execution/dry-runs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("dry_run_id") == contract_execution_dry_run_id for row in payload):
            fail("contract execution dry-run list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/contract-execution/dry-runs/{contract_execution_dry_run_id}")
        if status != 200 or payload.get("dry_run_id") != contract_execution_dry_run_id:
            fail("contract execution dry-run detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/source-onboarding/refresh", method="POST", body="{}")
        if status != 200 or payload.get("source_count") != 2:
            fail("source onboarding refresh endpoint contract failed")

        status, payload = request_json(base_url, "/api/source-onboarding")
        if status != 200 or payload.get("source_count") != 2 or payload.get("source_gis_modified") is not False:
            fail("source onboarding status endpoint contract failed")

        status, payload = request_json(base_url, "/api/source-onboarding/sources")
        if status != 200 or not isinstance(payload, list) or len(payload) != 2:
            fail("source onboarding sources endpoint contract failed")

        status, payload = request_json(base_url, "/api/source-onboarding/sources/israel-and-palestine-260521-free-shp-zip")
        if status != 200 or payload.get("readiness", {}).get("level") != "ready_for_safe_access_selected_pilot":
            fail("source onboarding detail endpoint contract failed")

        status, payload = request_json(base_url, "/api/local-intake")
        if status != 200 or payload.get("source_count") != 2 or payload.get("source_gis_modified") is not False:
            fail("local intake status endpoint contract failed")

        status, payload = request_json(base_url, "/api/local-intake/sources")
        if status != 200 or payload.get("source_count") != 2:
            fail("local intake sources endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/local-intake/preview",
            method="POST",
            body=json.dumps({"dataset_id": "israel-and-palestine-260521-free-shp-zip"}),
        )
        if status != 200 or payload.get("source", {}).get("readiness_level") != "ready_for_safe_access_selected_pilot":
            fail("local intake dataset preview endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/local-intake/preview",
            method="POST",
            body=json.dumps({"path": str(MAPS_ROOT / "israel-and-palestine-260521-free.shp.zip")}),
        )
        if status != 200 or payload.get("input_type") != "registered_file":
            fail("local intake path preview endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/local-intake/preview",
            method="POST",
            body=json.dumps({"path": str(MAPS_ROOT / "analysis_output")}),
        )
        if status != 400 or payload.get("error") != "local_intake_analysis_output_not_allowed":
            fail("local intake analysis_output rejection contract failed")

        status, payload = request_json(
            base_url,
            "/api/local-intake/plan",
            method="POST",
            body=json.dumps({"dataset_id": "israel-and-palestine-260521-free-shp-zip"}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("plan_id"):
            fail("local intake plan endpoint contract failed")
        local_intake_plan_id = payload.get("plan_id")


        status, payload = request_json(base_url, "/api/source-import-guardrails")
        if status != 200 or payload.get("source_import_guardrails_version") != "source_import_guardrails_v001" or payload.get("guardrail_count", 0) < 8:
            fail("source import guardrails status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/source-import-guardrails/preview",
            method="POST",
            body=json.dumps({"dataset_id": "israel-and-palestine-260521-free-shp-zip", "template_id": "safe_access"}),
        )
        if status != 200 or payload.get("import_readiness") != "ready_for_manual_review" or payload.get("summary", {}).get("hard_failed_count") != 0:
            fail("source import guardrails preview endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/source-import-guardrails/request",
            method="POST",
            body=json.dumps({"dataset_id": "israel-and-palestine-260521-free-shp-zip", "template_id": "safe_access", "created_by": "api_contract"}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("request", {}).get("request_id"):
            fail("source import guardrails request endpoint contract failed")
        source_import_request_id = payload.get("request", {}).get("request_id")

        status, payload = request_json(base_url, "/api/source-import-guardrails/requests?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("request_id") == source_import_request_id for row in payload):
            fail("source import guardrails requests list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/source-import-guardrails/requests/{source_import_request_id}")
        if status != 200 or payload.get("request_id") != source_import_request_id or len(payload.get("guardrails", [])) < 8:
            fail("source import guardrails detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/source-import-guardrails/requests/{source_import_request_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Source Import Guardrails Review" not in content:
            fail("source import guardrails download endpoint contract failed")

        status, payload = request_json(
            base_url,
            f"/api/source-import-guardrails/requests/{source_import_request_id}/decision",
            method="POST",
            body=json.dumps({
                "decision": "approve",
                "reviewer": "api_contract",
                "approval_phrase": "approve metadata-only import",
                "source_files_read_only_ack": True,
                "generated_outputs_only_ack": True,
                "no_browser_upload_ack": True,
                "claim_boundary_ack": True,
            }),
        )
        if status != 200 or payload.get("decision", {}).get("decision_state") != "approved_for_metadata_only_import":
            fail("source import guardrails decision endpoint contract failed")
        source_import_decision_id = payload.get("decision", {}).get("decision_id")

        status, payload = request_json(base_url, "/api/source-handoff")
        if status != 200 or payload.get("source_handoff_version") != "source_handoff_v001":
            fail("source handoff status endpoint contract failed")

        status, payload = request_json(base_url, "/api/source-handoff/candidates?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("request_id") == source_import_request_id for row in payload):
            fail("source handoff candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/source-handoff/create",
            method="POST",
            body=json.dumps({
                "request_id": source_import_request_id,
                "profile_id": "safe_access_pedestrian_review",
                "pilot_osm_id": "53796999",
                "target_workspace_id": "safe_access_kfar_saba_pbf_enriched_v001",
                "created_by": "api_contract",
            }),
        )
        if status != 200 or payload.get("handoff", {}).get("handoff_readiness") != "ready_for_controlled_execution" or payload.get("handoff", {}).get("queue_status") != "planned":
            fail("source handoff create endpoint contract failed")
        source_handoff_id = payload.get("handoff", {}).get("handoff_id")

        status, payload = request_json(base_url, "/api/source-handoff/handoffs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("handoff_id") == source_handoff_id for row in payload):
            fail("source handoff list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/source-handoff/handoffs/{source_handoff_id}")
        if status != 200 or payload.get("handoff_id") != source_handoff_id or not payload.get("mapper_plan_id"):
            fail("source handoff detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/source-handoff/handoffs/{source_handoff_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Source Handoff" not in content:
            fail("source handoff download endpoint contract failed")

        status, payload = request_json(base_url, "/api/source-handoff-execution")
        if status != 200 or payload.get("source_handoff_execution_version") != "source_handoff_execution_v001":
            fail("source handoff execution status endpoint contract failed")

        status, payload = request_json(base_url, "/api/source-handoff-execution/candidates?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("handoff_id") == source_handoff_id for row in payload):
            fail("source handoff execution candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/source-handoff-execution/execute",
            method="POST",
            body=json.dumps({"handoff_id": source_handoff_id}),
        )
        if status != 400 or payload.get("error") != "source_handoff_execution_ack_missing":
            fail("source handoff execution acknowledgement guard endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/source-handoff-execution/execute",
            method="POST",
            body=json.dumps({
                "handoff_id": source_handoff_id,
                "execution_ack": "execute approved handoff",
                "source_files_read_only_ack": True,
                "generated_outputs_only_ack": True,
                "claim_boundary_ack": True,
                "compare_outputs_ack": True,
                "route_aware": False,
                "created_by": "api_contract",
            }),
        )
        if status != 200 or payload.get("execution", {}).get("execution_readiness") != "executed_and_verified":
            fail("source handoff execution execute endpoint contract failed")
        source_handoff_execution_id = payload.get("execution", {}).get("execution_id")

        status, payload = request_json(base_url, "/api/source-handoff-execution/executions?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("execution_id") == source_handoff_execution_id for row in payload):
            fail("source handoff execution list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/source-handoff-execution/executions/{source_handoff_execution_id}")
        if status != 200 or payload.get("execution_id") != source_handoff_execution_id or payload.get("comparison", {}).get("comparison_readiness") != "outputs_match_handoff_evidence":
            fail("source handoff execution detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/source-handoff-execution/executions/{source_handoff_execution_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Source Handoff Execution" not in content:
            fail("source handoff execution download endpoint contract failed")

        status, payload = request_json(base_url, "/api/execution-evidence-package")
        if status != 200 or payload.get("execution_evidence_package_version") != "execution_evidence_package_v001":
            fail("execution evidence package status endpoint contract failed")

        status, payload = request_json(base_url, "/api/execution-evidence-package/candidates?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("execution_id") == source_handoff_execution_id for row in payload):
            fail("execution evidence package candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/execution-evidence-package/create",
            method="POST",
            body=json.dumps({
                "execution_id": source_handoff_execution_id,
                "created_by": "api_contract",
                "notes": "API contract execution evidence package.",
            }),
        )
        if status != 200 or payload.get("package", {}).get("package_readiness") != "ready_for_reviewer":
            fail("execution evidence package create endpoint contract failed")
        execution_evidence_package_id = payload.get("package", {}).get("package_id")

        status, payload = request_json(base_url, "/api/execution-evidence-package/packages?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("package_id") == execution_evidence_package_id for row in payload):
            fail("execution evidence package list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/execution-evidence-package/packages/{execution_evidence_package_id}")
        if status != 200 or payload.get("package_id") != execution_evidence_package_id or payload.get("execution_id") != source_handoff_execution_id:
            fail("execution evidence package detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/execution-evidence-package/packages/{execution_evidence_package_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Execution Evidence Package" not in content:
            fail("execution evidence package download endpoint contract failed")

        time.sleep(1.1)
        status, payload = request_json(
            base_url,
            "/api/execution-evidence-package/create",
            method="POST",
            body=json.dumps({
                "execution_id": source_handoff_execution_id,
                "created_by": "api_contract",
                "notes": "API contract second execution evidence package for diffing.",
            }),
        )
        if status != 200 or payload.get("package", {}).get("package_readiness") != "ready_for_reviewer":
            fail("second execution evidence package create endpoint contract failed")
        second_execution_evidence_package_id = payload.get("package", {}).get("package_id")

        status, payload = request_json(base_url, "/api/execution-result-diff")
        if status != 200 or payload.get("execution_result_diff_version") != "execution_result_diff_v001":
            fail("execution result diff status endpoint contract failed")

        status, payload = request_json(base_url, "/api/execution-result-diff/candidates?limit=5")
        if status != 200 or not isinstance(payload, list) or not payload:
            fail("execution result diff candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/execution-result-diff/create",
            method="POST",
            body=json.dumps({
                "left_package_id": execution_evidence_package_id,
                "right_package_id": second_execution_evidence_package_id,
                "created_by": "api_contract",
                "notes": "API contract execution result diff.",
            }),
        )
        if status != 200 or payload.get("diff", {}).get("diff_readiness") != "ready_for_reviewer":
            fail("execution result diff create endpoint contract failed")
        execution_result_diff_id = payload.get("diff", {}).get("diff_id")

        status, payload = request_json(base_url, "/api/execution-result-diff/diffs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("diff_id") == execution_result_diff_id for row in payload):
            fail("execution result diff list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/execution-result-diff/diffs/{execution_result_diff_id}")
        if status != 200 or payload.get("diff_id") != execution_result_diff_id or payload.get("diff_readiness") != "ready_for_reviewer":
            fail("execution result diff detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/execution-result-diff/diffs/{execution_result_diff_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Execution Result Diff" not in content:
            fail("execution result diff download endpoint contract failed")

        status, payload = request_json(base_url, "/api/execution-diff-gallery")
        if status != 200 or payload.get("execution_diff_gallery_version") != "execution_diff_gallery_v001" or payload.get("indexed_diff_count", 0) < 1:
            fail("execution diff gallery status endpoint contract failed")

        status, payload = request_json(base_url, "/api/execution-diff-gallery/items?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("diff_id") == execution_result_diff_id for row in payload):
            fail("execution diff gallery items endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/execution-diff-gallery/create",
            method="POST",
            body=json.dumps({"created_by": "api_contract", "notes": "API contract v062 execution diff gallery.", "limit": 50}),
        )
        if status != 200 or payload.get("gallery", {}).get("gallery_readiness") != "ready_for_reviewer":
            fail("execution diff gallery create endpoint contract failed")
        execution_diff_gallery_id = payload.get("gallery", {}).get("gallery_id")

        status, payload = request_json(base_url, "/api/execution-diff-gallery/galleries?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("gallery_id") == execution_diff_gallery_id for row in payload):
            fail("execution diff gallery list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/execution-diff-gallery/galleries/{execution_diff_gallery_id}")
        if status != 200 or payload.get("gallery_id") != execution_diff_gallery_id or payload.get("gallery_readiness") != "ready_for_reviewer":
            fail("execution diff gallery detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/execution-diff-gallery/galleries/{execution_diff_gallery_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Execution Diff Gallery" not in content:
            fail("execution diff gallery download endpoint contract failed")

        status, payload = request_json(base_url, "/api/execution-diff-detail")
        if status != 200 or payload.get("execution_diff_detail_version") != "execution_diff_detail_v001" or payload.get("baseline_candidate_count", 0) < 1:
            fail("execution diff detail status endpoint contract failed")

        status, payload = request_json(base_url, "/api/execution-diff-detail/baselines?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("diff_id") == execution_result_diff_id for row in payload):
            fail("execution diff detail baselines endpoint contract failed")
        baseline_diff_id = payload[0].get("diff_id")

        status, payload = request_json(base_url, f"/api/execution-diff-detail/inspect?diff_id={execution_result_diff_id}&baseline_diff_id={baseline_diff_id}")
        if status != 200 or payload.get("diff_id") != execution_result_diff_id or not payload.get("drilldown", {}).get("table_breakdown"):
            fail("execution diff detail inspect endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/execution-diff-detail/create",
            method="POST",
            body=json.dumps({
                "diff_id": execution_result_diff_id,
                "baseline_diff_id": baseline_diff_id,
                "created_by": "api_contract",
                "notes": "API contract v062 execution diff detail drilldown.",
            }),
        )
        if status != 200 or payload.get("detail", {}).get("drilldown_readiness") != "ready_for_reviewer":
            fail("execution diff detail create endpoint contract failed")
        execution_diff_detail_id = payload.get("detail", {}).get("detail_id")

        status, payload = request_json(base_url, "/api/execution-diff-detail/drilldowns?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("detail_id") == execution_diff_detail_id for row in payload):
            fail("execution diff detail list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/execution-diff-detail/drilldowns/{execution_diff_detail_id}")
        if status != 200 or payload.get("detail_id") != execution_diff_detail_id or payload.get("drilldown_readiness") != "ready_for_reviewer":
            fail("execution diff detail detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/execution-diff-detail/drilldowns/{execution_diff_detail_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Execution Diff Detail Drilldown" not in content:
            fail("execution diff detail download endpoint contract failed")

        status, payload = request_json(base_url, "/api/reproducibility-audit-packet")
        if status != 200 or payload.get("reproducibility_audit_packet_version") != "reproducibility_audit_packet_v001" or payload.get("candidate_count", 0) < 1:
            fail("reproducibility audit packet status endpoint contract failed")

        status, payload = request_json(base_url, "/api/reproducibility-audit-packet/candidates?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("detail_id") == execution_diff_detail_id for row in payload):
            fail("reproducibility audit packet candidates endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/reproducibility-audit-packet/create",
            method="POST",
            body=json.dumps({
                "detail_id": execution_diff_detail_id,
                "created_by": "api_contract",
                "notes": "API contract v062 reproducibility audit packet.",
            }),
        )
        if status != 200 or payload.get("packet", {}).get("packet_readiness") != "ready_for_reviewer":
            fail("reproducibility audit packet create endpoint contract failed")
        reproducibility_audit_packet_id = payload.get("packet", {}).get("packet_id")

        status, payload = request_json(base_url, "/api/reproducibility-audit-packet/packets?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("packet_id") == reproducibility_audit_packet_id for row in payload):
            fail("reproducibility audit packet list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/reproducibility-audit-packet/packets/{reproducibility_audit_packet_id}")
        if status != 200 or payload.get("packet_id") != reproducibility_audit_packet_id or payload.get("packet_readiness") != "ready_for_reviewer":
            fail("reproducibility audit packet detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/reproducibility-audit-packet/packets/{reproducibility_audit_packet_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Reproducibility Audit Packet" not in content:
            fail("reproducibility audit packet download endpoint contract failed")

        status, payload = request_json(base_url, "/api/reviewer-audit-index")
        if status != 200 or payload.get("reviewer_audit_index_version") != "reviewer_audit_index_v001" or payload.get("ready_packet_count", 0) < 1:
            fail("reviewer audit index status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/reviewer-audit-index/create",
            method="POST",
            body=json.dumps({"created_by": "api_contract", "notes": "API contract v062 reviewer audit index.", "packet_limit": 25}),
        )
        if status != 200 or payload.get("index", {}).get("index_readiness") != "ready_for_reviewer":
            fail("reviewer audit index create endpoint contract failed")
        reviewer_audit_index_id = payload.get("index", {}).get("index_id")

        status, payload = request_json(base_url, "/api/reviewer-audit-index/indexes?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("index_id") == reviewer_audit_index_id for row in payload):
            fail("reviewer audit index list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/reviewer-audit-index/indexes/{reviewer_audit_index_id}")
        if status != 200 or payload.get("index_id") != reviewer_audit_index_id or payload.get("index_readiness") != "ready_for_reviewer":
            fail("reviewer audit index detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/reviewer-audit-index/indexes/{reviewer_audit_index_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Reviewer Audit Index" not in content:
            fail("reviewer audit index download endpoint contract failed")

        status, payload = request_json(base_url, "/api/portfolio-export-launcher")
        if status != 200 or payload.get("portfolio_export_launcher_version") != "portfolio_export_launcher_v001" or payload.get("launch_target_count", 0) < 3:
            fail("portfolio export launcher status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/portfolio-export-launcher/create",
            method="POST",
            body=json.dumps({"created_by": "api_contract", "notes": "API contract v062 portfolio export launcher.", "target_limit": 25}),
        )
        if status != 200 or payload.get("launcher", {}).get("launcher_readiness") != "ready_for_portfolio_launch":
            fail("portfolio export launcher create endpoint contract failed")
        portfolio_export_launcher_id = payload.get("launcher", {}).get("launcher_id")

        status, payload = request_json(base_url, "/api/portfolio-export-launcher/launchers?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("launcher_id") == portfolio_export_launcher_id for row in payload):
            fail("portfolio export launcher list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/portfolio-export-launcher/launchers/{portfolio_export_launcher_id}")
        if status != 200 or payload.get("launcher_id") != portfolio_export_launcher_id or payload.get("launcher_readiness") != "ready_for_portfolio_launch":
            fail("portfolio export launcher detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-export-launcher/launchers/{portfolio_export_launcher_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Portfolio Export Launcher" not in content:
            fail("portfolio export launcher download endpoint contract failed")

        status, payload = request_json(base_url, "/api/portable-release-package")
        if status != 200 or payload.get("portable_release_package_version") != "portable_release_package_v001" or payload.get("ready_launcher_count", 0) < 1:
            fail("portable release package status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/portable-release-package/create",
            method="POST",
            body=json.dumps({"created_by": "api_contract", "notes": "API contract v062 portable release package.", "target_limit": 30}),
        )
        if status != 200 or payload.get("package", {}).get("package_readiness") != "ready_to_share_portable_release":
            fail("portable release package create endpoint contract failed")
        portable_release_package_id = payload.get("package", {}).get("package_id")

        status, payload = request_json(base_url, "/api/portable-release-package/packages?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("package_id") == portable_release_package_id for row in payload):
            fail("portable release package list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/portable-release-package/packages/{portable_release_package_id}")
        if status != 200 or payload.get("package_id") != portable_release_package_id or payload.get("package_readiness") != "ready_to_share_portable_release":
            fail("portable release package detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portable-release-package/packages/{portable_release_package_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("portable release package download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if "README.md" not in names or "package_manifest.json" not in names:
                fail("portable release package ZIP contract failed")

        status, payload = request_json(base_url, "/api/demo-script-pack")
        if status != 200 or payload.get("demo_script_pack_version") != "demo_script_pack_v001" or payload.get("screenshot_target_count", 0) < 6:
            fail("demo script pack status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/demo-script-pack/create",
            method="POST",
            body=json.dumps({"created_by": "api_contract", "notes": "API contract v062 demo script pack."}),
        )
        if status != 200 or payload.get("pack", {}).get("pack_readiness") != "ready_for_demo_walkthrough":
            fail("demo script pack create endpoint contract failed")
        demo_script_pack_id = payload.get("pack", {}).get("pack_id")

        status, payload = request_json(base_url, "/api/demo-script-pack/packs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("pack_id") == demo_script_pack_id for row in payload):
            fail("demo script pack list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/demo-script-pack/packs/{demo_script_pack_id}")
        if status != 200 or payload.get("pack_id") != demo_script_pack_id or payload.get("pack_readiness") != "ready_for_demo_walkthrough":
            fail("demo script pack detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/demo-script-pack/packs/{demo_script_pack_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Demo Script Pack" not in content:
            fail("demo script pack download endpoint contract failed")

        status, payload = request_json(base_url, "/api/visual-qa-snapshot-ledger")
        if status != 200 or payload.get("visual_qa_snapshot_ledger_version") != "visual_qa_snapshot_ledger_v001" or payload.get("screenshot_target_count", 0) < 6:
            fail("visual QA ledger status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/visual-qa-snapshot-ledger/create",
            method="POST",
            body=json.dumps({"pack_id": demo_script_pack_id, "created_by": "api_contract", "notes": "API contract v063 visual QA ledger."}),
        )
        if status != 200 or payload.get("ledger", {}).get("ledger_readiness") != "ready_for_visual_qa_tracking":
            fail("visual QA ledger create endpoint contract failed")
        visual_qa_ledger_id = payload.get("ledger", {}).get("ledger_id")

        status, payload = request_json(base_url, "/api/visual-qa-snapshot-ledger/ledgers?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("ledger_id") == visual_qa_ledger_id for row in payload):
            fail("visual QA ledger list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/visual-qa-snapshot-ledger/ledgers/{visual_qa_ledger_id}")
        if status != 200 or payload.get("ledger_id") != visual_qa_ledger_id or payload.get("ledger_readiness") != "ready_for_visual_qa_tracking":
            fail("visual QA ledger detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/visual-qa-snapshot-ledger/ledgers/{visual_qa_ledger_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Visual QA Snapshot Ledger" not in content:
            fail("visual QA ledger download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/visual-qa-snapshot-ledger/create",
            method="POST",
            body=json.dumps({"pack_id": demo_script_pack_id, "created_by": "api_contract", "notes": "API contract v072 baseline visual QA ledger."}),
        )
        if status != 200 or payload.get("ledger", {}).get("ledger_readiness") != "ready_for_visual_qa_tracking":
            fail("second visual QA ledger create endpoint contract failed")
        second_visual_qa_ledger_id = payload.get("ledger", {}).get("ledger_id")

        status, payload = request_json(base_url, "/api/visual-baseline-comparison")
        if status != 200 or payload.get("visual_baseline_comparison_version") != "visual_baseline_comparison_manifest_v001" or payload.get("baseline_candidate_count", 0) < 1:
            fail("visual baseline comparison status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/visual-baseline-comparison/create",
            method="POST",
            body=json.dumps({"latest_ledger_id": second_visual_qa_ledger_id, "baseline_ledger_id": visual_qa_ledger_id, "created_by": "api_contract", "notes": "API contract v072 visual baseline comparison."}),
        )
        if status != 200 or payload.get("comparison", {}).get("comparison_readiness") != "ready_for_visual_baseline_review":
            fail("visual baseline comparison create endpoint contract failed")
        visual_baseline_comparison_id = payload.get("comparison", {}).get("comparison_id")

        status, payload = request_json(base_url, "/api/visual-baseline-comparison/comparisons?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("comparison_id") == visual_baseline_comparison_id for row in payload):
            fail("visual baseline comparison list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/visual-baseline-comparison/comparisons/{visual_baseline_comparison_id}")
        if status != 200 or payload.get("comparison_id") != visual_baseline_comparison_id or payload.get("comparison_readiness") != "ready_for_visual_baseline_review":
            fail("visual baseline comparison detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/visual-baseline-comparison/comparisons/{visual_baseline_comparison_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Visual Baseline Comparison Manifest" not in content:
            fail("visual baseline comparison download endpoint contract failed")

        status, payload = request_json(base_url, "/api/demo-artifact-completeness")
        if status != 200 or payload.get("demo_artifact_completeness_version") != "demo_artifact_completeness_validator_v001" or payload.get("missing_required_artifacts", 1) != 0:
            fail("demo artifact completeness status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/demo-artifact-completeness/create",
            method="POST",
            body=json.dumps({"created_by": "api_contract", "notes": "API contract v072 demo artifact completeness check."}),
        )
        if status != 200 or payload.get("check", {}).get("check_readiness") != "ready_for_demo_artifact_review":
            fail("demo artifact completeness create endpoint contract failed")
        demo_artifact_completeness_id = payload.get("check", {}).get("check_id")

        status, payload = request_json(base_url, "/api/demo-artifact-completeness/checks?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("check_id") == demo_artifact_completeness_id for row in payload):
            fail("demo artifact completeness list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/demo-artifact-completeness/checks/{demo_artifact_completeness_id}")
        if status != 200 or payload.get("check_id") != demo_artifact_completeness_id or payload.get("check_readiness") != "ready_for_demo_artifact_review":
            fail("demo artifact completeness detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/demo-artifact-completeness/checks/{demo_artifact_completeness_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower() or b"Demo Artifact Completeness Validator" not in content:
            fail("demo artifact completeness download endpoint contract failed")

        status, payload = request_json(base_url, "/api/visual-evidence-capture")
        if status != 200 or payload.get("visual_evidence_capture_version") != "visual_evidence_capture_v001" or payload.get("browser_available") is not True:
            fail("visual evidence capture status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/visual-evidence-capture/create",
            method="POST",
            body=json.dumps({"ledger_id": visual_qa_ledger_id, "base_url": base_url, "created_by": "api_contract", "notes": "API contract v072 visual evidence capture."}),
            timeout=240,
        )
        if status != 200 or payload.get("capture", {}).get("capture_readiness") != "ready_for_visual_evidence_review":
            fail("visual evidence capture create endpoint contract failed")
        visual_evidence_capture_id = payload.get("capture", {}).get("capture_id")

        status, payload = request_json(base_url, "/api/visual-evidence-capture/captures?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("capture_id") == visual_evidence_capture_id for row in payload):
            fail("visual evidence capture list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/visual-evidence-capture/captures/{visual_evidence_capture_id}")
        if status != 200 or payload.get("capture_id") != visual_evidence_capture_id or payload.get("captured_count", 0) < 6:
            fail("visual evidence capture detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/visual-evidence-capture/captures/{visual_evidence_capture_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Visual Evidence Capture" not in content:
            fail("visual evidence capture download endpoint contract failed")

        status, payload = request_json(base_url, "/api/visual-evidence-review-diff")
        if status != 200 or payload.get("visual_evidence_review_diff_version") != "visual_evidence_review_diff_v001":
            fail("visual evidence review diff status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/visual-evidence-review-diff/create",
            method="POST",
            body=json.dumps({"latest_capture_id": visual_evidence_capture_id, "created_by": "api_contract", "notes": "API contract v072 visual evidence review diff."}),
        )
        if status != 200 or payload.get("diff", {}).get("diff_readiness") != "ready_for_visual_evidence_diff_review":
            fail("visual evidence review diff create endpoint contract failed")
        visual_evidence_review_diff_id = payload.get("diff", {}).get("diff_id")

        status, payload = request_json(base_url, "/api/visual-evidence-review-diff/diffs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("diff_id") == visual_evidence_review_diff_id for row in payload):
            fail("visual evidence review diff list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/visual-evidence-review-diff/diffs/{visual_evidence_review_diff_id}")
        if status != 200 or payload.get("diff_id") != visual_evidence_review_diff_id or payload.get("diff_summary", {}).get("latest_targets", 0) < 6:
            fail("visual evidence review diff detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/visual-evidence-review-diff/diffs/{visual_evidence_review_diff_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Visual Evidence Review Diff" not in content:
            fail("visual evidence review diff download endpoint contract failed")

        status, payload = request_json(base_url, "/api/visual-evidence-review-annotations")
        if status != 200 or payload.get("visual_evidence_review_annotations_version") != "visual_evidence_review_annotations_v001":
            fail("visual evidence review annotations status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/visual-evidence-review-annotations/create",
            method="POST",
            body=json.dumps({"diff_id": visual_evidence_review_diff_id, "created_by": "api_contract", "notes": "API contract v072 visual evidence review annotations."}),
        )
        if status != 200 or payload.get("annotations", {}).get("annotation_readiness") != "ready_for_visual_evidence_annotation_review":
            fail("visual evidence review annotations create endpoint contract failed")
        visual_evidence_review_annotations_id = payload.get("annotations", {}).get("annotation_id")

        status, payload = request_json(base_url, "/api/visual-evidence-review-annotations/annotations?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("annotation_id") == visual_evidence_review_annotations_id for row in payload):
            fail("visual evidence review annotations list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/visual-evidence-review-annotations/annotations/{visual_evidence_review_annotations_id}")
        if status != 200 or payload.get("annotation_id") != visual_evidence_review_annotations_id or payload.get("target_count", 0) < 6:
            fail("visual evidence review annotations detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/visual-evidence-review-annotations/annotations/{visual_evidence_review_annotations_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Visual Evidence Review Annotations" not in content:
            fail("visual evidence review annotations download endpoint contract failed")

        status, payload = request_json(base_url, "/api/visual-evidence-signoff-packet")
        if status != 200 or payload.get("visual_evidence_signoff_packet_version") != "visual_evidence_signoff_packet_v001":
            fail("visual evidence sign-off packet status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/visual-evidence-signoff-packet/create",
            method="POST",
            body=json.dumps({"annotation_id": visual_evidence_review_annotations_id, "created_by": "api_contract", "reviewer": "api_contract", "notes": "API contract v072 visual evidence sign-off packet."}),
        )
        if status != 200 or payload.get("packet", {}).get("packet_readiness") != "ready_for_visual_evidence_signoff_review":
            fail("visual evidence sign-off packet create endpoint contract failed")
        visual_evidence_signoff_packet_id = payload.get("packet", {}).get("packet_id")

        status, payload = request_json(base_url, "/api/visual-evidence-signoff-packet/packets?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("packet_id") == visual_evidence_signoff_packet_id for row in payload):
            fail("visual evidence sign-off packet list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/visual-evidence-signoff-packet/packets/{visual_evidence_signoff_packet_id}")
        if status != 200 or payload.get("packet_id") != visual_evidence_signoff_packet_id or payload.get("target_count", 0) < 6:
            fail("visual evidence sign-off packet detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/visual-evidence-signoff-packet/packets/{visual_evidence_signoff_packet_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Visual Evidence Sign-Off Packet" not in content:
            fail("visual evidence sign-off packet download endpoint contract failed")

        status, payload = request_json(base_url, "/api/final-reviewer-launch-checklist")
        if status != 200 or payload.get("final_reviewer_launch_checklist_version") != "final_reviewer_launch_checklist_v001":
            fail("final reviewer launch checklist status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/final-reviewer-launch-checklist/create",
            method="POST",
            body=json.dumps({"packet_id": visual_evidence_signoff_packet_id, "created_by": "api_contract", "reviewer": "api_contract", "notes": "API contract v072 final reviewer launch checklist."}),
        )
        if status != 200 or payload.get("checklist", {}).get("checklist_readiness") != "ready_for_final_reviewer_launch":
            fail("final reviewer launch checklist create endpoint contract failed")
        final_reviewer_launch_checklist_id = payload.get("checklist", {}).get("checklist_id")

        status, payload = request_json(base_url, "/api/final-reviewer-launch-checklist/checklists?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("checklist_id") == final_reviewer_launch_checklist_id for row in payload):
            fail("final reviewer launch checklist list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/final-reviewer-launch-checklist/checklists/{final_reviewer_launch_checklist_id}")
        if status != 200 or payload.get("checklist_id") != final_reviewer_launch_checklist_id or payload.get("action_count", 0) < 8:
            fail("final reviewer launch checklist detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/final-reviewer-launch-checklist/checklists/{final_reviewer_launch_checklist_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Final Reviewer Launch Checklist" not in content:
            fail("final reviewer launch checklist download endpoint contract failed")


        status, payload = request_json(base_url, "/api/recruiter-demo-brief")
        if status != 200 or payload.get("recruiter_demo_brief_version") != "recruiter_demo_brief_v001":
            fail("recruiter demo brief status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/recruiter-demo-brief/create",
            method="POST",
            body=json.dumps({"checklist_id": final_reviewer_launch_checklist_id, "created_by": "api_contract", "audience": "technical_recruiter", "notes": "API contract v072 recruiter-facing demo brief."}),
        )
        if status != 200 or payload.get("brief", {}).get("brief_readiness") != "ready_for_recruiter_demo":
            fail("recruiter demo brief create endpoint contract failed")
        recruiter_demo_brief_id = payload.get("brief", {}).get("brief_id")

        status, payload = request_json(base_url, "/api/recruiter-demo-brief/briefs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("brief_id") == recruiter_demo_brief_id for row in payload):
            fail("recruiter demo brief list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/recruiter-demo-brief/briefs/{recruiter_demo_brief_id}")
        if status != 200 or payload.get("brief_id") != recruiter_demo_brief_id or payload.get("section_count", 0) < 6:
            fail("recruiter demo brief detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/recruiter-demo-brief/briefs/{recruiter_demo_brief_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Recruiter-Facing Demo Brief" not in content:
            fail("recruiter demo brief download endpoint contract failed")


        status, payload = request_json(base_url, "/api/public-portfolio-package")
        if status != 200 or payload.get("public_portfolio_interview_package_version") != "public_portfolio_interview_package_v001":
            fail("public portfolio package status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/public-portfolio-package/create",
            method="POST",
            body=json.dumps({"brief_id": recruiter_demo_brief_id, "created_by": "api_contract", "audience": "portfolio_reviewer", "notes": "API contract v072 public portfolio interview package."}),
        )
        if status != 200 or payload.get("package", {}).get("package_readiness") != "ready_for_public_portfolio_package":
            fail("public portfolio package create endpoint contract failed")
        public_portfolio_package_id = payload.get("package", {}).get("package_id")

        status, payload = request_json(base_url, "/api/public-portfolio-package/packages?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("package_id") == public_portfolio_package_id for row in payload):
            fail("public portfolio package list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/public-portfolio-package/packages/{public_portfolio_package_id}")
        if status != 200 or payload.get("package_id") != public_portfolio_package_id or payload.get("readme_section_count", 0) < 8:
            fail("public portfolio package detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/public-portfolio-package/packages/{public_portfolio_package_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Public Portfolio Interview Package" not in content:
            fail("public portfolio package download endpoint contract failed")

        status, payload = request_json(base_url, "/api/demo-review-playbook")
        if status != 200 or payload.get("demo_review_playbook_version") != "demo_review_playbook_v001":
            fail("demo review playbook status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/demo-review-playbook/create",
            method="POST",
            body=json.dumps({"package_id": public_portfolio_package_id, "created_by": "api_contract", "audience": "portfolio_reviewer", "notes": "API contract v083 demo review playbook."}),
        )
        if status != 200 or payload.get("playbook", {}).get("playbook_readiness") != "ready_for_demo_review_playbook":
            fail("demo review playbook create endpoint contract failed")
        demo_review_playbook_id = payload.get("playbook", {}).get("playbook_id")

        status, payload = request_json(base_url, "/api/demo-review-playbook/playbooks?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("playbook_id") == demo_review_playbook_id for row in payload):
            fail("demo review playbook list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/demo-review-playbook/playbooks/{demo_review_playbook_id}")
        if status != 200 or payload.get("playbook_id") != demo_review_playbook_id or payload.get("sharing_checklist_item_count", 0) < 8:
            fail("demo review playbook detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/demo-review-playbook/playbooks/{demo_review_playbook_id}/download")
        if status != 200 or len(content) < 1000 or "html" not in content_type.lower() or b"Demo Review Playbook" not in content:
            fail("demo review playbook download endpoint contract failed")

        status, payload = request_json(base_url, "/api/github-publication-bundle")
        if status != 200 or payload.get("github_publication_bundle_version") != "github_publication_bundle_v001":
            fail("GitHub publication bundle status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/github-publication-bundle/create",
            method="POST",
            body=json.dumps({"playbook_id": demo_review_playbook_id, "created_by": "api_contract", "audience": "github_portfolio_reviewer", "notes": "API contract v083 GitHub publication bundle."}),
        )
        if status != 200 or payload.get("bundle", {}).get("bundle_readiness") != "ready_for_github_publication_bundle":
            fail("GitHub publication bundle create endpoint contract failed")
        github_publication_bundle_id = payload.get("bundle", {}).get("bundle_id")

        status, payload = request_json(base_url, "/api/github-publication-bundle/bundles?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("bundle_id") == github_publication_bundle_id for row in payload):
            fail("GitHub publication bundle list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/github-publication-bundle/bundles/{github_publication_bundle_id}")
        if status != 200 or payload.get("bundle_id") != github_publication_bundle_id or payload.get("readme_section_count", 0) < 8:
            fail("GitHub publication bundle detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/github-publication-bundle/bundles/{github_publication_bundle_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("GitHub publication bundle download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            if "README_public.md" not in set(zf.namelist()):
                fail("GitHub publication ZIP should include README_public.md")

        status, payload = request_json(base_url, "/api/repository-publication-qa")
        if status != 200 or payload.get("repository_publication_qa_version") != "repository_publication_qa_v001":
            fail("repository publication QA status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/repository-publication-qa/create",
            method="POST",
            body=json.dumps({"bundle_id": github_publication_bundle_id, "created_by": "api_contract", "audience": "github_repository_reviewer", "notes": "API contract v083 repository publication QA."}),
        )
        if status != 200 or payload.get("review", {}).get("qa_readiness") != "ready_for_repository_publication_qa":
            fail("repository publication QA create endpoint contract failed")
        repository_publication_qa_id = payload.get("review", {}).get("review_id")

        status, payload = request_json(base_url, "/api/repository-publication-qa/reviews?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("review_id") == repository_publication_qa_id for row in payload):
            fail("repository publication QA list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/repository-publication-qa/reviews/{repository_publication_qa_id}")
        if status != 200 or payload.get("review_id") != repository_publication_qa_id or payload.get("required_check_count", 0) < 8:
            fail("repository publication QA detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/repository-publication-qa/reviews/{repository_publication_qa_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("repository publication QA download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if "PUBLIC_SHARING_WALKTHROUGH.md" not in names:
                fail("repository publication QA ZIP should include PUBLIC_SHARING_WALKTHROUGH.md")

        status, payload = request_json(base_url, "/api/repository-export-handoff")
        if status != 200 or payload.get("repository_export_handoff_version") != "repository_export_handoff_v001":
            fail("repository export handoff status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/repository-export-handoff/create",
            method="POST",
            body=json.dumps({"repository_qa_id": repository_publication_qa_id, "created_by": "api_contract", "audience": "github_repository_reviewer", "notes": "API contract v083 repository export handoff."}),
        )
        if status != 200 or payload.get("handoff", {}).get("handoff_readiness") != "ready_for_repository_export_handoff":
            fail("repository export handoff create endpoint contract failed")
        repository_export_handoff_id = payload.get("handoff", {}).get("handoff_id")

        status, payload = request_json(base_url, "/api/repository-export-handoff/handoffs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("handoff_id") == repository_export_handoff_id for row in payload):
            fail("repository export handoff list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/repository-export-handoff/handoffs/{repository_export_handoff_id}")
        if status != 200 or payload.get("handoff_id") != repository_export_handoff_id or payload.get("include_file_count", 0) < 6:
            fail("repository export handoff detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/repository-export-handoff/handoffs/{repository_export_handoff_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("repository export handoff download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if "GITHUB_REPOSITORY_FILE_PLAN.md" not in names:
                fail("repository export handoff ZIP should include GITHUB_REPOSITORY_FILE_PLAN.md")

        status, payload = request_json(base_url, "/api/repository-dry-run-review")
        if status != 200 or payload.get("repository_dry_run_review_version") != "repository_dry_run_review_v001":
            fail("repository dry-run review status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/repository-dry-run-review/create",
            method="POST",
            body=json.dumps({"handoff_id": repository_export_handoff_id, "created_by": "api_contract", "audience": "github_repository_reviewer", "notes": "API contract v083 repository dry-run review."}),
        )
        if status != 200 or payload.get("review", {}).get("review_readiness") != "ready_for_repository_dry_run_review":
            fail("repository dry-run review create endpoint contract failed")
        repository_dry_run_review_id = payload.get("review", {}).get("review_id")

        status, payload = request_json(base_url, "/api/repository-dry-run-review/reviews?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("review_id") == repository_dry_run_review_id for row in payload):
            fail("repository dry-run review list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/repository-dry-run-review/reviews/{repository_dry_run_review_id}")
        if status != 200 or payload.get("review_id") != repository_dry_run_review_id or payload.get("archive_file_count", 0) < 8:
            fail("repository dry-run review detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/repository-dry-run-review/reviews/{repository_dry_run_review_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("repository dry-run review download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if "FINAL_PUBLIC_SHARING_CHECKLIST.md" not in names:
                fail("repository dry-run ZIP should include FINAL_PUBLIC_SHARING_CHECKLIST.md")

        status, payload = request_json(base_url, "/api/repository-final-package-review")
        if status != 200 or payload.get("repository_final_package_review_version") != "repository_final_package_review_v001":
            fail("repository final package review status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/repository-final-package-review/create",
            method="POST",
            body=json.dumps({"dry_run_review_id": repository_dry_run_review_id, "created_by": "api_contract", "audience": "github_repository_reviewer", "notes": "API contract v083 repository final package review."}),
        )
        if status != 200 or payload.get("review", {}).get("review_readiness") != "ready_for_repository_final_package_review" or payload.get("review", {}).get("public_path_issue_count") != 0:
            fail("repository final package review create endpoint contract failed")
        repository_final_package_review_id = payload.get("review", {}).get("review_id")

        status, payload = request_json(base_url, "/api/repository-final-package-review/reviews?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("review_id") == repository_final_package_review_id for row in payload):
            fail("repository final package review list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/repository-final-package-review/reviews/{repository_final_package_review_id}")
        if status != 200 or payload.get("review_id") != repository_final_package_review_id or payload.get("redacted_path_count", 0) < 1:
            fail("repository final package review detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/repository-final-package-review/reviews/{repository_final_package_review_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("repository final package review download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if "REDACTED_PATH_EVIDENCE.md" not in names:
                fail("repository final package ZIP should include REDACTED_PATH_EVIDENCE.md")

        status, payload = request_json(base_url, "/api/public-readme-cleanup-review")
        if status != 200 or payload.get("public_readme_cleanup_review_version") != "public_readme_cleanup_review_v001":
            fail("public README cleanup review status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/public-readme-cleanup-review/create",
            method="POST",
            body=json.dumps({
                "final_package_review_id": repository_final_package_review_id,
                "created_by": "api_contract",
                "audience": "github_repository_reviewer",
                "notes": "API contract v083 public README cleanup review.",
            }),
        )
        if status != 200 or payload.get("review", {}).get("review_readiness") != "ready_for_public_readme_cleanup_review" or payload.get("review", {}).get("public_readme_issue_count") != 0:
            fail("public README cleanup review create endpoint contract failed")
        if payload.get("review", {}).get("screenshot_evidence_count", 0) < 8:
            fail("public README cleanup review should expose screenshot evidence checklist")
        public_readme_cleanup_review_id = payload.get("review", {}).get("review_id")

        status, payload = request_json(base_url, "/api/public-readme-cleanup-review/reviews?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("review_id") == public_readme_cleanup_review_id for row in payload):
            fail("public README cleanup review list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/public-readme-cleanup-review/reviews/{public_readme_cleanup_review_id}")
        if status != 200 or payload.get("review_id") != public_readme_cleanup_review_id or payload.get("public_readme_issue_count") != 0:
            fail("public README cleanup review detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/public-readme-cleanup-review/reviews/{public_readme_cleanup_review_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("public README cleanup review download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if {"PUBLIC_README_CLEANUP_REVIEW.md", "PUBLIC_README_DRAFT.md", "SCREENSHOT_EVIDENCE_CHECKLIST.md", "public_readme_cleanup_review_manifest.json"} - names:
                fail("public README cleanup ZIP missing expected files")

        status, payload = request_json(base_url, "/api/public-repository-polish-package")
        if status != 200 or payload.get("public_repository_polish_package_version") != "public_repository_polish_package_v001":
            fail("public repository polish package status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/public-repository-polish-package/create",
            method="POST",
            body=json.dumps({
                "cleanup_review_id": public_readme_cleanup_review_id,
                "created_by": "api_contract",
                "audience": "github_repository_reviewer",
                "notes": "API contract v083 public repository polish package.",
            }),
        )
        if status != 200 or payload.get("package", {}).get("package_readiness") != "ready_for_public_repository_polish" or payload.get("package", {}).get("public_readme_issue_count") != 0:
            fail("public repository polish package create endpoint contract failed")
        if payload.get("package", {}).get("screenshot_target_count", 0) < 8:
            fail("public repository polish package should expose screenshot targets")
        public_repository_polish_package_id = payload.get("package", {}).get("package_id")

        status, payload = request_json(base_url, "/api/public-repository-polish-package/packages?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("package_id") == public_repository_polish_package_id for row in payload):
            fail("public repository polish package list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/public-repository-polish-package/packages/{public_repository_polish_package_id}")
        if status != 200 or payload.get("package_id") != public_repository_polish_package_id or payload.get("public_readme_issue_count") != 0:
            fail("public repository polish package detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/public-repository-polish-package/packages/{public_repository_polish_package_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("public repository polish package download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if {"FINAL_PUBLIC_REPOSITORY_POLISH.md", "PUBLIC_REPOSITORY_FILE_PLAN.md", "MANUAL_SCREENSHOT_CAPTURE_PACKAGE.md", "PUBLIC_SHARING_CHECKLIST.md", "PUBLIC_REPOSITORY_READY_README.md", "public_repository_polish_package_manifest.json"} - names:
                fail("public repository polish package ZIP missing expected files")

        status, payload = request_json(base_url, "/api/repository-export-checklist")
        if status != 200 or payload.get("repository_export_checklist_version") != "repository_export_checklist_v001":
            fail("repository export checklist status endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/repository-export-checklist/create",
            method="POST",
            body=json.dumps({
                "package_id": public_repository_polish_package_id,
                "created_by": "api_contract",
                "audience": "github_repository_reviewer",
                "notes": "API contract v083 repository export checklist.",
            }),
        )
        if status != 200 or payload.get("checklist", {}).get("checklist_readiness") != "ready_for_repository_export_checklist" or payload.get("checklist", {}).get("required_failed_count") != 0:
            fail("repository export checklist create endpoint contract failed")
        if payload.get("checklist", {}).get("screenshot_target_count", 0) < 8:
            fail("repository export checklist should expose screenshot targets")
        repository_export_checklist_id = payload.get("checklist", {}).get("checklist_id")

        status, payload = request_json(base_url, "/api/repository-export-checklist/checklists?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("checklist_id") == repository_export_checklist_id for row in payload):
            fail("repository export checklist list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/repository-export-checklist/checklists/{repository_export_checklist_id}")
        if status != 200 or payload.get("checklist_id") != repository_export_checklist_id or payload.get("required_failed_count") != 0:
            fail("repository export checklist detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/repository-export-checklist/checklists/{repository_export_checklist_id}/download")
        if status != 200 or len(content) < 1000 or "zip" not in content_type.lower():
            fail("repository export checklist download endpoint contract failed")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = set(zf.namelist())
            if {"FINAL_REPOSITORY_EXPORT_CHECKLIST.md", "SCREENSHOT_CAPTURE_PASS.md", "PUBLIC_REPOSITORY_TREE.md", "README_FINAL_REVIEW_NOTES.md", "repository_export_checklist_manifest.json"} - names:
                fail("repository export checklist ZIP missing expected files")

        status, payload = request_json(base_url, "/api/pilot-areas/metadata")
        if status != 200 or payload.get("pilot_count", 0) < 1000:
            fail("pilot metadata endpoint contract failed")

        status, payload = request_json(base_url, "/api/pilot-areas?q=Kfar%20Saba&limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("osm_id") == "53796999" for row in payload):
            fail("pilot area search endpoint contract failed")

        status, payload = request_json(base_url, "/api/pilot-areas/53796999")
        if status != 200 or payload.get("route_aware_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
            fail("pilot area detail endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/preflight/safe-access-pilot?pilot_osm_id=53796999&dataset_id=israel-and-palestine-260521-free-shp-zip&route_aware=true",
        )
        if status != 200 or not payload.get("can_start_job"):
            fail("pilot preflight endpoint contract failed")
        if payload.get("workspaces", {}).get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
            fail("pilot preflight active workspace contract failed")
        if payload.get("source_gis_modified") is not False:
            fail("pilot preflight read-only evidence contract failed")

        profile_query = "/api/analysis-profiles?dataset_id=israel-and-palestine-260521-free-shp-zip&pilot_osm_id=53796999&route_aware=true"
        status, payload = request_json(base_url, profile_query)
        if status != 200 or len(payload.get("profiles", [])) < 6:
            fail("analysis profiles list endpoint contract failed")
        safe_profile = next((profile for profile in payload.get("profiles", []) if profile.get("profile_id") == "safe_access_pedestrian_review"), None)
        if not safe_profile or safe_profile.get("can_run") is not True:
            fail("analysis profiles list should expose runnable Safe Access profile")
        transit_profile = next((profile for profile in payload.get("profiles", []) if profile.get("profile_id") == "transit_stop_walk_access"), None)
        if not transit_profile or transit_profile.get("can_run") is not True:
            fail("analysis profiles list should expose runnable Transit Access profile")
        park_profile = next((profile for profile in payload.get("profiles", []) if profile.get("profile_id") == "park_playground_access"), None)
        if not park_profile or park_profile.get("can_run") is not True:
            fail("analysis profiles list should expose runnable Park Access profile")
        profile_count = len(payload.get("profiles", []))

        status, payload = request_json(
            base_url,
            "/api/analysis-profiles/safe_access_pedestrian_review?dataset_id=israel-and-palestine-260521-free-shp-zip&pilot_osm_id=53796999",
        )
        if status != 200 or payload.get("readiness", {}).get("readiness_level") != "ready_to_run":
            fail("analysis profile detail endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/analysis-profiles/safe_access_pedestrian_review/readiness?dataset_id=israel-and-palestine-260521-free-shp-zip&pilot_osm_id=53796999",
        )
        if status != 200 or payload.get("can_run") is not True:
            fail("analysis profile readiness endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/analysis-profiles/safe_access_pedestrian_review/plan",
            method="POST",
            body=json.dumps({
                "dataset_id": "israel-and-palestine-260521-free-shp-zip",
                "pilot_osm_id": "53796999",
                "route_aware": True,
            }),
        )
        if status != 200 or not payload.get("can_start_job"):
            fail("analysis profile plan endpoint contract failed")

        status, payload = request_json(base_url, "/api/profile-runners")
        if status != 200 or not any(row.get("profile_id") == "transit_stop_walk_access" for row in payload.get("runners", [])):
            fail("profile runners endpoint contract failed")
        if not any(row.get("profile_id") == "park_playground_access" for row in payload.get("runners", [])):
            fail("profile runners should expose park_playground_access")
        if not any(row.get("profile_id") == "osm_tag_quality" for row in payload.get("runners", [])):
            fail("profile runners should expose osm_tag_quality")

        status, payload = request_json(base_url, "/api/osm-tag-quality")
        if status != 200 or payload.get("summary", {}).get("counts", {}).get("tag_count_rows") != 482:
            fail("OSM tag quality status endpoint contract failed")

        status, payload = request_json(base_url, "/api/osm-tag-quality/summary")
        if status != 200 or payload.get("counts", {}).get("source_count") != 2:
            fail("OSM tag quality summary endpoint contract failed")

        status, payload = request_json(base_url, "/api/osm-tag-quality/results?limit=3")
        if status != 200 or not isinstance(payload, list) or len(payload) != 3:
            fail("OSM tag quality results endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-runners/osm_tag_quality/run",
            method="POST",
            body=json.dumps({"workspace_id": "osm_tag_quality_kfar_saba_v001"}),
        )
        if status != 200 or payload.get("workspace", {}).get("summary", {}).get("counts", {}).get("tag_count_rows") != 482:
            fail("OSM tag quality runner endpoint contract failed")
        osm_workspace_id = payload.get("workspace", {}).get("manifest", {}).get("workspace_id")

        status, payload = request_json(base_url, f"/api/profile-workspaces/{osm_workspace_id}/summary")
        if status != 200 or payload.get("counts", {}).get("pbf_presence_rows", 0) <= 0:
            fail("OSM tag quality profile workspace summary endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-workspaces/{osm_workspace_id}/results?limit=3")
        if status != 200 or not isinstance(payload, list) or len(payload) != 3:
            fail("OSM tag quality profile workspace results endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/profile-workspaces/{osm_workspace_id}/download/tag_quality_summary")
        if status != 200 or len(content) < 1000 or "csv" not in content_type.lower():
            fail("OSM tag quality output download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-runners/transit_stop_walk_access/run",
            method="POST",
            body=json.dumps({
                "base_workspace_id": "safe_access_kfar_saba_route_aware_v001",
                "workspace_id": "transit_stop_walk_access_kfar_saba_v001",
            }),
        )
        if status != 200 or payload.get("workspace", {}).get("summary", {}).get("counts", {}).get("transit_stops") != 180:
            fail("transit profile runner endpoint contract failed")
        transit_workspace_id = payload.get("workspace", {}).get("manifest", {}).get("workspace_id")

        status, payload = request_json(base_url, "/api/profile-workspaces")
        if status != 200 or not isinstance(payload, list) or not any(row.get("workspace_id") == transit_workspace_id for row in payload):
            fail("profile workspaces endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-workspaces/{transit_workspace_id}/summary")
        if status != 200 or payload.get("counts", {}).get("transit_stops") != 180:
            fail("profile workspace summary endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-workspaces/{transit_workspace_id}/results?limit=3")
        if status != 200 or not isinstance(payload, list) or len(payload) != 3:
            fail("profile workspace results endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/profile-workspaces/{transit_workspace_id}/download/transit_stop_access_results")
        if status != 200 or len(content) < 1000 or "csv" not in content_type.lower():
            fail("profile workspace output download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/profile-runners/park_playground_access/run",
            method="POST",
            body=json.dumps({
                "base_workspace_id": "safe_access_kfar_saba_route_aware_v001",
                "workspace_id": "park_playground_access_kfar_saba_v001",
            }),
        )
        if status != 200 or payload.get("workspace", {}).get("summary", {}).get("counts", {}).get("public_spaces") != 145:
            fail("park profile runner endpoint contract failed")
        park_workspace_id = payload.get("workspace", {}).get("manifest", {}).get("workspace_id")

        status, payload = request_json(base_url, "/api/profile-workspaces")
        if status != 200 or not isinstance(payload, list) or not any(row.get("workspace_id") == park_workspace_id for row in payload):
            fail("park profile workspace list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-workspaces/{park_workspace_id}/summary")
        if status != 200 or payload.get("counts", {}).get("parks") != 103 or payload.get("counts", {}).get("playgrounds") != 39:
            fail("park profile workspace summary endpoint contract failed")

        status, payload = request_json(base_url, f"/api/profile-workspaces/{park_workspace_id}/results?limit=3")
        if status != 200 or not isinstance(payload, list) or len(payload) != 3:
            fail("park profile workspace results endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/profile-workspaces/{park_workspace_id}/download/park_playground_access_results")
        if status != 200 or len(content) < 1000 or "csv" not in content_type.lower():
            fail("park profile workspace output download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/portfolio-reports/from-profile-workspace",
            method="POST",
            body=json.dumps({"workspace_id": transit_workspace_id}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("report_id") or payload.get("profile_id") != "transit_stop_walk_access":
            fail("portfolio profile workspace report generation endpoint contract failed")
        profile_report_id = payload["report_id"]

        status, payload = request_json(base_url, f"/api/portfolio-reports/{profile_report_id}")
        if status != 200 or payload.get("report_type") != "profile_workspace":
            fail("portfolio profile workspace report detail endpoint contract failed")
        if payload.get("counts", {}).get("transit_stops") != 180:
            fail("portfolio profile workspace report count contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-reports/{profile_report_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower():
            fail("portfolio profile workspace report download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/portfolio-reports/from-profile-workspace",
            method="POST",
            body=json.dumps({"workspace_id": park_workspace_id}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("report_id") or payload.get("profile_id") != "park_playground_access":
            fail("portfolio park profile report generation endpoint contract failed")
        park_profile_report_id = payload["report_id"]

        status, payload = request_json(base_url, f"/api/portfolio-reports/{park_profile_report_id}")
        if status != 200 or payload.get("counts", {}).get("public_spaces") != 145:
            fail("portfolio park profile report detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-reports/{park_profile_report_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower():
            fail("portfolio park profile report download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/portfolio-reports/from-profile-workspace",
            method="POST",
            body=json.dumps({"workspace_id": authored_workspace_id}),
        )
        if status != 200 or not payload.get("ok") or payload.get("profile_id") != "cycling_micromobility_access":
            fail("portfolio authored profile report generation endpoint contract failed")
        authored_profile_report_id = payload["report_id"]

        status, payload = request_json(base_url, f"/api/portfolio-reports/{authored_profile_report_id}")
        if status != 200 or payload.get("counts", {}).get("result_rows", 0) < 5 or len(payload.get("top_authored_results", [])) == 0:
            fail("portfolio authored profile report detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-reports/{authored_profile_report_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower():
            fail("portfolio authored profile report download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/portfolio-reports/profile-comparison",
            method="POST",
            body=json.dumps({
                "base_workspace_id": "safe_access_kfar_saba_route_aware_v001",
                "profile_workspace_ids": [transit_workspace_id, park_workspace_id],
            }),
        )
        if status != 200 or not payload.get("ok") or payload.get("report_type") != "profile_comparison":
            fail("portfolio profile comparison endpoint contract failed")
        profile_comparison_id = payload["report_id"]

        status, payload = request_json(base_url, f"/api/portfolio-reports/{profile_comparison_id}")
        if status != 200 or len(payload.get("comparison_rows", [])) != 3:
            fail("portfolio profile comparison detail endpoint contract failed")
        comparison_profiles = {row.get("profile_id") for row in payload.get("comparison_rows", [])}
        if {"safe_access_pedestrian_review", "transit_stop_walk_access", "park_playground_access"} - comparison_profiles:
            fail("portfolio profile comparison should cover all implemented profiles")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-reports/{profile_comparison_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower():
            fail("portfolio profile comparison download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/export-bundles/profile-dashboard",
            method="POST",
            body=json.dumps({
                "base_workspace_id": "safe_access_kfar_saba_route_aware_v001",
                "profile_workspace_ids": [transit_workspace_id, park_workspace_id],
            }),
        )
        if status != 200 or not payload.get("ok") or payload.get("profile_count", 0) < 4:
            fail("profile dashboard export bundle generation endpoint contract failed")
        profile_export_bundle_id = payload["bundle_id"]

        status, payload = request_json(base_url, "/api/export-bundles?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(bundle.get("bundle_id") == profile_export_bundle_id for bundle in payload):
            fail("profile dashboard export bundle list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/export-bundles/{profile_export_bundle_id}")
        if status != 200 or payload.get("bundle_type") != "profile_dashboard_export_bundle":
            fail("profile dashboard export bundle detail endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/export-bundles/{profile_export_bundle_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower():
            fail("profile dashboard export bundle download endpoint contract failed")

        workflow_body = json.dumps({
            "dataset_id": "israel-and-palestine-260521-free-shp-zip",
            "pilot_osm_id": "53796999",
            "template_id": "safe_access",
            "route_aware": True,
        })
        status, payload = request_json(
            base_url,
            "/api/analysis-workflow/plan?dataset_id=israel-and-palestine-260521-free-shp-zip&pilot_osm_id=53796999&template_id=safe_access&route_aware=true",
        )
        if status != 200 or not payload.get("can_start_job"):
            fail("analysis workflow GET plan endpoint contract failed")
        if payload.get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
            fail("analysis workflow GET plan active workspace contract failed")

        status, payload = request_json(base_url, "/api/analysis-workflow/plan", method="POST", body=workflow_body)
        if status != 200 or not payload.get("can_start_job"):
            fail("analysis workflow POST plan endpoint contract failed")

        status, payload = request_json(base_url, "/api/analysis-workflow/start", method="POST", body=workflow_body)
        if status != 202 or not payload.get("ok") or not payload.get("job", {}).get("job_id"):
            fail("analysis workflow start endpoint contract failed")
        workflow_job_id = payload["job"]["job_id"]
        workflow_job_payload = payload
        for _ in range(50):
            status, workflow_job_payload = request_json(base_url, f"/api/jobs/{workflow_job_id}")
            if status == 200 and workflow_job_payload.get("status") in {"succeeded", "failed"}:
                break
            time.sleep(0.1)
        if status != 200 or workflow_job_payload.get("status") != "succeeded":
            fail("analysis workflow job detail endpoint contract failed")
        if workflow_job_payload.get("result", {}).get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
            fail("analysis workflow job result contract failed")

        status, payload = request_json(base_url, "/api/analysis-runs?limit=10")
        if status != 200 or not isinstance(payload, list) or not any(run.get("run_id") == workflow_job_id for run in payload):
            fail("analysis runs list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/analysis-runs/{workflow_job_id}")
        if status != 200 or payload.get("run", {}).get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
            fail("analysis run detail endpoint contract failed")
        outputs = payload.get("outputs", [])
        risk_output = next((item for item in outputs if item.get("output_id") == "table_risk_assessment_results"), None)
        if not risk_output:
            fail("analysis run detail should include risk assessment output")

        status, payload = request_json(base_url, f"/api/analysis-runs/{workflow_job_id}/outputs")
        if status != 200 or len(payload.get("outputs", [])) < 6:
            fail("analysis run outputs endpoint contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/analysis-runs/{workflow_job_id}/outputs/{risk_output['output_id']}")
        if status != 200 or len(content) < 1000 or "csv" not in content_type.lower():
            fail("analysis run output download endpoint contract failed")

        status, payload = request_json(base_url, f"/api/analysis-runs/{workflow_job_id}/rerun", method="POST", body="{}")
        if status != 202 or not payload.get("ok") or not payload.get("job", {}).get("job_id"):
            fail("analysis run rerun endpoint contract failed")
        rerun_job_id = payload["job"]["job_id"]
        rerun_job_payload = payload
        for _ in range(50):
            status, rerun_job_payload = request_json(base_url, f"/api/jobs/{rerun_job_id}")
            if status == 200 and rerun_job_payload.get("status") in {"succeeded", "failed"}:
                break
            time.sleep(0.1)
        if status != 200 or rerun_job_payload.get("status") != "succeeded":
            fail("analysis run rerun job detail endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/portfolio-reports/from-run",
            method="POST",
            body=json.dumps({"run_id": workflow_job_id}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("report_id"):
            fail("portfolio report generation endpoint contract failed")
        portfolio_report_id = payload["report_id"]

        status, payload = request_json(base_url, "/api/portfolio-reports?limit=10")
        if status != 200 or not isinstance(payload, list) or not any(report.get("report_id") == portfolio_report_id for report in payload):
            fail("portfolio report list endpoint contract failed")

        status, payload = request_json(base_url, f"/api/portfolio-reports/{portfolio_report_id}")
        if status != 200 or payload.get("report_id") != portfolio_report_id:
            fail("portfolio report detail endpoint contract failed")
        if payload.get("counts", {}).get("pedestrian_generators") != 391:
            fail("portfolio report detail count contract failed")

        status, content, content_type = request_bytes(base_url, f"/api/portfolio-reports/{portfolio_report_id}/download")
        if status != 200 or len(content) < 1000 or "markdown" not in content_type.lower():
            fail("portfolio report download endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/portfolio-reports/compare",
            method="POST",
            body=json.dumps({"run_ids": [workflow_job_id, rerun_job_id]}),
        )
        if status != 200 or not payload.get("ok") or not payload.get("report_id"):
            fail("portfolio report compare endpoint contract failed")
        portfolio_compare_id = payload["report_id"]

        status, payload = request_json(base_url, "/api/dashboard-workspaces/safe_access_kfar_saba_route_aware_v001/summary")
        if status != 200 or payload.get("counts", {}).get("pedestrian_generators") != 391:
            fail("dashboard summary endpoint contract failed")
        if payload.get("route_aware_analysis", {}).get("rows") != 391:
            fail("route-aware summary contract failed")

        status, payload = request_json(base_url, "/api/dashboard-workspaces/safe_access_kfar_saba_route_aware_v001/candidates?limit=2&min_score=70")
        if status != 200 or not isinstance(payload, list) or len(payload) != 2:
            fail("dashboard candidates endpoint contract failed")
        if not payload[0].get("route_aware_available"):
            fail("route-aware candidate enrichment contract failed")

        status, payload = request_json(base_url, "/api/dashboard-workspaces/safe_access_kfar_saba_route_aware_v001/network-access?limit=2&min_route_score=90")
        if status != 200 or not isinstance(payload, list) or len(payload) != 2:
            fail("network access endpoint contract failed")

        status, payload = request_json(base_url, "/api/dashboard-workspaces/missing_workspace/summary")
        if status != 404 or payload.get("error") != "workspace_not_found":
            fail("missing workspace should return 404")

        status, payload = request_json(base_url, "/api/catalog/sources/missing_dataset")
        if status != 404 or payload.get("error") != "dataset_not_found":
            fail("missing dataset should return 404")

        status, payload = request_json(base_url, "/api/runs/safe-access-kfar-saba", method="POST", body="{")
        if status != 400 or payload.get("error") != "bad_request":
            fail("invalid JSON should return 400")

        status, payload = request_json(
            base_url,
            "/api/runs/safe-access-pilot",
            method="POST",
            body=json.dumps({
                "pilot_osm_id": "53796999",
                "workspace_id": "safe_access_kfar_saba_pbf_enriched_v001",
                "route_workspace_id": "safe_access_kfar_saba_route_aware_v001",
                "route_aware": True,
            }),
        )
        if status != 200 or payload.get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
            fail("safe access pilot run endpoint contract failed")

        status, payload = request_json(
            base_url,
            "/api/jobs/safe-access-pilot",
            method="POST",
            body=json.dumps({
                "pilot_osm_id": "53796999",
                "workspace_id": "safe_access_kfar_saba_pbf_enriched_v001",
                "route_workspace_id": "safe_access_kfar_saba_route_aware_v001",
                "route_aware": True,
            }),
        )
        if status != 202 or not payload.get("job_id"):
            fail("safe access pilot job start endpoint contract failed")
        job_id = payload["job_id"]
        job_payload = payload
        for _ in range(50):
            status, job_payload = request_json(base_url, f"/api/jobs/{job_id}")
            if status == 200 and job_payload.get("status") in {"succeeded", "failed"}:
                break
            time.sleep(0.1)
        if status != 200 or job_payload.get("status") != "succeeded":
            fail("safe access pilot job detail endpoint contract failed")
        if job_payload.get("result", {}).get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
            fail("safe access pilot job result contract failed")

        status, payload = request_json(base_url, "/api/jobs?limit=5")
        if status != 200 or not isinstance(payload, list) or not any(row.get("job_id") == job_id for row in payload):
            fail("job history endpoint contract failed")

        result = {
            "passed": True,
            "base_url": base_url,
            "checked_endpoints": 362,
            "product_architecture_version": product_architecture_version,
            "profile_dashboard_contract_version": profile_dashboard_contract_version,
            "scoring_rules_version": "scoring_rules_v001",
            "postgis_plan_id": postgis_plan_id,
            "profile_mapper_contracts_version": profile_mapper_contracts_version,
            "profile_mapper_plan_id": profile_mapper_plan_id,
            "contract_execution_dry_run_id": contract_execution_dry_run_id,
            "template_authoring_draft_id": template_authoring_draft_id,
            "execution_queue_job_id": execution_queue_job_id,
            "dataset_package_id": dataset_package_id,
            "authored_profile_workspace_id": authored_workspace_id,
            "authored_queue_job_id": authored_queue_job_id,
            "authored_profile_report_id": authored_profile_report_id,
            "profile_promotion_proposal_id": profile_promotion_proposal_id,
            "profile_acceptance_decision_id": profile_acceptance_decision_id,
            "profile_contract_diff_id": profile_contract_diff_id,
            "profile_application_plan_id": profile_application_plan_id,
            "profile_config_apply_proposal_id": profile_config_apply_proposal_id,
            "profile_contract_regression_preview_id": profile_contract_regression_preview_id,
            "release_readiness_snapshot_id": release_readiness_snapshot_id,
            "release_readiness_gate_count": release_readiness_gate_count,
            "portfolio_demo_snapshot_id": portfolio_demo_snapshot_id,
            "portfolio_demo_step_count": portfolio_demo_step_count,
            "portfolio_evidence_bundle_id": portfolio_evidence_bundle_id,
            "bundle_review_checklist_id": bundle_review_checklist_id,
            "portfolio_narrative_id": portfolio_narrative_id,
            "portfolio_handoff_page_id": portfolio_handoff_page_id,
            "portfolio_evidence_gallery_id": portfolio_evidence_gallery_id,
            "multi_pilot_comparison_id": multi_pilot_comparison_id,
            "comparison_map_export_id": comparison_map_export_id,
            "workflow_job_id": workflow_job_id,
            "rerun_job_id": rerun_job_id,
            "job_id": job_id,
            "portfolio_report_id": portfolio_report_id,
            "profile_report_id": profile_report_id,
            "park_profile_report_id": park_profile_report_id,
            "profile_comparison_id": profile_comparison_id,
            "profile_export_bundle_id": profile_export_bundle_id,
            "local_intake_plan_id": local_intake_plan_id,
            "source_import_request_id": source_import_request_id,
            "source_import_decision_id": source_import_decision_id,
            "source_handoff_id": source_handoff_id,
            "source_handoff_execution_id": source_handoff_execution_id,
            "execution_evidence_package_id": execution_evidence_package_id,
            "second_execution_evidence_package_id": second_execution_evidence_package_id,
            "execution_result_diff_id": execution_result_diff_id,
            "execution_diff_gallery_id": execution_diff_gallery_id,
            "execution_diff_detail_id": execution_diff_detail_id,
            "reproducibility_audit_packet_id": reproducibility_audit_packet_id,
            "reviewer_audit_index_id": reviewer_audit_index_id,
            "portfolio_export_launcher_id": portfolio_export_launcher_id,
            "portable_release_package_id": portable_release_package_id,
            "demo_script_pack_id": demo_script_pack_id,
            "visual_qa_ledger_id": visual_qa_ledger_id,
            "visual_baseline_comparison_id": visual_baseline_comparison_id,
            "demo_artifact_completeness_id": demo_artifact_completeness_id,
            "visual_evidence_capture_id": visual_evidence_capture_id,
            "visual_evidence_review_diff_id": visual_evidence_review_diff_id,
            "visual_evidence_review_annotations_id": visual_evidence_review_annotations_id,
            "visual_evidence_signoff_packet_id": visual_evidence_signoff_packet_id,
            "final_reviewer_launch_checklist_id": final_reviewer_launch_checklist_id,
            "recruiter_demo_brief_id": recruiter_demo_brief_id,
            "public_portfolio_package_id": public_portfolio_package_id,
            "demo_review_playbook_id": demo_review_playbook_id,
            "github_publication_bundle_id": github_publication_bundle_id,
            "repository_publication_qa_id": repository_publication_qa_id,
            "repository_export_handoff_id": repository_export_handoff_id,
            "repository_dry_run_review_id": repository_dry_run_review_id,
            "repository_final_package_review_id": repository_final_package_review_id,
            "public_readme_cleanup_review_id": public_readme_cleanup_review_id,
            "public_repository_polish_package_id": public_repository_polish_package_id,
            "repository_export_checklist_id": repository_export_checklist_id,
            "portfolio_compare_id": portfolio_compare_id,
            "analysis_profile_count": profile_count,
            "transit_profile_workspace_id": transit_workspace_id,
            "park_profile_workspace_id": park_workspace_id,
            "osm_tag_quality_workspace_id": osm_workspace_id,
        }
        (PROJECT_DIR / "api_contract_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
