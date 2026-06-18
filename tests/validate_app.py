from __future__ import annotations

import json
from pathlib import Path
import zipfile
import sys
import time
import threading
from http.server import ThreadingHTTPServer


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
FRONTEND_STATIC_DIR = PROJECT_DIR / "frontend" / "static"
PORTFOLIO_DIR = PROJECT_DIR / "portfolio"


def infer_maps_root(project_dir: Path) -> Path:
    for parent in project_dir.parents:
        if parent.name == "analysis_output":
            return parent.parent
    return project_dir.parent


ROOT = infer_maps_root(PROJECT_DIR)
OUTPUT_ROOT = ROOT / "analysis_output"
MVP_DIR = OUTPUT_ROOT / "kfar_saba_mvp"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
FORBIDDEN_TERMS = ["danger" + "ous", "un" + "safe", "definitely " + "danger" + "ous"]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> None:
    required = [
        BACKEND_DIR / "app.py",
        BACKEND_DIR / "product_architecture.py",
        BACKEND_DIR / "profile_dashboard.py",
        BACKEND_DIR / "local_intake.py",
        BACKEND_DIR / "profile_export_bundle.py",
        BACKEND_DIR / "analysis_profiles.py",
        BACKEND_DIR / "analysis_runs.py",
        BACKEND_DIR / "transit_access_analyzer.py",
        BACKEND_DIR / "park_playground_access_analyzer.py",
        BACKEND_DIR / "portfolio_report_builder.py",
        BACKEND_DIR / "analysis_workflow.py",
        BACKEND_DIR / "source_onboarding.py",
        BACKEND_DIR / "preflight.py",
        BACKEND_DIR / "pilot_area_catalog.py",
        BACKEND_DIR / "run_job_manager.py",
        BACKEND_DIR / "scoring_rules.py",
        BACKEND_DIR / "postgis_backend.py",
        BACKEND_DIR / "profile_mapper.py",
        BACKEND_DIR / "contract_execution.py",
        BACKEND_DIR / "template_authoring.py",
        BACKEND_DIR / "execution_queue.py",
        BACKEND_DIR / "dataset_package.py",
        BACKEND_DIR / "authored_profile_runner.py",
        BACKEND_DIR / "profile_promotion.py",
        BACKEND_DIR / "release_readiness.py",
        BACKEND_DIR / "portfolio_demo.py",
        BACKEND_DIR / "portfolio_evidence_bundle.py",
        BACKEND_DIR / "bundle_review_checklist.py",
        BACKEND_DIR / "portfolio_narrative_export.py",
        BACKEND_DIR / "portfolio_handoff_page.py",
        BACKEND_DIR / "portfolio_evidence_gallery.py",
        BACKEND_DIR / "multi_pilot_comparison.py",
        BACKEND_DIR / "comparison_map_exports.py",
            BACKEND_DIR / "source_import_guardrails.py",
            BACKEND_DIR / "source_handoff.py",
            BACKEND_DIR / "source_handoff_execution.py",
            BACKEND_DIR / "execution_evidence_package.py",
            BACKEND_DIR / "execution_result_diff.py",
            BACKEND_DIR / "execution_diff_gallery.py",
            BACKEND_DIR / "execution_diff_detail.py",
            BACKEND_DIR / "reproducibility_audit_packet.py",
            BACKEND_DIR / "reviewer_audit_index.py",
            BACKEND_DIR / "portfolio_export_launcher.py",
            BACKEND_DIR / "portable_release_package.py",
            BACKEND_DIR / "demo_script_pack.py",
            BACKEND_DIR / "visual_qa_snapshot_ledger.py",
            BACKEND_DIR / "visual_baseline_comparison.py",
            BACKEND_DIR / "demo_artifact_completeness.py",
            BACKEND_DIR / "visual_evidence_capture.py",
            BACKEND_DIR / "visual_evidence_review_diff.py",
            BACKEND_DIR / "visual_evidence_review_annotations.py",
            BACKEND_DIR / "visual_evidence_signoff_packet.py",
            BACKEND_DIR / "final_reviewer_launch_checklist.py",
            BACKEND_DIR / "recruiter_demo_brief.py",
            BACKEND_DIR / "public_portfolio_interview_package.py",
            BACKEND_DIR / "demo_review_playbook.py",
            BACKEND_DIR / "github_publication_bundle.py",
            BACKEND_DIR / "repository_publication_qa.py",
            BACKEND_DIR / "repository_export_handoff.py",
            BACKEND_DIR / "repository_dry_run_review.py",
            BACKEND_DIR / "repository_final_package_review.py",
            BACKEND_DIR / "public_readme_cleanup_review.py",
            BACKEND_DIR / "public_repository_polish_package.py",
            BACKEND_DIR / "repository_export_checklist.py",
        BACKEND_DIR / "route_network_analyzer.py",
        BACKEND_DIR / "workspace_runner.py",
        BACKEND_DIR / "generic_safe_access_mapper.py",
        PROJECT_DIR / "README.md",
        PROJECT_DIR / "project_manifest.json",
        PROJECT_DIR / "config" / "scoring_rules_v001.json",
        PROJECT_DIR / "config" / "postgis_schema_v001.sql",
        PROJECT_DIR / "config" / "profile_mapper_contracts_v001.json",
        PROJECT_DIR / "CHANGELOG.md",
            PROJECT_DIR / "docs" / "source_import_guardrails.md",
            PROJECT_DIR / "docs" / "source_handoff.md",
            PROJECT_DIR / "docs" / "source_handoff_execution.md",
            PROJECT_DIR / "docs" / "execution_evidence_package.md",
            PROJECT_DIR / "docs" / "execution_result_diff.md",
            PROJECT_DIR / "docs" / "execution_diff_gallery.md",
            PROJECT_DIR / "docs" / "execution_diff_detail.md",
            PROJECT_DIR / "docs" / "reproducibility_audit_packet.md",
            PROJECT_DIR / "docs" / "reviewer_audit_index.md",
            PROJECT_DIR / "docs" / "portfolio_export_launcher.md",
            PROJECT_DIR / "docs" / "portable_release_package.md",
            PROJECT_DIR / "docs" / "demo_script_pack.md",
            PROJECT_DIR / "docs" / "visual_qa_snapshot_ledger.md",
            PROJECT_DIR / "docs" / "visual_baseline_comparison.md",
            PROJECT_DIR / "docs" / "demo_artifact_completeness.md",
            PROJECT_DIR / "docs" / "visual_evidence_capture.md",
            PROJECT_DIR / "docs" / "visual_evidence_review_diff.md",
            PROJECT_DIR / "docs" / "visual_evidence_review_annotations.md",
            PROJECT_DIR / "docs" / "visual_evidence_signoff_packet.md",
            PROJECT_DIR / "docs" / "final_reviewer_launch_checklist.md",
            PROJECT_DIR / "docs" / "recruiter_demo_brief.md",
            PROJECT_DIR / "docs" / "public_portfolio_interview_package.md",
            PROJECT_DIR / "docs" / "demo_review_playbook.md",
            PROJECT_DIR / "docs" / "github_publication_bundle.md",
            PROJECT_DIR / "docs" / "repository_publication_qa.md",
            PROJECT_DIR / "docs" / "repository_export_handoff.md",
            PROJECT_DIR / "docs" / "repository_dry_run_review.md",
            PROJECT_DIR / "docs" / "repository_final_package_review.md",
            PROJECT_DIR / "docs" / "public_readme_cleanup_review.md",
            PROJECT_DIR / "docs" / "public_repository_polish_package.md",
            PROJECT_DIR / "docs" / "repository_export_checklist.md",
        PROJECT_DIR / "RELEASE_CHECKLIST.md",
        FRONTEND_STATIC_DIR / "index.html",
        FRONTEND_STATIC_DIR / "app.js",
        FRONTEND_STATIC_DIR / "styles.css",
        PROJECT_DIR / "scripts" / "run_app.ps1",
        PROJECT_DIR / "scripts" / "validate.ps1",
        PROJECT_DIR / "scripts" / "test_api_contract.ps1",
        PROJECT_DIR / "scripts" / "generate_portfolio_artifacts.py",
        PROJECT_DIR / "scripts" / "generate_portfolio_artifacts.ps1",
        PROJECT_DIR / "docs" / "architecture.md",
        PROJECT_DIR / "docs" / "api.md",
        PROJECT_DIR / "docs" / "data_model.md",
        PROJECT_DIR / "docs" / "operations.md",
        PROJECT_DIR / "docs" / "portfolio.md",
        PROJECT_DIR / "docs" / "testing.md",
        PROJECT_DIR / "docs" / "universal_gis_analytics_architecture.md",
        PROJECT_DIR / "docs" / "product_architecture.md",
        PROJECT_DIR / "docs" / "profile_result_contract.md",
        PROJECT_DIR / "docs" / "local_intake_wizard.md",
        PROJECT_DIR / "docs" / "profile_export_bundle.md",
        PROJECT_DIR / "docs" / "scoring_rules.md",
        PROJECT_DIR / "docs" / "postgis_backend.md",
        PROJECT_DIR / "docs" / "profile_mapper_sdk.md",
        PROJECT_DIR / "docs" / "contract_execution.md",
        PROJECT_DIR / "docs" / "template_authoring.md",
        PROJECT_DIR / "docs" / "execution_queue.md",
        PROJECT_DIR / "docs" / "dataset_package.md",
        PROJECT_DIR / "docs" / "authored_profile_runner.md",
        PROJECT_DIR / "docs" / "authored_dashboard_contract.md",
        PROJECT_DIR / "docs" / "profile_promotion_wizard.md",
        PROJECT_DIR / "docs" / "proposal_acceptance_workflow.md",
        PROJECT_DIR / "docs" / "accepted_contract_application_plan.md",
        PROJECT_DIR / "docs" / "profile_contract_diff_review.md",
        PROJECT_DIR / "docs" / "guarded_config_apply_proposal.md",
        PROJECT_DIR / "docs" / "profile_contract_regression_preview.md",
        PROJECT_DIR / "docs" / "release_readiness_dashboard.md",
        PROJECT_DIR / "docs" / "portfolio_demo_walkthrough.md",
        PROJECT_DIR / "docs" / "portfolio_evidence_bundle.md",
        PROJECT_DIR / "docs" / "bundle_review_checklist.md",
        PROJECT_DIR / "docs" / "portfolio_narrative_export.md",
        PROJECT_DIR / "docs" / "portfolio_handoff_page.md",
        PROJECT_DIR / "docs" / "portfolio_evidence_gallery.md",
        PROJECT_DIR / "docs" / "multi_pilot_comparison.md",
        PROJECT_DIR / "docs" / "comparison_map_exports.md",
        PROJECT_DIR / "docs" / "implementation_plan.md",
        PROJECT_DIR / "docs" / "upload_and_ingestion_design.md",
        PROJECT_DIR / "docs" / "top_project_options.md",
        PROJECT_DIR / "tests" / "test_api_contract.py",
        OUTPUT_ROOT / "data_inventory.csv",
        OUTPUT_ROOT / "layer_summary.csv",
        OUTPUT_ROOT / "osm_tag_counts.csv",
        MVP_DIR / "risk_assessment_results.csv",
        MVP_DIR / "pedestrian_generators.csv",
        MVP_DIR / "crossings.csv",
        MVP_DIR / "road_segments.csv",
        MVP_DIR / "validation_summary.json",
    ]
    for path in required:
        if not path.exists():
            fail(f"missing required file: {path}")

    upstream_validation = json.loads((MVP_DIR / "validation_summary.json").read_text(encoding="utf-8"))
    if not upstream_validation.get("passed"):
        fail("upstream Kfar Saba MVP validation is not passed")
    if upstream_validation.get("analysis_crs") != "EPSG:2039":
        fail("upstream analysis CRS is not EPSG:2039")

    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            BACKEND_DIR / "app.py",
            BACKEND_DIR / "product_architecture.py",
            BACKEND_DIR / "profile_dashboard.py",
            BACKEND_DIR / "local_intake.py",
            BACKEND_DIR / "profile_export_bundle.py",
            BACKEND_DIR / "scoring_rules.py",
            BACKEND_DIR / "postgis_backend.py",
            BACKEND_DIR / "profile_mapper.py",
            BACKEND_DIR / "contract_execution.py",
        BACKEND_DIR / "template_authoring.py",
        BACKEND_DIR / "execution_queue.py",
        BACKEND_DIR / "dataset_package.py",
        BACKEND_DIR / "authored_profile_runner.py",
        BACKEND_DIR / "profile_promotion.py",
        BACKEND_DIR / "release_readiness.py",
            BACKEND_DIR / "portfolio_demo.py",
            BACKEND_DIR / "portfolio_evidence_bundle.py",
            BACKEND_DIR / "bundle_review_checklist.py",
            BACKEND_DIR / "portfolio_narrative_export.py",
            BACKEND_DIR / "portfolio_handoff_page.py",
            BACKEND_DIR / "portfolio_evidence_gallery.py",
            BACKEND_DIR / "multi_pilot_comparison.py",
            BACKEND_DIR / "comparison_map_exports.py",
            BACKEND_DIR / "source_import_guardrails.py",
            BACKEND_DIR / "source_handoff.py",
            BACKEND_DIR / "source_handoff_execution.py",
            BACKEND_DIR / "execution_evidence_package.py",
            BACKEND_DIR / "execution_result_diff.py",
            BACKEND_DIR / "execution_diff_gallery.py",
            BACKEND_DIR / "execution_diff_detail.py",
            BACKEND_DIR / "reproducibility_audit_packet.py",
            BACKEND_DIR / "reviewer_audit_index.py",
            BACKEND_DIR / "portfolio_export_launcher.py",
            BACKEND_DIR / "portable_release_package.py",
            BACKEND_DIR / "demo_script_pack.py",
            BACKEND_DIR / "visual_qa_snapshot_ledger.py",
            BACKEND_DIR / "visual_baseline_comparison.py",
            BACKEND_DIR / "demo_artifact_completeness.py",
            BACKEND_DIR / "visual_evidence_capture.py",
            BACKEND_DIR / "visual_evidence_review_diff.py",
            BACKEND_DIR / "visual_evidence_review_annotations.py",
            BACKEND_DIR / "visual_evidence_signoff_packet.py",
            BACKEND_DIR / "final_reviewer_launch_checklist.py",
            BACKEND_DIR / "recruiter_demo_brief.py",
            BACKEND_DIR / "public_portfolio_interview_package.py",
            BACKEND_DIR / "analysis_profiles.py",
            BACKEND_DIR / "transit_access_analyzer.py",
            BACKEND_DIR / "park_playground_access_analyzer.py",
            BACKEND_DIR / "portfolio_report_builder.py",
            BACKEND_DIR / "workspace_runner.py",
            BACKEND_DIR / "generic_safe_access_mapper.py",
            PROJECT_DIR / "README.md",
            PROJECT_DIR / "project_manifest.json",
            PROJECT_DIR / "CHANGELOG.md",
            PROJECT_DIR / "docs" / "source_import_guardrails.md",
            PROJECT_DIR / "docs" / "source_handoff.md",
            PROJECT_DIR / "docs" / "source_handoff_execution.md",
            PROJECT_DIR / "docs" / "execution_evidence_package.md",
            PROJECT_DIR / "docs" / "execution_result_diff.md",
            PROJECT_DIR / "docs" / "execution_diff_gallery.md",
            PROJECT_DIR / "docs" / "execution_diff_detail.md",
            PROJECT_DIR / "docs" / "reproducibility_audit_packet.md",
            PROJECT_DIR / "docs" / "reviewer_audit_index.md",
            PROJECT_DIR / "docs" / "portfolio_export_launcher.md",
            PROJECT_DIR / "docs" / "portable_release_package.md",
            PROJECT_DIR / "docs" / "demo_script_pack.md",
            PROJECT_DIR / "docs" / "visual_qa_snapshot_ledger.md",
            PROJECT_DIR / "docs" / "visual_baseline_comparison.md",
            PROJECT_DIR / "docs" / "demo_artifact_completeness.md",
            PROJECT_DIR / "docs" / "visual_evidence_capture.md",
            PROJECT_DIR / "docs" / "visual_evidence_review_diff.md",
            PROJECT_DIR / "docs" / "visual_evidence_review_annotations.md",
            PROJECT_DIR / "docs" / "visual_evidence_signoff_packet.md",
            PROJECT_DIR / "docs" / "final_reviewer_launch_checklist.md",
            PROJECT_DIR / "docs" / "recruiter_demo_brief.md",
            PROJECT_DIR / "docs" / "public_portfolio_interview_package.md",
            PROJECT_DIR / "RELEASE_CHECKLIST.md",
            PROJECT_DIR / "scripts" / "generate_portfolio_artifacts.py",
            FRONTEND_STATIC_DIR / "index.html",
            FRONTEND_STATIC_DIR / "app.js",
            FRONTEND_STATIC_DIR / "styles.css",
        ]
    )
    if REVIEW_WORDING not in text:
        fail("approved review wording is missing")
    lowered = text.lower()
    if any(term in lowered for term in FORBIDDEN_TERMS):
        fail("absolute safety claim wording found")

    sys.path.insert(0, str(BACKEND_DIR))
    import app  # noqa: PLC0415

    if app.APP_VERSION != "v083":
        fail("unexpected app version")
    if not str(app.STATIC_DIR).endswith(r"frontend\static"):
        fail("static directory is not packaged under frontend/static")
    manifest_payload = app.project_manifest()
    if manifest_payload.get("version") != "v083_2026-06-01":
        fail("project manifest version mismatch")
    if app.status_for_error({"error": "workspace_not_found"}) != 404:
        fail("workspace_not_found should map to 404")
    if app.status_for_error({"error": "bad_request"}) != 400:
        fail("bad_request should map to 400")
    if app.status_for_error({"error": "base_workspace_not_found"}) != 404:
        fail("base_workspace_not_found should map to 404")
    if app.status_for_error({"error": "pilot_area_not_found"}) != 404:
        fail("pilot_area_not_found should map to 404")
    if app.status_for_error({"error": "job_not_found"}) != 404:
        fail("job_not_found should map to 404")
    if app.status_for_error({"error": "analysis_profile_not_found"}) != 404:
        fail("analysis_profile_not_found should map to 404")
    if app.status_for_error({"error": "profile_workspace_not_found"}) != 404:
        fail("profile_workspace_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_profile_workspace_missing"}) != 400:
        fail("portfolio_profile_workspace_missing should map to 400")
    if app.status_for_error({"error": "profile_compare_needs_workspaces"}) != 400:
        fail("profile_compare_needs_workspaces should map to 400")
    if app.status_for_error({"error": "profile_dashboard_profile_not_found"}) != 404:
        fail("profile_dashboard_profile_not_found should map to 404")
    if app.status_for_error({"error": "local_intake_analysis_output_not_allowed"}) != 400:
        fail("local_intake_analysis_output_not_allowed should map to 400")
    if app.status_for_error({"error": "local_intake_path_not_found"}) != 404:
        fail("local_intake_path_not_found should map to 404")
    if app.status_for_error({"error": "export_bundle_not_found"}) != 404:
        fail("export_bundle_not_found should map to 404")
    if app.status_for_error({"error": "scoring_profile_not_found"}) != 404:
        fail("scoring_profile_not_found should map to 404")
    if app.status_for_error({"error": "postgis_schema_not_found"}) != 404:
        fail("postgis_schema_not_found should map to 404")
    if app.status_for_error({"error": "postgis_plan_not_found"}) != 404:
        fail("postgis_plan_not_found should map to 404")
    if app.status_for_error({"error": "profile_mapper_contract_not_found"}) != 404:
        fail("profile_mapper_contract_not_found should map to 404")
    if app.status_for_error({"error": "profile_mapper_plan_not_found"}) != 404:
        fail("profile_mapper_plan_not_found should map to 404")
    if app.status_for_error({"error": "contract_execution_dry_run_not_found"}) != 404:
        fail("contract_execution_dry_run_not_found should map to 404")
    if app.status_for_error({"error": "authored_profile_draft_missing"}) != 400:
        fail("authored_profile_draft_missing should map to 400")
    if app.status_for_error({"error": "authored_profile_source_missing"}) != 503:
        fail("authored_profile_source_missing should map to 503")
    if app.status_for_error({"error": "profile_promotion_candidate_not_found"}) != 404:
        fail("profile_promotion_candidate_not_found should map to 404")
    if app.status_for_error({"error": "profile_promotion_candidate_not_ready"}) != 400:
        fail("profile_promotion_candidate_not_ready should map to 400")
    if app.status_for_error({"error": "profile_acceptance_decision_not_found"}) != 404:
        fail("profile_acceptance_decision_not_found should map to 404")
    if app.status_for_error({"error": "profile_acceptance_decision_invalid"}) != 400:
        fail("profile_acceptance_decision_invalid should map to 400")
    if app.status_for_error({"error": "profile_application_plan_not_found"}) != 404:
        fail("profile_application_plan_not_found should map to 404")
    if app.status_for_error({"error": "profile_contract_diff_not_found"}) != 404:
        fail("profile_contract_diff_not_found should map to 404")
    if app.status_for_error({"error": "profile_config_apply_proposal_not_found"}) != 404:
        fail("profile_config_apply_proposal_not_found should map to 404")
    if app.status_for_error({"error": "profile_contract_regression_preview_not_found"}) != 404:
        fail("profile_contract_regression_preview_not_found should map to 404")
    if app.status_for_error({"error": "release_readiness_snapshot_not_found"}) != 404:
        fail("release_readiness_snapshot_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_demo_snapshot_not_found"}) != 404:
        fail("portfolio_demo_snapshot_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_evidence_bundle_not_found"}) != 404:
        fail("portfolio_evidence_bundle_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_evidence_bundle_output_not_found"}) != 404:
        fail("portfolio_evidence_bundle_output_not_found should map to 404")
    if app.status_for_error({"error": "bundle_review_checklist_not_found"}) != 404:
        fail("bundle_review_checklist_not_found should map to 404")
    if app.status_for_error({"error": "bundle_review_checklist_output_not_found"}) != 404:
        fail("bundle_review_checklist_output_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_narrative_not_found"}) != 404:
        fail("portfolio_narrative_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_narrative_output_not_found"}) != 404:
        fail("portfolio_narrative_output_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_handoff_page_not_found"}) != 404:
        fail("portfolio_handoff_page_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_handoff_page_output_not_found"}) != 404:
        fail("portfolio_handoff_page_output_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_evidence_gallery_not_found"}) != 404:
        fail("portfolio_evidence_gallery_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_evidence_gallery_output_not_found"}) != 404:
        fail("portfolio_evidence_gallery_output_not_found should map to 404")
    if app.status_for_error({"error": "multi_pilot_comparison_not_found"}) != 404:
        fail("multi_pilot_comparison_not_found should map to 404")
    if app.status_for_error({"error": "multi_pilot_comparison_output_not_found"}) != 404:
        fail("multi_pilot_comparison_output_not_found should map to 404")
    if app.status_for_error({"error": "comparison_map_export_not_found"}) != 404:
        fail("comparison_map_export_not_found should map to 404")
    if app.status_for_error({"error": "comparison_map_export_output_not_found"}) != 404:
        fail("comparison_map_export_output_not_found should map to 404")
    if app.status_for_error({"error": "source_handoff_not_found"}) != 404:
        fail("source_handoff_not_found should map to 404")
    if app.status_for_error({"error": "source_handoff_output_not_found"}) != 404:
        fail("source_handoff_output_not_found should map to 404")
    if app.status_for_error({"error": "source_handoff_execution_not_found"}) != 404:
        fail("source_handoff_execution_not_found should map to 404")
    if app.status_for_error({"error": "source_handoff_execution_output_not_found"}) != 404:
        fail("source_handoff_execution_output_not_found should map to 404")
    if app.status_for_error({"error": "execution_evidence_package_not_found"}) != 404:
        fail("execution_evidence_package_not_found should map to 404")
    if app.status_for_error({"error": "execution_evidence_package_output_not_found"}) != 404:
        fail("execution_evidence_package_output_not_found should map to 404")
    if app.status_for_error({"error": "execution_result_diff_not_found"}) != 404:
        fail("execution_result_diff_not_found should map to 404")
    if app.status_for_error({"error": "execution_result_diff_output_not_found"}) != 404:
        fail("execution_result_diff_output_not_found should map to 404")
    if app.status_for_error({"error": "execution_diff_gallery_not_found"}) != 404:
        fail("execution_diff_gallery_not_found should map to 404")
    if app.status_for_error({"error": "execution_diff_gallery_output_not_found"}) != 404:
        fail("execution_diff_gallery_output_not_found should map to 404")
    if app.status_for_error({"error": "execution_diff_detail_not_found"}) != 404:
        fail("execution_diff_detail_not_found should map to 404")
    if app.status_for_error({"error": "execution_diff_detail_output_not_found"}) != 404:
        fail("execution_diff_detail_output_not_found should map to 404")
    if app.status_for_error({"error": "reproducibility_audit_packet_not_found"}) != 404:
        fail("reproducibility_audit_packet_not_found should map to 404")
    if app.status_for_error({"error": "reproducibility_audit_packet_output_not_found"}) != 404:
        fail("reproducibility_audit_packet_output_not_found should map to 404")
    if app.status_for_error({"error": "reviewer_audit_index_not_found"}) != 404:
        fail("reviewer_audit_index_not_found should map to 404")
    if app.status_for_error({"error": "reviewer_audit_index_output_not_found"}) != 404:
        fail("reviewer_audit_index_output_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_export_launcher_not_found"}) != 404:
        fail("portfolio_export_launcher_not_found should map to 404")
    if app.status_for_error({"error": "portfolio_export_launcher_output_not_found"}) != 404:
        fail("portfolio_export_launcher_output_not_found should map to 404")
    if app.status_for_error({"error": "portable_release_package_not_found"}) != 404:
        fail("portable_release_package_not_found should map to 404")
    if app.status_for_error({"error": "portable_release_package_output_not_found"}) != 404:
        fail("portable_release_package_output_not_found should map to 404")
    if app.status_for_error({"error": "demo_script_pack_not_found"}) != 404:
        fail("demo_script_pack_not_found should map to 404")
    if app.status_for_error({"error": "demo_script_pack_output_not_found"}) != 404:
        fail("demo_script_pack_output_not_found should map to 404")
    if app.status_for_error({"error": "visual_qa_ledger_not_found"}) != 404:
        fail("visual_qa_ledger_not_found should map to 404")
    if app.status_for_error({"error": "visual_qa_ledger_output_not_found"}) != 404:
        fail("visual_qa_ledger_output_not_found should map to 404")
    if app.status_for_error({"error": "visual_baseline_comparison_not_found"}) != 404:
        fail("visual_baseline_comparison_not_found should map to 404")
    if app.status_for_error({"error": "visual_baseline_comparison_output_not_found"}) != 404:
        fail("visual_baseline_comparison_output_not_found should map to 404")
    if app.status_for_error({"error": "demo_artifact_completeness_check_not_found"}) != 404:
        fail("demo_artifact_completeness_check_not_found should map to 404")
    if app.status_for_error({"error": "demo_artifact_completeness_output_not_found"}) != 404:
        fail("demo_artifact_completeness_output_not_found should map to 404")
    if app.status_for_error({"error": "visual_evidence_capture_not_found"}) != 404:
        fail("visual_evidence_capture_not_found should map to 404")
    if app.status_for_error({"error": "visual_evidence_capture_output_not_found"}) != 404:
        fail("visual_evidence_capture_output_not_found should map to 404")
    if app.status_for_error({"error": "visual_evidence_review_diff_not_found"}) != 404:
        fail("visual_evidence_review_diff_not_found should map to 404")
    if app.status_for_error({"error": "visual_evidence_review_diff_output_not_found"}) != 404:
        fail("visual_evidence_review_diff_output_not_found should map to 404")
    if app.status_for_error({"error": "visual_evidence_review_annotations_not_found"}) != 404:
        fail("visual_evidence_review_annotations_not_found should map to 404")
    if app.status_for_error({"error": "visual_evidence_review_annotations_output_not_found"}) != 404:
        fail("visual_evidence_review_annotations_output_not_found should map to 404")
    if app.status_for_error({"error": "visual_evidence_signoff_packet_not_found"}) != 404:
        fail("visual_evidence_signoff_packet_not_found should map to 404")
    if app.status_for_error({"error": "visual_evidence_signoff_packet_output_not_found"}) != 404:
        fail("visual_evidence_signoff_packet_output_not_found should map to 404")
    if app.status_for_error({"error": "final_reviewer_launch_checklist_not_found"}) != 404:
        fail("final_reviewer_launch_checklist_not_found should map to 404")
    if app.status_for_error({"error": "final_reviewer_launch_checklist_output_not_found"}) != 404:
        fail("final_reviewer_launch_checklist_output_not_found should map to 404")
    if app.status_for_error({"error": "recruiter_demo_brief_not_found"}) != 404:
        fail("recruiter_demo_brief_not_found should map to 404")
    if app.status_for_error({"error": "recruiter_demo_brief_output_not_found"}) != 404:
        fail("recruiter_demo_brief_output_not_found should map to 404")
    if app.status_for_error({"error": "public_portfolio_package_not_found"}) != 404:
        fail("public_portfolio_package_not_found should map to 404")
    if app.status_for_error({"error": "public_portfolio_package_output_not_found"}) != 404:
        fail("public_portfolio_package_output_not_found should map to 404")
    if app.status_for_error({"error": "demo_review_playbook_not_found"}) != 404:
        fail("demo_review_playbook_not_found should map to 404")
    if app.status_for_error({"error": "demo_review_playbook_output_not_found"}) != 404:
        fail("demo_review_playbook_output_not_found should map to 404")
    if app.status_for_error({"error": "github_publication_bundle_not_found"}) != 404:
        fail("github_publication_bundle_not_found should map to 404")
    if app.status_for_error({"error": "github_publication_bundle_output_not_found"}) != 404:
        fail("github_publication_bundle_output_not_found should map to 404")
    if app.status_for_error({"error": "repository_publication_qa_not_found"}) != 404:
        fail("repository_publication_qa_not_found should map to 404")
    if app.status_for_error({"error": "repository_publication_qa_output_not_found"}) != 404:
        fail("repository_publication_qa_output_not_found should map to 404")
    if app.status_for_error({"error": "repository_export_handoff_not_found"}) != 404:
        fail("repository_export_handoff_not_found should map to 404")
    if app.status_for_error({"error": "repository_export_handoff_output_not_found"}) != 404:
        fail("repository_export_handoff_output_not_found should map to 404")
    if app.status_for_error({"error": "repository_dry_run_review_not_found"}) != 404:
        fail("repository_dry_run_review_not_found should map to 404")
    if app.status_for_error({"error": "repository_dry_run_review_output_not_found"}) != 404:
        fail("repository_dry_run_review_output_not_found should map to 404")
    if app.status_for_error({"error": "repository_final_package_review_not_found"}) != 404:
        fail("repository_final_package_review_not_found should map to 404")
    if app.status_for_error({"error": "repository_final_package_review_output_not_found"}) != 404:
        fail("repository_final_package_review_output_not_found should map to 404")
    if app.status_for_error({"error": "public_readme_cleanup_review_not_found"}) != 404:
        fail("public_readme_cleanup_review_not_found should map to 404")
    if app.status_for_error({"error": "public_readme_cleanup_review_output_not_found"}) != 404:
        fail("public_readme_cleanup_review_output_not_found should map to 404")
    if app.status_for_error({"error": "public_repository_polish_package_not_found"}) != 404:
        fail("public_repository_polish_package_not_found should map to 404")
    if app.status_for_error({"error": "public_repository_polish_package_output_not_found"}) != 404:
        fail("public_repository_polish_package_output_not_found should map to 404")
    if app.status_for_error({"error": "repository_export_checklist_not_found"}) != 404:
        fail("repository_export_checklist_not_found should map to 404")
    if app.status_for_error({"error": "repository_export_checklist_output_not_found"}) != 404:
        fail("repository_export_checklist_output_not_found should map to 404")
    if app.status_for_error({"error": "source_import_request_not_found"}) != 404:
        fail("source_import_request_not_found should map to 404")
    if app.status_for_error({"error": "source_import_review_output_not_found"}) != 404:
        fail("source_import_review_output_not_found should map to 404")
    if app.status_for_error({"error": "source_import_input_missing"}) != 400:
        fail("source_import_input_missing should map to 400")
    if app.status_for_error({"error": "source_import_decision_invalid"}) != 400:
        fail("source_import_decision_invalid should map to 400")
    if app.status_for_error({"error": "source_handoff_input_missing"}) != 400:
        fail("source_handoff_input_missing should map to 400")
    if app.status_for_error({"error": "source_handoff_no_approved_request"}) != 400:
        fail("source_handoff_no_approved_request should map to 400")
    if app.status_for_error({"error": "source_handoff_not_approved"}) != 400:
        fail("source_handoff_not_approved should map to 400")
    if app.status_for_error({"error": "source_handoff_not_ready"}) != 400:
        fail("source_handoff_not_ready should map to 400")
    if app.status_for_error({"error": "source_handoff_execution_input_missing"}) != 400:
        fail("source_handoff_execution_input_missing should map to 400")
    if app.status_for_error({"error": "source_handoff_execution_ack_missing"}) != 400:
        fail("source_handoff_execution_ack_missing should map to 400")
    if app.status_for_error({"error": "source_handoff_execution_not_ready"}) != 400:
        fail("source_handoff_execution_not_ready should map to 400")
    if app.status_for_error({"error": "execution_evidence_package_input_missing"}) != 400:
        fail("execution_evidence_package_input_missing should map to 400")
    if app.status_for_error({"error": "execution_evidence_package_not_ready"}) != 400:
        fail("execution_evidence_package_not_ready should map to 400")
    if app.status_for_error({"error": "execution_result_diff_input_missing"}) != 400:
        fail("execution_result_diff_input_missing should map to 400")
    if app.status_for_error({"error": "execution_result_diff_not_ready"}) != 400:
        fail("execution_result_diff_not_ready should map to 400")
    if app.status_for_error({"error": "execution_diff_gallery_not_ready"}) != 400:
        fail("execution_diff_gallery_not_ready should map to 400")
    if app.status_for_error({"error": "execution_diff_detail_not_ready"}) != 400:
        fail("execution_diff_detail_not_ready should map to 400")
    if app.status_for_error({"error": "reproducibility_audit_packet_not_ready"}) != 400:
        fail("reproducibility_audit_packet_not_ready should map to 400")
    if app.status_for_error({"error": "reviewer_audit_index_not_ready"}) != 400:
        fail("reviewer_audit_index_not_ready should map to 400")
    if app.status_for_error({"error": "portfolio_export_launcher_input_missing"}) != 400:
        fail("portfolio_export_launcher_input_missing should map to 400")
    if app.status_for_error({"error": "portfolio_export_launcher_not_ready"}) != 400:
        fail("portfolio_export_launcher_not_ready should map to 400")
    if app.status_for_error({"error": "portable_release_package_input_missing"}) != 400:
        fail("portable_release_package_input_missing should map to 400")
    if app.status_for_error({"error": "portable_release_package_not_ready"}) != 400:
        fail("portable_release_package_not_ready should map to 400")
    if app.status_for_error({"error": "demo_script_pack_input_missing"}) != 400:
        fail("demo_script_pack_input_missing should map to 400")
    if app.status_for_error({"error": "demo_script_pack_not_ready"}) != 400:
        fail("demo_script_pack_not_ready should map to 400")
    if app.status_for_error({"error": "visual_qa_ledger_input_missing"}) != 400:
        fail("visual_qa_ledger_input_missing should map to 400")
    if app.status_for_error({"error": "visual_qa_ledger_not_ready"}) != 400:
        fail("visual_qa_ledger_not_ready should map to 400")
    if app.status_for_error({"error": "visual_baseline_comparison_input_missing"}) != 400:
        fail("visual_baseline_comparison_input_missing should map to 400")
    if app.status_for_error({"error": "visual_baseline_comparison_not_ready"}) != 400:
        fail("visual_baseline_comparison_not_ready should map to 400")
    if app.status_for_error({"error": "demo_artifact_completeness_input_missing"}) != 400:
        fail("demo_artifact_completeness_input_missing should map to 400")
    if app.status_for_error({"error": "demo_artifact_completeness_not_ready"}) != 400:
        fail("demo_artifact_completeness_not_ready should map to 400")
    if app.status_for_error({"error": "visual_evidence_capture_input_missing"}) != 400:
        fail("visual_evidence_capture_input_missing should map to 400")
    if app.status_for_error({"error": "visual_evidence_capture_not_ready"}) != 400:
        fail("visual_evidence_capture_not_ready should map to 400")
    if app.status_for_error({"error": "visual_evidence_review_diff_input_missing"}) != 400:
        fail("visual_evidence_review_diff_input_missing should map to 400")
    if app.status_for_error({"error": "visual_evidence_review_diff_not_ready"}) != 400:
        fail("visual_evidence_review_diff_not_ready should map to 400")
    if app.status_for_error({"error": "visual_evidence_review_annotations_input_missing"}) != 400:
        fail("visual_evidence_review_annotations_input_missing should map to 400")
    if app.status_for_error({"error": "visual_evidence_review_annotations_not_ready"}) != 400:
        fail("visual_evidence_review_annotations_not_ready should map to 400")
    if app.status_for_error({"error": "visual_evidence_signoff_packet_input_missing"}) != 400:
        fail("visual_evidence_signoff_packet_input_missing should map to 400")
    if app.status_for_error({"error": "visual_evidence_signoff_packet_not_ready"}) != 400:
        fail("visual_evidence_signoff_packet_not_ready should map to 400")
    if app.status_for_error({"error": "final_reviewer_launch_checklist_input_missing"}) != 400:
        fail("final_reviewer_launch_checklist_input_missing should map to 400")
    if app.status_for_error({"error": "final_reviewer_launch_checklist_not_ready"}) != 400:
        fail("final_reviewer_launch_checklist_not_ready should map to 400")
    if app.status_for_error({"error": "recruiter_demo_brief_input_missing"}) != 400:
        fail("recruiter_demo_brief_input_missing should map to 400")
    if app.status_for_error({"error": "recruiter_demo_brief_not_ready"}) != 400:
        fail("recruiter_demo_brief_not_ready should map to 400")
    if app.status_for_error({"error": "public_portfolio_package_input_missing"}) != 400:
        fail("public_portfolio_package_input_missing should map to 400")
    if app.status_for_error({"error": "public_portfolio_package_not_ready"}) != 400:
        fail("public_portfolio_package_not_ready should map to 400")
    if app.status_for_error({"error": "demo_review_playbook_input_missing"}) != 400:
        fail("demo_review_playbook_input_missing should map to 400")
    if app.status_for_error({"error": "demo_review_playbook_not_ready"}) != 400:
        fail("demo_review_playbook_not_ready should map to 400")
    if app.status_for_error({"error": "github_publication_bundle_input_missing"}) != 400:
        fail("github_publication_bundle_input_missing should map to 400")
    if app.status_for_error({"error": "github_publication_bundle_not_ready"}) != 400:
        fail("github_publication_bundle_not_ready should map to 400")
    if app.status_for_error({"error": "repository_publication_qa_input_missing"}) != 400:
        fail("repository_publication_qa_input_missing should map to 400")
    if app.status_for_error({"error": "repository_publication_qa_not_ready"}) != 400:
        fail("repository_publication_qa_not_ready should map to 400")
    if app.status_for_error({"error": "repository_export_handoff_input_missing"}) != 400:
        fail("repository_export_handoff_input_missing should map to 400")
    if app.status_for_error({"error": "repository_export_handoff_not_ready"}) != 400:
        fail("repository_export_handoff_not_ready should map to 400")
    if app.status_for_error({"error": "repository_dry_run_review_input_missing"}) != 400:
        fail("repository_dry_run_review_input_missing should map to 400")
    if app.status_for_error({"error": "repository_dry_run_review_not_ready"}) != 400:
        fail("repository_dry_run_review_not_ready should map to 400")
    if app.status_for_error({"error": "repository_final_package_review_input_missing"}) != 400:
        fail("repository_final_package_review_input_missing should map to 400")
    if app.status_for_error({"error": "repository_final_package_review_not_ready"}) != 400:
        fail("repository_final_package_review_not_ready should map to 400")
    if app.status_for_error({"error": "public_readme_cleanup_review_input_missing"}) != 400:
        fail("public_readme_cleanup_review_input_missing should map to 400")
    if app.status_for_error({"error": "public_readme_cleanup_review_not_ready"}) != 400:
        fail("public_readme_cleanup_review_not_ready should map to 400")
    if app.status_for_error({"error": "public_repository_polish_package_input_missing"}) != 400:
        fail("public_repository_polish_package_input_missing should map to 400")
    if app.status_for_error({"error": "public_repository_polish_package_not_ready"}) != 400:
        fail("public_repository_polish_package_not_ready should map to 400")
    if app.status_for_error({"error": "repository_export_checklist_input_missing"}) != 400:
        fail("repository_export_checklist_input_missing should map to 400")
    if app.status_for_error({"error": "repository_export_checklist_not_ready"}) != 400:
        fail("repository_export_checklist_not_ready should map to 400")
    if app.status_for_error({"error": "profile_application_plan_not_ready"}) != 400:
        fail("profile_application_plan_not_ready should map to 400")
    if app.status_for_error({"error": "profile_contract_diff_not_ready"}) != 400:
        fail("profile_contract_diff_not_ready should map to 400")
    if app.status_for_error({"error": "profile_config_apply_proposal_not_ready"}) != 400:
        fail("profile_config_apply_proposal_not_ready should map to 400")
    if app.status_for_error({"error": "profile_contract_regression_preview_not_ready"}) != 400:
        fail("profile_contract_regression_preview_not_ready should map to 400")

    architecture = app.PRODUCT_ARCHITECTURE.blueprint()
    if not architecture.get("ok"):
        fail(f"product architecture blueprint failed: {architecture}")
    if architecture.get("recommended_variant_id") != "universal_gis_review_studio":
        fail("product architecture should recommend the universal GIS workbench direction")
    if architecture.get("current_evidence", {}).get("implemented_profile_count", 0) < 3:
        fail("product architecture should expose at least three implemented profiles")
    if not any(stage.get("name") == "profile_runner" and stage.get("status") == "implemented_for_three_profiles" for stage in architecture.get("canonical_pipeline", [])):
        fail("product architecture should expose the implemented profile runner pipeline stage")
    if architecture.get("source_gis_modified") is not False:
        fail("product architecture should preserve source read-only evidence")
    architecture_variants = app.PRODUCT_ARCHITECTURE.variants()
    if len(architecture_variants.get("variants", [])) != 3:
        fail("product architecture should expose three top project variants")
    architecture_roadmap = app.PRODUCT_ARCHITECTURE.roadmap()
    if not any(item.get("release") == "v083" and item.get("status") == "current" for item in architecture_roadmap.get("roadmap", [])):
        fail("product architecture roadmap should include current v083")
    if not any(item.get("release") == "v084" and item.get("status") == "next" for item in architecture_roadmap.get("roadmap", [])):
        fail("product architecture roadmap should include next v084")
    architecture_plan = app.PRODUCT_ARCHITECTURE.implementation_plan({"target_version": "v083"})
    if architecture_plan.get("target_version") != "v083" or architecture_plan.get("focus") != "figma_aligned_dashboard_polish" or len(architecture_plan.get("milestones", [])) < 4:
        fail("product architecture implementation plan should expose v083 dashboard polish milestones")
    profile_dashboard = app.PROFILE_DASHBOARD.overview()
    if not profile_dashboard.get("ok") or profile_dashboard.get("implemented_profile_count", 0) < 3:
        fail(f"profile dashboard overview failed: {profile_dashboard}")
    if "primary_score" not in profile_dashboard.get("result_contract_fields", []):
        fail("profile dashboard contract should include primary_score")
    profile_dashboard_profiles = {profile.get("profile_id"): profile for profile in profile_dashboard.get("profiles", [])}
    for profile_id, expected_count in {
        "safe_access_pedestrian_review": 391,
        "transit_stop_walk_access": 180,
        "park_playground_access": 145,
    }.items():
        if profile_dashboard_profiles.get(profile_id, {}).get("result_count") != expected_count:
            fail(f"profile dashboard count mismatch for {profile_id}")
        summary_payload = app.PROFILE_DASHBOARD.summary(profile_id)
        if summary_payload.get("result_count") != expected_count or summary_payload.get("source_gis_modified") is not False:
            fail(f"profile dashboard summary failed for {profile_id}: {summary_payload}")
        result_payload = app.PROFILE_DASHBOARD.results(profile_id, limit=3)
        if result_payload.get("row_count") != 3:
            fail(f"profile dashboard result limit failed for {profile_id}: {result_payload}")
        first_row = result_payload.get("rows", [{}])[0]
        required_profile_fields = {"profile_id", "workspace_id", "result_id", "entity_type", "primary_score", "flags", "data_quality_flags", "review_wording", "lon", "lat", "source_gis_modified"}
        if required_profile_fields - set(first_row):
            fail(f"profile dashboard row is missing contract fields for {profile_id}")
        if first_row.get("review_wording") != REVIEW_WORDING:
            fail(f"profile dashboard row wording mismatch for {profile_id}")
        if first_row.get("source_gis_modified") is not False:
            fail(f"profile dashboard row should preserve source read-only evidence for {profile_id}")
    missing_profile_dashboard = app.PROFILE_DASHBOARD.results("missing_profile")
    if missing_profile_dashboard.get("error") != "profile_dashboard_profile_not_found":
        fail("missing profile dashboard request should return profile_dashboard_profile_not_found")

    scoring_overview = app.SCORING_RULES.overview()
    if not scoring_overview.get("ok") or scoring_overview.get("profile_count") != 3:
        fail(f"scoring rules overview failed: {scoring_overview}")
    if scoring_overview.get("scoring_rules_version") != "scoring_rules_v001":
        fail("scoring rules version mismatch")
    for profile_id, expected_count in {
        "safe_access_pedestrian_review": 391,
        "transit_stop_walk_access": 180,
        "park_playground_access": 145,
    }.items():
        scoring_profile = app.SCORING_RULES.profile(profile_id)
        # v001 reclassified no_reachable_crossing_on_network_proxy from a scoring rule to a
        # zero-point context flag (network unreachability is a data-quality flag, not risk),
        # so point-bearing scoring_rules is now 9 (was 10). The scoring audit immediately
        # below is the authoritative config<->actual reconciliation gate.
        if not scoring_profile.get("ok") or len(scoring_profile.get("scoring_rules", [])) < 9:
            fail(f"scoring profile failed for {profile_id}: {scoring_profile}")
        scoring_audit = app.SCORING_RULES.audit(profile_id, limit=5)
        if scoring_audit.get("rows_audited") != expected_count:
            fail(f"scoring audit row count mismatch for {profile_id}: {scoring_audit}")
        if scoring_audit.get("mismatch_count") != 0 or scoring_audit.get("exact_match_count") != expected_count:
            fail(f"scoring audit should exactly match actual scores for {profile_id}: {scoring_audit}")
        if scoring_audit.get("source_gis_modified") is not False:
            fail(f"scoring audit should preserve source read-only evidence for {profile_id}")
    missing_scoring_profile = app.SCORING_RULES.profile("missing_profile")
    if missing_scoring_profile.get("error") != "scoring_profile_not_found":
        fail("missing scoring profile should return scoring_profile_not_found")

    postgis_status = app.POSTGIS_BACKEND.status()
    if not postgis_status.get("ok") or postgis_status.get("connection_status") != "not_configured":
        fail(f"PostGIS backend status failed: {postgis_status}")
    postgis_schema = app.POSTGIS_BACKEND.schema()
    if not postgis_schema.get("ok") or postgis_schema.get("table_count", 0) < 10 or postgis_schema.get("index_count", 0) < 8:
        fail(f"PostGIS schema summary failed: {postgis_schema}")
    if "profile_results" not in postgis_schema.get("tables", []):
        fail("PostGIS schema should include profile_results")
    postgis_readiness = postgis_status.get("readiness", {})
    if postgis_readiness.get("profile_result_rows", 0) < 716:
        fail(f"PostGIS readiness should expose at least the three base profile result sets: {postgis_readiness}")
    if postgis_readiness.get("source_gis_modified") is not False:
        fail("PostGIS readiness should preserve source read-only evidence")
    postgis_plan_preview = app.POSTGIS_BACKEND.migration_plan({"scope": "kfar_saba_pilot"})
    if not postgis_plan_preview.get("ok") or len(postgis_plan_preview.get("phases", [])) < 5:
        fail(f"PostGIS migration plan preview failed: {postgis_plan_preview}")
    postgis_plan = app.POSTGIS_BACKEND.migration_plan({"scope": "kfar_saba_pilot"}, write_files=True)
    if not postgis_plan.get("ok") or not Path(postgis_plan.get("json_file", "")).exists():
        fail(f"PostGIS migration plan creation failed: {postgis_plan}")
    if postgis_plan.get("source_gis_modified") is not False:
        fail("PostGIS migration plan should preserve source read-only evidence")
    if not any(row.get("plan_id") == postgis_plan.get("plan_id") for row in app.POSTGIS_BACKEND.list_plans(10)):
        fail("PostGIS migration plan should appear in plan list")
    postgis_detail = app.POSTGIS_BACKEND.detail(postgis_plan.get("plan_id"))
    if postgis_detail.get("plan_id") != postgis_plan.get("plan_id"):
        fail("PostGIS migration plan detail failed")
    missing_postgis_plan = app.POSTGIS_BACKEND.detail("missing_plan")
    if missing_postgis_plan.get("error") != "postgis_plan_not_found":
        fail("missing PostGIS plan should return postgis_plan_not_found")


    profile_mapper = app.PROFILE_MAPPER.overview()
    if not profile_mapper.get("ok") or profile_mapper.get("contract_count") != 6:
        fail(f"profile mapper overview failed: {profile_mapper}")
    if profile_mapper.get("validation", {}).get("invalid_contract_count") != 0:
        fail(f"profile mapper contracts should validate: {profile_mapper.get('validation')}")
    if profile_mapper.get("source_gis_modified") is not False:
        fail("profile mapper should preserve source read-only evidence")
    mapper_contracts = app.PROFILE_MAPPER.contracts()
    if mapper_contracts.get("profile_mapper_contracts_version") != "profile_mapper_contracts_v001":
        fail(f"profile mapper contracts version failed: {mapper_contracts}")
    safe_mapper_contract = app.PROFILE_MAPPER.contract("safe_access_pedestrian_review")
    if safe_mapper_contract.get("contract", {}).get("status") != "implemented":
        fail(f"safe access mapper contract failed: {safe_mapper_contract}")
    missing_mapper_contract = app.PROFILE_MAPPER.contract("missing_profile")
    if missing_mapper_contract.get("error") != "profile_mapper_contract_not_found":
        fail("missing mapper contract should return profile_mapper_contract_not_found")
    mapper_compatibility = app.PROFILE_MAPPER.compatibility(dataset_id="israel-and-palestine-260521-free-shp-zip")
    if mapper_compatibility.get("contract_count") != 6 or mapper_compatibility.get("compatible_contract_count", 0) < 5:
        fail(f"profile mapper compatibility failed: {mapper_compatibility}")
    safe_mapper_row = next((row for row in mapper_compatibility.get("rows", []) if row.get("profile_id") == "safe_access_pedestrian_review"), {})
    if safe_mapper_row.get("can_plan") is not True or safe_mapper_row.get("can_run") is not True:
        fail(f"safe access mapper compatibility failed: {safe_mapper_row}")
    mapper_plan_preview = app.PROFILE_MAPPER.mapper_plan({"profile_id": "safe_access_pedestrian_review"})
    if not mapper_plan_preview.get("ok") or len(mapper_plan_preview.get("phases", [])) < 5:
        fail(f"profile mapper plan preview failed: {mapper_plan_preview}")
    mapper_plan = app.PROFILE_MAPPER.mapper_plan({"profile_id": "safe_access_pedestrian_review"}, write_files=True)
    if not mapper_plan.get("ok") or not Path(mapper_plan.get("json_file", "")).exists():
        fail(f"profile mapper plan creation failed: {mapper_plan}")
    if mapper_plan.get("source_gis_modified") is not False:
        fail("profile mapper plan should preserve source read-only evidence")
    if not any(row.get("plan_id") == mapper_plan.get("plan_id") for row in app.PROFILE_MAPPER.list_plans(10)):
        fail("profile mapper plan should appear in plan list")
    mapper_detail = app.PROFILE_MAPPER.detail(mapper_plan.get("plan_id"))
    if mapper_detail.get("plan_id") != mapper_plan.get("plan_id"):
        fail("profile mapper plan detail failed")
    missing_mapper_plan = app.PROFILE_MAPPER.detail("missing_plan")
    if missing_mapper_plan.get("error") != "profile_mapper_plan_not_found":
        fail("missing profile mapper plan should return profile_mapper_plan_not_found")

    contract_execution_status = app.CONTRACT_EXECUTION.status()
    if not contract_execution_status.get("ok") or contract_execution_status.get("adapter_count") != 6:
        fail(f"contract execution status failed: {contract_execution_status}")
    if contract_execution_status.get("executable_now_count") != 4:
        fail(f"contract execution should expose four executable adapters: {contract_execution_status}")
    if contract_execution_status.get("source_gis_modified") is not False:
        fail("contract execution status should preserve source read-only evidence")
    contract_execution_adapters = app.CONTRACT_EXECUTION.adapters_response()
    if len(contract_execution_adapters.get("adapters", [])) != 6:
        fail("contract execution adapters response failed")
    contract_dry_run_preview = app.CONTRACT_EXECUTION.dry_run({"profile_id": "safe_access_pedestrian_review"})
    if not contract_dry_run_preview.get("ok") or contract_dry_run_preview.get("can_execute_now") is not True:
        fail(f"contract execution dry-run preview failed: {contract_dry_run_preview}")
    if contract_dry_run_preview.get("dry_run_only") is not True:
        fail("contract execution preview should be dry-run only")
    blocked_contract_dry_run = app.CONTRACT_EXECUTION.dry_run({"profile_id": "cycling_micromobility_access"})
    if blocked_contract_dry_run.get("can_execute_now") is not False or not blocked_contract_dry_run.get("blockers"):
        fail(f"planned cycling dry-run should be blocked by runner status: {blocked_contract_dry_run}")
    contract_dry_run = app.CONTRACT_EXECUTION.dry_run({"profile_id": "safe_access_pedestrian_review"}, write_files=True)
    if not contract_dry_run.get("ok") or not Path(contract_dry_run.get("json_file", "")).exists():
        fail(f"contract execution dry-run creation failed: {contract_dry_run}")
    if contract_dry_run.get("source_gis_modified") is not False:
        fail("contract execution dry run should preserve source read-only evidence")
    if not any(row.get("dry_run_id") == contract_dry_run.get("dry_run_id") for row in app.CONTRACT_EXECUTION.list_dry_runs(10)):
        fail("contract execution dry run should appear in list")
    contract_dry_run_detail = app.CONTRACT_EXECUTION.detail(contract_dry_run.get("dry_run_id"))
    if contract_dry_run_detail.get("dry_run_id") != contract_dry_run.get("dry_run_id"):
        fail("contract execution dry run detail failed")
    missing_contract_dry_run = app.CONTRACT_EXECUTION.detail("missing_dry_run")
    if missing_contract_dry_run.get("error") != "contract_execution_dry_run_not_found":
        fail("missing contract execution dry run should return contract_execution_dry_run_not_found")

    template_authoring_status = app.TEMPLATE_AUTHORING.status()
    if not template_authoring_status.get("ok") or template_authoring_status.get("blueprint_count") < 4:
        fail(f"template authoring status failed: {template_authoring_status}")
    template_options = app.TEMPLATE_AUTHORING.options()
    if len(template_options.get("blueprints", [])) < 4:
        fail("template authoring options should expose blueprints")
    template_draft_preview = app.TEMPLATE_AUTHORING.draft({"template_id": "cycling_micromobility_access"})
    if not template_draft_preview.get("ok") or template_draft_preview.get("contract", {}).get("status") != "draft":
        fail(f"template authoring draft preview failed: {template_draft_preview}")
    template_draft = app.TEMPLATE_AUTHORING.draft({"template_id": "cycling_micromobility_access"}, write_files=True)
    if not template_draft.get("ok") or not Path(template_draft.get("json_file", "")).exists():
        fail(f"template authoring draft creation failed: {template_draft}")
    if template_draft.get("source_gis_modified") is not False:
        fail("template authoring should preserve source read-only evidence")
    if not any(row.get("draft_id") == template_draft.get("draft_id") for row in app.TEMPLATE_AUTHORING.list_drafts(10)):
        fail("template authoring draft should appear in list")
    template_draft_detail = app.TEMPLATE_AUTHORING.detail(template_draft.get("draft_id"))
    if template_draft_detail.get("draft_id") != template_draft.get("draft_id"):
        fail("template authoring draft detail failed")
    missing_template_draft = app.TEMPLATE_AUTHORING.detail("missing_draft")
    if missing_template_draft.get("error") != "template_authoring_draft_not_found":
        fail("missing template authoring draft should return template_authoring_draft_not_found")

    authored_runner_status = app.AUTHORED_PROFILE_RUNNER.status()
    if not authored_runner_status.get("ok") or authored_runner_status.get("tag_counts_exists") is not True:
        fail(f"authored profile runner status failed: {authored_runner_status}")
    authored_workspace_id = "authored_profile_cycling_micromobility_access_v001"
    authored_run = app.AUTHORED_PROFILE_RUNNER.ensure_workspace(
        template_draft.get("draft_id"),
        workspace_id=authored_workspace_id,
    )
    if not authored_run.get("ok") or authored_run.get("workspace", {}).get("manifest", {}).get("authored_profile_workspace") is not True:
        fail(f"authored profile runner failed: {authored_run}")
    authored_summary = app.profile_workspace_summary(authored_workspace_id)
    authored_counts = authored_summary.get("counts", {})
    if authored_counts.get("result_rows", 0) < 5 or authored_counts.get("source_evidence_rows", 0) < 1:
        fail(f"authored profile summary counts failed: {authored_summary}")
    authored_results = app.profile_workspace_results(authored_workspace_id, 5)
    if not isinstance(authored_results, list) or len(authored_results) < 5:
        fail(f"authored profile results failed: {authored_results}")
    authored_output = app.profile_workspace_output_file(authored_workspace_id, "authored_profile_results")
    if not authored_output.get("ok") or not authored_output.get("path", Path()).exists():
        fail(f"authored profile output file failed: {authored_output}")
    authored_dashboard_summary = app.PROFILE_DASHBOARD.summary("cycling_micromobility_access")
    if authored_dashboard_summary.get("result_count") != authored_counts.get("result_rows") or authored_dashboard_summary.get("profile_source") != "authored_profile_workspace":
        fail(f"authored profile dashboard summary failed: {authored_dashboard_summary}")
    authored_dashboard_results = app.PROFILE_DASHBOARD.results("cycling_micromobility_access", limit=3)
    if authored_dashboard_results.get("row_count") != 3:
        fail(f"authored profile dashboard results failed: {authored_dashboard_results}")
    authored_dashboard_first = authored_dashboard_results.get("rows", [{}])[0]
    if authored_dashboard_first.get("profile_id") != "cycling_micromobility_access" or "source_evidence" not in authored_dashboard_first:
        fail(f"authored profile dashboard row contract failed: {authored_dashboard_first}")
    profile_promotion_status = app.PROFILE_PROMOTION.status()
    if not profile_promotion_status.get("ok") or profile_promotion_status.get("profile_promotion_version") != "profile_promotion_wizard_v001":
        fail(f"profile promotion status failed: {profile_promotion_status}")
    promotion_candidates = app.PROFILE_PROMOTION.candidates(20)
    promotion_candidate = next((row for row in promotion_candidates if row.get("workspace_id") == authored_workspace_id), {})
    if promotion_candidate.get("recommendation") != "ready_for_promotion_proposal" or promotion_candidate.get("missing_required_tags") != 0:
        fail(f"profile promotion candidate failed: {promotion_candidate}")
    promotion_candidate_detail = app.PROFILE_PROMOTION.candidate(authored_workspace_id)
    if promotion_candidate_detail.get("workspace_id") != authored_workspace_id or not promotion_candidate_detail.get("gates"):
        fail(f"profile promotion candidate detail failed: {promotion_candidate_detail}")
    promotion_proposal_result = app.PROFILE_PROMOTION.propose({"workspace_id": authored_workspace_id})
    if not promotion_proposal_result.get("ok") or promotion_proposal_result.get("proposal", {}).get("status") != "ready_for_manual_review":
        fail(f"profile promotion proposal failed: {promotion_proposal_result}")
    promotion_proposal = promotion_proposal_result.get("proposal", {})
    promotion_proposal_id = promotion_proposal.get("proposal_id")
    if promotion_proposal.get("mapper_contract_patch_preview", {}).get("mutates_config") is not False:
        fail("profile promotion proposal must not mutate profile mapper config")
    for output_path in promotion_proposal.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"profile promotion output missing: {output_path}")
    promotion_detail = app.PROFILE_PROMOTION.detail(promotion_proposal_id)
    if promotion_detail.get("proposal_id") != promotion_proposal_id or promotion_detail.get("profile_id") != "cycling_micromobility_access":
        fail(f"profile promotion proposal detail failed: {promotion_detail}")
    promotion_list = app.PROFILE_PROMOTION.list_proposals(20)
    if not any(row.get("proposal_id") == promotion_proposal_id for row in promotion_list):
        fail("profile promotion proposal should appear in proposal list")
    promotion_queue = app.PROFILE_PROMOTION.review_queue(20)
    queued = next((row for row in promotion_queue if row.get("proposal_id") == promotion_proposal_id), {})
    if queued.get("decision_status") != "pending_review" or queued.get("mutates_config") is not False:
        fail(f"profile promotion review queue failed: {queued}")
    contract_diff_candidates = app.PROFILE_PROMOTION.contract_diff_candidates(20)
    contract_diff_candidate = next((row for row in contract_diff_candidates if row.get("proposal_id") == promotion_proposal_id), {})
    if contract_diff_candidate.get("proposal_id") != promotion_proposal_id or contract_diff_candidate.get("mutates_config") is not False:
        fail(f"profile contract diff candidate failed: {contract_diff_candidate}")
    contract_diff_result = app.PROFILE_PROMOTION.create_contract_diff({"proposal_id": promotion_proposal_id})
    if not contract_diff_result.get("ok") or contract_diff_result.get("contract_diff", {}).get("diff_status") != "ready_for_manual_review":
        fail(f"profile contract diff failed: {contract_diff_result}")
    contract_diff = contract_diff_result.get("contract_diff", {})
    profile_contract_diff_id = contract_diff.get("diff_id")
    if contract_diff.get("mutates_config") is not False or contract_diff.get("source_gis_modified") is not False:
        fail("profile contract diff must not mutate config or source GIS")
    summary = contract_diff.get("summary", {})
    if summary.get("field_count", 0) < 1 or "field_groups" not in summary:
        fail(f"profile contract diff summary failed: {summary}")
    if summary.get("added_count", 0) + summary.get("changed_count", 0) + summary.get("removed_count", 0) < 1:
        fail("profile contract diff should expose at least one reviewable field change")
    for output_path in contract_diff.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"profile contract diff output missing: {output_path}")
    contract_diff_detail = app.PROFILE_PROMOTION.contract_diff_detail(profile_contract_diff_id)
    if contract_diff_detail.get("diff_id") != profile_contract_diff_id:
        fail(f"profile contract diff detail failed: {contract_diff_detail}")
    contract_diff_list = app.PROFILE_PROMOTION.list_contract_diffs(20)
    if not any(row.get("diff_id") == profile_contract_diff_id for row in contract_diff_list):
        fail("profile contract diff should appear in diff list")
    invalid_decision = app.PROFILE_PROMOTION.decide(promotion_proposal_id, {"decision": "maybe"})
    if invalid_decision.get("error") != "profile_acceptance_decision_invalid":
        fail(f"profile promotion invalid decision failed: {invalid_decision}")
    acceptance_result = app.PROFILE_PROMOTION.decide(promotion_proposal_id, {
        "decision": "approve",
        "reviewer": "validation_reviewer",
        "notes": "Approved for later manual implementation planning.",
    })
    if not acceptance_result.get("ok") or acceptance_result.get("decision", {}).get("decision_status") != "approved":
        fail(f"profile promotion acceptance failed: {acceptance_result}")
    acceptance_decision = acceptance_result.get("decision", {})
    acceptance_decision_id = acceptance_decision.get("decision_id")
    if acceptance_decision.get("mutates_config") is not False or acceptance_decision.get("source_gis_modified") is not False:
        fail("profile promotion acceptance must not mutate config or source GIS")
    for output_path in acceptance_decision.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"profile promotion acceptance output missing: {output_path}")
    latest_decision = app.PROFILE_PROMOTION.latest_decision(promotion_proposal_id)
    if latest_decision.get("decision_id") != acceptance_decision_id or latest_decision.get("decision_status") != "approved":
        fail(f"profile promotion latest decision failed: {latest_decision}")
    decision_list = app.PROFILE_PROMOTION.list_decisions(20)
    if not any(row.get("decision_id") == acceptance_decision_id for row in decision_list):
        fail("profile promotion decision should appear in decision list")
    application_candidates = app.PROFILE_PROMOTION.application_candidates(20)
    application_candidate = next((row for row in application_candidates if row.get("proposal_id") == promotion_proposal_id), {})
    if application_candidate.get("decision_status") != "approved" or application_candidate.get("mutates_config") is not False:
        fail(f"profile application candidate failed: {application_candidate}")
    application_plan_result = app.PROFILE_PROMOTION.create_application_plan({
        "proposal_id": promotion_proposal_id,
        "decision_id": acceptance_decision_id,
    })
    if not application_plan_result.get("ok") or application_plan_result.get("application_plan", {}).get("plan_status") != "ready_for_manual_implementation":
        fail(f"profile application plan failed: {application_plan_result}")
    application_plan = application_plan_result.get("application_plan", {})
    application_plan_id = application_plan.get("plan_id")
    if application_plan.get("mutates_config") is not False or application_plan.get("source_gis_modified") is not False:
        fail("profile application plan must not mutate config or source GIS")
    if application_plan.get("config_patch_preview", {}).get("mutates_config") is not False:
        fail("profile application patch preview must be planning-only")
    if application_plan.get("field_change_count", 0) < 1:
        fail("profile application plan should expose at least one contract field change")
    for output_path in application_plan.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"profile application plan output missing: {output_path}")
    application_plan_detail = app.PROFILE_PROMOTION.application_plan_detail(application_plan_id)
    if application_plan_detail.get("plan_id") != application_plan_id:
        fail(f"profile application plan detail failed: {application_plan_detail}")
    application_plan_list = app.PROFILE_PROMOTION.list_application_plans(20)
    if not any(row.get("plan_id") == application_plan_id for row in application_plan_list):
        fail("profile application plan should appear in plan list")

    config_apply_candidates = app.PROFILE_PROMOTION.config_apply_candidates(20)
    config_apply_candidate = next((row for row in config_apply_candidates if row.get("proposal_id") == promotion_proposal_id), {})
    if config_apply_candidate.get("application_plan_id") != application_plan_id or config_apply_candidate.get("mutates_config") is not False:
        fail(f"profile config apply candidate failed: {config_apply_candidate}")
    config_apply_result = app.PROFILE_PROMOTION.create_config_apply_proposal({
        "application_plan_id": application_plan_id,
        "proposal_id": promotion_proposal_id,
    })
    if not config_apply_result.get("ok") or config_apply_result.get("config_apply_proposal", {}).get("apply_status") != "ready_for_explicit_approval":
        fail(f"profile config apply proposal failed: {config_apply_result}")
    config_apply_proposal = config_apply_result.get("config_apply_proposal", {})
    profile_config_apply_proposal_id = config_apply_proposal.get("apply_id")
    if config_apply_proposal.get("mutates_config") is not False or config_apply_proposal.get("source_gis_modified") is not False:
        fail("profile config apply proposal must not mutate config or source GIS")
    if config_apply_proposal.get("proposed_config_preview_mutates_config") is not False:
        fail("profile config apply preview must be non-mutating")
    if len(str(config_apply_proposal.get("current_config_sha256") or "")) != 64 or len(str(config_apply_proposal.get("proposed_config_sha256") or "")) != 64:
        fail("profile config apply proposal should record current and proposed config hashes")
    for output_path in config_apply_proposal.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"profile config apply proposal output missing: {output_path}")
    config_apply_detail = app.PROFILE_PROMOTION.config_apply_proposal_detail(profile_config_apply_proposal_id)
    if config_apply_detail.get("apply_id") != profile_config_apply_proposal_id:
        fail(f"profile config apply proposal detail failed: {config_apply_detail}")
    config_apply_list = app.PROFILE_PROMOTION.list_config_apply_proposals(20)
    if not any(row.get("apply_id") == profile_config_apply_proposal_id for row in config_apply_list):
        fail("profile config apply proposal should appear in proposal list")
    regression_candidates = app.PROFILE_PROMOTION.contract_regression_candidates(20)
    regression_candidate = next((row for row in regression_candidates if row.get("apply_id") == profile_config_apply_proposal_id), {})
    if regression_candidate.get("regression_status") not in {"ready_for_regression_preview", "preview_created"} or regression_candidate.get("mutates_config") is not False:
        fail(f"profile contract regression candidate failed: {regression_candidate}")
    regression_result = app.PROFILE_PROMOTION.create_contract_regression_preview({
        "apply_id": profile_config_apply_proposal_id,
        "proposal_id": promotion_proposal_id,
    })
    if not regression_result.get("ok") or regression_result.get("regression_preview", {}).get("regression_status") != "passed":
        fail(f"profile contract regression preview failed: {regression_result}")
    regression_preview = regression_result.get("regression_preview", {})
    profile_contract_regression_preview_id = regression_preview.get("preview_id")
    if regression_preview.get("mutates_config") is not False or regression_preview.get("source_gis_modified") is not False:
        fail("profile contract regression preview must not mutate config or source GIS")
    if regression_preview.get("failed_check_count") != 0 or regression_preview.get("check_count", 0) < 8:
        fail(f"profile contract regression checks failed: {regression_preview}")
    for output_path in regression_preview.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"profile contract regression preview output missing: {output_path}")
    regression_detail = app.PROFILE_PROMOTION.contract_regression_preview_detail(profile_contract_regression_preview_id)
    if regression_detail.get("preview_id") != profile_contract_regression_preview_id:
        fail(f"profile contract regression preview detail failed: {regression_detail}")
    regression_list = app.PROFILE_PROMOTION.list_contract_regression_previews(20)
    if not any(row.get("preview_id") == profile_contract_regression_preview_id for row in regression_list):
        fail("profile contract regression preview should appear in preview list")
    execution_queue_status = app.EXECUTION_QUEUE.status()
    if not execution_queue_status.get("ok") or execution_queue_status.get("executable_profile_count") < 4:
        fail(f"execution queue status failed: {execution_queue_status}")
    execution_queue_job = app.EXECUTION_QUEUE.enqueue({
        "profile_id": "osm_tag_quality",
        "target_workspace_id": "osm_tag_quality_kfar_saba_v001",
        "execute_now": True,
    }, app.run_profile)
    if not execution_queue_job.get("ok") or execution_queue_job.get("status") != "succeeded":
        fail(f"execution queue job failed: {execution_queue_job}")
    if execution_queue_job.get("source_gis_modified") is not False:
        fail("execution queue should preserve source read-only evidence")
    if execution_queue_job.get("runner_result", {}).get("workspace_id") != "osm_tag_quality_kfar_saba_v001":
        fail("execution queue should execute the OSM tag quality runner")
    if not any(row.get("job_id") == execution_queue_job.get("job_id") for row in app.EXECUTION_QUEUE.list_jobs(10)):
        fail("execution queue job should appear in list")
    execution_queue_detail = app.EXECUTION_QUEUE.detail(execution_queue_job.get("job_id"))
    if execution_queue_detail.get("job_id") != execution_queue_job.get("job_id"):
        fail("execution queue job detail failed")
    blocked_execution_job = app.EXECUTION_QUEUE.enqueue({"profile_id": "cycling_micromobility_access"}, app.run_profile)
    if blocked_execution_job.get("error") != "execution_queue_profile_blocked" or blocked_execution_job.get("status") != "blocked":
        fail("execution queue should block non-executable cycling profile")
    missing_execution_job = app.EXECUTION_QUEUE.detail("missing_job")
    if missing_execution_job.get("error") != "execution_queue_job_not_found":
        fail("missing execution queue job should return execution_queue_job_not_found")
    authored_queue_job = app.EXECUTION_QUEUE.enqueue_authored_draft({
        "draft_id": template_draft.get("draft_id"),
        "workspace_id": "authored_profile_queue_cycling_micromobility_access_v001",
        "execute_now": True,
    }, app.TEMPLATE_AUTHORING, app.run_authored_profile)
    if authored_queue_job.get("status") != "succeeded" or authored_queue_job.get("runner_result", {}).get("workspace_id") != "authored_profile_queue_cycling_micromobility_access_v001":
        fail(f"authored draft queue job failed: {authored_queue_job}")

    dataset_package_status = app.DATASET_PACKAGES.status()
    if not dataset_package_status.get("ok") or dataset_package_status.get("source_count") != 2:
        fail(f"dataset package status failed: {dataset_package_status}")
    dataset_package = app.DATASET_PACKAGES.create_with_runner({
        "dataset_id": "israel-and-palestine-260521-free-shp-zip",
        "template_id": "generic_osm_tag_coverage",
        "queue_profile_id": "osm_tag_quality",
        "target_workspace_id": "osm_tag_quality_kfar_saba_v001",
    }, app.run_profile)
    if not dataset_package.get("ok") or not Path(dataset_package.get("files", {}).get("manifest", "")).exists():
        fail(f"dataset package creation failed: {dataset_package}")
    if dataset_package.get("source_gis_modified") is not False:
        fail("dataset package should preserve source read-only evidence")
    if dataset_package.get("execution_queue_status") != "succeeded":
        fail("dataset package should include succeeded execution queue evidence")
    if not any(row.get("package_id") == dataset_package.get("package_id") for row in app.DATASET_PACKAGES.list_packages(10)):
        fail("dataset package should appear in list")
    dataset_package_detail = app.DATASET_PACKAGES.detail(dataset_package.get("package_id"))
    if dataset_package_detail.get("package_id") != dataset_package.get("package_id"):
        fail("dataset package detail failed")
    dataset_package_output = app.DATASET_PACKAGES.output_file(dataset_package.get("package_id"))
    if not dataset_package_output.get("ok") or not dataset_package_output.get("path", Path()).exists():
        fail("dataset package output resolver failed")
    missing_dataset_package = app.DATASET_PACKAGES.detail("missing_package")
    if missing_dataset_package.get("error") != "dataset_package_not_found":
        fail("missing dataset package should return dataset_package_not_found")


    local_intake_status = app.LOCAL_INTAKE.status()
    if local_intake_status.get("source_count") != 2 or local_intake_status.get("source_gis_modified") is not False:
        fail(f"local intake status failed: {local_intake_status}")
    local_intake_sources = app.LOCAL_INTAKE.sources()
    if local_intake_sources.get("source_count") != 2:
        fail("local intake should expose two registered sources")
    local_intake_preview = app.LOCAL_INTAKE.preview({"dataset_id": "israel-and-palestine-260521-free-shp-zip"})
    if not local_intake_preview.get("ok") or local_intake_preview.get("source", {}).get("readiness_level") != "ready_for_safe_access_selected_pilot":
        fail(f"local intake dataset preview failed: {local_intake_preview}")
    local_intake_path_preview = app.LOCAL_INTAKE.preview({"path": str(ROOT / "israel-and-palestine-260521-free.shp.zip")})
    if not local_intake_path_preview.get("ok") or local_intake_path_preview.get("input_type") != "registered_file":
        fail(f"local intake path preview failed: {local_intake_path_preview}")
    blocked_intake = app.LOCAL_INTAKE.preview({"path": str(ROOT / "analysis_output")})
    if blocked_intake.get("error") != "local_intake_analysis_output_not_allowed":
        fail("local intake should reject generated analysis_output paths")
    local_intake_plan = app.LOCAL_INTAKE.create_plan({"dataset_id": "israel-and-palestine-260521-free-shp-zip"})
    if not local_intake_plan.get("ok") or not Path(local_intake_plan.get("plan_file", "")).exists():
        fail(f"local intake plan creation failed: {local_intake_plan}")
    if local_intake_plan.get("source_gis_modified") is not False:
        fail("local intake plan should preserve source read-only evidence")


    source_import_status = app.SOURCE_IMPORT_GUARDRAILS.status()
    if not source_import_status.get("ok") or source_import_status.get("source_import_guardrails_version") != "source_import_guardrails_v001":
        fail(f"source import guardrails status failed: {source_import_status}")
    if int(source_import_status.get("guardrail_count") or 0) < 8 or int(source_import_status.get("reviewable_source_count") or 0) < 1:
        fail("source import guardrails should expose reviewable sources and guardrails")
    source_import_preview = app.SOURCE_IMPORT_GUARDRAILS.preview({"dataset_id": "israel-and-palestine-260521-free-shp-zip", "template_id": "safe_access"})
    if not source_import_preview.get("ok") or source_import_preview.get("import_readiness") != "ready_for_manual_review":
        fail(f"source import guardrail preview failed: {source_import_preview}")
    if int(source_import_preview.get("summary", {}).get("hard_failed_count") or 0) != 0:
        fail("source import guardrail preview should have no hard failures for the Geofabrik ZIP")
    source_import_request_result = app.SOURCE_IMPORT_GUARDRAILS.create_request({
        "dataset_id": "israel-and-palestine-260521-free-shp-zip",
        "template_id": "safe_access",
        "created_by": "validate_app",
        "notes": "Validation-created v053 source import review packet.",
    })
    if not source_import_request_result.get("ok") or not source_import_request_result.get("request", {}).get("request_id"):
        fail(f"source import request creation failed: {source_import_request_result}")
    source_import_request = source_import_request_result.get("request", {})
    source_import_request_id = source_import_request.get("request_id")
    source_import_md = Path(str(source_import_request.get("files", {}).get("markdown") or ""))
    if not source_import_md.exists() or source_import_md.stat().st_size < 1000 or "Source Import Guardrails Review" not in source_import_md.read_text(encoding="utf-8"):
        fail("source import guardrail Markdown review packet is missing or incomplete")
    source_import_detail = app.SOURCE_IMPORT_GUARDRAILS.detail(source_import_request_id)
    if source_import_detail.get("request_id") != source_import_request_id:
        fail("source import guardrail detail failed")
    source_import_list = app.SOURCE_IMPORT_GUARDRAILS.list_requests(10)
    if not any(row.get("request_id") == source_import_request_id for row in source_import_list):
        fail("source import request should appear in request list")
    source_import_output = app.SOURCE_IMPORT_GUARDRAILS.output_file(source_import_request_id)
    if not source_import_output.get("ok") or not Path(source_import_output.get("path", "")).exists():
        fail("source import guardrail output resolver failed")
    invalid_source_import_decision = app.SOURCE_IMPORT_GUARDRAILS.decide(source_import_request_id, {"decision": "approve"})
    if invalid_source_import_decision.get("error") != "source_import_decision_invalid":
        fail("source import approval should require explicit acknowledgements")
    source_import_decision_result = app.SOURCE_IMPORT_GUARDRAILS.decide(source_import_request_id, {
        "decision": "approve",
        "reviewer": "validate_app",
        "approval_phrase": "approve metadata-only import",
        "source_files_read_only_ack": True,
        "generated_outputs_only_ack": True,
        "no_browser_upload_ack": True,
        "claim_boundary_ack": True,
        "notes": "Validation approval for metadata-only source import handoff.",
    })
    if not source_import_decision_result.get("ok") or source_import_decision_result.get("decision", {}).get("decision_state") != "approved_for_metadata_only_import":
        fail(f"source import approval decision failed: {source_import_decision_result}")
    source_import_decision_id = source_import_decision_result.get("decision", {}).get("decision_id")
    missing_source_import = app.SOURCE_IMPORT_GUARDRAILS.detail("missing_source_import_request")
    if missing_source_import.get("error") != "source_import_request_not_found":
        fail("missing source import request should return source_import_request_not_found")

    source_handoff_status = app.SOURCE_HANDOFF.status()
    if not source_handoff_status.get("ok") or source_handoff_status.get("source_handoff_version") != "source_handoff_v001":
        fail(f"source handoff status failed: {source_handoff_status}")
    source_handoff_candidates = app.SOURCE_HANDOFF.candidates(10)
    if not any(row.get("request_id") == source_import_request_id for row in source_handoff_candidates):
        fail("source handoff candidates should include the approved source import request")
    source_handoff_result = app.SOURCE_HANDOFF.create_handoff({
        "request_id": source_import_request_id,
        "profile_id": "safe_access_pedestrian_review",
        "pilot_osm_id": "53796999",
        "target_workspace_id": "safe_access_kfar_saba_pbf_enriched_v001",
        "created_by": "validate_app",
    })
    if not source_handoff_result.get("ok") or not source_handoff_result.get("handoff", {}).get("handoff_id"):
        fail(f"source handoff creation failed: {source_handoff_result}")
    source_handoff = source_handoff_result.get("handoff", {})
    source_handoff_id = source_handoff.get("handoff_id")
    if source_handoff.get("handoff_readiness") != "ready_for_controlled_execution" or source_handoff.get("queue_status") != "planned":
        fail(f"source handoff should create ready planned queue evidence: {source_handoff}")
    if not source_handoff.get("mapper_plan_id") or not source_handoff.get("contract_dry_run_id") or not source_handoff.get("queue_job_id"):
        fail("source handoff should link mapper plan, dry-run and queue job ids")
    source_handoff_md = Path(str(source_handoff.get("files", {}).get("markdown") or ""))
    if not source_handoff_md.exists() or source_handoff_md.stat().st_size < 1000 or "Source Handoff" not in source_handoff_md.read_text(encoding="utf-8"):
        fail("source handoff Markdown artifact is missing or incomplete")
    source_handoff_detail = app.SOURCE_HANDOFF.detail(source_handoff_id)
    if source_handoff_detail.get("handoff_id") != source_handoff_id:
        fail("source handoff detail failed")
    source_handoff_list = app.SOURCE_HANDOFF.list_handoffs(10)
    if not any(row.get("handoff_id") == source_handoff_id for row in source_handoff_list):
        fail("source handoff should appear in handoff list")
    source_handoff_output = app.SOURCE_HANDOFF.output_file(source_handoff_id)
    if not source_handoff_output.get("ok") or not Path(source_handoff_output.get("path", "")).exists():
        fail("source handoff output resolver failed")
    missing_source_handoff = app.SOURCE_HANDOFF.detail("missing_source_handoff")
    if missing_source_handoff.get("error") != "source_handoff_not_found":
        fail("missing source handoff should return source_handoff_not_found")

    source_handoff_execution_status = app.SOURCE_HANDOFF_EXECUTION.status()
    if not source_handoff_execution_status.get("ok") or source_handoff_execution_status.get("source_handoff_execution_version") != "source_handoff_execution_v001":
        fail(f"source handoff execution status failed: {source_handoff_execution_status}")
    invalid_execution = app.SOURCE_HANDOFF_EXECUTION.execute_handoff({"handoff_id": source_handoff_id}, app.run_profile)
    if invalid_execution.get("error") != "source_handoff_execution_ack_missing":
        fail("source handoff execution should require explicit acknowledgements")
    source_handoff_execution_candidates = app.SOURCE_HANDOFF_EXECUTION.candidates(10)
    if not any(row.get("handoff_id") == source_handoff_id for row in source_handoff_execution_candidates):
        fail("source handoff execution candidates should include the ready handoff")
    source_handoff_execution_result = app.SOURCE_HANDOFF_EXECUTION.execute_handoff({
        "handoff_id": source_handoff_id,
        "execution_ack": "execute approved handoff",
        "source_files_read_only_ack": True,
        "generated_outputs_only_ack": True,
        "claim_boundary_ack": True,
        "compare_outputs_ack": True,
        "route_aware": False,
        "created_by": "validate_app",
    }, app.run_profile)
    if not source_handoff_execution_result.get("ok") or not source_handoff_execution_result.get("execution", {}).get("execution_id"):
        fail(f"source handoff execution failed: {source_handoff_execution_result}")
    source_handoff_execution = source_handoff_execution_result.get("execution", {})
    source_handoff_execution_id = source_handoff_execution.get("execution_id")
    if source_handoff_execution.get("execution_readiness") != "executed_and_verified" or source_handoff_execution.get("execution_status") != "succeeded":
        fail(f"source handoff execution should be verified after queue success: {source_handoff_execution}")
    comparison = source_handoff_execution.get("comparison", {})
    if comparison.get("comparison_readiness") != "outputs_match_handoff_evidence" or comparison.get("missing_outputs"):
        fail(f"source handoff execution comparison failed: {comparison}")
    source_handoff_execution_md = Path(str(source_handoff_execution.get("files", {}).get("markdown") or ""))
    if not source_handoff_execution_md.exists() or source_handoff_execution_md.stat().st_size < 1000 or "Source Handoff Execution" not in source_handoff_execution_md.read_text(encoding="utf-8"):
        fail("source handoff execution Markdown artifact is missing or incomplete")
    source_handoff_execution_detail = app.SOURCE_HANDOFF_EXECUTION.detail(source_handoff_execution_id)
    if source_handoff_execution_detail.get("execution_id") != source_handoff_execution_id:
        fail("source handoff execution detail failed")
    source_handoff_execution_list = app.SOURCE_HANDOFF_EXECUTION.list_executions(10)
    if not any(row.get("execution_id") == source_handoff_execution_id for row in source_handoff_execution_list):
        fail("source handoff execution should appear in execution list")
    source_handoff_execution_output = app.SOURCE_HANDOFF_EXECUTION.output_file(source_handoff_execution_id)
    if not source_handoff_execution_output.get("ok") or not Path(source_handoff_execution_output.get("path", "")).exists():
        fail("source handoff execution output resolver failed")
    missing_source_handoff_execution = app.SOURCE_HANDOFF_EXECUTION.detail("missing_source_handoff_execution")
    if missing_source_handoff_execution.get("error") != "source_handoff_execution_not_found":
        fail("missing source handoff execution should return source_handoff_execution_not_found")

    execution_package_status = app.EXECUTION_EVIDENCE_PACKAGE.status()
    if not execution_package_status.get("ok") or execution_package_status.get("execution_evidence_package_version") != "execution_evidence_package_v001":
        fail(f"execution evidence package status failed: {execution_package_status}")
    execution_package_candidates = app.EXECUTION_EVIDENCE_PACKAGE.candidates(10)
    if not any(row.get("execution_id") == source_handoff_execution_id for row in execution_package_candidates):
        fail("execution evidence package candidates should include the verified handoff execution")
    execution_package_result = app.EXECUTION_EVIDENCE_PACKAGE.create_package({
        "execution_id": source_handoff_execution_id,
        "created_by": "validate_app",
        "notes": "Validation-created v054 execution evidence package.",
    })
    if not execution_package_result.get("ok") or not execution_package_result.get("package", {}).get("package_id"):
        fail(f"execution evidence package creation failed: {execution_package_result}")
    execution_package = execution_package_result.get("package", {})
    execution_evidence_package_id = execution_package.get("package_id")
    if execution_package.get("package_readiness") != "ready_for_reviewer":
        fail(f"execution evidence package should be ready for reviewer: {execution_package}")
    execution_package_md = Path(str(execution_package.get("files", {}).get("markdown") or ""))
    if not execution_package_md.exists() or execution_package_md.stat().st_size < 1000 or "Execution Evidence Package" not in execution_package_md.read_text(encoding="utf-8"):
        fail("execution evidence package Markdown artifact is missing or incomplete")
    execution_package_detail = app.EXECUTION_EVIDENCE_PACKAGE.detail(execution_evidence_package_id)
    if execution_package_detail.get("package_id") != execution_evidence_package_id:
        fail("execution evidence package detail failed")
    execution_package_list = app.EXECUTION_EVIDENCE_PACKAGE.list_packages(10)
    if not any(row.get("package_id") == execution_evidence_package_id for row in execution_package_list):
        fail("execution evidence package should appear in package list")
    execution_package_output = app.EXECUTION_EVIDENCE_PACKAGE.output_file(execution_evidence_package_id)
    if not execution_package_output.get("ok") or not Path(execution_package_output.get("path", "")).exists():
        fail("execution evidence package output resolver failed")
    missing_execution_package = app.EXECUTION_EVIDENCE_PACKAGE.detail("missing_execution_evidence_package")
    if missing_execution_package.get("error") != "execution_evidence_package_not_found":
        fail("missing execution evidence package should return execution_evidence_package_not_found")

    time.sleep(1.1)
    second_execution_package_result = app.EXECUTION_EVIDENCE_PACKAGE.create_package({
        "execution_id": source_handoff_execution_id,
        "created_by": "validate_app",
        "notes": "Validation-created v055 second execution evidence package for diffing.",
    })
    if not second_execution_package_result.get("ok") or not second_execution_package_result.get("package", {}).get("package_id"):
        fail(f"second execution evidence package creation failed: {second_execution_package_result}")
    second_execution_package = second_execution_package_result.get("package", {})
    second_execution_evidence_package_id = second_execution_package.get("package_id")

    execution_result_diff_status = app.EXECUTION_RESULT_DIFF.status()
    if not execution_result_diff_status.get("ok") or execution_result_diff_status.get("execution_result_diff_version") != "execution_result_diff_v001":
        fail(f"execution result diff status failed: {execution_result_diff_status}")
    execution_result_diff_candidates = app.EXECUTION_RESULT_DIFF.candidates(10)
    if not execution_result_diff_candidates:
        fail("execution result diff candidates should include ready package pairs")
    execution_result_diff_result = app.EXECUTION_RESULT_DIFF.create_diff({
        "left_package_id": execution_evidence_package_id,
        "right_package_id": second_execution_evidence_package_id,
        "created_by": "validate_app",
        "notes": "Validation-created v055 execution result diff.",
    })
    if not execution_result_diff_result.get("ok") or not execution_result_diff_result.get("diff", {}).get("diff_id"):
        fail(f"execution result diff creation failed: {execution_result_diff_result}")
    execution_result_diff = execution_result_diff_result.get("diff", {})
    execution_result_diff_id = execution_result_diff.get("diff_id")
    if execution_result_diff.get("diff_readiness") != "ready_for_reviewer":
        fail(f"execution result diff should be ready for reviewer: {execution_result_diff}")
    execution_result_diff_md = Path(str(execution_result_diff.get("files", {}).get("markdown") or ""))
    if not execution_result_diff_md.exists() or execution_result_diff_md.stat().st_size < 1000 or "Execution Result Diff" not in execution_result_diff_md.read_text(encoding="utf-8"):
        fail("execution result diff Markdown artifact is missing or incomplete")
    execution_result_diff_detail = app.EXECUTION_RESULT_DIFF.detail(execution_result_diff_id)
    if execution_result_diff_detail.get("diff_id") != execution_result_diff_id:
        fail("execution result diff detail failed")
    execution_result_diff_list = app.EXECUTION_RESULT_DIFF.list_diffs(10)
    if not any(row.get("diff_id") == execution_result_diff_id for row in execution_result_diff_list):
        fail("execution result diff should appear in diff list")
    execution_result_diff_output = app.EXECUTION_RESULT_DIFF.output_file(execution_result_diff_id)
    if not execution_result_diff_output.get("ok") or not Path(execution_result_diff_output.get("path", "")).exists():
        fail("execution result diff output resolver failed")
    missing_execution_result_diff = app.EXECUTION_RESULT_DIFF.detail("missing_execution_result_diff")
    if missing_execution_result_diff.get("error") != "execution_result_diff_not_found":
        fail("missing execution result diff should return execution_result_diff_not_found")

    execution_diff_gallery_status = app.EXECUTION_DIFF_GALLERY.status()
    if not execution_diff_gallery_status.get("ok") or execution_diff_gallery_status.get("execution_diff_gallery_version") != "execution_diff_gallery_v001":
        fail(f"execution diff gallery status failed: {execution_diff_gallery_status}")
    if execution_diff_gallery_status.get("indexed_diff_count", 0) < 1:
        fail("execution diff gallery should index at least one execution result diff")
    execution_diff_gallery_items = app.EXECUTION_DIFF_GALLERY.items(limit=10)
    if not any(row.get("diff_id") == execution_result_diff_id for row in execution_diff_gallery_items):
        fail("execution diff gallery items should include the validation-created diff")
    execution_diff_gallery_result = app.EXECUTION_DIFF_GALLERY.create_gallery({
        "created_by": "validate_app",
        "notes": "Validation-created v056 execution diff gallery.",
        "limit": 50,
    })
    if not execution_diff_gallery_result.get("ok") or not execution_diff_gallery_result.get("gallery", {}).get("gallery_id"):
        fail(f"execution diff gallery creation failed: {execution_diff_gallery_result}")
    execution_diff_gallery = execution_diff_gallery_result.get("gallery", {})
    execution_diff_gallery_id = execution_diff_gallery.get("gallery_id")
    if execution_diff_gallery.get("gallery_readiness") != "ready_for_reviewer":
        fail(f"execution diff gallery should be ready for reviewer: {execution_diff_gallery}")
    execution_diff_gallery_md = Path(str(execution_diff_gallery.get("files", {}).get("markdown") or ""))
    if not execution_diff_gallery_md.exists() or execution_diff_gallery_md.stat().st_size < 1000 or "Execution Diff Gallery" not in execution_diff_gallery_md.read_text(encoding="utf-8"):
        fail("execution diff gallery Markdown artifact is missing or incomplete")
    execution_diff_gallery_detail = app.EXECUTION_DIFF_GALLERY.detail(execution_diff_gallery_id)
    if execution_diff_gallery_detail.get("gallery_id") != execution_diff_gallery_id:
        fail("execution diff gallery detail failed")
    execution_diff_gallery_list = app.EXECUTION_DIFF_GALLERY.list_galleries(10)
    if not any(row.get("gallery_id") == execution_diff_gallery_id for row in execution_diff_gallery_list):
        fail("execution diff gallery should appear in gallery list")
    execution_diff_gallery_output = app.EXECUTION_DIFF_GALLERY.output_file(execution_diff_gallery_id)
    if not execution_diff_gallery_output.get("ok") or not Path(execution_diff_gallery_output.get("path", "")).exists():
        fail("execution diff gallery output resolver failed")
    missing_execution_diff_gallery = app.EXECUTION_DIFF_GALLERY.detail("missing_execution_diff_gallery")
    if missing_execution_diff_gallery.get("error") != "execution_diff_gallery_not_found":
        fail("missing execution diff gallery should return execution_diff_gallery_not_found")

    execution_diff_detail_status = app.EXECUTION_DIFF_DETAIL.status()
    if not execution_diff_detail_status.get("ok") or execution_diff_detail_status.get("execution_diff_detail_version") != "execution_diff_detail_v001":
        fail(f"execution diff detail status failed: {execution_diff_detail_status}")
    execution_diff_baselines = app.EXECUTION_DIFF_DETAIL.baselines(10)
    if not execution_diff_baselines or not any(row.get("diff_id") == execution_result_diff_id for row in execution_diff_baselines):
        fail("execution diff detail baselines should include the validation-created diff")
    execution_diff_inspect = app.EXECUTION_DIFF_DETAIL.inspect_diff(execution_result_diff_id, execution_diff_baselines[0].get("diff_id"))
    if not execution_diff_inspect.get("ok") or not execution_diff_inspect.get("drilldown", {}).get("table_breakdown"):
        fail(f"execution diff detail inspect failed: {execution_diff_inspect}")
    execution_diff_detail_result = app.EXECUTION_DIFF_DETAIL.create_drilldown({
        "diff_id": execution_result_diff_id,
        "baseline_diff_id": execution_diff_baselines[0].get("diff_id"),
        "created_by": "validate_app",
        "notes": "Validation-created v062 execution diff detail drilldown.",
    })
    if not execution_diff_detail_result.get("ok") or not execution_diff_detail_result.get("detail", {}).get("detail_id"):
        fail(f"execution diff detail creation failed: {execution_diff_detail_result}")
    execution_diff_detail = execution_diff_detail_result.get("detail", {})
    execution_diff_detail_id = execution_diff_detail.get("detail_id")
    if execution_diff_detail.get("drilldown_readiness") != "ready_for_reviewer":
        fail(f"execution diff detail should be ready for reviewer: {execution_diff_detail}")
    execution_diff_detail_md = Path(str(execution_diff_detail.get("files", {}).get("markdown") or ""))
    if not execution_diff_detail_md.exists() or execution_diff_detail_md.stat().st_size < 1000 or "Execution Diff Detail Drilldown" not in execution_diff_detail_md.read_text(encoding="utf-8"):
        fail("execution diff detail Markdown artifact is missing or incomplete")
    execution_diff_detail_detail = app.EXECUTION_DIFF_DETAIL.detail(execution_diff_detail_id)
    if execution_diff_detail_detail.get("detail_id") != execution_diff_detail_id:
        fail("execution diff detail detail failed")
    execution_diff_detail_list = app.EXECUTION_DIFF_DETAIL.list_drilldowns(10)
    if not any(row.get("detail_id") == execution_diff_detail_id for row in execution_diff_detail_list):
        fail("execution diff detail should appear in drilldown list")
    execution_diff_detail_output = app.EXECUTION_DIFF_DETAIL.output_file(execution_diff_detail_id)
    if not execution_diff_detail_output.get("ok") or not Path(execution_diff_detail_output.get("path", "")).exists():
        fail("execution diff detail output resolver failed")
    missing_execution_diff_detail = app.EXECUTION_DIFF_DETAIL.detail("missing_execution_diff_detail")
    if missing_execution_diff_detail.get("error") != "execution_diff_detail_not_found":
        fail("missing execution diff detail should return execution_diff_detail_not_found")

    reproducibility_packet_status = app.REPRODUCIBILITY_AUDIT_PACKET.status()
    if not reproducibility_packet_status.get("ok") or reproducibility_packet_status.get("reproducibility_audit_packet_version") != "reproducibility_audit_packet_v001":
        fail(f"reproducibility audit packet status failed: {reproducibility_packet_status}")
    reproducibility_packet_candidates = app.REPRODUCIBILITY_AUDIT_PACKET.candidates(10)
    if not reproducibility_packet_candidates or not any(row.get("detail_id") == execution_diff_detail_id for row in reproducibility_packet_candidates):
        fail("reproducibility audit packet candidates should include the validation-created drilldown")
    reproducibility_packet_result = app.REPRODUCIBILITY_AUDIT_PACKET.create_packet({
        "detail_id": execution_diff_detail_id,
        "created_by": "validate_app",
        "notes": "Validation-created v062 reproducibility audit packet.",
    })
    if not reproducibility_packet_result.get("ok") or not reproducibility_packet_result.get("packet", {}).get("packet_id"):
        fail(f"reproducibility audit packet creation failed: {reproducibility_packet_result}")
    reproducibility_packet = reproducibility_packet_result.get("packet", {})
    reproducibility_packet_id = reproducibility_packet.get("packet_id")
    if reproducibility_packet.get("packet_readiness") != "ready_for_reviewer":
        fail(f"reproducibility audit packet should be ready for reviewer: {reproducibility_packet}")
    reproducibility_packet_md = Path(str(reproducibility_packet.get("files", {}).get("markdown") or ""))
    if not reproducibility_packet_md.exists() or reproducibility_packet_md.stat().st_size < 1000 or "Reproducibility Audit Packet" not in reproducibility_packet_md.read_text(encoding="utf-8"):
        fail("reproducibility audit packet Markdown artifact is missing or incomplete")
    reproducibility_packet_detail = app.REPRODUCIBILITY_AUDIT_PACKET.detail(reproducibility_packet_id)
    if reproducibility_packet_detail.get("packet_id") != reproducibility_packet_id:
        fail("reproducibility audit packet detail failed")
    reproducibility_packet_list = app.REPRODUCIBILITY_AUDIT_PACKET.list_packets(10)
    if not any(row.get("packet_id") == reproducibility_packet_id for row in reproducibility_packet_list):
        fail("reproducibility audit packet should appear in packet list")
    reproducibility_packet_output = app.REPRODUCIBILITY_AUDIT_PACKET.output_file(reproducibility_packet_id)
    if not reproducibility_packet_output.get("ok") or not Path(reproducibility_packet_output.get("path", "")).exists():
        fail("reproducibility audit packet output resolver failed")
    missing_reproducibility_packet = app.REPRODUCIBILITY_AUDIT_PACKET.detail("missing_reproducibility_audit_packet")
    if missing_reproducibility_packet.get("error") != "reproducibility_audit_packet_not_found":
        fail("missing reproducibility audit packet should return reproducibility_audit_packet_not_found")

    reviewer_audit_index_status = app.REVIEWER_AUDIT_INDEX.status()
    if not reviewer_audit_index_status.get("ok") or reviewer_audit_index_status.get("reviewer_audit_index_version") != "reviewer_audit_index_v001":
        fail(f"reviewer audit index status failed: {reviewer_audit_index_status}")
    reviewer_audit_index_result = app.REVIEWER_AUDIT_INDEX.create_index({
        "created_by": "validate_app",
        "notes": "Validation-created v062 reviewer audit index.",
        "packet_limit": 25,
    })
    if not reviewer_audit_index_result.get("ok") or not reviewer_audit_index_result.get("index", {}).get("index_id"):
        fail(f"reviewer audit index creation failed: {reviewer_audit_index_result}")
    reviewer_audit_index = reviewer_audit_index_result.get("index", {})
    reviewer_audit_index_id = reviewer_audit_index.get("index_id")
    if reviewer_audit_index.get("index_readiness") != "ready_for_reviewer":
        fail(f"reviewer audit index should be ready for reviewer: {reviewer_audit_index}")
    reviewer_audit_index_md = Path(str(reviewer_audit_index.get("files", {}).get("markdown") or ""))
    if not reviewer_audit_index_md.exists() or reviewer_audit_index_md.stat().st_size < 1000 or "Reviewer Audit Index" not in reviewer_audit_index_md.read_text(encoding="utf-8"):
        fail("reviewer audit index Markdown artifact is missing or incomplete")
    reviewer_audit_index_detail = app.REVIEWER_AUDIT_INDEX.detail(reviewer_audit_index_id)
    if reviewer_audit_index_detail.get("index_id") != reviewer_audit_index_id:
        fail("reviewer audit index detail failed")
    reviewer_audit_index_list = app.REVIEWER_AUDIT_INDEX.list_indexes(10)
    if not any(row.get("index_id") == reviewer_audit_index_id for row in reviewer_audit_index_list):
        fail("reviewer audit index should appear in index list")
    reviewer_audit_index_output = app.REVIEWER_AUDIT_INDEX.output_file(reviewer_audit_index_id)
    if not reviewer_audit_index_output.get("ok") or not Path(reviewer_audit_index_output.get("path", "")).exists():
        fail("reviewer audit index output resolver failed")
    missing_reviewer_audit_index = app.REVIEWER_AUDIT_INDEX.detail("missing_reviewer_audit_index")
    if missing_reviewer_audit_index.get("error") != "reviewer_audit_index_not_found":
        fail("missing reviewer audit index should return reviewer_audit_index_not_found")

    portfolio_export_launcher_status = app.PORTFOLIO_EXPORT_LAUNCHER.status()
    if not portfolio_export_launcher_status.get("ok") or portfolio_export_launcher_status.get("portfolio_export_launcher_version") != "portfolio_export_launcher_v001":
        fail(f"portfolio export launcher status failed: {portfolio_export_launcher_status}")
    if portfolio_export_launcher_status.get("launch_target_count", 0) < 3:
        fail(f"portfolio export launcher should expose at least three launch targets: {portfolio_export_launcher_status}")
    portfolio_export_launcher_result = app.PORTFOLIO_EXPORT_LAUNCHER.create_launcher({
        "created_by": "validate_app",
        "notes": "Validation-created v062 portfolio export launcher.",
        "target_limit": 25,
    })
    if not portfolio_export_launcher_result.get("ok") or not portfolio_export_launcher_result.get("launcher", {}).get("launcher_id"):
        fail(f"portfolio export launcher creation failed: {portfolio_export_launcher_result}")
    portfolio_export_launcher = portfolio_export_launcher_result.get("launcher", {})
    portfolio_export_launcher_id = portfolio_export_launcher.get("launcher_id")
    if portfolio_export_launcher.get("launcher_readiness") != "ready_for_portfolio_launch":
        fail(f"portfolio export launcher should be ready: {portfolio_export_launcher}")
    portfolio_export_launcher_md = Path(str(portfolio_export_launcher.get("files", {}).get("markdown") or ""))
    if not portfolio_export_launcher_md.exists() or portfolio_export_launcher_md.stat().st_size < 1000 or "Portfolio Export Launcher" not in portfolio_export_launcher_md.read_text(encoding="utf-8"):
        fail("portfolio export launcher Markdown should exist and contain launcher title")
    portfolio_export_launcher_detail = app.PORTFOLIO_EXPORT_LAUNCHER.detail(portfolio_export_launcher_id)
    if portfolio_export_launcher_detail.get("launcher_id") != portfolio_export_launcher_id:
        fail("portfolio export launcher detail should resolve generated launcher")
    portfolio_export_launcher_list = app.PORTFOLIO_EXPORT_LAUNCHER.list_launchers(10)
    if not any(row.get("launcher_id") == portfolio_export_launcher_id for row in portfolio_export_launcher_list):
        fail("portfolio export launcher list should include generated launcher")
    portfolio_export_launcher_output = app.PORTFOLIO_EXPORT_LAUNCHER.output_file(portfolio_export_launcher_id)
    if not portfolio_export_launcher_output.get("ok") or not Path(portfolio_export_launcher_output.get("path", "")).exists():
        fail("portfolio export launcher output should resolve Markdown")
    missing_portfolio_export_launcher = app.PORTFOLIO_EXPORT_LAUNCHER.detail("missing_portfolio_export_launcher")
    if missing_portfolio_export_launcher.get("error") != "portfolio_export_launcher_not_found":
        fail("missing portfolio export launcher should return portfolio_export_launcher_not_found")

    portable_release_package_status = app.PORTABLE_RELEASE_PACKAGE.status()
    if not portable_release_package_status.get("ok") or portable_release_package_status.get("portable_release_package_version") != "portable_release_package_v001":
        fail(f"portable release package status failed: {portable_release_package_status}")
    if portable_release_package_status.get("ready_launcher_count", 0) < 1:
        fail(f"portable release package should see at least one ready launcher: {portable_release_package_status}")
    portable_release_package_result = app.PORTABLE_RELEASE_PACKAGE.create_package({
        "created_by": "validate_app",
        "notes": "Validation-created v062 portable release package.",
        "target_limit": 30,
    })
    if not portable_release_package_result.get("ok") or not portable_release_package_result.get("package", {}).get("package_id"):
        fail(f"portable release package creation failed: {portable_release_package_result}")
    portable_release_package = portable_release_package_result.get("package", {})
    portable_release_package_id = portable_release_package.get("package_id")
    if portable_release_package.get("package_readiness") != "ready_to_share_portable_release":
        fail(f"portable release package should be ready: {portable_release_package}")
    if portable_release_package.get("package_policy", {}).get("includes_source_gis") is not False:
        fail("portable release package must exclude source GIS files")
    portable_zip = Path(str(portable_release_package.get("files", {}).get("zip") or ""))
    if not portable_zip.exists() or portable_zip.stat().st_size < 1000:
        fail("portable release package ZIP should exist and be non-empty")
    with zipfile.ZipFile(portable_zip) as zf:
        names = set(zf.namelist())
        if "README.md" not in names or "package_manifest.json" not in names:
            fail(f"portable release package ZIP missing required files: {names}")
        if not any(name.startswith("evidence/portfolio_export_launcher/") for name in names):
            fail("portable release package ZIP should include launcher evidence")
        if any(name.lower().endswith((".shp", ".dbf", ".osm.pbf", ".gpkg")) for name in names):
            fail("portable release package ZIP should not include source GIS files")
    portable_release_package_detail = app.PORTABLE_RELEASE_PACKAGE.detail(portable_release_package_id)
    if portable_release_package_detail.get("package_id") != portable_release_package_id:
        fail("portable release package detail should resolve generated package")
    portable_release_package_list = app.PORTABLE_RELEASE_PACKAGE.list_packages(10)
    if not any(row.get("package_id") == portable_release_package_id for row in portable_release_package_list):
        fail("portable release package list should include generated package")
    portable_release_package_output = app.PORTABLE_RELEASE_PACKAGE.output_file(portable_release_package_id)
    if not portable_release_package_output.get("ok") or not Path(portable_release_package_output.get("path", "")).exists():
        fail("portable release package output should resolve ZIP")
    missing_portable_release_package = app.PORTABLE_RELEASE_PACKAGE.detail("missing_portable_release_package")
    if missing_portable_release_package.get("error") != "portable_release_package_not_found":
        fail("missing portable release package should return portable_release_package_not_found")

    demo_script_pack_status = app.DEMO_SCRIPT_PACK.status()
    if not demo_script_pack_status.get("ok") or demo_script_pack_status.get("demo_script_pack_version") != "demo_script_pack_v001":
        fail(f"demo script pack status failed: {demo_script_pack_status}")
    if demo_script_pack_status.get("screenshot_target_count", 0) < 6 or demo_script_pack_status.get("script_step_count", 0) < 6:
        fail(f"demo script pack should expose script steps and screenshot targets: {demo_script_pack_status}")
    demo_script_pack_result = app.DEMO_SCRIPT_PACK.create_pack({
        "created_by": "validate_app",
        "notes": "Validation-created v071 final launch checklist.",
    })
    if not demo_script_pack_result.get("ok") or not demo_script_pack_result.get("pack", {}).get("pack_id"):
        fail(f"demo script pack creation failed: {demo_script_pack_result}")
    demo_script_pack = demo_script_pack_result.get("pack", {})
    demo_script_pack_id = demo_script_pack.get("pack_id")
    if demo_script_pack.get("pack_readiness") != "ready_for_demo_walkthrough":
        fail(f"demo script pack should be ready: {demo_script_pack}")
    demo_script_md = Path(str(demo_script_pack.get("files", {}).get("demo_script") or ""))
    smoke_plan_md = Path(str(demo_script_pack.get("files", {}).get("screenshot_smoke_plan") or ""))
    contact_sheet_html = Path(str(demo_script_pack.get("files", {}).get("contact_sheet") or ""))
    if not demo_script_md.exists() or demo_script_md.stat().st_size < 1000 or "Demo Script Pack" not in demo_script_md.read_text(encoding="utf-8"):
        fail("demo script pack Markdown should exist and contain pack title")
    if not smoke_plan_md.exists() or "Screenshot Smoke Plan" not in smoke_plan_md.read_text(encoding="utf-8"):
        fail("demo script pack screenshot smoke plan should exist")
    if not contact_sheet_html.exists() or "Demo Script Pack Contact Sheet" not in contact_sheet_html.read_text(encoding="utf-8"):
        fail("demo script pack contact sheet should exist")
    if not any(row.get("target_id") == "demo_script_pack_panel" for row in demo_script_pack.get("screenshot_targets", [])):
        fail("demo script pack should include its own panel in screenshot targets")
    demo_script_pack_detail = app.DEMO_SCRIPT_PACK.detail(demo_script_pack_id)
    if demo_script_pack_detail.get("pack_id") != demo_script_pack_id:
        fail("demo script pack detail should resolve generated pack")
    demo_script_pack_list = app.DEMO_SCRIPT_PACK.list_packs(10)
    if not any(row.get("pack_id") == demo_script_pack_id for row in demo_script_pack_list):
        fail("demo script pack list should include generated pack")
    demo_script_pack_output = app.DEMO_SCRIPT_PACK.output_file(demo_script_pack_id)
    if not demo_script_pack_output.get("ok") or not Path(demo_script_pack_output.get("path", "")).exists():
        fail("demo script pack output should resolve Markdown")
    missing_demo_script_pack = app.DEMO_SCRIPT_PACK.detail("missing_demo_script_pack")
    if missing_demo_script_pack.get("error") != "demo_script_pack_not_found":
        fail("missing demo script pack should return demo_script_pack_not_found")

    visual_qa_status = app.VISUAL_QA_LEDGER.status()
    if not visual_qa_status.get("ok") or visual_qa_status.get("visual_qa_snapshot_ledger_version") != "visual_qa_snapshot_ledger_v001":
        fail(f"visual QA ledger status failed: {visual_qa_status}")
    if visual_qa_status.get("screenshot_target_count", 0) < 6:
        fail(f"visual QA ledger should expose screenshot targets: {visual_qa_status}")
    visual_qa_result = app.VISUAL_QA_LEDGER.create_ledger({
        "pack_id": demo_script_pack_id,
        "created_by": "validate_app",
        "notes": "Validation-created v063 visual QA snapshot ledger.",
    })
    if not visual_qa_result.get("ok") or not visual_qa_result.get("ledger", {}).get("ledger_id"):
        fail(f"visual QA ledger creation failed: {visual_qa_result}")
    visual_qa_ledger = visual_qa_result.get("ledger", {})
    visual_qa_ledger_id = visual_qa_ledger.get("ledger_id")
    if visual_qa_ledger.get("ledger_readiness") != "ready_for_visual_qa_tracking":
        fail(f"visual QA ledger should be ready: {visual_qa_ledger}")
    visual_qa_md = Path(str(visual_qa_ledger.get("files", {}).get("markdown") or ""))
    visual_qa_contact_sheet = Path(str(visual_qa_ledger.get("files", {}).get("contact_sheet") or ""))
    if not visual_qa_md.exists() or visual_qa_md.stat().st_size < 1000 or "Visual QA Snapshot Ledger" not in visual_qa_md.read_text(encoding="utf-8"):
        fail("visual QA ledger Markdown should exist and contain ledger title")
    if not visual_qa_contact_sheet.exists() or "Visual QA Snapshot Ledger" not in visual_qa_contact_sheet.read_text(encoding="utf-8"):
        fail("visual QA contact sheet should exist")
    if not any(row.get("target_id") == "demo_script_pack_panel" for row in visual_qa_ledger.get("qa_items", [])):
        fail("visual QA ledger should include demo script pack target")
    visual_qa_detail = app.VISUAL_QA_LEDGER.detail(visual_qa_ledger_id)
    if visual_qa_detail.get("ledger_id") != visual_qa_ledger_id:
        fail("visual QA ledger detail should resolve generated ledger")
    visual_qa_list = app.VISUAL_QA_LEDGER.list_ledgers(10)
    if not any(row.get("ledger_id") == visual_qa_ledger_id for row in visual_qa_list):
        fail("visual QA ledger list should include generated ledger")
    visual_qa_output = app.VISUAL_QA_LEDGER.output_file(visual_qa_ledger_id)
    if not visual_qa_output.get("ok") or not Path(visual_qa_output.get("path", "")).exists():
        fail("visual QA ledger output should resolve Markdown")
    missing_visual_qa = app.VISUAL_QA_LEDGER.detail("missing_visual_qa_ledger")
    if missing_visual_qa.get("error") != "visual_qa_ledger_not_found":
        fail("missing visual QA ledger should return visual_qa_ledger_not_found")

    second_visual_qa_result = app.VISUAL_QA_LEDGER.create_ledger({
        "pack_id": demo_script_pack_id,
        "created_by": "validate_app",
        "notes": "Validation-created v069 baseline visual QA snapshot ledger.",
    })
    if not second_visual_qa_result.get("ok") or not second_visual_qa_result.get("ledger", {}).get("ledger_id"):
        fail(f"second visual QA ledger creation failed: {second_visual_qa_result}")
    second_visual_qa_ledger_id = second_visual_qa_result.get("ledger", {}).get("ledger_id")

    visual_baseline_status = app.VISUAL_BASELINE_COMPARISON.status()
    if not visual_baseline_status.get("ok") or visual_baseline_status.get("visual_baseline_comparison_version") != "visual_baseline_comparison_manifest_v001":
        fail(f"visual baseline comparison status failed: {visual_baseline_status}")
    if visual_baseline_status.get("baseline_candidate_count", 0) < 1:
        fail(f"visual baseline comparison should see at least one baseline candidate: {visual_baseline_status}")
    visual_baseline_result = app.VISUAL_BASELINE_COMPARISON.create_comparison({
        "latest_ledger_id": second_visual_qa_ledger_id,
        "baseline_ledger_id": visual_qa_ledger_id,
        "created_by": "validate_app",
        "notes": "Validation-created v069 visual baseline comparison.",
    })
    if not visual_baseline_result.get("ok") or not visual_baseline_result.get("comparison", {}).get("comparison_id"):
        fail(f"visual baseline comparison creation failed: {visual_baseline_result}")
    visual_baseline_comparison = visual_baseline_result.get("comparison", {})
    visual_baseline_comparison_id = visual_baseline_comparison.get("comparison_id")
    if visual_baseline_comparison.get("comparison_readiness") != "ready_for_visual_baseline_review":
        fail(f"visual baseline comparison should be ready: {visual_baseline_comparison}")
    visual_baseline_md = Path(str(visual_baseline_comparison.get("files", {}).get("markdown") or ""))
    if not visual_baseline_md.exists() or visual_baseline_md.stat().st_size < 1000 or "Visual Baseline Comparison Manifest" not in visual_baseline_md.read_text(encoding="utf-8"):
        fail("visual baseline comparison Markdown should exist and contain title")
    visual_baseline_summary = visual_baseline_comparison.get("target_delta_summary", {})
    if visual_baseline_summary.get("baseline_targets", 0) < 6 or visual_baseline_summary.get("latest_targets", 0) < 6:
        fail(f"visual baseline comparison should compare target sets: {visual_baseline_summary}")
    visual_baseline_detail = app.VISUAL_BASELINE_COMPARISON.detail(visual_baseline_comparison_id)
    if visual_baseline_detail.get("comparison_id") != visual_baseline_comparison_id:
        fail("visual baseline comparison detail should resolve generated comparison")
    visual_baseline_list = app.VISUAL_BASELINE_COMPARISON.list_comparisons(10)
    if not any(row.get("comparison_id") == visual_baseline_comparison_id for row in visual_baseline_list):
        fail("visual baseline comparison list should include generated comparison")
    visual_baseline_output = app.VISUAL_BASELINE_COMPARISON.output_file(visual_baseline_comparison_id)
    if not visual_baseline_output.get("ok") or not Path(visual_baseline_output.get("path", "")).exists():
        fail("visual baseline comparison output should resolve Markdown")
    missing_visual_baseline = app.VISUAL_BASELINE_COMPARISON.detail("missing_visual_baseline_comparison")
    if missing_visual_baseline.get("error") != "visual_baseline_comparison_not_found":
        fail("missing visual baseline comparison should return visual_baseline_comparison_not_found")

    demo_artifact_status = app.DEMO_ARTIFACT_COMPLETENESS.status()
    if not demo_artifact_status.get("ok") or demo_artifact_status.get("demo_artifact_completeness_version") != "demo_artifact_completeness_validator_v001":
        fail(f"demo artifact completeness status failed: {demo_artifact_status}")
    if demo_artifact_status.get("required_artifact_count", 0) < 12 or demo_artifact_status.get("missing_required_artifacts", 1) != 0:
        fail(f"demo artifact completeness should find required generated artifacts: {demo_artifact_status}")
    demo_artifact_result = app.DEMO_ARTIFACT_COMPLETENESS.create_check({
        "created_by": "validate_app",
        "notes": "Validation-created v069 demo artifact completeness check.",
    })
    if not demo_artifact_result.get("ok") or not demo_artifact_result.get("check", {}).get("check_id"):
        fail(f"demo artifact completeness creation failed: {demo_artifact_result}")
    demo_artifact_check = demo_artifact_result.get("check", {})
    demo_artifact_check_id = demo_artifact_check.get("check_id")
    if demo_artifact_check.get("check_readiness") != "ready_for_demo_artifact_review":
        fail(f"demo artifact completeness check should be ready: {demo_artifact_check}")
    demo_artifact_md = Path(str(demo_artifact_check.get("files", {}).get("markdown") or ""))
    if not demo_artifact_md.exists() or demo_artifact_md.stat().st_size < 1000 or "Demo Artifact Completeness Validator" not in demo_artifact_md.read_text(encoding="utf-8"):
        fail("demo artifact completeness Markdown should exist and contain title")
    demo_artifact_summary = demo_artifact_check.get("summary", {})
    if demo_artifact_summary.get("complete_required_artifacts", 0) < 12 or demo_artifact_summary.get("missing_required_artifacts", 1) != 0:
        fail(f"demo artifact completeness should pass required checks: {demo_artifact_summary}")
    demo_artifact_detail = app.DEMO_ARTIFACT_COMPLETENESS.detail(demo_artifact_check_id)
    if demo_artifact_detail.get("check_id") != demo_artifact_check_id:
        fail("demo artifact completeness detail should resolve generated check")
    demo_artifact_list = app.DEMO_ARTIFACT_COMPLETENESS.list_checks(10)
    if not any(row.get("check_id") == demo_artifact_check_id for row in demo_artifact_list):
        fail("demo artifact completeness list should include generated check")
    demo_artifact_output = app.DEMO_ARTIFACT_COMPLETENESS.output_file(demo_artifact_check_id)
    if not demo_artifact_output.get("ok") or not Path(demo_artifact_output.get("path", "")).exists():
        fail("demo artifact completeness output should resolve Markdown")
    missing_demo_artifact = app.DEMO_ARTIFACT_COMPLETENESS.detail("missing_demo_artifact_completeness")
    if missing_demo_artifact.get("error") != "demo_artifact_completeness_check_not_found":
        fail("missing demo artifact completeness check should return demo_artifact_completeness_check_not_found")

    visual_capture_status = app.VISUAL_EVIDENCE_CAPTURE.status()
    if not visual_capture_status.get("ok") or visual_capture_status.get("visual_evidence_capture_version") != "visual_evidence_capture_v001":
        fail(f"visual evidence capture status failed: {visual_capture_status}")
    if visual_capture_status.get("browser_available") is not True or visual_capture_status.get("target_count", 0) < 6:
        fail(f"visual evidence capture should detect browser and targets: {visual_capture_status}")
    capture_server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    capture_thread = threading.Thread(target=capture_server.serve_forever, daemon=True)
    capture_thread.start()
    capture_base_url = f"http://127.0.0.1:{capture_server.server_address[1]}"
    try:
        visual_capture_result = app.VISUAL_EVIDENCE_CAPTURE.create_capture({
            "ledger_id": visual_qa_ledger_id,
            "base_url": capture_base_url,
            "created_by": "validate_app",
            "notes": "Validation-created v069 visual evidence capture.",
        })
    finally:
        capture_server.shutdown()
        capture_thread.join(timeout=5)
    if not visual_capture_result.get("ok") or not visual_capture_result.get("capture", {}).get("capture_id"):
        fail(f"visual evidence capture creation failed: {visual_capture_result}")
    visual_capture = visual_capture_result.get("capture", {})
    visual_capture_id = visual_capture.get("capture_id")
    if visual_capture.get("capture_readiness") != "ready_for_visual_evidence_review":
        fail(f"visual evidence capture should be ready: {visual_capture}")
    if visual_capture.get("captured_count", 0) < 6 or visual_capture.get("failed_count", 1) != 0:
        fail(f"visual evidence capture should capture targets without failures: {visual_capture}")
    visual_capture_sheet = Path(str(visual_capture.get("files", {}).get("contact_sheet") or ""))
    if not visual_capture_sheet.exists() or visual_capture_sheet.stat().st_size < 1000 or "Visual Evidence Capture" not in visual_capture_sheet.read_text(encoding="utf-8"):
        fail("visual evidence capture contact sheet should exist and contain title")
    visual_capture_pngs = [Path(str(row.get("screenshot_path") or "")) for row in visual_capture.get("capture_rows", [])]
    if len([path for path in visual_capture_pngs if path.exists() and path.stat().st_size > 1000]) < 6:
        fail("visual evidence capture should create screenshot PNG files")
    visual_capture_detail = app.VISUAL_EVIDENCE_CAPTURE.detail(visual_capture_id)
    if visual_capture_detail.get("capture_id") != visual_capture_id:
        fail("visual evidence capture detail should resolve generated capture")
    visual_capture_list = app.VISUAL_EVIDENCE_CAPTURE.list_captures(10)
    if not any(row.get("capture_id") == visual_capture_id for row in visual_capture_list):
        fail("visual evidence capture list should include generated capture")
    visual_capture_output = app.VISUAL_EVIDENCE_CAPTURE.output_file(visual_capture_id)
    if not visual_capture_output.get("ok") or not Path(visual_capture_output.get("path", "")).exists():
        fail("visual evidence capture output should resolve contact sheet")
    missing_visual_capture = app.VISUAL_EVIDENCE_CAPTURE.detail("missing_visual_evidence_capture")
    if missing_visual_capture.get("error") != "visual_evidence_capture_not_found":
        fail("missing visual evidence capture should return visual_evidence_capture_not_found")

    visual_diff_status = app.VISUAL_EVIDENCE_REVIEW_DIFF.status()
    if not visual_diff_status.get("ok") or visual_diff_status.get("visual_evidence_review_diff_version") != "visual_evidence_review_diff_v001":
        fail(f"visual evidence review diff status failed: {visual_diff_status}")
    if visual_diff_status.get("baseline_candidate_count", 0) < 1:
        fail(f"visual evidence review diff should see at least one baseline capture: {visual_diff_status}")
    visual_diff_result = app.VISUAL_EVIDENCE_REVIEW_DIFF.create_diff({
        "latest_capture_id": visual_capture_id,
        "created_by": "validate_app",
        "notes": "Validation-created v069 visual evidence review diff.",
    })
    if not visual_diff_result.get("ok") or not visual_diff_result.get("diff", {}).get("diff_id"):
        fail(f"visual evidence review diff creation failed: {visual_diff_result}")
    visual_diff = visual_diff_result.get("diff", {})
    visual_diff_id = visual_diff.get("diff_id")
    if visual_diff.get("diff_readiness") != "ready_for_visual_evidence_diff_review":
        fail(f"visual evidence review diff should be ready: {visual_diff}")
    if visual_diff.get("diff_summary", {}).get("latest_targets", 0) < 6:
        fail(f"visual evidence review diff should compare captured target rows: {visual_diff}")
    visual_diff_html = Path(str(visual_diff.get("files", {}).get("html") or ""))
    if not visual_diff_html.exists() or visual_diff_html.stat().st_size < 1000 or "Visual Evidence Review Diff" not in visual_diff_html.read_text(encoding="utf-8"):
        fail("visual evidence review diff HTML should exist and contain title")
    visual_diff_detail = app.VISUAL_EVIDENCE_REVIEW_DIFF.detail(visual_diff_id)
    if visual_diff_detail.get("diff_id") != visual_diff_id:
        fail("visual evidence review diff detail should resolve generated diff")
    visual_diff_list = app.VISUAL_EVIDENCE_REVIEW_DIFF.list_diffs(10)
    if not any(row.get("diff_id") == visual_diff_id for row in visual_diff_list):
        fail("visual evidence review diff list should include generated diff")
    visual_diff_output = app.VISUAL_EVIDENCE_REVIEW_DIFF.output_file(visual_diff_id)
    if not visual_diff_output.get("ok") or not Path(visual_diff_output.get("path", "")).exists():
        fail("visual evidence review diff output should resolve HTML")
    missing_visual_diff = app.VISUAL_EVIDENCE_REVIEW_DIFF.detail("missing_visual_evidence_review_diff")
    if missing_visual_diff.get("error") != "visual_evidence_review_diff_not_found":
        fail("missing visual evidence review diff should return visual_evidence_review_diff_not_found")

    visual_annotations_status = app.VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.status()
    if not visual_annotations_status.get("ok") or visual_annotations_status.get("visual_evidence_review_annotations_version") != "visual_evidence_review_annotations_v001":
        fail(f"visual evidence review annotations status failed: {visual_annotations_status}")
    if visual_annotations_status.get("ready_diff_count", 0) < 1:
        fail(f"visual evidence review annotations should see at least one ready diff: {visual_annotations_status}")
    visual_annotations_result = app.VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.create_annotations({
        "diff_id": visual_diff_id,
        "created_by": "validate_app",
        "notes": "Validation-created v069 visual evidence review annotations.",
    })
    if not visual_annotations_result.get("ok") or not visual_annotations_result.get("annotations", {}).get("annotation_id"):
        fail(f"visual evidence review annotations creation failed: {visual_annotations_result}")
    visual_annotations = visual_annotations_result.get("annotations", {})
    visual_annotations_id = visual_annotations.get("annotation_id")
    if visual_annotations.get("annotation_readiness") != "ready_for_visual_evidence_annotation_review":
        fail(f"visual evidence review annotations should be ready: {visual_annotations}")
    if visual_annotations.get("target_count", 0) < 6:
        fail(f"visual evidence review annotations should cover diff targets: {visual_annotations}")
    visual_annotations_html = Path(str(visual_annotations.get("files", {}).get("html") or ""))
    if not visual_annotations_html.exists() or visual_annotations_html.stat().st_size < 1000 or "Visual Evidence Review Annotations" not in visual_annotations_html.read_text(encoding="utf-8"):
        fail("visual evidence review annotations HTML should exist and contain title")
    visual_annotations_detail = app.VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.detail(visual_annotations_id)
    if visual_annotations_detail.get("annotation_id") != visual_annotations_id:
        fail("visual evidence review annotations detail should resolve generated annotation set")
    visual_annotations_list = app.VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.list_annotations(10)
    if not any(row.get("annotation_id") == visual_annotations_id for row in visual_annotations_list):
        fail("visual evidence review annotations list should include generated annotation set")
    visual_annotations_output = app.VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.output_file(visual_annotations_id)
    if not visual_annotations_output.get("ok") or not Path(visual_annotations_output.get("path", "")).exists():
        fail("visual evidence review annotations output should resolve HTML")
    missing_visual_annotations = app.VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.detail("missing_visual_evidence_review_annotations")
    if missing_visual_annotations.get("error") != "visual_evidence_review_annotations_not_found":
        fail("missing visual evidence review annotations should return visual_evidence_review_annotations_not_found")

    visual_signoff_status = app.VISUAL_EVIDENCE_SIGNOFF_PACKET.status()
    if not visual_signoff_status.get("ok") or visual_signoff_status.get("visual_evidence_signoff_packet_version") != "visual_evidence_signoff_packet_v001":
        fail(f"visual evidence sign-off packet status failed: {visual_signoff_status}")
    if visual_signoff_status.get("ready_annotation_count", 0) < 1:
        fail(f"visual evidence sign-off packet should see ready annotations: {visual_signoff_status}")
    visual_signoff_result = app.VISUAL_EVIDENCE_SIGNOFF_PACKET.create_packet({
        "annotation_id": visual_annotations_id,
        "created_by": "validate_app",
        "reviewer": "validate_app",
        "notes": "Validation-created v069 visual evidence sign-off packet.",
    })
    if not visual_signoff_result.get("ok") or not visual_signoff_result.get("packet", {}).get("packet_id"):
        fail(f"visual evidence sign-off packet creation failed: {visual_signoff_result}")
    visual_signoff_packet = visual_signoff_result.get("packet", {})
    visual_signoff_packet_id = visual_signoff_packet.get("packet_id")
    if visual_signoff_packet.get("packet_readiness") != "ready_for_visual_evidence_signoff_review":
        fail(f"visual evidence sign-off packet should be ready: {visual_signoff_packet}")
    if visual_signoff_packet.get("target_count", 0) < 6:
        fail(f"visual evidence sign-off packet should cover annotation targets: {visual_signoff_packet}")
    if visual_signoff_packet.get("signoff_status") not in {"signed_off_for_local_portfolio_demo", "conditional_signoff_attention_required", "pending_validation_or_api_contract"}:
        fail(f"visual evidence sign-off packet status is unexpected: {visual_signoff_packet}")
    visual_signoff_html = Path(str(visual_signoff_packet.get("files", {}).get("html") or ""))
    if not visual_signoff_html.exists() or visual_signoff_html.stat().st_size < 1000 or "Visual Evidence Sign-Off Packet" not in visual_signoff_html.read_text(encoding="utf-8"):
        fail("visual evidence sign-off packet HTML should exist and contain title")
    visual_signoff_detail = app.VISUAL_EVIDENCE_SIGNOFF_PACKET.detail(visual_signoff_packet_id)
    if visual_signoff_detail.get("packet_id") != visual_signoff_packet_id:
        fail("visual evidence sign-off packet detail should resolve generated packet")
    visual_signoff_list = app.VISUAL_EVIDENCE_SIGNOFF_PACKET.list_packets(10)
    if not any(row.get("packet_id") == visual_signoff_packet_id for row in visual_signoff_list):
        fail("visual evidence sign-off packet list should include generated packet")
    visual_signoff_output = app.VISUAL_EVIDENCE_SIGNOFF_PACKET.output_file(visual_signoff_packet_id)
    if not visual_signoff_output.get("ok") or not Path(visual_signoff_output.get("path", "")).exists():
        fail("visual evidence sign-off packet output should resolve HTML")
    missing_visual_signoff = app.VISUAL_EVIDENCE_SIGNOFF_PACKET.detail("missing_visual_evidence_signoff_packet")
    if missing_visual_signoff.get("error") != "visual_evidence_signoff_packet_not_found":
        fail("missing visual evidence sign-off packet should return visual_evidence_signoff_packet_not_found")

    final_launch_status = app.FINAL_REVIEWER_LAUNCH_CHECKLIST.status()
    if not final_launch_status.get("ok") or final_launch_status.get("final_reviewer_launch_checklist_version") != "final_reviewer_launch_checklist_v001":
        fail(f"final reviewer launch checklist status failed: {final_launch_status}")
    if final_launch_status.get("ready_signoff_packet_count", 0) < 1:
        fail(f"final reviewer launch checklist should see ready sign-off packets: {final_launch_status}")
    final_launch_result = app.FINAL_REVIEWER_LAUNCH_CHECKLIST.create_checklist({
        "packet_id": visual_signoff_packet_id,
        "created_by": "validate_app",
        "reviewer": "validate_app",
        "notes": "Validation-created v071 final reviewer launch checklist.",
    })
    if not final_launch_result.get("ok") or not final_launch_result.get("checklist", {}).get("checklist_id"):
        fail(f"final reviewer launch checklist creation failed: {final_launch_result}")
    final_launch_checklist = final_launch_result.get("checklist", {})
    final_launch_checklist_id = final_launch_checklist.get("checklist_id")
    if final_launch_checklist.get("checklist_readiness") != "ready_for_final_reviewer_launch":
        fail(f"final reviewer launch checklist should be ready: {final_launch_checklist}")
    if final_launch_checklist.get("action_count", 0) < 8:
        fail(f"final reviewer launch checklist should contain launch actions: {final_launch_checklist}")
    if final_launch_checklist.get("launch_status") not in {"ready_for_local_portfolio_walkthrough", "ready_with_reviewer_attention_items", "pending_validation_or_api_contract"}:
        fail(f"final reviewer launch checklist status is unexpected: {final_launch_checklist}")
    final_launch_html = Path(str(final_launch_checklist.get("files", {}).get("html") or ""))
    if not final_launch_html.exists() or final_launch_html.stat().st_size < 1000 or "Final Reviewer Launch Checklist" not in final_launch_html.read_text(encoding="utf-8"):
        fail("final reviewer launch checklist HTML should exist and contain title")
    final_launch_detail = app.FINAL_REVIEWER_LAUNCH_CHECKLIST.detail(final_launch_checklist_id)
    if final_launch_detail.get("checklist_id") != final_launch_checklist_id:
        fail("final reviewer launch checklist detail should resolve generated checklist")
    final_launch_list = app.FINAL_REVIEWER_LAUNCH_CHECKLIST.list_checklists(10)
    if not any(row.get("checklist_id") == final_launch_checklist_id for row in final_launch_list):
        fail("final reviewer launch checklist list should include generated checklist")
    final_launch_output = app.FINAL_REVIEWER_LAUNCH_CHECKLIST.output_file(final_launch_checklist_id)
    if not final_launch_output.get("ok") or not Path(final_launch_output.get("path", "")).exists():
        fail("final reviewer launch checklist output should resolve HTML")
    missing_final_launch = app.FINAL_REVIEWER_LAUNCH_CHECKLIST.detail("missing_final_reviewer_launch_checklist")
    if missing_final_launch.get("error") != "final_reviewer_launch_checklist_not_found":
        fail("missing final reviewer launch checklist should return final_reviewer_launch_checklist_not_found")
    recruiter_brief_status = app.RECRUITER_DEMO_BRIEF.status()
    if not recruiter_brief_status.get("ok") or recruiter_brief_status.get("recruiter_demo_brief_version") != "recruiter_demo_brief_v001":
        fail(f"recruiter demo brief status failed: {recruiter_brief_status}")
    if recruiter_brief_status.get("ready_launch_checklist_count", 0) < 1:
        fail(f"recruiter demo brief should see ready launch checklists: {recruiter_brief_status}")
    recruiter_brief_result = app.RECRUITER_DEMO_BRIEF.create_brief({
        "checklist_id": final_launch_checklist_id,
        "created_by": "validate_app",
        "audience": "technical_recruiter",
        "notes": "Validation-created v071 recruiter-facing demo brief.",
    })
    if not recruiter_brief_result.get("ok") or not recruiter_brief_result.get("brief", {}).get("brief_id"):
        fail(f"recruiter demo brief creation failed: {recruiter_brief_result}")
    recruiter_brief = recruiter_brief_result.get("brief", {})
    recruiter_brief_id = recruiter_brief.get("brief_id")
    if recruiter_brief.get("brief_readiness") != "ready_for_recruiter_demo":
        fail(f"recruiter demo brief should be ready: {recruiter_brief}")
    if recruiter_brief.get("section_count", 0) < 6 or recruiter_brief.get("proof_point_count", 0) < 5:
        fail(f"recruiter demo brief should contain sections and proof points: {recruiter_brief}")
    if recruiter_brief.get("brief_status") not in {"ready_for_recruiter_walkthrough", "ready_with_reviewer_attention_items", "pending_validation_or_api_contract"}:
        fail(f"recruiter demo brief status is unexpected: {recruiter_brief}")
    recruiter_brief_html = Path(str(recruiter_brief.get("files", {}).get("html") or ""))
    if not recruiter_brief_html.exists() or recruiter_brief_html.stat().st_size < 1000 or "Recruiter-Facing Demo Brief" not in recruiter_brief_html.read_text(encoding="utf-8"):
        fail("recruiter demo brief HTML should exist and contain title")
    recruiter_brief_detail = app.RECRUITER_DEMO_BRIEF.detail(recruiter_brief_id)
    if recruiter_brief_detail.get("brief_id") != recruiter_brief_id:
        fail("recruiter demo brief detail should resolve generated brief")
    recruiter_brief_list = app.RECRUITER_DEMO_BRIEF.list_briefs(10)
    if not any(row.get("brief_id") == recruiter_brief_id for row in recruiter_brief_list):
        fail("recruiter demo brief list should include generated brief")
    recruiter_brief_output = app.RECRUITER_DEMO_BRIEF.output_file(recruiter_brief_id)
    if not recruiter_brief_output.get("ok") or not Path(recruiter_brief_output.get("path", "")).exists():
        fail("recruiter demo brief output should resolve HTML")
    missing_recruiter_brief = app.RECRUITER_DEMO_BRIEF.detail("missing_recruiter_demo_brief")
    if missing_recruiter_brief.get("error") != "recruiter_demo_brief_not_found":
        fail("missing recruiter demo brief should return recruiter_demo_brief_not_found")

    public_package_status = app.PUBLIC_PORTFOLIO_PACKAGE.status()
    if not public_package_status.get("ok") or public_package_status.get("public_portfolio_interview_package_version") != "public_portfolio_interview_package_v001":
        fail(f"public portfolio package status failed: {public_package_status}")
    if public_package_status.get("ready_recruiter_demo_brief_count", 0) < 1:
        fail("public portfolio package should find at least one ready recruiter demo brief")
    public_package_result = app.PUBLIC_PORTFOLIO_PACKAGE.create_package({
        "brief_id": recruiter_brief_id,
        "created_by": "validate_app",
        "audience": "portfolio_reviewer",
        "notes": "Validation-created v075 public portfolio interview package.",
    })
    if not public_package_result.get("ok") or public_package_result.get("package", {}).get("package_readiness") != "ready_for_public_portfolio_package":
        fail(f"public portfolio package create failed: {public_package_result}")
    public_package = public_package_result.get("package", {})
    public_package_id = public_package.get("package_id")
    if public_package.get("readme_section_count", 0) < 8 or public_package.get("interview_step_count", 0) < 5:
        fail("public portfolio package should include README sections and interview steps")
    public_package_html = Path(public_package.get("files", {}).get("html", ""))
    public_package_readme = Path(public_package.get("files", {}).get("readme", ""))
    public_package_interview = Path(public_package.get("files", {}).get("interview_walkthrough", ""))
    if not public_package_html.exists() or public_package_html.stat().st_size < 1000 or "Public Portfolio Interview Package" not in public_package_html.read_text(encoding="utf-8"):
        fail("public portfolio package HTML output missing expected content")
    if not public_package_readme.exists() or "GeoReview Studio" not in public_package_readme.read_text(encoding="utf-8"):
        fail("public portfolio README output missing expected content")
    if not public_package_interview.exists() or "Public Portfolio Interview Package" not in public_package_interview.read_text(encoding="utf-8"):
        fail("public portfolio interview output missing expected content")
    public_package_detail = app.PUBLIC_PORTFOLIO_PACKAGE.detail(public_package_id)
    if public_package_detail.get("package_id") != public_package_id:
        fail("public portfolio package detail failed")
    public_package_list = app.PUBLIC_PORTFOLIO_PACKAGE.list_packages(10)
    if not any(row.get("package_id") == public_package_id for row in public_package_list):
        fail("public portfolio package should appear in package list")
    public_package_output = app.PUBLIC_PORTFOLIO_PACKAGE.output_file(public_package_id)
    if public_package_output.get("path") != public_package_html:
        fail("public portfolio package output file failed")
    missing_public_package = app.PUBLIC_PORTFOLIO_PACKAGE.detail("missing_public_portfolio_package")
    if missing_public_package.get("error") != "public_portfolio_package_not_found":
        fail("missing public portfolio package should return public_portfolio_package_not_found")

    demo_playbook_status = app.DEMO_REVIEW_PLAYBOOK.status()
    if not demo_playbook_status.get("ok") or demo_playbook_status.get("demo_review_playbook_version") != "demo_review_playbook_v001":
        fail(f"demo review playbook status failed: {demo_playbook_status}")
    if demo_playbook_status.get("ready_public_portfolio_package_count", 0) < 1:
        fail("demo review playbook should find at least one ready public portfolio package")
    demo_playbook_result = app.DEMO_REVIEW_PLAYBOOK.create_playbook({
        "package_id": public_package_id,
        "created_by": "validate_app",
        "audience": "portfolio_reviewer",
        "notes": "Validation-created v075 demo review playbook.",
    })
    if not demo_playbook_result.get("ok") or demo_playbook_result.get("playbook", {}).get("playbook_readiness") != "ready_for_demo_review_playbook":
        fail(f"demo review playbook create failed: {demo_playbook_result}")
    demo_playbook = demo_playbook_result.get("playbook", {})
    demo_playbook_id = demo_playbook.get("playbook_id")
    if demo_playbook.get("demo_agenda_item_count", 0) < 6 or demo_playbook.get("sharing_checklist_item_count", 0) < 8 or demo_playbook.get("review_question_count", 0) < 5:
        fail("demo review playbook should include agenda, checklist and questions")
    demo_playbook_html = Path(demo_playbook.get("files", {}).get("html", ""))
    demo_playbook_md = Path(demo_playbook.get("files", {}).get("playbook", ""))
    demo_checklist_md = Path(demo_playbook.get("files", {}).get("checklist", ""))
    if not demo_playbook_html.exists() or demo_playbook_html.stat().st_size < 1000 or "Demo Review Playbook" not in demo_playbook_html.read_text(encoding="utf-8"):
        fail("demo review playbook HTML output missing expected content")
    if not demo_playbook_md.exists() or "Demo Review Playbook" not in demo_playbook_md.read_text(encoding="utf-8"):
        fail("demo review playbook Markdown output missing expected content")
    if not demo_checklist_md.exists() or "Final Sharing Checklist" not in demo_checklist_md.read_text(encoding="utf-8"):
        fail("demo review checklist Markdown output missing expected content")
    demo_playbook_detail = app.DEMO_REVIEW_PLAYBOOK.detail(demo_playbook_id)
    if demo_playbook_detail.get("playbook_id") != demo_playbook_id:
        fail("demo review playbook detail failed")
    demo_playbook_list = app.DEMO_REVIEW_PLAYBOOK.list_playbooks(10)
    if not any(row.get("playbook_id") == demo_playbook_id for row in demo_playbook_list):
        fail("demo review playbook should appear in playbook list")
    demo_playbook_output = app.DEMO_REVIEW_PLAYBOOK.output_file(demo_playbook_id)
    if demo_playbook_output.get("path") != demo_playbook_html:
        fail("demo review playbook output file failed")
    missing_demo_playbook = app.DEMO_REVIEW_PLAYBOOK.detail("missing_demo_review_playbook")
    if missing_demo_playbook.get("error") != "demo_review_playbook_not_found":
        fail("missing demo review playbook should return demo_review_playbook_not_found")

    github_bundle_status = app.GITHUB_PUBLICATION_BUNDLE.status()
    if not github_bundle_status.get("ok") or github_bundle_status.get("github_publication_bundle_version") != "github_publication_bundle_v001":
        fail(f"GitHub publication bundle status failed: {github_bundle_status}")
    if github_bundle_status.get("ready_demo_review_playbook_count", 0) < 1:
        fail("GitHub publication bundle should find at least one ready demo review playbook")
    github_bundle_result = app.GITHUB_PUBLICATION_BUNDLE.create_bundle({
        "playbook_id": demo_playbook_id,
        "created_by": "validate_app",
        "audience": "github_portfolio_reviewer",
        "notes": "Validation-created v075 GitHub publication bundle.",
    })
    if not github_bundle_result.get("ok") or github_bundle_result.get("bundle", {}).get("bundle_readiness") != "ready_for_github_publication_bundle":
        fail(f"GitHub publication bundle create failed: {github_bundle_result}")
    github_bundle = github_bundle_result.get("bundle", {})
    github_bundle_id = github_bundle.get("bundle_id")
    if github_bundle.get("readme_section_count", 0) < 8 or github_bundle.get("repo_file_count", 0) < 6 or github_bundle.get("publication_checklist_item_count", 0) < 8:
        fail("GitHub publication bundle should include README sections, repo files and checklist items")
    github_bundle_html = Path(github_bundle.get("files", {}).get("html", ""))
    github_bundle_readme = Path(github_bundle.get("files", {}).get("readme_export", ""))
    github_bundle_case_study = Path(github_bundle.get("files", {}).get("case_study", ""))
    github_bundle_repo_manifest = Path(github_bundle.get("files", {}).get("repo_manifest", ""))
    github_bundle_zip = Path(github_bundle.get("files", {}).get("zip", ""))
    if not github_bundle_html.exists() or github_bundle_html.stat().st_size < 1000 or "GitHub-ready Publication Bundle" not in github_bundle_html.read_text(encoding="utf-8"):
        fail("GitHub publication bundle HTML output missing expected content")
    if not github_bundle_readme.exists() or "GeoReview Studio" not in github_bundle_readme.read_text(encoding="utf-8"):
        fail("GitHub README export missing expected content")
    if not github_bundle_case_study.exists() or "Portfolio Case Study" not in github_bundle_case_study.read_text(encoding="utf-8"):
        fail("GitHub case study output missing expected content")
    if not github_bundle_repo_manifest.exists() or "Repository File Manifest" not in github_bundle_repo_manifest.read_text(encoding="utf-8"):
        fail("GitHub repository manifest output missing expected content")
    if not github_bundle_zip.exists() or github_bundle_zip.stat().st_size < 1000:
        fail("GitHub publication ZIP missing or too small")
    with zipfile.ZipFile(github_bundle_zip) as zf:
        names = set(zf.namelist())
        if {"README_public.md", "PORTFOLIO_CASE_STUDY.md", "REPOSITORY_FILE_MANIFEST.md"} - names:
            fail("GitHub publication ZIP missing expected Markdown files")
    github_bundle_detail = app.GITHUB_PUBLICATION_BUNDLE.detail(github_bundle_id)
    if github_bundle_detail.get("bundle_id") != github_bundle_id:
        fail("GitHub publication bundle detail failed")
    github_bundle_list = app.GITHUB_PUBLICATION_BUNDLE.list_bundles(10)
    if not any(row.get("bundle_id") == github_bundle_id for row in github_bundle_list):
        fail("GitHub publication bundle should appear in bundle list")
    github_bundle_output = app.GITHUB_PUBLICATION_BUNDLE.output_file(github_bundle_id)
    if github_bundle_output.get("path") != github_bundle_zip:
        fail("GitHub publication bundle output file failed")
    missing_github_bundle = app.GITHUB_PUBLICATION_BUNDLE.detail("missing_github_publication_bundle")
    if missing_github_bundle.get("error") != "github_publication_bundle_not_found":
        fail("missing GitHub publication bundle should return github_publication_bundle_not_found")

    repository_qa_status = app.REPOSITORY_PUBLICATION_QA.status()
    if not repository_qa_status.get("ok") or repository_qa_status.get("repository_publication_qa_version") != "repository_publication_qa_v001":
        fail(f"repository publication QA status failed: {repository_qa_status}")
    if repository_qa_status.get("ready_github_publication_bundle_count", 0) < 1:
        fail("repository publication QA should find at least one ready GitHub publication bundle")
    repository_qa_result = app.REPOSITORY_PUBLICATION_QA.create_review({
        "bundle_id": github_bundle_id,
        "created_by": "validate_app",
        "audience": "github_repository_reviewer",
        "notes": "Validation-created v083 repository publication QA.",
    })
    if not repository_qa_result.get("ok") or repository_qa_result.get("review", {}).get("qa_readiness") != "ready_for_repository_publication_qa":
        fail(f"repository publication QA create failed: {repository_qa_result}")
    repository_qa = repository_qa_result.get("review", {})
    repository_qa_id = repository_qa.get("review_id")
    if repository_qa.get("required_check_count", 0) < 8 or repository_qa.get("walkthrough_step_count", 0) < 8:
        fail("repository publication QA should include required checks and walkthrough steps")
    repository_qa_html = Path(repository_qa.get("files", {}).get("html", ""))
    repository_qa_checklist = Path(repository_qa.get("files", {}).get("checklist", ""))
    repository_qa_walkthrough = Path(repository_qa.get("files", {}).get("walkthrough", ""))
    repository_qa_zip = Path(repository_qa.get("files", {}).get("zip", ""))
    if not repository_qa_html.exists() or repository_qa_html.stat().st_size < 1000 or "Repository Publication QA" not in repository_qa_html.read_text(encoding="utf-8"):
        fail("repository publication QA HTML output missing expected content")
    if not repository_qa_checklist.exists() or "Repository QA Checklist" not in repository_qa_checklist.read_text(encoding="utf-8"):
        fail("repository QA checklist missing expected content")
    if not repository_qa_walkthrough.exists() or "Public Sharing Walkthrough" not in repository_qa_walkthrough.read_text(encoding="utf-8"):
        fail("repository QA walkthrough missing expected content")
    if not repository_qa_zip.exists() or repository_qa_zip.stat().st_size < 1000:
        fail("repository QA ZIP missing or too small")
    with zipfile.ZipFile(repository_qa_zip) as zf:
        names = set(zf.namelist())
        if {"REPOSITORY_QA_CHECKLIST.md", "PUBLIC_SHARING_WALKTHROUGH.md", "repository_publication_qa_manifest.json"} - names:
            fail("repository QA ZIP missing expected files")
    repository_qa_detail = app.REPOSITORY_PUBLICATION_QA.detail(repository_qa_id)
    if repository_qa_detail.get("review_id") != repository_qa_id:
        fail("repository publication QA detail failed")
    repository_qa_list = app.REPOSITORY_PUBLICATION_QA.list_reviews(10)
    if not any(row.get("review_id") == repository_qa_id for row in repository_qa_list):
        fail("repository publication QA should appear in review list")
    repository_qa_output = app.REPOSITORY_PUBLICATION_QA.output_file(repository_qa_id)
    if repository_qa_output.get("path") != repository_qa_zip:
        fail("repository publication QA output file failed")
    missing_repository_qa = app.REPOSITORY_PUBLICATION_QA.detail("missing_repository_publication_qa")
    if missing_repository_qa.get("error") != "repository_publication_qa_not_found":
        fail("missing repository publication QA should return repository_publication_qa_not_found")

    repository_handoff_status = app.REPOSITORY_EXPORT_HANDOFF.status()
    if not repository_handoff_status.get("ok") or repository_handoff_status.get("repository_export_handoff_version") != "repository_export_handoff_v001":
        fail(f"repository export handoff status failed: {repository_handoff_status}")
    if repository_handoff_status.get("ready_repository_qa_count", 0) < 1:
        fail("repository export handoff should find at least one ready repository QA")
    repository_handoff_result = app.REPOSITORY_EXPORT_HANDOFF.create_handoff({
        "repository_qa_id": repository_qa_id,
        "created_by": "validate_app",
        "audience": "github_repository_reviewer",
        "notes": "Validation-created v083 repository export handoff.",
    })
    if not repository_handoff_result.get("ok") or repository_handoff_result.get("handoff", {}).get("handoff_readiness") != "ready_for_repository_export_handoff":
        fail(f"repository export handoff create failed: {repository_handoff_result}")
    repository_handoff = repository_handoff_result.get("handoff", {})
    repository_handoff_id = repository_handoff.get("handoff_id")
    if repository_handoff.get("include_file_count", 0) < 6 or repository_handoff.get("exclude_file_count", 0) < 4 or repository_handoff.get("license_decision_item_count", 0) < 3:
        fail("repository export handoff should include file plan and license checklist")
    if repository_handoff.get("required_failed_count") != 0:
        fail("repository export handoff should have zero failed required checks")
    repository_handoff_html = Path(repository_handoff.get("files", {}).get("html", ""))
    repository_handoff_doc = Path(repository_handoff.get("files", {}).get("handoff", ""))
    repository_handoff_plan = Path(repository_handoff.get("files", {}).get("file_plan", ""))
    repository_handoff_checklist = Path(repository_handoff.get("files", {}).get("checklist", ""))
    repository_handoff_zip = Path(repository_handoff.get("files", {}).get("zip", ""))
    if not repository_handoff_html.exists() or repository_handoff_html.stat().st_size < 1000 or "Repository Export Handoff" not in repository_handoff_html.read_text(encoding="utf-8"):
        fail("repository export handoff HTML output missing expected content")
    if not repository_handoff_doc.exists() or "Repository Export Handoff" not in repository_handoff_doc.read_text(encoding="utf-8"):
        fail("repository export handoff Markdown missing expected content")
    if not repository_handoff_plan.exists() or "GitHub Repository File Plan" not in repository_handoff_plan.read_text(encoding="utf-8"):
        fail("repository export file plan missing expected content")
    if not repository_handoff_checklist.exists() or "Screenshot and License Checklist" not in repository_handoff_checklist.read_text(encoding="utf-8"):
        fail("repository export checklist missing expected content")
    if not repository_handoff_zip.exists() or repository_handoff_zip.stat().st_size < 1000:
        fail("repository export handoff ZIP missing or too small")
    with zipfile.ZipFile(repository_handoff_zip) as zf:
        names = set(zf.namelist())
        if {"REPOSITORY_EXPORT_HANDOFF.md", "GITHUB_REPOSITORY_FILE_PLAN.md", "SCREENSHOT_AND_LICENSE_CHECKLIST.md", "repository_export_handoff_manifest.json"} - names:
            fail("repository export handoff ZIP missing expected files")
    repository_handoff_detail = app.REPOSITORY_EXPORT_HANDOFF.detail(repository_handoff_id)
    if repository_handoff_detail.get("handoff_id") != repository_handoff_id:
        fail("repository export handoff detail failed")
    repository_handoff_list = app.REPOSITORY_EXPORT_HANDOFF.list_handoffs(10)
    if not any(row.get("handoff_id") == repository_handoff_id for row in repository_handoff_list):
        fail("repository export handoff should appear in handoff list")
    repository_handoff_output = app.REPOSITORY_EXPORT_HANDOFF.output_file(repository_handoff_id)
    if repository_handoff_output.get("path") != repository_handoff_zip:
        fail("repository export handoff output file failed")
    missing_repository_handoff = app.REPOSITORY_EXPORT_HANDOFF.detail("missing_repository_export_handoff")
    if missing_repository_handoff.get("error") != "repository_export_handoff_not_found":
        fail("missing repository export handoff should return repository_export_handoff_not_found")


    repository_dry_run_status = app.REPOSITORY_DRY_RUN_REVIEW.status()
    if not repository_dry_run_status.get("ok") or repository_dry_run_status.get("repository_dry_run_review_version") != "repository_dry_run_review_v001":
        fail(f"repository dry-run review status failed: {repository_dry_run_status}")
    if repository_dry_run_status.get("ready_handoff_count", 0) < 1:
        fail("repository dry-run review should find at least one ready export handoff")
    repository_dry_run_result = app.REPOSITORY_DRY_RUN_REVIEW.create_review({
        "handoff_id": repository_handoff_id,
        "created_by": "validate_app",
        "audience": "github_repository_reviewer",
        "notes": "Validation-created v083 repository dry-run review.",
    })
    if not repository_dry_run_result.get("ok") or repository_dry_run_result.get("review", {}).get("review_readiness") != "ready_for_repository_dry_run_review":
        fail(f"repository dry-run review create failed: {repository_dry_run_result}")
    repository_dry_run = repository_dry_run_result.get("review", {})
    repository_dry_run_id = repository_dry_run.get("review_id")
    if repository_dry_run.get("archive_file_count", 0) < 8 or repository_dry_run.get("final_checklist_item_count", 0) < 8:
        fail("repository dry-run review should include archive preview and final checklist")
    if repository_dry_run.get("required_failed_count") != 0:
        fail("repository dry-run review should have zero failed required checks")
    repository_dry_run_html = Path(repository_dry_run.get("files", {}).get("html", ""))
    repository_dry_run_doc = Path(repository_dry_run.get("files", {}).get("review", ""))
    repository_dry_run_archive = Path(repository_dry_run.get("files", {}).get("archive_preview", ""))
    repository_dry_run_checklist = Path(repository_dry_run.get("files", {}).get("final_checklist", ""))
    repository_dry_run_zip = Path(repository_dry_run.get("files", {}).get("zip", ""))
    if not repository_dry_run_html.exists() or repository_dry_run_html.stat().st_size < 1000 or "Repository Dry-Run Review" not in repository_dry_run_html.read_text(encoding="utf-8"):
        fail("repository dry-run review HTML output missing expected content")
    if not repository_dry_run_doc.exists() or "Repository Dry-Run Review" not in repository_dry_run_doc.read_text(encoding="utf-8"):
        fail("repository dry-run review Markdown missing expected content")
    if not repository_dry_run_archive.exists() or "Archive Structure Preview" not in repository_dry_run_archive.read_text(encoding="utf-8"):
        fail("repository dry-run archive preview missing expected content")
    if not repository_dry_run_checklist.exists() or "Final Public Sharing Checklist" not in repository_dry_run_checklist.read_text(encoding="utf-8"):
        fail("repository dry-run final checklist missing expected content")
    if not repository_dry_run_zip.exists() or repository_dry_run_zip.stat().st_size < 1000:
        fail("repository dry-run ZIP missing or too small")
    with zipfile.ZipFile(repository_dry_run_zip) as zf:
        names = set(zf.namelist())
        if {"REPOSITORY_DRY_RUN_REVIEW.md", "ARCHIVE_STRUCTURE_PREVIEW.md", "FINAL_PUBLIC_SHARING_CHECKLIST.md", "repository_dry_run_review_manifest.json"} - names:
            fail("repository dry-run ZIP missing expected files")
    repository_dry_run_detail = app.REPOSITORY_DRY_RUN_REVIEW.detail(repository_dry_run_id)
    if repository_dry_run_detail.get("review_id") != repository_dry_run_id:
        fail("repository dry-run review detail failed")
    repository_dry_run_list = app.REPOSITORY_DRY_RUN_REVIEW.list_reviews(10)
    if not any(row.get("review_id") == repository_dry_run_id for row in repository_dry_run_list):
        fail("repository dry-run review should appear in review list")
    repository_dry_run_output = app.REPOSITORY_DRY_RUN_REVIEW.output_file(repository_dry_run_id)
    if repository_dry_run_output.get("path") != repository_dry_run_zip:
        fail("repository dry-run review output file failed")
    missing_repository_dry_run = app.REPOSITORY_DRY_RUN_REVIEW.detail("missing_repository_dry_run_review")
    if missing_repository_dry_run.get("error") != "repository_dry_run_review_not_found":
        fail("missing repository dry-run review should return repository_dry_run_review_not_found")
    repository_final_package_status = app.REPOSITORY_FINAL_PACKAGE_REVIEW.status()
    if not repository_final_package_status.get("ok") or repository_final_package_status.get("repository_final_package_review_version") != "repository_final_package_review_v001":
        fail(f"repository final package review status failed: {repository_final_package_status}")
    if repository_final_package_status.get("ready_dry_run_review_count", 0) < 1:
        fail("repository final package review should find at least one ready dry-run review")
    repository_final_package_result = app.REPOSITORY_FINAL_PACKAGE_REVIEW.create_review({
        "dry_run_review_id": repository_dry_run_id,
        "created_by": "validate_app",
        "audience": "github_repository_reviewer",
        "notes": "Validation-created v083 repository export checklist.",
    })
    if not repository_final_package_result.get("ok") or repository_final_package_result.get("review", {}).get("review_readiness") != "ready_for_repository_final_package_review":
        fail(f"repository final package review create failed: {repository_final_package_result}")
    repository_final_package = repository_final_package_result.get("review", {})
    repository_final_package_id = repository_final_package.get("review_id")
    if repository_final_package.get("required_failed_count") != 0:
        fail("repository final package review should have zero failed required checks")
    if repository_final_package.get("public_path_issue_count") != 0 or repository_final_package.get("redacted_path_count", 0) < 1:
        fail("repository final package review should expose clean public paths and redacted path evidence")
    repository_final_package_html = Path(repository_final_package.get("files", {}).get("html", ""))
    repository_final_package_doc = Path(repository_final_package.get("files", {}).get("review", ""))
    repository_final_package_paths = Path(repository_final_package.get("files", {}).get("redacted_path_evidence", ""))
    repository_final_package_checklist = Path(repository_final_package.get("files", {}).get("publication_checklist", ""))
    repository_final_package_zip = Path(repository_final_package.get("files", {}).get("zip", ""))
    if not repository_final_package_html.exists() or repository_final_package_html.stat().st_size < 1000 or "Final Repository Package Review" not in repository_final_package_html.read_text(encoding="utf-8"):
        fail("repository final package review HTML output missing expected content")
    if not repository_final_package_doc.exists() or "Final Repository Package Review" not in repository_final_package_doc.read_text(encoding="utf-8"):
        fail("repository final package review Markdown missing expected content")
    if not repository_final_package_paths.exists() or "Redacted Path Evidence" not in repository_final_package_paths.read_text(encoding="utf-8"):
        fail("repository final package redacted path evidence missing expected content")
    if not repository_final_package_checklist.exists() or "Publication Decision Checklist" not in repository_final_package_checklist.read_text(encoding="utf-8"):
        fail("repository final package publication checklist missing expected content")
    if not repository_final_package_zip.exists() or repository_final_package_zip.stat().st_size < 1000:
        fail("repository final package ZIP missing or too small")
    with zipfile.ZipFile(repository_final_package_zip) as zf:
        names = set(zf.namelist())
        if {"FINAL_REPOSITORY_PACKAGE_REVIEW.md", "REDACTED_PATH_EVIDENCE.md", "PUBLICATION_DECISION_CHECKLIST.md", "repository_final_package_review_manifest.json"} - names:
            fail("repository final package ZIP missing expected files")
    repository_final_package_detail = app.REPOSITORY_FINAL_PACKAGE_REVIEW.detail(repository_final_package_id)
    if repository_final_package_detail.get("review_id") != repository_final_package_id:
        fail("repository final package review detail failed")
    repository_final_package_list = app.REPOSITORY_FINAL_PACKAGE_REVIEW.list_reviews(10)
    if not any(row.get("review_id") == repository_final_package_id for row in repository_final_package_list):
        fail("repository final package review should appear in review list")
    repository_final_package_output = app.REPOSITORY_FINAL_PACKAGE_REVIEW.output_file(repository_final_package_id)
    if repository_final_package_output.get("path") != repository_final_package_zip:
        fail("repository final package review output file failed")
    missing_repository_final_package = app.REPOSITORY_FINAL_PACKAGE_REVIEW.detail("missing_repository_final_package_review")
    if missing_repository_final_package.get("error") != "repository_final_package_review_not_found":
        fail("missing repository final package review should return repository_final_package_review_not_found")
    public_readme_cleanup_status = app.PUBLIC_README_CLEANUP_REVIEW.status()
    if not public_readme_cleanup_status.get("ok") or public_readme_cleanup_status.get("public_readme_cleanup_review_version") != "public_readme_cleanup_review_v001":
        fail(f"public README cleanup review status failed: {public_readme_cleanup_status}")
    if public_readme_cleanup_status.get("ready_final_package_review_count", 0) < 1:
        fail("public README cleanup review should find at least one ready final package review")
    public_readme_cleanup_result = app.PUBLIC_README_CLEANUP_REVIEW.create_review({
        "final_package_review_id": repository_final_package_id,
        "created_by": "validate_app",
        "audience": "github_repository_reviewer",
        "notes": "Validation-created v083 public README cleanup review.",
    })
    if not public_readme_cleanup_result.get("ok") or public_readme_cleanup_result.get("review", {}).get("review_readiness") != "ready_for_public_readme_cleanup_review":
        fail(f"public README cleanup review create failed: {public_readme_cleanup_result}")
    public_readme_cleanup = public_readme_cleanup_result.get("review", {})
    public_readme_cleanup_id = public_readme_cleanup.get("review_id")
    if public_readme_cleanup.get("required_failed_count") != 0 or public_readme_cleanup.get("public_readme_issue_count") != 0:
        fail("public README cleanup review should have zero required failures and zero README issues")
    if public_readme_cleanup.get("screenshot_evidence_count", 0) < 8:
        fail("public README cleanup review should expose screenshot evidence checklist")
    public_readme_cleanup_html = Path(public_readme_cleanup.get("files", {}).get("html", ""))
    public_readme_cleanup_doc = Path(public_readme_cleanup.get("files", {}).get("review", ""))
    public_readme_cleanup_readme = Path(public_readme_cleanup.get("files", {}).get("public_readme_draft", ""))
    public_readme_cleanup_screenshots = Path(public_readme_cleanup.get("files", {}).get("screenshot_evidence_checklist", ""))
    public_readme_cleanup_zip = Path(public_readme_cleanup.get("files", {}).get("zip", ""))
    if not public_readme_cleanup_html.exists() or public_readme_cleanup_html.stat().st_size < 1000 or "Public README Cleanup Review" not in public_readme_cleanup_html.read_text(encoding="utf-8"):
        fail("public README cleanup HTML output missing expected content")
    if not public_readme_cleanup_doc.exists() or "Public README Cleanup Review" not in public_readme_cleanup_doc.read_text(encoding="utf-8"):
        fail("public README cleanup Markdown missing expected content")
    readme_text = public_readme_cleanup_readme.read_text(encoding="utf-8") if public_readme_cleanup_readme.exists() else ""
    if not public_readme_cleanup_readme.exists() or "docs/screenshots/" not in readme_text or "analysis_output" in readme_text:
        fail("public README draft missing expected repository-relative screenshot references")
    if not public_readme_cleanup_screenshots.exists() or "Screenshot Evidence Checklist" not in public_readme_cleanup_screenshots.read_text(encoding="utf-8"):
        fail("public README cleanup screenshot checklist missing expected content")
    if not public_readme_cleanup_zip.exists() or public_readme_cleanup_zip.stat().st_size < 1000:
        fail("public README cleanup ZIP missing or too small")
    with zipfile.ZipFile(public_readme_cleanup_zip) as zf:
        names = set(zf.namelist())
        if {"PUBLIC_README_CLEANUP_REVIEW.md", "PUBLIC_README_DRAFT.md", "SCREENSHOT_EVIDENCE_CHECKLIST.md", "public_readme_cleanup_review_manifest.json"} - names:
            fail("public README cleanup ZIP missing expected files")
    public_readme_cleanup_detail = app.PUBLIC_README_CLEANUP_REVIEW.detail(public_readme_cleanup_id)
    if public_readme_cleanup_detail.get("review_id") != public_readme_cleanup_id:
        fail("public README cleanup detail failed")
    public_readme_cleanup_list = app.PUBLIC_README_CLEANUP_REVIEW.list_reviews(10)
    if not any(row.get("review_id") == public_readme_cleanup_id for row in public_readme_cleanup_list):
        fail("public README cleanup review should appear in review list")
    public_readme_cleanup_output = app.PUBLIC_README_CLEANUP_REVIEW.output_file(public_readme_cleanup_id)
    if public_readme_cleanup_output.get("path") != public_readme_cleanup_zip:
        fail("public README cleanup output file failed")
    missing_public_readme_cleanup = app.PUBLIC_README_CLEANUP_REVIEW.detail("missing_public_readme_cleanup_review")
    if missing_public_readme_cleanup.get("error") != "public_readme_cleanup_review_not_found":
        fail("missing public README cleanup review should return public_readme_cleanup_review_not_found")

    public_repository_polish_status = app.PUBLIC_REPOSITORY_POLISH_PACKAGE.status()
    if not public_repository_polish_status.get("ok") or public_repository_polish_status.get("public_repository_polish_package_version") != "public_repository_polish_package_v001":
        fail(f"public repository polish package status failed: {public_repository_polish_status}")
    if public_repository_polish_status.get("ready_cleanup_review_count", 0) < 1:
        fail("public repository polish package should find at least one ready cleanup review")
    public_repository_polish_result = app.PUBLIC_REPOSITORY_POLISH_PACKAGE.create_package({
        "cleanup_review_id": public_readme_cleanup_id,
        "created_by": "validate_app",
        "audience": "github_repository_reviewer",
        "notes": "Validation-created v083 public repository polish package.",
    })
    if not public_repository_polish_result.get("ok") or public_repository_polish_result.get("package", {}).get("package_readiness") != "ready_for_public_repository_polish":
        fail(f"public repository polish package create failed: {public_repository_polish_result}")
    public_repository_polish = public_repository_polish_result.get("package", {})
    public_repository_polish_id = public_repository_polish.get("package_id")
    if public_repository_polish.get("required_failed_count") != 0 or public_repository_polish.get("public_readme_issue_count") != 0:
        fail("public repository polish package should have zero required failures and zero README issues")
    if public_repository_polish.get("screenshot_target_count", 0) < 8:
        fail("public repository polish package should expose manual screenshot targets")
    public_repository_polish_html = Path(public_repository_polish.get("files", {}).get("html", ""))
    public_repository_polish_doc = Path(public_repository_polish.get("files", {}).get("summary", ""))
    public_repository_polish_file_plan = Path(public_repository_polish.get("files", {}).get("file_plan", ""))
    public_repository_polish_screenshots = Path(public_repository_polish.get("files", {}).get("manual_screenshot_capture_package", ""))
    public_repository_polish_checklist = Path(public_repository_polish.get("files", {}).get("public_sharing_checklist", ""))
    public_repository_polish_readme = Path(public_repository_polish.get("files", {}).get("public_repository_ready_readme", ""))
    public_repository_polish_zip = Path(public_repository_polish.get("files", {}).get("zip", ""))
    if not public_repository_polish_html.exists() or public_repository_polish_html.stat().st_size < 1000 or "Final Public Repository Polish Package" not in public_repository_polish_html.read_text(encoding="utf-8"):
        fail("public repository polish HTML output missing expected content")
    if not public_repository_polish_doc.exists() or "Final Public Repository Polish Package" not in public_repository_polish_doc.read_text(encoding="utf-8"):
        fail("public repository polish Markdown missing expected content")
    if not public_repository_polish_file_plan.exists() or "Public Repository File Plan" not in public_repository_polish_file_plan.read_text(encoding="utf-8"):
        fail("public repository polish file plan missing expected content")
    if not public_repository_polish_screenshots.exists() or "Manual Screenshot Capture Package" not in public_repository_polish_screenshots.read_text(encoding="utf-8"):
        fail("public repository polish screenshot package missing expected content")
    if not public_repository_polish_checklist.exists() or "Public Sharing Checklist" not in public_repository_polish_checklist.read_text(encoding="utf-8"):
        fail("public repository polish checklist missing expected content")
    polish_readme_text = public_repository_polish_readme.read_text(encoding="utf-8") if public_repository_polish_readme.exists() else ""
    if not public_repository_polish_readme.exists() or "docs/screenshots/" not in polish_readme_text or "analysis_output" in polish_readme_text:
        fail("public repository ready README missing expected repository-relative screenshot references")
    if not public_repository_polish_zip.exists() or public_repository_polish_zip.stat().st_size < 1000:
        fail("public repository polish ZIP missing or too small")
    with zipfile.ZipFile(public_repository_polish_zip) as zf:
        names = set(zf.namelist())
        if {"FINAL_PUBLIC_REPOSITORY_POLISH.md", "PUBLIC_REPOSITORY_FILE_PLAN.md", "MANUAL_SCREENSHOT_CAPTURE_PACKAGE.md", "PUBLIC_SHARING_CHECKLIST.md", "PUBLIC_REPOSITORY_READY_README.md", "public_repository_polish_package_manifest.json"} - names:
            fail("public repository polish ZIP missing expected files")
    public_repository_polish_detail = app.PUBLIC_REPOSITORY_POLISH_PACKAGE.detail(public_repository_polish_id)
    if public_repository_polish_detail.get("package_id") != public_repository_polish_id:
        fail("public repository polish package detail failed")
    public_repository_polish_list = app.PUBLIC_REPOSITORY_POLISH_PACKAGE.list_packages(10)
    if not any(row.get("package_id") == public_repository_polish_id for row in public_repository_polish_list):
        fail("public repository polish package should appear in package list")
    public_repository_polish_output = app.PUBLIC_REPOSITORY_POLISH_PACKAGE.output_file(public_repository_polish_id)
    if public_repository_polish_output.get("path") != public_repository_polish_zip:
        fail("public repository polish package output file failed")
    missing_public_repository_polish = app.PUBLIC_REPOSITORY_POLISH_PACKAGE.detail("missing_public_repository_polish_package")
    if missing_public_repository_polish.get("error") != "public_repository_polish_package_not_found":
        fail("missing public repository polish package should return public_repository_polish_package_not_found")

    repository_export_status = app.REPOSITORY_EXPORT_CHECKLIST.status()
    if not repository_export_status.get("ok") or repository_export_status.get("repository_export_checklist_version") != "repository_export_checklist_v001":
        fail(f"repository export checklist status failed: {repository_export_status}")
    if repository_export_status.get("ready_polish_package_count", 0) < 1:
        fail("repository export checklist should find at least one ready polish package")
    repository_export_result = app.REPOSITORY_EXPORT_CHECKLIST.create_checklist({
        "package_id": public_repository_polish_id,
        "created_by": "validate_app",
        "audience": "github_repository_reviewer",
        "notes": "Validation-created v083 repository export checklist.",
    })
    if not repository_export_result.get("ok") or repository_export_result.get("checklist", {}).get("checklist_readiness") != "ready_for_repository_export_checklist":
        fail(f"repository export checklist create failed: {repository_export_result}")
    repository_export_checklist = repository_export_result.get("checklist", {})
    repository_export_checklist_id = repository_export_checklist.get("checklist_id")
    if repository_export_checklist.get("required_failed_count") != 0:
        fail("repository export checklist should have zero required failures")
    if repository_export_checklist.get("screenshot_target_count", 0) < 8:
        fail("repository export checklist should expose at least eight screenshot targets")
    if repository_export_checklist.get("screenshot_evidence_count", 0) < 8:
        fail("repository export checklist should detect screenshot evidence")
    repository_export_html = Path(repository_export_checklist.get("files", {}).get("html", ""))
    repository_export_doc = Path(repository_export_checklist.get("files", {}).get("checklist", ""))
    repository_export_screenshots = Path(repository_export_checklist.get("files", {}).get("screenshot_capture_pass", ""))
    repository_export_tree = Path(repository_export_checklist.get("files", {}).get("repository_tree", ""))
    repository_export_notes = Path(repository_export_checklist.get("files", {}).get("readme_final_review_notes", ""))
    repository_export_zip = Path(repository_export_checklist.get("files", {}).get("zip", ""))
    if not repository_export_html.exists() or repository_export_html.stat().st_size < 1000 or "Final Repository Export Checklist" not in repository_export_html.read_text(encoding="utf-8"):
        fail("repository export checklist HTML output missing expected content")
    if not repository_export_doc.exists() or "Final Repository Export Checklist" not in repository_export_doc.read_text(encoding="utf-8"):
        fail("repository export checklist Markdown missing expected content")
    if not repository_export_screenshots.exists() or "Screenshot Capture Pass" not in repository_export_screenshots.read_text(encoding="utf-8"):
        fail("repository export screenshot pass missing expected content")
    if not repository_export_tree.exists() or "Public Repository Tree" not in repository_export_tree.read_text(encoding="utf-8"):
        fail("repository export tree missing expected content")
    if not repository_export_notes.exists() or "README Final Review Notes" not in repository_export_notes.read_text(encoding="utf-8"):
        fail("repository export README notes missing expected content")
    if not repository_export_zip.exists() or repository_export_zip.stat().st_size < 1000:
        fail("repository export checklist ZIP missing or too small")
    with zipfile.ZipFile(repository_export_zip) as zf:
        names = set(zf.namelist())
        if {"FINAL_REPOSITORY_EXPORT_CHECKLIST.md", "SCREENSHOT_CAPTURE_PASS.md", "PUBLIC_REPOSITORY_TREE.md", "README_FINAL_REVIEW_NOTES.md", "repository_export_checklist_manifest.json"} - names:
            fail("repository export checklist ZIP missing expected files")
    repository_export_detail = app.REPOSITORY_EXPORT_CHECKLIST.detail(repository_export_checklist_id)
    if repository_export_detail.get("checklist_id") != repository_export_checklist_id:
        fail("repository export checklist detail failed")
    repository_export_list = app.REPOSITORY_EXPORT_CHECKLIST.list_checklists(10)
    if not any(row.get("checklist_id") == repository_export_checklist_id for row in repository_export_list):
        fail("repository export checklist should appear in checklist list")
    repository_export_output = app.REPOSITORY_EXPORT_CHECKLIST.output_file(repository_export_checklist_id)
    if repository_export_output.get("path") != repository_export_zip:
        fail("repository export checklist output file failed")
    missing_repository_export = app.REPOSITORY_EXPORT_CHECKLIST.detail("missing_repository_export_checklist")
    if missing_repository_export.get("error") != "repository_export_checklist_not_found":
        fail("missing repository export checklist should return repository_export_checklist_not_found")

    pilot_meta = app.PILOTS.metadata()
    if pilot_meta.get("pilot_count", 0) < 1000:
        fail("pilot area catalog should expose inspected Geofabrik place polygons")
    kfar_saba_pilot = app.PILOTS.detail("53796999")
    if kfar_saba_pilot.get("osm_id") != "53796999":
        fail("pilot catalog should include Kfar Saba OSM place polygon")
    if kfar_saba_pilot.get("route_aware_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("Kfar Saba pilot should map to the existing route-aware workspace id")
    pilot_search = app.PILOTS.list_pilots({"q": ["Kfar Saba"], "limit": ["5"]})
    if not any(row.get("osm_id") == "53796999" for row in pilot_search):
        fail("pilot search should find Kfar Saba by English query")
    preflight = app.PREFLIGHT.safe_access_pilot(
        pilot_osm_id="53796999",
        dataset_id="israel-and-palestine-260521-free-shp-zip",
        route_aware=True,
    )
    if not preflight.get("ok"):
        fail(f"pilot preflight failed: {preflight}")
    if not preflight.get("can_start_job"):
        fail("pilot preflight should allow the selected Kfar Saba build")
    if preflight.get("source_gis_modified") is not False:
        fail("pilot preflight should preserve source GIS read-only evidence")
    if preflight.get("workspaces", {}).get("route_aware_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("pilot preflight should expose route-aware workspace id")
    if preflight.get("workspaces", {}).get("route_aware_exists") is not True:
        fail("pilot preflight should detect existing route-aware workspace")
    if preflight.get("required_layer_status") != "ready":
        fail("pilot preflight should detect required Geofabrik layers")
    if not preflight.get("pbf_enrichment", {}).get("available"):
        fail("pilot preflight should detect raw PBF availability")

    summary = app.DATA.summary()
    if summary["counts"]["pedestrian_generators"] != 391:
        fail("unexpected pedestrian generator count")
    if summary["counts"]["crossings"] != 342:
        fail("unexpected crossing count")

    candidates = app.DATA.candidates({"limit": ["5"], "min_score": ["70"]})
    if len(candidates) == 0:
        fail("candidate API returned no high-score candidates")
    if not all(row["review_wording"] == REVIEW_WORDING for row in candidates):
        fail("candidate review wording mismatch")

    features = app.DATA.map_features()
    if not features["generators"] or not features["crossings"] or not features["candidates"]:
        fail("map features are incomplete")

    sources = app.CATALOG.source_files()
    if len(sources) < 2:
        fail("catalog source count is too small")
    source_ids = {source["dataset_id"] for source in sources}
    if "israel-and-palestine-260521-free-shp-zip" not in source_ids:
        fail("shapefile ZIP source is missing from catalog")
    if "israel-and-palestine-260521-osm-pbf" not in source_ids:
        fail("OSM PBF source is missing from catalog")

    onboarding_refresh = app.ONBOARDING.refresh()
    if not onboarding_refresh.get("ok"):
        fail(f"source onboarding refresh failed: {onboarding_refresh}")
    onboarding_status = app.ONBOARDING.status()
    if onboarding_status.get("source_count") != 2:
        fail("source onboarding should detect exactly the two local source GIS files")
    if onboarding_status.get("source_gis_modified") is not False:
        fail("source onboarding status should preserve source GIS read-only evidence")
    onboarding_sources = app.ONBOARDING.sources()
    onboarding_by_id = {source.get("dataset_id"): source for source in onboarding_sources}
    zip_onboarding = onboarding_by_id.get("israel-and-palestine-260521-free-shp-zip")
    pbf_onboarding = onboarding_by_id.get("israel-and-palestine-260521-osm-pbf")
    if not zip_onboarding or not pbf_onboarding:
        fail("source onboarding should expose ZIP and PBF dataset ids")
    if len(zip_onboarding.get("layers", [])) != 20:
        fail("source onboarding should profile 20 layers from the Geofabrik ZIP")
    if zip_onboarding.get("readiness", {}).get("level") != "ready_for_safe_access_selected_pilot":
        fail("source onboarding should mark the Geofabrik ZIP ready for selected-pilot Safe Access")
    if pbf_onboarding.get("readiness", {}).get("level") != "ready_as_osm_tag_enrichment_source":
        fail("source onboarding should mark the PBF as an enrichment source")
    if "analysis_output" in str(zip_onboarding.get("path", "")):
        fail("source onboarding must exclude generated analysis_output files")
    if not (OUTPUT_ROOT / "georeview_studio_source_onboarding" / "source_onboarding_catalog.json").exists():
        fail("source onboarding JSON cache is missing")
    if not (OUTPUT_ROOT / "georeview_studio_source_onboarding" / "source_onboarding_sources.csv").exists():
        fail("source onboarding CSV cache is missing")

    profile_payload = app.PROFILES.list_profiles(
        dataset_id="israel-and-palestine-260521-free-shp-zip",
        pilot_osm_id="53796999",
        route_aware=True,
    )
    if not profile_payload.get("ok") or len(profile_payload.get("profiles", [])) < 6:
        fail(f"analysis profiles list failed: {profile_payload}")
    profiles_by_id = {profile.get("profile_id"): profile for profile in profile_payload.get("profiles", [])}
    safe_access_profile = profiles_by_id.get("safe_access_pedestrian_review")
    if not safe_access_profile or safe_access_profile.get("can_run") is not True:
        fail("Safe Access analysis profile should be runnable for Kfar Saba")
    transit_profile = profiles_by_id.get("transit_stop_walk_access")
    if not transit_profile or transit_profile.get("can_plan") is not True or transit_profile.get("can_run") is not True:
        fail("transit stop walk-access profile should expose runnable readiness")
    park_profile = profiles_by_id.get("park_playground_access")
    if not park_profile or park_profile.get("can_plan") is not True or park_profile.get("can_run") is not True:
        fail("park and playground access profile should expose runnable readiness")
    profile_detail = app.PROFILES.detail(
        "safe_access_pedestrian_review",
        dataset_id="israel-and-palestine-260521-free-shp-zip",
        pilot_osm_id="53796999",
    )
    if profile_detail.get("readiness", {}).get("readiness_level") != "ready_to_run":
        fail("Safe Access profile detail should include ready_to_run readiness")
    profile_plan = app.plan_analysis_profile("safe_access_pedestrian_review", {
        "dataset_id": "israel-and-palestine-260521-free-shp-zip",
        "pilot_osm_id": "53796999",
        "route_aware": True,
    })
    if not profile_plan.get("ok") or not profile_plan.get("can_start_job"):
        fail(f"analysis profile plan adapter failed: {profile_plan}")
    missing_profile = app.PROFILES.detail("missing_profile")
    if missing_profile.get("error") != "analysis_profile_not_found":
        fail("missing analysis profile should return analysis_profile_not_found")
    runners = app.list_profile_runners()
    if not runners.get("ok") or not any(row.get("profile_id") == "transit_stop_walk_access" for row in runners.get("runners", [])):
        fail("profile runners should expose transit_stop_walk_access")
    if not any(row.get("profile_id") == "park_playground_access" for row in runners.get("runners", [])):
        fail("profile runners should expose park_playground_access")
    osm_profile = profiles_by_id.get("osm_tag_quality")
    if not osm_profile or osm_profile.get("can_plan") is not True or osm_profile.get("can_run") is not True:
        fail("OSM tag quality profile should expose runnable readiness")
    if not any(row.get("profile_id") == "osm_tag_quality" for row in runners.get("runners", [])):
        fail("profile runners should expose osm_tag_quality")
    osm_status = app.OSM_TAG_QUALITY.status()
    if not osm_status.get("ok") or osm_status.get("summary", {}).get("counts", {}).get("tag_count_rows") != 482:
        fail(f"OSM tag quality status failed: {osm_status}")
    osm_run = app.run_profile("osm_tag_quality", {"workspace_id": "osm_tag_quality_kfar_saba_v001"})
    if not osm_run.get("ok"):
        fail(f"OSM tag quality runner failed: {osm_run}")
    osm_summary = osm_run.get("workspace", {}).get("summary", {})
    osm_counts = osm_summary.get("counts", {})
    if osm_counts.get("tag_count_rows") != 482 or osm_counts.get("source_count") != 2 or osm_counts.get("scope_count") != 2:
        fail(f"OSM tag quality summary counts failed: {osm_summary}")
    if osm_counts.get("key_tag_count", 0) < 10 or osm_counts.get("shapefile_not_preserved_count", 0) < 2 or osm_counts.get("pbf_presence_rows", 0) <= 0:
        fail(f"OSM tag quality evidence counts failed: {osm_summary}")
    osm_results = app.profile_workspace_results("osm_tag_quality_kfar_saba_v001", 5)
    if not isinstance(osm_results, list) or len(osm_results) != 5:
        fail("OSM tag quality profile results should return rows")
    osm_output = app.profile_workspace_output_file("osm_tag_quality_kfar_saba_v001", "tag_quality_summary")
    if not osm_output.get("ok") or not osm_output.get("path", Path()).exists():
        fail("OSM tag quality output resolver failed")
    transit_run = app.run_profile("transit_stop_walk_access", {
        "base_workspace_id": "safe_access_kfar_saba_route_aware_v001",
        "workspace_id": "transit_stop_walk_access_kfar_saba_v001",
    })
    if not transit_run.get("ok"):
        fail(f"transit profile runner failed: {transit_run}")
    transit_summary = transit_run.get("workspace", {}).get("summary", {})
    if transit_summary.get("counts", {}).get("transit_stops") != 180:
        fail("transit profile should expose 180 bus stops")
    if transit_summary.get("source_gis_modified") is not False:
        fail("transit profile summary should preserve source read-only evidence")
    transit_workspaces = app.TRANSIT.list_workspaces()
    if not any(row.get("workspace_id") == "transit_stop_walk_access_kfar_saba_v001" for row in transit_workspaces):
        fail("transit profile workspace should be visible")
    transit_results = app.TRANSIT.results("transit_stop_walk_access_kfar_saba_v001", 5)
    if not isinstance(transit_results, list) or len(transit_results) != 5:
        fail("transit profile results should return rows")
    transit_output = app.TRANSIT.output_file("transit_stop_walk_access_kfar_saba_v001", "transit_stop_access_results")
    if not transit_output.get("ok") or not transit_output.get("path", Path()).exists():
        fail("transit profile output resolver failed")
    park_run = app.run_profile("park_playground_access", {
        "base_workspace_id": "safe_access_kfar_saba_route_aware_v001",
        "workspace_id": "park_playground_access_kfar_saba_v001",
    })
    if not park_run.get("ok"):
        fail(f"park profile runner failed: {park_run}")
    park_summary = park_run.get("workspace", {}).get("summary", {})
    if park_summary.get("counts", {}).get("public_spaces") != 145:
        fail("park profile should expose 145 public spaces")
    if park_summary.get("counts", {}).get("parks") != 103:
        fail("park profile should expose 103 parks")
    if park_summary.get("counts", {}).get("playgrounds") != 39:
        fail("park profile should expose 39 playgrounds")
    if park_summary.get("source_gis_modified") is not False:
        fail("park profile summary should preserve source read-only evidence")
    profile_workspaces = app.list_profile_workspaces()
    if not any(row.get("workspace_id") == "park_playground_access_kfar_saba_v001" for row in profile_workspaces):
        fail("park profile workspace should be visible")
    park_results = app.profile_workspace_results("park_playground_access_kfar_saba_v001", 5)
    if not isinstance(park_results, list) or len(park_results) != 5:
        fail("park profile results should return rows")
    park_output = app.profile_workspace_output_file("park_playground_access_kfar_saba_v001", "park_playground_access_results")
    if not park_output.get("ok") or not park_output.get("path", Path()).exists():
        fail("park profile output resolver failed")
    park_profile_report = app.PORTFOLIO_REPORTS.generate_from_profile_workspace("park_playground_access_kfar_saba_v001")
    if not park_profile_report.get("ok"):
        fail(f"park profile portfolio report generation failed: {park_profile_report}")
    park_profile_report_id = park_profile_report.get("report_id")
    park_profile_markdown = Path(park_profile_report.get("markdown_file", ""))
    if not park_profile_report_id or not park_profile_markdown.exists():
        fail("park profile report file was not created")
    park_profile_detail = app.PORTFOLIO_REPORTS.detail(park_profile_report_id)
    if park_profile_detail.get("report_type") != "profile_workspace":
        fail("park profile report should use profile_workspace report type")
    if park_profile_detail.get("profile_id") != "park_playground_access":
        fail("park profile report should expose profile_id")
    if park_profile_detail.get("counts", {}).get("public_spaces") != 145:
        fail("park profile report should include public-space count evidence")
    if len(park_profile_detail.get("top_public_spaces", [])) == 0:
        fail("park profile report should include a top public-space sample")
    park_profile_text = park_profile_markdown.read_text(encoding="utf-8")
    if REVIEW_WORDING not in park_profile_text:
        fail("park profile report is missing approved review wording")
    if any(term in park_profile_text.lower() for term in FORBIDDEN_TERMS):
        fail("park profile report contains absolute safety claim wording")
    if park_profile_detail.get("source_gis_modified") is not False:
        fail("park profile report should preserve source read-only evidence")
    profile_comparison = app.generate_profile_comparison_report({
        "base_workspace_id": "safe_access_kfar_saba_route_aware_v001",
        "profile_workspace_ids": [
            "transit_stop_walk_access_kfar_saba_v001",
            "park_playground_access_kfar_saba_v001",
        ],
    })
    if not profile_comparison.get("ok"):
        fail(f"profile comparison report generation failed: {profile_comparison}")
    profile_comparison_id = profile_comparison.get("report_id")
    profile_comparison_markdown = Path(profile_comparison.get("markdown_file", ""))
    if not profile_comparison_id or not profile_comparison_markdown.exists():
        fail("profile comparison report file was not created")
    profile_comparison_detail = app.PORTFOLIO_REPORTS.detail(profile_comparison_id)
    if profile_comparison_detail.get("report_type") != "profile_comparison":
        fail("profile comparison should use profile_comparison report type")
    if len(profile_comparison_detail.get("profiles", [])) != 2:
        fail("profile comparison should include two profile workspaces")
    if len(profile_comparison_detail.get("comparison_rows", [])) != 3:
        fail("profile comparison should include Safe Access, Transit, and Park rows")
    profile_ids = {row.get("profile_id") for row in profile_comparison_detail.get("comparison_rows", [])}
    if {"safe_access_pedestrian_review", "transit_stop_walk_access", "park_playground_access"} - profile_ids:
        fail("profile comparison rows should cover all implemented profiles")
    if profile_comparison_detail.get("base_profile", {}).get("generator_counts", {}).get("bus_stops") != 180:
        fail("profile comparison should expose Safe Access bus stop count")
    if profile_comparison_detail.get("source_gis_modified") is not False:
        fail("profile comparison should preserve source read-only evidence")
    profile_comparison_text = profile_comparison_markdown.read_text(encoding="utf-8")
    if REVIEW_WORDING not in profile_comparison_text:
        fail("profile comparison report is missing approved review wording")
    if any(term in profile_comparison_text.lower() for term in FORBIDDEN_TERMS):
        fail("profile comparison report contains absolute safety claim wording")
    authored_profile_report = app.PORTFOLIO_REPORTS.generate_from_profile_workspace(authored_workspace_id)
    if not authored_profile_report.get("ok"):
        fail(f"authored profile portfolio report generation failed: {authored_profile_report}")
    authored_profile_report_id = authored_profile_report.get("report_id")
    authored_profile_detail = app.PORTFOLIO_REPORTS.detail(authored_profile_report_id)
    if authored_profile_detail.get("profile_id") != "cycling_micromobility_access":
        fail(f"authored profile report detail failed: {authored_profile_detail}")
    if authored_profile_detail.get("counts", {}).get("result_rows") != authored_counts.get("result_rows"):
        fail("authored profile report should expose authored result row count")
    if len(authored_profile_detail.get("top_authored_results", [])) == 0:
        fail("authored profile report should include authored result sample")
    authored_profile_text = Path(authored_profile_report.get("markdown_file", "")).read_text(encoding="utf-8")
    if REVIEW_WORDING not in authored_profile_text:
        fail("authored profile report is missing approved review wording")
    profile_bundle = app.PROFILE_EXPORT_BUNDLES.generate({})
    if not profile_bundle.get("ok") or profile_bundle.get("profile_count", 0) < 4:
        fail(f"profile dashboard export bundle generation failed: {profile_bundle}")
    profile_bundle_id = profile_bundle.get("bundle_id")
    profile_bundle_detail = app.PROFILE_EXPORT_BUNDLES.detail(profile_bundle_id)
    if profile_bundle_detail.get("bundle_type") != "profile_dashboard_export_bundle":
        fail("profile dashboard export bundle detail failed")
    if profile_bundle_detail.get("profile_count", 0) < 4:
        fail("profile dashboard export bundle should include authored profiles")
    if profile_bundle_detail.get("source_gis_modified") is not False:
        fail("profile dashboard export bundle should preserve source read-only evidence")
    profile_bundle_file = app.PROFILE_EXPORT_BUNDLES.bundle_file(profile_bundle_id)
    if not profile_bundle_file.get("ok") or not profile_bundle_file.get("path", Path()).exists():
        fail("profile dashboard export bundle file resolver failed")
    profile_bundle_text = profile_bundle_file.get("path").read_text(encoding="utf-8")
    if REVIEW_WORDING not in profile_bundle_text:
        fail("profile dashboard export bundle is missing approved review wording")
    if any(term in profile_bundle_text.lower() for term in FORBIDDEN_TERMS):
        fail("profile dashboard export bundle contains absolute safety claim wording")
    if not any(row.get("bundle_id") == profile_bundle_id for row in app.PROFILE_EXPORT_BUNDLES.list_bundles(10)):
        fail("profile dashboard export bundle list should include generated bundle")
    transit_profile_report = app.PORTFOLIO_REPORTS.generate_from_profile_workspace("transit_stop_walk_access_kfar_saba_v001")
    if not transit_profile_report.get("ok"):
        fail(f"transit profile portfolio report generation failed: {transit_profile_report}")
    transit_profile_report_id = transit_profile_report.get("report_id")
    transit_profile_markdown = Path(transit_profile_report.get("markdown_file", ""))
    transit_profile_json = Path(transit_profile_report.get("json_file", ""))
    if not transit_profile_report_id or not transit_profile_markdown.exists() or not transit_profile_json.exists():
        fail("transit profile report files were not created")
    transit_profile_detail = app.PORTFOLIO_REPORTS.detail(transit_profile_report_id)
    if transit_profile_detail.get("report_type") != "profile_workspace":
        fail("transit profile report should use profile_workspace report type")
    if transit_profile_detail.get("profile_id") != "transit_stop_walk_access":
        fail("transit profile report should expose profile_id")
    if transit_profile_detail.get("counts", {}).get("transit_stops") != 180:
        fail("transit profile report should include transit stop count evidence")
    if len(transit_profile_detail.get("top_transit_stops", [])) == 0:
        fail("transit profile report should include a top transit stop sample")
    transit_profile_text = transit_profile_markdown.read_text(encoding="utf-8")
    if REVIEW_WORDING not in transit_profile_text:
        fail("transit profile report is missing approved review wording")
    if any(term in transit_profile_text.lower() for term in FORBIDDEN_TERMS):
        fail("transit profile report contains absolute safety claim wording")
    if transit_profile_detail.get("source_gis_modified") is not False:
        fail("transit profile report should preserve source read-only evidence")

    analysis_payload = {
        "dataset_id": "israel-and-palestine-260521-free-shp-zip",
        "pilot_osm_id": "53796999",
        "template_id": "safe_access",
        "route_aware": True,
    }
    analysis_plan = app.ANALYSIS.plan(analysis_payload)
    if not analysis_plan.get("ok"):
        fail(f"analysis workflow plan failed: {analysis_plan}")
    if not analysis_plan.get("can_start_job"):
        fail("analysis workflow plan should be startable for Kfar Saba")
    if analysis_plan.get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("analysis workflow plan should expose the route-aware active workspace")
    if analysis_plan.get("source_gis_modified") is not False:
        fail("analysis workflow plan should preserve source GIS read-only evidence")
    step_statuses = {step.get("step"): step.get("status") for step in analysis_plan.get("steps", [])}
    if step_statuses.get("source_onboarding") != "ready" or step_statuses.get("pilot_preflight") != "ready":
        fail("analysis workflow should connect source onboarding and pilot preflight readiness")
    analysis_start = app.start_analysis_workflow(analysis_payload)
    if not analysis_start.get("ok"):
        fail(f"analysis workflow start failed: {analysis_start}")
    analysis_job_id = analysis_start.get("job", {}).get("job_id")
    if not analysis_job_id:
        fail("analysis workflow start should return a job id")
    for _ in range(50):
        analysis_job_detail = app.JOBS.detail(analysis_job_id)
        if analysis_job_detail.get("status") in {"succeeded", "failed"}:
            break
        time.sleep(0.1)
    if analysis_job_detail.get("status") != "succeeded":
        fail(f"analysis workflow job did not succeed: {analysis_job_detail}")
    if analysis_job_detail.get("result", {}).get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("analysis workflow job should finish with the active route-aware workspace")
    analysis_runs = app.ANALYSIS_RUNS.list(20)
    if not any(run.get("run_id") == analysis_job_id for run in analysis_runs):
        fail("analysis workflow job should be visible in Analysis Runs")
    analysis_run_detail = app.ANALYSIS_RUNS.detail(analysis_job_id)
    if not analysis_run_detail.get("ok"):
        fail(f"analysis run detail failed: {analysis_run_detail}")
    if analysis_run_detail.get("run", {}).get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("analysis run detail should expose active workspace")
    if len(analysis_run_detail.get("outputs", [])) < 6:
        fail("analysis run detail should expose workspace outputs")
    risk_output = next((item for item in analysis_run_detail.get("outputs", []) if item.get("output_id") == "table_risk_assessment_results"), None)
    if not risk_output or not Path(risk_output.get("path", "")).exists():
        fail("analysis run should expose risk assessment CSV output")
    output_file = app.ANALYSIS_RUNS.output_file(analysis_job_id, risk_output["output_id"])
    if not output_file.get("ok") or not output_file.get("path", Path()).exists():
        fail("analysis run output download resolver failed")
    rerun = app.rerun_analysis_run(analysis_job_id)
    if not rerun.get("ok"):
        fail(f"analysis run rerun failed: {rerun}")
    rerun_job_id = rerun.get("job", {}).get("job_id")
    if not rerun_job_id:
        fail("analysis run rerun should return a job id")
    for _ in range(50):
        rerun_job_detail = app.JOBS.detail(rerun_job_id)
        if rerun_job_detail.get("status") in {"succeeded", "failed"}:
            break
        time.sleep(0.1)
    if rerun_job_detail.get("status") != "succeeded":
        fail(f"analysis run rerun job did not succeed: {rerun_job_detail}")
    portfolio_report = app.PORTFOLIO_REPORTS.generate_from_run(analysis_job_id)
    if not portfolio_report.get("ok"):
        fail(f"portfolio report generation failed: {portfolio_report}")
    portfolio_report_id = portfolio_report.get("report_id")
    portfolio_markdown = Path(portfolio_report.get("markdown_file", ""))
    portfolio_json = Path(portfolio_report.get("json_file", ""))
    if not portfolio_report_id or not portfolio_markdown.exists() or not portfolio_json.exists():
        fail("portfolio report files were not created")
    portfolio_text = portfolio_markdown.read_text(encoding="utf-8")
    if REVIEW_WORDING not in portfolio_text:
        fail("portfolio report is missing approved review wording")
    if any(term in portfolio_text.lower() for term in FORBIDDEN_TERMS):
        fail("portfolio report contains absolute safety claim wording")
    portfolio_detail = app.PORTFOLIO_REPORTS.detail(portfolio_report_id)
    if portfolio_detail.get("report_id") != portfolio_report_id:
        fail("portfolio report detail failed")
    if portfolio_detail.get("counts", {}).get("pedestrian_generators") != 391:
        fail("portfolio report should include workspace count evidence")
    portfolio_file = app.PORTFOLIO_REPORTS.report_file(portfolio_report_id)
    if not portfolio_file.get("ok") or portfolio_file.get("path") != portfolio_markdown:
        fail("portfolio report download resolver failed")
    portfolio_compare = app.PORTFOLIO_REPORTS.compare_runs([analysis_job_id, rerun_job_id])
    if not portfolio_compare.get("ok"):
        fail(f"portfolio compare generation failed: {portfolio_compare}")
    portfolio_compare_id = portfolio_compare.get("report_id")
    portfolio_compare_detail = app.PORTFOLIO_REPORTS.detail(portfolio_compare_id)
    if len(portfolio_compare_detail.get("runs", [])) < 2:
        fail("portfolio compare report should include at least two runs")
    portfolio_reports = app.PORTFOLIO_REPORTS.list_reports(20)
    if not any(report.get("report_id") == portfolio_report_id for report in portfolio_reports):
        fail("portfolio report list should include generated report")

    zip_profile = app.CATALOG.profile("israel-and-palestine-260521-free-shp-zip")
    if zip_profile.get("dataset", {}).get("layer_count", 0) < 10:
        fail("shapefile ZIP profile does not expose expected layers")
    if not zip_profile.get("tag_summary", {}).get("important_categories"):
        fail("tag summary is missing important categories")

    check = app.CATALOG.safe_access_check("israel-and-palestine-260521-free-shp-zip")
    if check.get("template_id") != "safe_access":
        fail("safe access template check failed")
    if "readiness" not in check:
        fail("template readiness is missing")

    templates = app.CATALOG.templates()
    if not any(template["template_id"] == "safe_access" for template in templates):
        fail("safe access template is missing")

    run = app.RUNNER.ensure_safe_access_kfar_saba("israel-and-palestine-260521-free-shp-zip")
    if not run.get("ok"):
        fail(f"workspace runner failed: {run}")
    workspace = run.get("workspace", {})
    manifest = workspace.get("manifest", {})
    if manifest.get("workspace_id") != "safe_access_kfar_saba_v001":
        fail("generated workspace id mismatch")
    if manifest.get("source_gis_modified") is not False:
        fail("workspace manifest does not prove source GIS read-only behavior")
    if len(manifest.get("tables", [])) < 5:
        fail("generated workspace has too few canonical tables")
    summary_report = workspace.get("summary", {})
    if summary_report.get("counts", {}).get("pedestrian_generators") != 391:
        fail("workspace summary pedestrian generator count mismatch")
    quality_report = workspace.get("quality_report", {})
    if not quality_report.get("data_quality_principles"):
        fail("workspace quality report is missing")
    registry = app.RUNNER.list_workspaces()
    if not any(item["workspace_id"] == "safe_access_kfar_saba_v001" for item in registry):
        fail("generated workspace is missing from registry")

    generic_run = app.RUNNER.build_safe_access_generic(
        "israel-and-palestine-260521-free-shp-zip",
        pilot_osm_id="53796999",
        pilot_name="Kfar Saba",
        workspace_id="safe_access_kfar_saba_pbf_enriched_v001",
    )
    if not generic_run.get("ok"):
        fail(f"generic mapper failed: {generic_run}")
    generic_workspace = generic_run.get("workspace", {})
    generic_manifest = generic_workspace.get("manifest", {})
    if generic_manifest.get("workspace_id") != "safe_access_kfar_saba_pbf_enriched_v001":
        fail("PBF-enriched workspace id mismatch")
    if generic_manifest.get("mapper") != "geofabrik_zip_plus_osm_pbf_v001":
        fail("PBF-enriched mapper id mismatch")
    if generic_manifest.get("source_gis_modified") is not False:
        fail("generic workspace does not prove source GIS read-only behavior")
    if generic_manifest.get("raw_pbf_enrichment_used") is not True:
        fail("PBF-enriched mapper should declare raw PBF enrichment as true")
    generic_summary = generic_workspace.get("summary", {})
    generic_counts = generic_summary.get("counts", {})
    if generic_counts.get("pedestrian_generators") != 391:
        fail("PBF-enriched workspace should recover 391 pedestrian generators")
    if generic_counts.get("childcare") != 1:
        fail("PBF-enriched workspace should recover one childcare generator")
    if generic_counts.get("crossings") != 342:
        fail("PBF-enriched workspace crossing count mismatch")
    if generic_counts.get("road_segments") != 2603:
        fail("PBF-enriched workspace road segment count mismatch")
    if generic_counts.get("traffic_calming_features", 0) < 1:
        fail("PBF-enriched workspace should recover traffic calming features")
    generic_validation = generic_summary.get("validation", {})
    if generic_validation.get("pbf_points", 0) < 1 or generic_validation.get("pbf_lines", 0) < 1:
        fail("PBF enrichment did not read PBF points and lines")
    if not generic_summary.get("validation", {}).get("passed"):
        fail("generic workspace validation did not pass")
    registry = app.RUNNER.list_workspaces()
    if not any(item["workspace_id"] == "safe_access_kfar_saba_pbf_enriched_v001" for item in registry):
        fail("PBF-enriched workspace is missing from registry")

    dashboard_summary = app.DASHBOARDS.summary("safe_access_kfar_saba_pbf_enriched_v001")
    if dashboard_summary.get("counts", {}).get("pedestrian_generators") != 391:
        fail("workspace-aware dashboard summary generator count mismatch")
    if dashboard_summary.get("generator_types", {}).get("childcare") != 1:
        fail("workspace-aware dashboard summary did not expose childcare generator type")
    dashboard_candidates = app.DASHBOARDS.candidates(
        "safe_access_kfar_saba_pbf_enriched_v001",
        {"limit": ["5"], "min_score": ["70"]},
    )
    if not isinstance(dashboard_candidates, list) or len(dashboard_candidates) == 0:
        fail("workspace-aware dashboard candidates returned no rows")
    dashboard_features = app.DASHBOARDS.map_features("safe_access_kfar_saba_pbf_enriched_v001")
    if len(dashboard_features.get("generators", [])) != 391:
        fail("workspace-aware map features generator count mismatch")
    if len(dashboard_features.get("crossings", [])) != 342:
        fail("workspace-aware map features crossing count mismatch")
    generic_zip_summary = app.DASHBOARDS.summary("safe_access_kfar_saba_generic_v001")
    if generic_zip_summary.get("counts", {}).get("pedestrian_generators") != 390:
        fail("workspace-aware dashboard cannot read the older generic ZIP workspace")

    route_run = app.NETWORK.ensure_route_aware_workspace(
        "safe_access_kfar_saba_pbf_enriched_v001",
        "safe_access_kfar_saba_route_aware_v001",
    )
    if not route_run.get("ok"):
        fail(f"route-aware workspace build failed: {route_run}")
    route_workspace = route_run.get("workspace", {})
    route_manifest = route_workspace.get("manifest", {})
    if route_manifest.get("workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("route-aware workspace id mismatch")
    if route_manifest.get("source_gis_modified") is not False:
        fail("route-aware workspace does not preserve source GIS read-only behavior")
    if route_manifest.get("route_aware_analysis_used") is not True:
        fail("route-aware workspace manifest should declare route-aware analysis")
    route_summary = app.DASHBOARDS.summary("safe_access_kfar_saba_route_aware_v001")
    route_analysis = route_summary.get("route_aware_analysis", {})
    if route_analysis.get("rows") != 391:
        fail("route-aware analysis should contain one row per generator")
    if route_analysis.get("network_nodes", 0) < 1000:
        fail("route-aware graph node count is too small")
    if route_analysis.get("route_reachable_generators", 0) < 350:
        fail("route-aware reachable generator count is too small")
    if route_analysis.get("median_route_nearest_crossing_m", 0) <= 0:
        fail("route-aware median distance should be positive")
    route_candidates = app.DASHBOARDS.candidates(
        "safe_access_kfar_saba_route_aware_v001",
        {"limit": ["5"], "min_score": ["70"]},
    )
    if not isinstance(route_candidates, list) or len(route_candidates) == 0:
        fail("route-aware dashboard candidates returned no rows")
    if not route_candidates[0].get("route_aware_available"):
        fail("route-aware candidates are not enriched with network fields")
    if route_candidates[0].get("route_review_priority_score", 0) < route_candidates[0].get("risk_score", 0):
        fail("route-aware priority score should not be lower than base risk score")
    route_network_rows = app.DASHBOARDS.network_access(
        "safe_access_kfar_saba_route_aware_v001",
        {"limit": ["5"], "min_route_score": ["90"]},
    )
    if not isinstance(route_network_rows, list) or len(route_network_rows) == 0:
        fail("route-aware network access endpoint returned no rows")
    pilot_run = app.build_pilot_workspace({
        "pilot_osm_id": "53796999",
        "pilot_name": "כפר סבא",
        "workspace_id": "safe_access_kfar_saba_pbf_enriched_v001",
        "route_workspace_id": "safe_access_kfar_saba_route_aware_v001",
        "route_aware": True,
    })
    if not pilot_run.get("ok"):
        fail(f"pilot workspace runner failed: {pilot_run}")
    if pilot_run.get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("pilot workspace runner should return the route-aware workspace as active")
    job = app.JOBS.start("safe_access_pilot", {
        "pilot_osm_id": "53796999",
        "pilot_name": "Kfar Saba",
        "workspace_id": "safe_access_kfar_saba_pbf_enriched_v001",
        "route_workspace_id": "safe_access_kfar_saba_route_aware_v001",
        "route_aware": True,
    }, app.build_pilot_workspace)
    job_id = job.get("job_id")
    if not job_id:
        fail("background pilot job did not return a job id")
    for _ in range(50):
        job_detail = app.JOBS.detail(job_id)
        if job_detail.get("status") in {"succeeded", "failed"}:
            break
        time.sleep(0.1)
    if job_detail.get("status") != "succeeded":
        fail(f"background pilot job did not succeed: {job_detail}")
    if job_detail.get("result", {}).get("active_workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("background pilot job should expose active route-aware workspace")
    if job_detail.get("source_gis_modified") is not False:
        fail("background job should preserve source GIS read-only evidence")
    if len(job_detail.get("logs", [])) < 3:
        fail("background job should record progress logs")
    job_registry = app.JOBS.list(10)
    if not any(item.get("job_id") == job_id for item in job_registry):
        fail("background job should be visible in job history")

    release_readiness = app.RELEASE_READINESS.overview()
    if not release_readiness.get("ok") or release_readiness.get("release_readiness_version") != "release_readiness_dashboard_v001":
        fail(f"release readiness overview failed: {release_readiness}")
    release_summary = release_readiness.get("summary", {})
    if release_summary.get("gate_count", 0) < 15 or release_summary.get("failed_gate_count", 0) != 0:
        fail(f"release readiness gates should have no failed gates: {release_summary}")
    if release_readiness.get("source_gis_modified") is not False or release_readiness.get("mutates_config") is not False:
        fail("release readiness must not mutate source GIS or mapper config")
    if not any(gate.get("gate_id") == "promotion_lifecycle_gates" for gate in release_readiness.get("gates", [])):
        fail("release readiness should include promotion lifecycle gates")
    release_gates = app.RELEASE_READINESS.gates_response()
    if release_gates.get("gate_count") != release_summary.get("gate_count") or release_gates.get("failed_gate_count") != 0:
        fail(f"release readiness gates response failed: {release_gates}")
    release_snapshot_result = app.RELEASE_READINESS.create_snapshot({"created_by": "validate_app", "notes": "Validation-created v053 readiness snapshot."})
    if not release_snapshot_result.get("ok") or release_snapshot_result.get("snapshot", {}).get("mutates_config") is not False:
        fail(f"release readiness snapshot failed: {release_snapshot_result}")
    release_snapshot = release_snapshot_result.get("snapshot", {})
    release_readiness_snapshot_id = release_snapshot.get("snapshot_id")
    for output_path in release_snapshot.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"release readiness snapshot output missing: {output_path}")
    release_snapshot_detail = app.RELEASE_READINESS.snapshot_detail(release_readiness_snapshot_id)
    if release_snapshot_detail.get("snapshot_id") != release_readiness_snapshot_id:
        fail("release readiness snapshot detail failed")
    release_snapshot_list = app.RELEASE_READINESS.list_snapshots(10)
    if not any(row.get("snapshot_id") == release_readiness_snapshot_id for row in release_snapshot_list):
        fail("release readiness snapshot should appear in snapshot list")
    missing_release_snapshot = app.RELEASE_READINESS.snapshot_detail("missing_snapshot")
    if missing_release_snapshot.get("error") != "release_readiness_snapshot_not_found":
        fail("missing release readiness snapshot should return release_readiness_snapshot_not_found")

    portfolio_demo = app.PORTFOLIO_DEMO.overview()
    if not portfolio_demo.get("ok") or portfolio_demo.get("portfolio_demo_version") != "portfolio_demo_walkthrough_v001":
        fail(f"portfolio demo overview failed: {portfolio_demo}")
    if portfolio_demo.get("step_count", 0) < 7 or portfolio_demo.get("source_gis_modified") is not False or portfolio_demo.get("mutates_config") is not False:
        fail(f"portfolio demo should expose at least seven non-mutating steps: {portfolio_demo}")
    demo_step_ids = {step.get("step_id") for step in portfolio_demo.get("steps", [])}
    for required_step in {"opening_positioning", "data_intake_evidence", "safe_access_profile", "quality_and_governance", "portfolio_outputs"}:
        if required_step not in demo_step_ids:
            fail(f"portfolio demo missing step: {required_step}")
    portfolio_demo_steps = app.PORTFOLIO_DEMO.steps_response()
    if portfolio_demo_steps.get("step_count") != portfolio_demo.get("step_count"):
        fail("portfolio demo steps response should match overview")
    portfolio_demo_snapshot_result = app.PORTFOLIO_DEMO.create_snapshot({"created_by": "validate_app", "notes": "Validation-created v053 demo snapshot."})
    if not portfolio_demo_snapshot_result.get("ok") or portfolio_demo_snapshot_result.get("snapshot", {}).get("mutates_config") is not False:
        fail(f"portfolio demo snapshot failed: {portfolio_demo_snapshot_result}")
    portfolio_demo_snapshot = portfolio_demo_snapshot_result.get("snapshot", {})
    portfolio_demo_snapshot_id = portfolio_demo_snapshot.get("snapshot_id")
    for output_path in portfolio_demo_snapshot.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"portfolio demo snapshot output missing: {output_path}")
    portfolio_demo_snapshot_detail = app.PORTFOLIO_DEMO.snapshot_detail(portfolio_demo_snapshot_id)
    if portfolio_demo_snapshot_detail.get("snapshot_id") != portfolio_demo_snapshot_id:
        fail("portfolio demo snapshot detail failed")
    portfolio_demo_snapshot_list = app.PORTFOLIO_DEMO.list_snapshots(10)
    if not any(row.get("snapshot_id") == portfolio_demo_snapshot_id for row in portfolio_demo_snapshot_list):
        fail("portfolio demo snapshot should appear in snapshot list")
    missing_portfolio_demo_snapshot = app.PORTFOLIO_DEMO.snapshot_detail("missing_snapshot")
    if missing_portfolio_demo_snapshot.get("error") != "portfolio_demo_snapshot_not_found":
        fail("missing portfolio demo snapshot should return portfolio_demo_snapshot_not_found")

    sys.path.insert(0, str(PROJECT_DIR / "scripts"))
    import generate_portfolio_artifacts  # noqa: PLC0415

    generate_portfolio_artifacts.main()
    portfolio_required = [
        PORTFOLIO_DIR / "index.html",
        PORTFOLIO_DIR / "assets" / "kfar_saba_static_map.svg",
        PORTFOLIO_DIR / "sample_review_candidates_top20.csv",
        PORTFOLIO_DIR / "case_study.md",
        PORTFOLIO_DIR / "portfolio_pitch.md",
        PORTFOLIO_DIR / "portfolio_manifest.json",
    ]
    for path in portfolio_required:
        if not path.exists() or path.stat().st_size <= 0:
            fail(f"portfolio artifact missing or empty: {path}")
    portfolio_manifest = json.loads((PORTFOLIO_DIR / "portfolio_manifest.json").read_text(encoding="utf-8"))
    if portfolio_manifest.get("workspace_id") != "safe_access_kfar_saba_route_aware_v001":
        fail("portfolio manifest workspace mismatch")
    sample_rows = sum(1 for _ in (PORTFOLIO_DIR / "sample_review_candidates_top20.csv").open("r", encoding="utf-8-sig")) - 1
    if sample_rows != 20:
        fail("portfolio sample export should contain 20 rows")

    portfolio_bundle_status = app.PORTFOLIO_EVIDENCE_BUNDLE.status()
    if not portfolio_bundle_status.get("ok") or portfolio_bundle_status.get("portfolio_evidence_bundle_version") != "portfolio_evidence_bundle_v001":
        fail(f"portfolio evidence bundle status failed: {portfolio_bundle_status}")
    portfolio_bundle_result = app.PORTFOLIO_EVIDENCE_BUNDLE.create_bundle({"created_by": "validate_app", "notes": "Validation-created v053 portfolio evidence bundle.", "reuse_latest": True})
    if not portfolio_bundle_result.get("ok") or portfolio_bundle_result.get("bundle", {}).get("mutates_config") is not False:
        fail(f"portfolio evidence bundle creation failed: {portfolio_bundle_result}")
    portfolio_bundle = portfolio_bundle_result.get("bundle", {})
    portfolio_evidence_bundle_id = portfolio_bundle.get("bundle_id")
    if portfolio_bundle.get("copied_file_count", 0) < 8 or portfolio_bundle.get("source_gis_modified") is not False:
        fail(f"portfolio evidence bundle should copy generated evidence only: {portfolio_bundle}")
    for output_path in portfolio_bundle.get("files", {}).values():
        if output_path and output_path != portfolio_bundle.get("files", {}).get("directory") and not Path(output_path).exists():
            fail(f"portfolio evidence bundle output missing: {output_path}")
    for item in portfolio_bundle.get("copied_files", []):
        if not Path(str(item.get("bundle_path") or "")).exists():
            fail(f"portfolio evidence copied file missing: {item}")
    portfolio_bundle_detail = app.PORTFOLIO_EVIDENCE_BUNDLE.detail(portfolio_evidence_bundle_id)
    if portfolio_bundle_detail.get("bundle_id") != portfolio_evidence_bundle_id:
        fail("portfolio evidence bundle detail failed")
    portfolio_bundle_list = app.PORTFOLIO_EVIDENCE_BUNDLE.list_bundles(10)
    if not any(row.get("bundle_id") == portfolio_evidence_bundle_id for row in portfolio_bundle_list):
        fail("portfolio evidence bundle should appear in bundle list")
    portfolio_bundle_file = app.PORTFOLIO_EVIDENCE_BUNDLE.output_file(portfolio_evidence_bundle_id, "portfolio_evidence_bundle_report")
    if not portfolio_bundle_file.get("ok") or not Path(portfolio_bundle_file.get("path", "")).exists():
        fail("portfolio evidence bundle output file failed")
    missing_portfolio_bundle = app.PORTFOLIO_EVIDENCE_BUNDLE.detail("missing_bundle")
    if missing_portfolio_bundle.get("error") != "portfolio_evidence_bundle_not_found":
        fail("missing portfolio evidence bundle should return portfolio_evidence_bundle_not_found")

    bundle_review_status = app.BUNDLE_REVIEW_CHECKLIST.status()
    if not bundle_review_status.get("ok") or bundle_review_status.get("bundle_review_checklist_version") != "bundle_review_checklist_v001":
        fail(f"bundle review checklist status failed: {bundle_review_status}")
    bundle_review_result = app.BUNDLE_REVIEW_CHECKLIST.create_checklist({"created_by": "validate_app", "notes": "Validation-created v053 bundle review checklist.", "create_bundle": True, "reuse_latest": True})
    if not bundle_review_result.get("ok") or bundle_review_result.get("checklist", {}).get("mutates_config") is not False:
        fail(f"bundle review checklist creation failed: {bundle_review_result}")
    bundle_review = bundle_review_result.get("checklist", {})
    bundle_review_checklist_id = bundle_review.get("checklist_id")
    if bundle_review.get("summary", {}).get("check_count", 0) < 12 or bundle_review.get("summary", {}).get("failed_count", 1) != 0:
        fail(f"bundle review checklist should have no failed checks: {bundle_review.get('summary')}")
    for output_path in bundle_review.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"bundle review checklist output missing: {output_path}")
    bundle_review_detail = app.BUNDLE_REVIEW_CHECKLIST.detail(bundle_review_checklist_id)
    if bundle_review_detail.get("checklist_id") != bundle_review_checklist_id:
        fail("bundle review checklist detail failed")
    bundle_review_list = app.BUNDLE_REVIEW_CHECKLIST.list_checklists(10)
    if not any(row.get("checklist_id") == bundle_review_checklist_id for row in bundle_review_list):
        fail("bundle review checklist should appear in checklist list")
    bundle_review_file = app.BUNDLE_REVIEW_CHECKLIST.output_file(bundle_review_checklist_id, "bundle_review_checklist_report")
    if not bundle_review_file.get("ok") or not Path(bundle_review_file.get("path", "")).exists():
        fail("bundle review checklist output file failed")
    missing_bundle_review = app.BUNDLE_REVIEW_CHECKLIST.detail("missing_checklist")
    if missing_bundle_review.get("error") != "bundle_review_checklist_not_found":
        fail("missing bundle review checklist should return bundle_review_checklist_not_found")

    narrative_status = app.PORTFOLIO_NARRATIVE_EXPORT.status()
    if not narrative_status.get("ok") or narrative_status.get("portfolio_narrative_export_version") != "portfolio_narrative_export_v001":
        fail(f"portfolio narrative export status failed: {narrative_status}")
    narrative_result = app.PORTFOLIO_NARRATIVE_EXPORT.create_narrative({"created_by": "validate_app", "notes": "Validation-created v053 portfolio narrative.", "create_checklist": True, "create_bundle": True, "reuse_latest": True})
    if not narrative_result.get("ok") or narrative_result.get("narrative", {}).get("mutates_config") is not False:
        fail(f"portfolio narrative export creation failed: {narrative_result}")
    narrative = narrative_result.get("narrative", {})
    portfolio_narrative_id = narrative.get("narrative_id")
    if narrative.get("narrative_readiness") not in {"ready_for_reviewer", "ready_with_review_warnings"} or len(narrative.get("sections", [])) < 7:
        fail(f"portfolio narrative should be reviewable: {narrative.get('narrative_readiness')}")
    for output_path in narrative.get("files", {}).values():
        if output_path and not Path(output_path).exists():
            fail(f"portfolio narrative output missing: {output_path}")
    narrative_detail = app.PORTFOLIO_NARRATIVE_EXPORT.detail(portfolio_narrative_id)
    if narrative_detail.get("narrative_id") != portfolio_narrative_id:
        fail("portfolio narrative detail failed")
    narrative_list = app.PORTFOLIO_NARRATIVE_EXPORT.list_narratives(10)
    if not any(row.get("narrative_id") == portfolio_narrative_id for row in narrative_list):
        fail("portfolio narrative should appear in narrative list")
    narrative_file = app.PORTFOLIO_NARRATIVE_EXPORT.output_file(portfolio_narrative_id, "portfolio_narrative_report")
    if not narrative_file.get("ok") or not Path(narrative_file.get("path", "")).exists():
        fail("portfolio narrative output file failed")
    missing_narrative = app.PORTFOLIO_NARRATIVE_EXPORT.detail("missing_narrative")
    if missing_narrative.get("error") != "portfolio_narrative_not_found":
        fail("missing portfolio narrative should return portfolio_narrative_not_found")

    handoff_status = app.PORTFOLIO_HANDOFF_PAGE.status()
    if not handoff_status.get("ok") or handoff_status.get("portfolio_handoff_page_version") != "portfolio_handoff_page_v001":
        fail(f"portfolio handoff page status failed: {handoff_status}")
    handoff_result = app.PORTFOLIO_HANDOFF_PAGE.create_page({"created_by": "validate_app", "notes": "Validation-created v053 portfolio handoff page.", "create_narrative": True, "create_checklist": True, "create_bundle": True, "reuse_latest": True})
    if not handoff_result.get("ok") or handoff_result.get("page", {}).get("mutates_config") is not False:
        fail(f"portfolio handoff page creation failed: {handoff_result}")
    handoff_page = handoff_result.get("page", {})
    portfolio_handoff_page_id = handoff_page.get("page_id")
    if handoff_page.get("handoff_readiness") not in {"ready_for_portfolio_handoff", "ready_with_review_warnings"}:
        fail(f"portfolio handoff page should be reviewable: {handoff_page.get('handoff_readiness')}")
    html_output = Path(str(handoff_page.get("files", {}).get("html") or ""))
    if not html_output.exists() or html_output.stat().st_size < 1000 or "GeoReview Studio" not in html_output.read_text(encoding="utf-8"):
        fail("portfolio handoff HTML output is missing or incomplete")
    handoff_detail = app.PORTFOLIO_HANDOFF_PAGE.detail(portfolio_handoff_page_id)
    if handoff_detail.get("page_id") != portfolio_handoff_page_id:
        fail("portfolio handoff page detail failed")
    handoff_list = app.PORTFOLIO_HANDOFF_PAGE.list_pages(10)
    if not any(row.get("page_id") == portfolio_handoff_page_id for row in handoff_list):
        fail("portfolio handoff page should appear in page list")
    handoff_file = app.PORTFOLIO_HANDOFF_PAGE.output_file(portfolio_handoff_page_id, "portfolio_handoff_page")
    if not handoff_file.get("ok") or not Path(handoff_file.get("path", "")).exists():
        fail("portfolio handoff page output file failed")
    missing_handoff = app.PORTFOLIO_HANDOFF_PAGE.detail("missing_handoff")
    if missing_handoff.get("error") != "portfolio_handoff_page_not_found":
        fail("missing portfolio handoff page should return portfolio_handoff_page_not_found")

    gallery_status = app.PORTFOLIO_EVIDENCE_GALLERY.status()
    if not gallery_status.get("ok") or gallery_status.get("portfolio_evidence_gallery_version") != "portfolio_evidence_gallery_v001":
        fail(f"portfolio evidence gallery status failed: {gallery_status}")
    gallery_result = app.PORTFOLIO_EVIDENCE_GALLERY.create_gallery({"created_by": "validate_app", "notes": "Validation-created v053 portfolio evidence gallery.", "create_handoff_page": True, "create_narrative": True, "create_checklist": True, "create_bundle": True, "reuse_latest": True})
    if not gallery_result.get("ok") or gallery_result.get("gallery", {}).get("mutates_config") is not False:
        fail(f"portfolio evidence gallery creation failed: {gallery_result}")
    gallery = gallery_result.get("gallery", {})
    portfolio_evidence_gallery_id = gallery.get("gallery_id")
    if gallery.get("gallery_readiness") not in {"ready_for_portfolio_gallery", "ready_with_review_warnings"}:
        fail(f"portfolio evidence gallery should be reviewable: {gallery.get('gallery_readiness')}")
    gallery_counts = gallery.get("artifact_counts", {})
    if int(gallery_counts.get("handoff_pages") or 0) < 1 or int(gallery_counts.get("narratives") or 0) < 1 or int(gallery_counts.get("bundles") or 0) < 1:
        fail(f"portfolio evidence gallery artifact counts are incomplete: {gallery_counts}")
    gallery_html = Path(str(gallery.get("files", {}).get("html") or ""))
    if not gallery_html.exists() or gallery_html.stat().st_size < 1000 or "GeoReview Studio" not in gallery_html.read_text(encoding="utf-8"):
        fail("portfolio evidence gallery HTML output is missing or incomplete")
    gallery_detail = app.PORTFOLIO_EVIDENCE_GALLERY.detail(portfolio_evidence_gallery_id)
    if gallery_detail.get("gallery_id") != portfolio_evidence_gallery_id:
        fail("portfolio evidence gallery detail failed")
    gallery_list = app.PORTFOLIO_EVIDENCE_GALLERY.list_galleries(10)
    if not any(row.get("gallery_id") == portfolio_evidence_gallery_id for row in gallery_list):
        fail("portfolio evidence gallery should appear in gallery list")
    gallery_file = app.PORTFOLIO_EVIDENCE_GALLERY.output_file(portfolio_evidence_gallery_id, "portfolio_evidence_gallery")
    if not gallery_file.get("ok") or not Path(gallery_file.get("path", "")).exists():
        fail("portfolio evidence gallery output file failed")
    missing_gallery = app.PORTFOLIO_EVIDENCE_GALLERY.detail("missing_gallery")
    if missing_gallery.get("error") != "portfolio_evidence_gallery_not_found":
        fail("missing portfolio evidence gallery should return portfolio_evidence_gallery_not_found")

    multi_status = app.MULTI_PILOT_COMPARISON.status()
    if not multi_status.get("ok") or multi_status.get("multi_pilot_comparison_version") != "multi_pilot_comparison_v001":
        fail(f"multi-pilot comparison status failed: {multi_status}")
    if int(multi_status.get("ready_pilot_count") or 0) < 2:
        fail(f"multi-pilot comparison should have two ready pilot workspaces: {multi_status}")
    multi_result = app.MULTI_PILOT_COMPARISON.create_comparison({"created_by": "validate_app", "notes": "Validation-created v053 multi-pilot comparison."})
    if not multi_result.get("ok") or multi_result.get("comparison", {}).get("mutates_config") is not False:
        fail(f"multi-pilot comparison creation failed: {multi_result}")
    multi_comparison = multi_result.get("comparison", {})
    multi_pilot_comparison_id = multi_comparison.get("comparison_id")
    if multi_comparison.get("comparison_readiness") != "ready_for_multi_pilot_review":
        fail(f"multi-pilot comparison should be ready: {multi_comparison.get('comparison_readiness')}")
    if multi_comparison.get("ready_pilot_count") < 2 or len(multi_comparison.get("comparison_matrix", [])) < 8:
        fail("multi-pilot comparison matrix is incomplete")
    pilot_labels = {row.get("pilot_label") for row in multi_comparison.get("pilot_metrics", [])}
    if {"Kfar Saba", "Raanana"} - pilot_labels:
        fail(f"multi-pilot comparison should include Kfar Saba and Raanana: {pilot_labels}")
    multi_html = Path(str(multi_comparison.get("files", {}).get("html") or ""))
    if not multi_html.exists() or multi_html.stat().st_size < 1000 or "Multi-Pilot Comparison" not in multi_html.read_text(encoding="utf-8"):
        fail("multi-pilot comparison HTML output is missing or incomplete")
    multi_detail = app.MULTI_PILOT_COMPARISON.detail(multi_pilot_comparison_id)
    if multi_detail.get("comparison_id") != multi_pilot_comparison_id:
        fail("multi-pilot comparison detail failed")
    multi_list = app.MULTI_PILOT_COMPARISON.list_comparisons(10)
    if not any(row.get("comparison_id") == multi_pilot_comparison_id for row in multi_list):
        fail("multi-pilot comparison should appear in comparison list")
    multi_file = app.MULTI_PILOT_COMPARISON.output_file(multi_pilot_comparison_id, "multi_pilot_comparison")
    if not multi_file.get("ok") or not Path(multi_file.get("path", "")).exists():
        fail("multi-pilot comparison output file failed")
    missing_multi = app.MULTI_PILOT_COMPARISON.detail("missing_multi_pilot")
    if missing_multi.get("error") != "multi_pilot_comparison_not_found":
        fail("missing multi-pilot comparison should return multi_pilot_comparison_not_found")

    map_export_status = app.COMPARISON_MAP_EXPORTS.status()
    if not map_export_status.get("ok") or map_export_status.get("comparison_map_exports_version") != "comparison_map_exports_v001":
        fail(f"comparison map exports status failed: {map_export_status}")
    if int(map_export_status.get("ready_pilot_count") or 0) < 2:
        fail(f"comparison map exports should have two ready pilot workspaces: {map_export_status}")
    map_export_result = app.COMPARISON_MAP_EXPORTS.create_export({"created_by": "validate_app", "notes": "Validation-created v053 comparison map export.", "top_limit": 20})
    if not map_export_result.get("ok") or map_export_result.get("export", {}).get("mutates_config") is not False:
        fail(f"comparison map export creation failed: {map_export_result}")
    map_export = map_export_result.get("export", {})
    comparison_map_export_id = map_export.get("export_id")
    if map_export.get("export_readiness") != "ready_for_portfolio_map_review":
        fail(f"comparison map export should be ready: {map_export.get('export_readiness')}")
    if map_export.get("ready_pilot_count") < 2 or map_export.get("top_candidate_rows", 0) < 20:
        fail("comparison map export should contain two pilot maps and candidate rows")
    map_html = Path(str(map_export.get("files", {}).get("html") or ""))
    map_csv = Path(str(map_export.get("files", {}).get("top_candidates_csv") or ""))
    if not map_html.exists() or map_html.stat().st_size < 1000 or "Comparison Map Export" not in map_html.read_text(encoding="utf-8"):
        fail("comparison map export HTML output is missing or incomplete")
    if not map_csv.exists() or map_csv.stat().st_size < 500:
        fail("comparison map export CSV output is missing or incomplete")
    for pilot_map in map_export.get("pilot_maps", []):
        svg_path = Path(str(pilot_map.get("svg_file") or ""))
        if not svg_path.exists() or svg_path.stat().st_size < 1000:
            fail(f"comparison map export SVG missing for {pilot_map.get('pilot_label')}")
    map_detail = app.COMPARISON_MAP_EXPORTS.detail(comparison_map_export_id)
    if map_detail.get("export_id") != comparison_map_export_id:
        fail("comparison map export detail failed")
    map_export_list = app.COMPARISON_MAP_EXPORTS.list_exports(10)
    if not any(row.get("export_id") == comparison_map_export_id for row in map_export_list):
        fail("comparison map export should appear in export list")
    map_file = app.COMPARISON_MAP_EXPORTS.output_file(comparison_map_export_id, "comparison_map_export")
    if not map_file.get("ok") or not Path(map_file.get("path", "")).exists():
        fail("comparison map export output file failed")
    missing_map = app.COMPARISON_MAP_EXPORTS.detail("missing_map_export")
    if missing_map.get("error") != "comparison_map_export_not_found":
        fail("missing comparison map export should return comparison_map_export_not_found")

    result = {
        "passed": True,
        "project_dir": str(PROJECT_DIR),
        "backend_dir": str(BACKEND_DIR),
        "frontend_static_dir": str(FRONTEND_STATIC_DIR),
        "app_version": app.APP_VERSION,
        "project_manifest_version": manifest_payload.get("version"),
        "workspace_id": app.WORKSPACE_ID,
        "profile_dashboard_contract_version": profile_dashboard.get("contract_version"),
        "profile_dashboard_profiles": len(profile_dashboard.get("profiles", [])),
        "profile_dashboard_authored_profiles": profile_dashboard.get("authored_profile_count"),
        "scoring_rules_version": scoring_overview.get("scoring_rules_version"),
        "scoring_rules_profiles": scoring_overview.get("profile_count"),
        "postgis_schema_tables": postgis_schema.get("table_count"),
        "postgis_schema_indexes": postgis_schema.get("index_count"),
        "postgis_profile_result_rows": postgis_readiness.get("profile_result_rows"),
        "postgis_plan_id": postgis_plan.get("plan_id"),
        "profile_mapper_contracts_version": profile_mapper.get("profile_mapper_contracts_version"),
        "profile_mapper_contract_count": profile_mapper.get("contract_count"),
        "profile_mapper_compatible_contracts": mapper_compatibility.get("compatible_contract_count"),
        "profile_mapper_plan_id": mapper_plan.get("plan_id"),
        "contract_execution_adapter_count": contract_execution_status.get("adapter_count"),
        "contract_execution_executable_now": contract_execution_status.get("executable_now_count"),
        "osm_tag_quality_workspace_id": osm_run.get("workspace", {}).get("manifest", {}).get("workspace_id"),
        "osm_tag_quality_rows": osm_counts.get("tag_count_rows"),
        "osm_tag_quality_key_tags": osm_counts.get("key_tag_count"),
        "osm_tag_quality_shapefile_gaps": osm_counts.get("shapefile_not_preserved_count"),
        "contract_execution_dry_run_id": contract_dry_run.get("dry_run_id"),
        "template_authoring_blueprints": template_authoring_status.get("blueprint_count"),
        "template_authoring_draft_id": template_draft.get("draft_id"),
        "execution_queue_job_id": execution_queue_job.get("job_id"),
        "execution_queue_job_status": execution_queue_job.get("status"),
        "dataset_package_id": dataset_package.get("package_id"),
        "dataset_package_execution_status": dataset_package.get("execution_queue_status"),
        "authored_profile_workspace_id": authored_workspace_id,
        "authored_profile_result_rows": authored_counts.get("result_rows"),
        "authored_profile_source_evidence_rows": authored_counts.get("source_evidence_rows"),
        "authored_queue_job_id": authored_queue_job.get("job_id"),
        "authored_queue_job_status": authored_queue_job.get("status"),
        "authored_dashboard_rows": authored_dashboard_summary.get("result_count"),
        "authored_profile_report_id": authored_profile_report_id,
        "profile_promotion_proposal_id": promotion_proposal_id,
        "profile_acceptance_decision_id": acceptance_decision_id,
        "profile_contract_diff_id": profile_contract_diff_id,
        "profile_application_plan_id": application_plan_id,
        "profile_config_apply_proposal_id": profile_config_apply_proposal_id,
        "profile_contract_regression_preview_id": profile_contract_regression_preview_id,
        "release_readiness_snapshot_id": release_readiness_snapshot_id,
        "release_readiness_level": release_readiness.get("readiness_level"),
        "release_readiness_gate_count": release_summary.get("gate_count"),
        "release_readiness_failed_gates": release_summary.get("failed_gate_count"),
        "portfolio_demo_snapshot_id": portfolio_demo_snapshot_id,
        "portfolio_demo_step_count": portfolio_demo.get("step_count"),
        "portfolio_evidence_bundle_id": portfolio_evidence_bundle_id,
        "portfolio_evidence_bundle_files": portfolio_bundle.get("copied_file_count"),
        "bundle_review_checklist_id": bundle_review_checklist_id,
        "bundle_review_checklist_readiness": bundle_review.get("summary", {}).get("review_readiness"),
        "portfolio_narrative_id": portfolio_narrative_id,
        "portfolio_narrative_readiness": narrative.get("narrative_readiness"),
        "portfolio_handoff_page_id": portfolio_handoff_page_id,
        "portfolio_handoff_readiness": handoff_page.get("handoff_readiness"),
        "portfolio_evidence_gallery_id": portfolio_evidence_gallery_id,
        "portfolio_evidence_gallery_readiness": gallery.get("gallery_readiness"),
        "multi_pilot_comparison_id": multi_pilot_comparison_id,
        "multi_pilot_comparison_readiness": multi_comparison.get("comparison_readiness"),
        "multi_pilot_ready_count": multi_comparison.get("ready_pilot_count"),
        "comparison_map_export_id": comparison_map_export_id,
        "comparison_map_export_readiness": map_export.get("export_readiness"),
        "comparison_map_export_ready_count": map_export.get("ready_pilot_count"),
        "profile_promotion_candidate_count": profile_promotion_status.get("candidate_count"),
        "profile_promotion_proposal_count": len(promotion_list),
        "profile_acceptance_decision_count": len(decision_list),
        "profile_contract_diff_candidate_count": len(contract_diff_candidates),
        "profile_contract_diff_count": len(contract_diff_list),
        "profile_application_candidate_count": len(application_candidates),
        "profile_application_plan_count": len(application_plan_list),
        "profile_config_apply_candidate_count": len(config_apply_candidates),
        "profile_config_apply_proposal_count": len(config_apply_list),
        "profile_contract_regression_candidate_count": len(regression_candidates),
        "profile_contract_regression_preview_count": len(regression_list),
        "local_intake_source_count": local_intake_status.get("source_count"),
        "local_intake_plan_id": local_intake_plan.get("plan_id"),
        "source_import_request_id": source_import_request_id,
        "source_import_decision_id": source_import_decision_id,
        "source_handoff_id": source_handoff_id,
        "source_handoff_readiness": source_handoff.get("handoff_readiness"),
        "source_handoff_queue_job_id": source_handoff.get("queue_job_id"),
        "source_handoff_queue_status": source_handoff.get("queue_status"),
        "source_handoff_execution_id": source_handoff_execution_id,
        "source_handoff_execution_readiness": source_handoff_execution.get("execution_readiness"),
        "source_handoff_execution_queue_job_id": source_handoff_execution.get("execution_queue_job_id"),
        "source_handoff_execution_workspace_id": source_handoff_execution.get("generated_workspace_id"),
        "source_handoff_execution_comparison": comparison.get("comparison_readiness"),
        "execution_evidence_package_id": execution_evidence_package_id,
        "execution_evidence_package_readiness": execution_package.get("package_readiness"),
        "execution_evidence_package_checks": len(execution_package.get("quality_checks", [])),
        "second_execution_evidence_package_id": second_execution_evidence_package_id,
        "execution_result_diff_id": execution_result_diff_id,
        "execution_result_diff_readiness": execution_result_diff.get("diff_readiness"),
        "execution_result_diff_classification": execution_result_diff.get("diff_classification"),
        "execution_diff_gallery_id": execution_diff_gallery_id,
        "execution_diff_gallery_readiness": execution_diff_gallery.get("gallery_readiness"),
        "execution_diff_gallery_items": execution_diff_gallery.get("item_count"),
        "execution_diff_detail_id": execution_diff_detail_id,
        "execution_diff_detail_readiness": execution_diff_detail.get("drilldown_readiness"),
        "execution_diff_detail_baseline": execution_diff_detail.get("baseline_diff_id"),
        "reproducibility_audit_packet_id": reproducibility_packet_id,
        "reproducibility_audit_packet_readiness": reproducibility_packet.get("packet_readiness"),
        "reproducibility_audit_packet_files": len(reproducibility_packet.get("copied_files", [])),
        "reviewer_audit_index_id": reviewer_audit_index_id,
        "reviewer_audit_index_readiness": reviewer_audit_index.get("index_readiness"),
        "reviewer_audit_index_ready_packets": reviewer_audit_index.get("ready_packet_count"),
        "portfolio_export_launcher_id": portfolio_export_launcher_id,
        "portfolio_export_launcher_readiness": portfolio_export_launcher.get("launcher_readiness"),
        "portfolio_export_launcher_targets": portfolio_export_launcher.get("launch_target_count"),
        "portable_release_package_id": portable_release_package_id,
        "portable_release_package_readiness": portable_release_package.get("package_readiness"),
        "portable_release_package_files": portable_release_package.get("included_file_count"),
        "portable_release_package_zip_bytes": portable_release_package.get("zip_size_bytes"),
        "demo_script_pack_id": demo_script_pack_id,
        "demo_script_pack_readiness": demo_script_pack.get("pack_readiness"),
        "demo_script_pack_steps": demo_script_pack.get("script_step_count"),
        "demo_script_pack_screenshot_targets": demo_script_pack.get("screenshot_target_count"),
        "visual_qa_ledger_id": visual_qa_ledger_id,
        "visual_qa_ledger_readiness": visual_qa_ledger.get("ledger_readiness"),
        "visual_qa_ledger_targets": visual_qa_ledger.get("screenshot_target_count"),
        "visual_qa_ledger_pending_captures": visual_qa_ledger.get("pending_capture_count"),
        "visual_baseline_comparison_id": visual_baseline_comparison_id,
        "visual_baseline_comparison_readiness": visual_baseline_comparison.get("comparison_readiness"),
        "visual_baseline_changed_targets": visual_baseline_comparison.get("target_delta_summary", {}).get("changed_targets"),
        "visual_baseline_added_targets": visual_baseline_comparison.get("target_delta_summary", {}).get("added_targets"),
        "demo_artifact_completeness_id": demo_artifact_check_id,
        "demo_artifact_completeness_readiness": demo_artifact_check.get("check_readiness"),
        "demo_artifact_complete_required": demo_artifact_check.get("summary", {}).get("complete_required_artifacts"),
        "demo_artifact_missing_required": demo_artifact_check.get("summary", {}).get("missing_required_artifacts"),
        "visual_evidence_capture_id": visual_capture_id,
        "visual_evidence_capture_readiness": visual_capture.get("capture_readiness"),
        "visual_evidence_captured": visual_capture.get("captured_count"),
        "visual_evidence_failed": visual_capture.get("failed_count"),
        "visual_evidence_review_diff_id": visual_diff_id,
        "visual_evidence_review_diff_readiness": visual_diff.get("diff_readiness"),
        "visual_evidence_review_changed_screenshots": visual_diff.get("changed_screenshots"),
        "visual_evidence_review_annotations_id": visual_annotations_id,
        "visual_evidence_review_annotations_readiness": visual_annotations.get("annotation_readiness"),
        "visual_evidence_review_annotations_targets": visual_annotations.get("target_count"),
        "visual_evidence_review_annotations_needs_review": visual_annotations.get("needs_reviewer_attention"),
        "visual_evidence_signoff_packet_id": visual_signoff_packet_id,
        "visual_evidence_signoff_packet_readiness": visual_signoff_packet.get("packet_readiness"),
        "visual_evidence_signoff_status": visual_signoff_packet.get("signoff_status"),
        "visual_evidence_signoff_targets": visual_signoff_packet.get("target_count"),
        "final_reviewer_launch_checklist_id": final_launch_checklist_id,
        "final_reviewer_launch_checklist_readiness": final_launch_checklist.get("checklist_readiness"),
        "final_reviewer_launch_status": final_launch_checklist.get("launch_status"),
        "final_reviewer_launch_actions": final_launch_checklist.get("action_count"),
        "recruiter_demo_brief_id": recruiter_brief_id,
        "recruiter_demo_brief_readiness": recruiter_brief.get("brief_readiness"),
        "recruiter_demo_brief_status": recruiter_brief.get("brief_status"),
        "recruiter_demo_brief_sections": recruiter_brief.get("section_count"),
        "public_portfolio_package_id": public_package_id,
        "public_portfolio_package_readiness": public_package.get("package_readiness"),
        "public_portfolio_package_status": public_package.get("package_status"),
        "public_portfolio_package_readme_sections": public_package.get("readme_section_count"),
        "demo_review_playbook_id": demo_playbook_id,
        "demo_review_playbook_readiness": demo_playbook.get("playbook_readiness"),
        "demo_review_playbook_status": demo_playbook.get("playbook_status"),
        "demo_review_playbook_checklist_items": demo_playbook.get("sharing_checklist_item_count"),
        "github_publication_bundle_id": github_bundle_id,
        "github_publication_bundle_readiness": github_bundle.get("bundle_readiness"),
        "github_publication_bundle_status": github_bundle.get("bundle_status"),
        "github_publication_bundle_readme_sections": github_bundle.get("readme_section_count"),
        "github_publication_bundle_zip_bytes": github_bundle.get("zip_size_bytes"),
        "repository_publication_qa_id": repository_qa_id,
        "repository_publication_qa_readiness": repository_qa.get("qa_readiness"),
        "repository_publication_qa_status": repository_qa.get("qa_status"),
        "repository_publication_qa_failed_required": repository_qa.get("failed_required_check_count"),
        "repository_publication_qa_zip_bytes": repository_qa.get("zip_size_bytes"),
        "repository_export_handoff_id": repository_handoff_id,
        "repository_export_handoff_readiness": repository_handoff.get("handoff_readiness"),
        "repository_export_handoff_status": repository_handoff.get("handoff_status"),
        "repository_export_handoff_required_failed": repository_handoff.get("required_failed_count"),
        "repository_export_handoff_zip_bytes": repository_handoff.get("zip_size_bytes"),
        "repository_dry_run_review_id": repository_dry_run_id,
        "repository_dry_run_review_readiness": repository_dry_run.get("review_readiness"),
        "repository_dry_run_review_status": repository_dry_run.get("review_status"),
        "repository_dry_run_review_required_failed": repository_dry_run.get("required_failed_count"),
        "repository_dry_run_review_zip_bytes": repository_dry_run.get("zip_size_bytes"),
        "repository_final_package_review_id": repository_final_package_id,
        "repository_final_package_review_readiness": repository_final_package.get("review_readiness"),
        "repository_final_package_review_status": repository_final_package.get("review_status"),
        "repository_final_package_review_required_failed": repository_final_package.get("required_failed_count"),
        "repository_final_package_review_public_path_issues": repository_final_package.get("public_path_issue_count"),
        "repository_final_package_review_redacted_paths": repository_final_package.get("redacted_path_count"),
        "repository_final_package_review_zip_bytes": repository_final_package.get("zip_size_bytes"),
        "public_readme_cleanup_review_id": public_readme_cleanup_id,
        "public_readme_cleanup_review_readiness": public_readme_cleanup.get("review_readiness"),
        "public_readme_cleanup_review_status": public_readme_cleanup.get("review_status"),
        "public_readme_cleanup_review_required_failed": public_readme_cleanup.get("required_failed_count"),
        "public_readme_cleanup_review_public_readme_issues": public_readme_cleanup.get("public_readme_issue_count"),
        "public_readme_cleanup_review_screenshot_targets": public_readme_cleanup.get("screenshot_evidence_count"),
        "public_readme_cleanup_review_zip_bytes": public_readme_cleanup.get("zip_size_bytes"),
        "public_repository_polish_package_id": public_repository_polish_id,
        "public_repository_polish_package_readiness": public_repository_polish.get("package_readiness"),
        "public_repository_polish_package_status": public_repository_polish.get("package_status"),
        "public_repository_polish_package_required_failed": public_repository_polish.get("required_failed_count"),
        "public_repository_polish_package_public_readme_issues": public_repository_polish.get("public_readme_issue_count"),
        "public_repository_polish_package_screenshot_targets": public_repository_polish.get("screenshot_target_count"),
        "public_repository_polish_package_zip_bytes": public_repository_polish.get("zip_size_bytes"),
        "repository_export_checklist_id": repository_export_checklist_id,
        "repository_export_checklist_readiness": repository_export_checklist.get("checklist_readiness"),
        "repository_export_checklist_status": repository_export_checklist.get("checklist_status"),
        "repository_export_checklist_required_failed": repository_export_checklist.get("required_failed_count"),
        "repository_export_checklist_screenshot_targets": repository_export_checklist.get("screenshot_target_count"),
        "repository_export_checklist_screenshot_evidence": repository_export_checklist.get("screenshot_evidence_count"),
        "repository_export_checklist_zip_bytes": repository_export_checklist.get("zip_size_bytes"),
        "source_import_guardrail_count": source_import_preview.get("summary", {}).get("guardrail_count"),
        "source_import_hard_failed_count": source_import_preview.get("summary", {}).get("hard_failed_count"),
        "profile_export_bundle_id": profile_bundle_id,
        "profile_export_bundle_profiles": profile_bundle_detail.get("profile_count"),
        "profile_dashboard_safe_access_rows": profile_dashboard_profiles.get("safe_access_pedestrian_review", {}).get("result_count"),
        "profile_dashboard_transit_rows": profile_dashboard_profiles.get("transit_stop_walk_access", {}).get("result_count"),
        "profile_dashboard_park_rows": profile_dashboard_profiles.get("park_playground_access", {}).get("result_count"),
        "product_architecture_version": architecture.get("product_architecture_version"),
        "product_architecture_recommended_variant": architecture.get("recommended_variant_id"),
        "product_architecture_implemented_profiles": architecture.get("current_evidence", {}).get("implemented_profile_count"),
        "product_architecture_variants": len(architecture_variants.get("variants", [])),
        "product_architecture_next_release": next((item.get("release") for item in architecture_roadmap.get("roadmap", []) if item.get("status") == "next"), ""),
        "release_readiness_snapshot_count": len(release_snapshot_list),
        "portfolio_demo_snapshot_count": len(portfolio_demo_snapshot_list),
        "portfolio_evidence_bundle_count": len(portfolio_bundle_list),
        "bundle_review_checklist_count": len(bundle_review_list),
        "portfolio_narrative_count": len(narrative_list),
        "portfolio_handoff_page_count": len(handoff_list),
        "portfolio_evidence_gallery_count": len(gallery_list),
        "multi_pilot_comparison_count": len(multi_list),
        "comparison_map_export_count": len(map_export_list),
        "candidate_sample_count": len(candidates),
        "generators": len(features["generators"]),
        "crossings": len(features["crossings"]),
        "major_road_refs": len(features["major_roads"]),
        "catalog_sources": len(sources),
        "source_onboarding_sources": onboarding_status.get("source_count"),
        "source_onboarding_zip_layers": len(zip_onboarding.get("layers", [])),
        "source_onboarding_zip_readiness": zip_onboarding.get("readiness", {}).get("level"),
        "analysis_profiles_count": len(profile_payload.get("profiles", [])),
        "analysis_profile_safe_access_can_run": safe_access_profile.get("can_run"),
        "analysis_profile_transit_can_plan": transit_profile.get("can_plan"),
        "analysis_profile_transit_can_run": transit_profile.get("can_run"),
        "analysis_profile_park_can_run": park_profile.get("can_run"),
        "transit_profile_workspace_id": transit_run.get("workspace", {}).get("manifest", {}).get("workspace_id"),
        "transit_profile_stops": transit_summary.get("counts", {}).get("transit_stops"),
        "transit_profile_results_sample_count": len(transit_results),
        "park_profile_workspace_id": park_run.get("workspace", {}).get("manifest", {}).get("workspace_id"),
        "park_profile_public_spaces": park_summary.get("counts", {}).get("public_spaces"),
        "park_profile_results_sample_count": len(park_results),
        "analysis_workflow_can_start": analysis_plan.get("can_start_job"),
        "analysis_workflow_active_workspace": analysis_plan.get("active_workspace_id"),
        "analysis_workflow_job_id": analysis_job_id,
        "analysis_workflow_job_status": analysis_job_detail.get("status"),
        "analysis_runs_count": len(analysis_runs),
        "analysis_run_outputs": len(analysis_run_detail.get("outputs", [])),
        "analysis_run_rerun_job_id": rerun_job_id,
        "analysis_run_rerun_status": rerun_job_detail.get("status"),
        "portfolio_report_id": portfolio_report_id,
        "profile_report_id": transit_profile_report_id,
        "profile_report_transit_stops": transit_profile_detail.get("counts", {}).get("transit_stops"),
        "park_profile_report_id": park_profile_report_id,
        "park_profile_report_public_spaces": park_profile_detail.get("counts", {}).get("public_spaces"),
        "profile_comparison_report_id": profile_comparison_id,
        "profile_comparison_rows": len(profile_comparison_detail.get("comparison_rows", [])),
        "portfolio_compare_report_id": portfolio_compare_id,
        "portfolio_reports_count": len(portfolio_reports),
        "zip_layers": zip_profile["dataset"]["layer_count"],
        "template_count": len(templates),
        "workspace_registry_count": len(registry),
        "generated_workspace_id": manifest.get("workspace_id"),
        "generated_workspace_created": run.get("created"),
        "generated_workspace_tables": len(manifest.get("tables", [])),
        "pbf_enriched_workspace_id": generic_manifest.get("workspace_id"),
        "pbf_enriched_workspace_created": generic_run.get("created"),
        "pbf_enriched_mapper": generic_manifest.get("mapper"),
        "pbf_enriched_generators": generic_counts.get("pedestrian_generators"),
        "pbf_enriched_childcare": generic_counts.get("childcare"),
        "pbf_enriched_crossings": generic_counts.get("crossings"),
        "pbf_enriched_road_segments": generic_counts.get("road_segments"),
        "pbf_enriched_traffic_calming": generic_counts.get("traffic_calming_features"),
        "pbf_points": generic_validation.get("pbf_points"),
        "pbf_lines": generic_validation.get("pbf_lines"),
        "dashboard_workspace_generators": dashboard_summary.get("counts", {}).get("pedestrian_generators"),
        "dashboard_candidate_sample_count": len(dashboard_candidates),
        "dashboard_workspace_count": len(registry),
        "pilot_area_count": pilot_meta.get("pilot_count"),
        "pilot_area_kfar_saba_workspace": kfar_saba_pilot.get("route_aware_workspace_id"),
        "pilot_search_count": len(pilot_search),
        "preflight_can_start_job": preflight.get("can_start_job"),
        "preflight_runtime_class": preflight.get("estimate", {}).get("runtime_class"),
        "pilot_runner_active_workspace": pilot_run.get("active_workspace_id"),
        "background_job_id": job_id,
        "background_job_status": job_detail.get("status"),
        "background_job_logs": len(job_detail.get("logs", [])),
        "job_history_count": len(job_registry),
        "route_aware_workspace_id": route_manifest.get("workspace_id"),
        "route_aware_workspace_created": route_run.get("created"),
        "route_aware_rows": route_analysis.get("rows"),
        "route_aware_network_nodes": route_analysis.get("network_nodes"),
        "route_aware_reachable_generators": route_analysis.get("route_reachable_generators"),
        "route_aware_median_crossing_m": route_analysis.get("median_route_nearest_crossing_m"),
        "route_aware_over_250m": route_analysis.get("generators_route_over_250m"),
        "route_aware_candidate_sample_count": len(route_candidates),
        "route_aware_endpoint_sample_count": len(route_network_rows),
        "portfolio_artifacts": len(portfolio_required),
        "portfolio_sample_rows": sample_rows,
        "api_hardening_checked": True,
    }
    (PROJECT_DIR / "validation_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
