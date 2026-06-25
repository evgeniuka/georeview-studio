from __future__ import annotations

import json
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
            "checked_endpoints": 183,
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
