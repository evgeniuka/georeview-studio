from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


RELEASE_READINESS_VERSION = "release_readiness_dashboard_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "release_readiness") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:140] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def safe_call(fn: Callable[[], object], default: object) -> object:
    try:
        result = fn()
        return result if result is not None else default
    except Exception as exc:  # visible in readiness evidence without breaking local dashboard
        return {"error": "readiness_probe_failed", "detail": repr(exc)}


class ReleaseReadinessDashboard:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        dependencies: dict[str, object],
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.dependencies = dependencies
        self.snapshots_dir = output_root / "georeview_studio_release_readiness"

    def overview(self) -> dict:
        context = self.context()
        gates = self.evaluate_gates(context)
        status_counts = self.status_counts(gates)
        readiness_level = self.readiness_level(status_counts)
        return {
            "ok": True,
            "release_readiness_version": RELEASE_READINESS_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": context.get("manifest", {}).get("version"),
            "readiness_level": readiness_level,
            "summary": {
                "gate_count": len(gates),
                "passed_gate_count": status_counts.get("passed", 0),
                "warning_gate_count": status_counts.get("warning", 0),
                "failed_gate_count": status_counts.get("failed", 0),
                "blocked_gate_count": status_counts.get("blocked", 0),
                "profile_result_rows": context.get("profile_result_rows", 0),
                "profile_count": context.get("profile_count", 0),
                "checked_api_endpoints": context.get("api_contract", {}).get("checked_endpoints", 0),
                "promotion_regression_previews": context.get("promotion", {}).get("regression_preview_count", 0),
            },
            "gates": gates,
            "gate_groups": self.group_counts(gates),
            "required_next_actions": self.required_next_actions(gates),
            "approved_review_wording": self.review_wording,
            "claim_boundary": "This dashboard proves release evidence for infrastructure review indicators; it is not a crash prediction model.",
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def gates_response(self) -> dict:
        overview = self.overview()
        return {
            "ok": True,
            "release_readiness_version": RELEASE_READINESS_VERSION,
            "app_version": self.app_version,
            "gate_count": overview.get("summary", {}).get("gate_count", 0),
            "failed_gate_count": overview.get("summary", {}).get("failed_gate_count", 0),
            "gates": overview.get("gates", []),
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_snapshot(self, body: dict | None = None) -> dict:
        body = body or {}
        overview = self.overview()
        stamp = utc_now()
        snapshot_id = f"release_readiness_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        snapshot = {
            "ok": True,
            "snapshot_id": snapshot_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Readiness snapshot for local portfolio review."),
            "readiness_level": overview.get("readiness_level"),
            "gate_count": overview.get("summary", {}).get("gate_count", 0),
            "failed_gate_count": overview.get("summary", {}).get("failed_gate_count", 0),
            "warning_gate_count": overview.get("summary", {}).get("warning_gate_count", 0),
            "overview": overview,
            "source_gis_modified": False,
            "mutates_config": False,
        }
        json_path = self.snapshots_dir / f"{snapshot_id}.json"
        md_path = self.snapshots_dir / f"{snapshot_id}.md"
        latest_path = self.snapshots_dir / "latest_release_readiness_snapshot.json"
        snapshot["files"] = {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)}
        write_json(json_path, snapshot)
        write_json(latest_path, snapshot)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(self.snapshot_markdown(snapshot), encoding="utf-8", newline="\n")
        return {"ok": True, "snapshot": snapshot, "source_gis_modified": False, "mutates_config": False}

    def list_snapshots(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.snapshots_dir.exists():
            return rows
        for path in sorted(self.snapshots_dir.glob("release_readiness_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            rows.append({
                "snapshot_id": payload.get("snapshot_id"),
                "created_at": payload.get("created_at"),
                "readiness_level": payload.get("readiness_level"),
                "gate_count": payload.get("gate_count"),
                "failed_gate_count": payload.get("failed_gate_count"),
                "warning_gate_count": payload.get("warning_gate_count"),
                "json_file": str(path),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def snapshot_detail(self, snapshot_id: str) -> dict:
        token = safe_token(snapshot_id, "missing")
        path = self.snapshots_dir / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "release_readiness_snapshot_not_found", "snapshot_id": snapshot_id, "source_gis_modified": False}
        return payload

    def context(self) -> dict:
        manifest = safe_call(self.manifest_reader, {})
        product_architecture = self.dependencies.get("product_architecture")
        profile_dashboard = self.dependencies.get("profile_dashboard")
        scoring_rules = self.dependencies.get("scoring_rules")
        postgis_backend = self.dependencies.get("postgis_backend")
        profile_mapper = self.dependencies.get("profile_mapper")
        contract_execution = self.dependencies.get("contract_execution")
        template_authoring = self.dependencies.get("template_authoring")
        execution_queue = self.dependencies.get("execution_queue")
        dataset_packages = self.dependencies.get("dataset_packages")
        authored_profile_runner = self.dependencies.get("authored_profile_runner")
        profile_promotion = self.dependencies.get("profile_promotion")
        onboarding = self.dependencies.get("onboarding")
        multi_pilot_comparison = self.dependencies.get("multi_pilot_comparison")
        comparison_map_exports = self.dependencies.get("comparison_map_exports")
        source_import_guardrails = self.dependencies.get("source_import_guardrails")
        source_handoff = self.dependencies.get("source_handoff")
        source_handoff_execution = self.dependencies.get("source_handoff_execution")
        execution_evidence_package = self.dependencies.get("execution_evidence_package")
        execution_result_diff = self.dependencies.get("execution_result_diff")
        execution_diff_gallery = self.dependencies.get("execution_diff_gallery")
        execution_diff_detail = self.dependencies.get("execution_diff_detail")
        reproducibility_audit_packet = self.dependencies.get("reproducibility_audit_packet")
        reviewer_audit_index = self.dependencies.get("reviewer_audit_index")
        portfolio_export_launcher = self.dependencies.get("portfolio_export_launcher")
        portable_release_package = self.dependencies.get("portable_release_package")
        demo_script_pack = self.dependencies.get("demo_script_pack")
        visual_qa_ledger = self.dependencies.get("visual_qa_ledger")
        visual_baseline_comparison = self.dependencies.get("visual_baseline_comparison")
        demo_artifact_completeness = self.dependencies.get("demo_artifact_completeness")
        visual_evidence_capture = self.dependencies.get("visual_evidence_capture")
        visual_evidence_review_diff = self.dependencies.get("visual_evidence_review_diff")
        visual_evidence_review_annotations = self.dependencies.get("visual_evidence_review_annotations")
        visual_evidence_signoff_packet = self.dependencies.get("visual_evidence_signoff_packet")
        final_reviewer_launch_checklist = self.dependencies.get("final_reviewer_launch_checklist")
        recruiter_demo_brief = self.dependencies.get("recruiter_demo_brief")
        public_portfolio_package = self.dependencies.get("public_portfolio_package")
        demo_review_playbook = self.dependencies.get("demo_review_playbook")
        github_publication_bundle = self.dependencies.get("github_publication_bundle")

        architecture = safe_call(product_architecture.blueprint, {}) if product_architecture else {}
        roadmap = safe_call(product_architecture.roadmap, {}) if product_architecture else {}
        profile_dashboard_overview = safe_call(profile_dashboard.overview, {}) if profile_dashboard else {}
        scoring_overview = safe_call(scoring_rules.overview, {}) if scoring_rules else {}
        scoring_audits = []
        for profile_id in ["safe_access_pedestrian_review", "transit_stop_walk_access", "park_playground_access"]:
            if scoring_rules:
                audit = safe_call(lambda profile_id=profile_id: scoring_rules.audit(profile_id, limit=1), {})
            else:
                audit = {}
            scoring_audits.append({
                "profile_id": profile_id,
                "rows_audited": audit.get("rows_audited", 0),
                "mismatch_count": audit.get("mismatch_count", 0),
                "source_gis_modified": audit.get("source_gis_modified"),
            })
        postgis_status = safe_call(postgis_backend.status, {}) if postgis_backend else {}
        postgis_schema = safe_call(postgis_backend.schema, {}) if postgis_backend else {}
        mapper_status = safe_call(profile_mapper.overview, {}) if profile_mapper else {}
        contract_status = safe_call(contract_execution.status, {}) if contract_execution else {}
        template_status = safe_call(template_authoring.status, {}) if template_authoring else {}
        queue_status = safe_call(execution_queue.status, {}) if execution_queue else {}
        package_status = safe_call(dataset_packages.status, {}) if dataset_packages else {}
        authored_status = safe_call(authored_profile_runner.status, {}) if authored_profile_runner else {}
        promotion_status = safe_call(profile_promotion.status, {}) if profile_promotion else {}
        onboarding_status = safe_call(onboarding.status, {}) if onboarding else {}
        multi_pilot_status = safe_call(multi_pilot_comparison.status, {}) if multi_pilot_comparison else {}
        map_export_status = safe_call(comparison_map_exports.status, {}) if comparison_map_exports else {}
        source_import_status = safe_call(source_import_guardrails.status, {}) if source_import_guardrails else {}
        source_handoff_status = safe_call(source_handoff.status, {}) if source_handoff else {}
        source_handoff_execution_status = safe_call(source_handoff_execution.status, {}) if source_handoff_execution else {}
        execution_evidence_package_status = safe_call(execution_evidence_package.status, {}) if execution_evidence_package else {}
        execution_result_diff_status = safe_call(execution_result_diff.status, {}) if execution_result_diff else {}
        execution_diff_gallery_status = safe_call(execution_diff_gallery.status, {}) if execution_diff_gallery else {}
        execution_diff_detail_status = safe_call(execution_diff_detail.status, {}) if execution_diff_detail else {}
        reproducibility_audit_packet_status = safe_call(reproducibility_audit_packet.status, {}) if reproducibility_audit_packet else {}
        reviewer_audit_index_status = safe_call(reviewer_audit_index.status, {}) if reviewer_audit_index else {}
        portfolio_export_launcher_status = safe_call(portfolio_export_launcher.status, {}) if portfolio_export_launcher else {}
        portable_release_package_status = safe_call(portable_release_package.status, {}) if portable_release_package else {}
        demo_script_pack_status = safe_call(demo_script_pack.status, {}) if demo_script_pack else {}
        visual_qa_ledger_status = safe_call(visual_qa_ledger.status, {}) if visual_qa_ledger else {}
        visual_baseline_comparison_status = safe_call(visual_baseline_comparison.status, {}) if visual_baseline_comparison else {}
        demo_artifact_completeness_status = safe_call(demo_artifact_completeness.status, {}) if demo_artifact_completeness else {}
        visual_evidence_capture_status = safe_call(visual_evidence_capture.status, {}) if visual_evidence_capture else {}
        visual_evidence_review_diff_status = safe_call(visual_evidence_review_diff.status, {}) if visual_evidence_review_diff else {}
        visual_evidence_review_annotations_status = safe_call(visual_evidence_review_annotations.status, {}) if visual_evidence_review_annotations else {}
        visual_evidence_signoff_packet_status = safe_call(visual_evidence_signoff_packet.status, {}) if visual_evidence_signoff_packet else {}
        final_reviewer_launch_checklist_status = safe_call(final_reviewer_launch_checklist.status, {}) if final_reviewer_launch_checklist else {}
        recruiter_demo_brief_status = safe_call(recruiter_demo_brief.status, {}) if recruiter_demo_brief else {}
        public_portfolio_package_status = safe_call(public_portfolio_package.status, {}) if public_portfolio_package else {}
        demo_review_playbook_status = safe_call(demo_review_playbook.status, {}) if demo_review_playbook else {}
        github_publication_bundle_status = safe_call(github_publication_bundle.status, {}) if github_publication_bundle else {}
        repository_publication_qa = self.dependencies.get("repository_publication_qa")
        repository_publication_qa_status = safe_call(repository_publication_qa.status, {}) if repository_publication_qa else {}
        repository_export_handoff = self.dependencies.get("repository_export_handoff")
        repository_export_handoff_status = safe_call(repository_export_handoff.status, {}) if repository_export_handoff else {}
        repository_dry_run_review = self.dependencies.get("repository_dry_run_review")
        repository_dry_run_review_status = safe_call(repository_dry_run_review.status, {}) if repository_dry_run_review else {}
        repository_final_package_review = self.dependencies.get("repository_final_package_review")
        repository_final_package_review_status = safe_call(repository_final_package_review.status, {}) if repository_final_package_review else {}
        public_readme_cleanup_review = self.dependencies.get("public_readme_cleanup_review")
        public_readme_cleanup_review_status = safe_call(public_readme_cleanup_review.status, {}) if public_readme_cleanup_review else {}
        public_repository_polish_package = self.dependencies.get("public_repository_polish_package")
        public_repository_polish_package_status = safe_call(public_repository_polish_package.status, {}) if public_repository_polish_package else {}
        repository_export_checklist = self.dependencies.get("repository_export_checklist")
        repository_export_checklist_status = safe_call(repository_export_checklist.status, {}) if repository_export_checklist else {}
        validation_summary = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")

        profile_rows = 0
        for row in profile_dashboard_overview.get("profiles", []):
            try:
                profile_rows += int(row.get("result_count") or 0)
            except (TypeError, ValueError):
                pass

        return {
            "manifest": manifest if isinstance(manifest, dict) else {},
            "architecture": architecture if isinstance(architecture, dict) else {},
            "roadmap": roadmap if isinstance(roadmap, dict) else {},
            "profile_dashboard": profile_dashboard_overview if isinstance(profile_dashboard_overview, dict) else {},
            "profile_result_rows": profile_rows,
            "profile_count": len(profile_dashboard_overview.get("profiles", [])) if isinstance(profile_dashboard_overview, dict) else 0,
            "scoring_overview": scoring_overview if isinstance(scoring_overview, dict) else {},
            "scoring_audits": scoring_audits,
            "postgis_status": postgis_status if isinstance(postgis_status, dict) else {},
            "postgis_schema": postgis_schema if isinstance(postgis_schema, dict) else {},
            "mapper": mapper_status if isinstance(mapper_status, dict) else {},
            "contract_execution": contract_status if isinstance(contract_status, dict) else {},
            "template_authoring": template_status if isinstance(template_status, dict) else {},
            "execution_queue": queue_status if isinstance(queue_status, dict) else {},
            "dataset_packages": package_status if isinstance(package_status, dict) else {},
            "authored_runner": authored_status if isinstance(authored_status, dict) else {},
            "promotion": promotion_status if isinstance(promotion_status, dict) else {},
            "onboarding": onboarding_status if isinstance(onboarding_status, dict) else {},
            "multi_pilot_comparison": multi_pilot_status if isinstance(multi_pilot_status, dict) else {},
            "comparison_map_exports": map_export_status if isinstance(map_export_status, dict) else {},
            "source_import_guardrails": source_import_status if isinstance(source_import_status, dict) else {},
            "source_handoff": source_handoff_status if isinstance(source_handoff_status, dict) else {},
            "source_handoff_execution": source_handoff_execution_status if isinstance(source_handoff_execution_status, dict) else {},
            "execution_evidence_package": execution_evidence_package_status if isinstance(execution_evidence_package_status, dict) else {},
            "execution_result_diff": execution_result_diff_status if isinstance(execution_result_diff_status, dict) else {},
            "execution_diff_gallery": execution_diff_gallery_status if isinstance(execution_diff_gallery_status, dict) else {},
            "execution_diff_detail": execution_diff_detail_status if isinstance(execution_diff_detail_status, dict) else {},
            "reproducibility_audit_packet": reproducibility_audit_packet_status if isinstance(reproducibility_audit_packet_status, dict) else {},
            "reviewer_audit_index": reviewer_audit_index_status if isinstance(reviewer_audit_index_status, dict) else {},
            "portfolio_export_launcher": portfolio_export_launcher_status if isinstance(portfolio_export_launcher_status, dict) else {},
            "portable_release_package": portable_release_package_status if isinstance(portable_release_package_status, dict) else {},
            "demo_script_pack": demo_script_pack_status if isinstance(demo_script_pack_status, dict) else {},
            "visual_qa_ledger": visual_qa_ledger_status if isinstance(visual_qa_ledger_status, dict) else {},
            "visual_baseline_comparison": visual_baseline_comparison_status if isinstance(visual_baseline_comparison_status, dict) else {},
            "demo_artifact_completeness": demo_artifact_completeness_status if isinstance(demo_artifact_completeness_status, dict) else {},
            "visual_evidence_capture": visual_evidence_capture_status if isinstance(visual_evidence_capture_status, dict) else {},
            "visual_evidence_review_diff": visual_evidence_review_diff_status if isinstance(visual_evidence_review_diff_status, dict) else {},
            "visual_evidence_review_annotations": visual_evidence_review_annotations_status if isinstance(visual_evidence_review_annotations_status, dict) else {},
            "visual_evidence_signoff_packet": visual_evidence_signoff_packet_status if isinstance(visual_evidence_signoff_packet_status, dict) else {},
            "final_reviewer_launch_checklist": final_reviewer_launch_checklist_status if isinstance(final_reviewer_launch_checklist_status, dict) else {},
            "recruiter_demo_brief": recruiter_demo_brief_status if isinstance(recruiter_demo_brief_status, dict) else {},
            "public_portfolio_package": public_portfolio_package_status if isinstance(public_portfolio_package_status, dict) else {},
            "demo_review_playbook": demo_review_playbook_status if isinstance(demo_review_playbook_status, dict) else {},
            "github_publication_bundle": github_publication_bundle_status if isinstance(github_publication_bundle_status, dict) else {},
            "repository_publication_qa": repository_publication_qa_status if isinstance(repository_publication_qa_status, dict) else {},
            "repository_export_handoff": repository_export_handoff_status if isinstance(repository_export_handoff_status, dict) else {},
            "repository_dry_run_review": repository_dry_run_review_status if isinstance(repository_dry_run_review_status, dict) else {},
            "repository_final_package_review": repository_final_package_review_status if isinstance(repository_final_package_review_status, dict) else {},
            "public_readme_cleanup_review": public_readme_cleanup_review_status if isinstance(public_readme_cleanup_review_status, dict) else {},
            "public_repository_polish_package": public_repository_polish_package_status if isinstance(public_repository_polish_package_status, dict) else {},
            "repository_export_checklist": repository_export_checklist_status if isinstance(repository_export_checklist_status, dict) else {},
            "validation_summary": validation_summary,
            "api_contract": api_contract,
        }

    def evaluate_gates(self, context: dict) -> list[dict]:
        manifest = context.get("manifest", {})
        architecture = context.get("architecture", {})
        roadmap = context.get("roadmap", {}).get("roadmap", [])
        current_release = next((row for row in roadmap if row.get("status") == "current"), {})
        next_release = next((row for row in roadmap if row.get("status") == "next"), {})
        profile_dashboard = context.get("profile_dashboard", {})
        scoring_audits = context.get("scoring_audits", [])
        postgis_status = context.get("postgis_status", {})
        postgis_schema = context.get("postgis_schema", {})
        mapper = context.get("mapper", {})
        contract_execution = context.get("contract_execution", {})
        template_authoring = context.get("template_authoring", {})
        execution_queue = context.get("execution_queue", {})
        dataset_packages = context.get("dataset_packages", {})
        authored_runner = context.get("authored_runner", {})
        promotion = context.get("promotion", {})
        onboarding = context.get("onboarding", {})
        multi_pilot_comparison = context.get("multi_pilot_comparison", {})
        comparison_map_exports = context.get("comparison_map_exports", {})
        source_import_guardrails = context.get("source_import_guardrails", {})
        source_handoff = context.get("source_handoff", {})
        source_handoff_execution = context.get("source_handoff_execution", {})
        execution_evidence_package = context.get("execution_evidence_package", {})
        execution_result_diff = context.get("execution_result_diff", {})
        execution_diff_gallery = context.get("execution_diff_gallery", {})
        execution_diff_detail = context.get("execution_diff_detail", {})
        reproducibility_audit_packet = context.get("reproducibility_audit_packet", {})
        reviewer_audit_index = context.get("reviewer_audit_index", {})
        portfolio_export_launcher = context.get("portfolio_export_launcher", {})
        portable_release_package = context.get("portable_release_package", {})
        demo_script_pack = context.get("demo_script_pack", {})
        visual_qa_ledger = context.get("visual_qa_ledger", {})
        visual_baseline_comparison = context.get("visual_baseline_comparison", {})
        demo_artifact_completeness = context.get("demo_artifact_completeness", {})
        visual_evidence_capture = context.get("visual_evidence_capture", {})
        visual_evidence_review_diff = context.get("visual_evidence_review_diff", {})
        visual_evidence_review_annotations = context.get("visual_evidence_review_annotations", {})
        visual_evidence_signoff_packet = context.get("visual_evidence_signoff_packet", {})
        final_reviewer_launch_checklist = context.get("final_reviewer_launch_checklist", {})
        recruiter_demo_brief = context.get("recruiter_demo_brief", {})
        public_portfolio_package = context.get("public_portfolio_package", {})
        demo_review_playbook = context.get("demo_review_playbook", {})
        github_publication_bundle = context.get("github_publication_bundle", {})
        repository_publication_qa = context.get("repository_publication_qa", {})
        repository_export_handoff = context.get("repository_export_handoff", {})
        repository_dry_run_review = context.get("repository_dry_run_review", {})
        repository_final_package_review = context.get("repository_final_package_review", {})
        public_readme_cleanup_review = context.get("public_readme_cleanup_review", {})
        public_repository_polish_package = context.get("public_repository_polish_package", {})
        repository_export_checklist = context.get("repository_export_checklist", {})
        validation_summary = context.get("validation_summary", {})
        api_contract = context.get("api_contract", {})

        gates = [
            self.gate(
                "release_manifest_current",
                "Project manifest points to the current local release",
                "passed" if str(manifest.get("version", "")).startswith(self.app_version) and str(manifest.get("local_url", "")).endswith("8847") else "failed",
                {"manifest_version": manifest.get("version"), "local_url": manifest.get("local_url")},
                "Update project_manifest.json when app version or port changes.",
            ),
            self.gate(
                "product_architecture_current",
                "Product architecture roadmap has v083 as current and v084 as next",
                "passed" if current_release.get("release") == "v083" and next_release.get("release") == "v084" else "failed",
                {"current_release": current_release, "next_release": next_release, "recommended_variant": architecture.get("recommended_variant_id")},
                "Keep product roadmap synchronized with promoted executable versions.",
            ),
            self.gate(
                "source_gis_read_only_policy",
                "Source GIS files remain read-only",
                "passed" if manifest.get("source_data_policy") and architecture.get("source_gis_modified") is False else "failed",
                {"source_data_policy": manifest.get("source_data_policy"), "architecture_source_gis_modified": architecture.get("source_gis_modified")},
                "Generated artifacts should stay under analysis_output.",
            ),
            self.gate(
                "approved_wording_policy",
                "Approved field-review wording is present",
                "passed" if manifest.get("approved_review_wording") == self.review_wording else "failed",
                {"approved_review_wording": manifest.get("approved_review_wording")},
                "Use only the approved infrastructure indicator wording in reports and UI.",
            ),
            self.gate(
                "profile_dashboard_outputs",
                "Profile dashboard exposes reusable result rows",
                "passed" if profile_dashboard.get("implemented_profile_count", 0) >= 3 and context.get("profile_result_rows", 0) >= 716 else "failed",
                {"implemented_profiles": profile_dashboard.get("implemented_profile_count"), "profile_result_rows": context.get("profile_result_rows")},
                "Run implemented profile workspaces before demo review.",
            ),
            self.gate(
                "scoring_audit_exact_match",
                "Configured scoring rules match generated profile scores",
                "passed" if scoring_audits and all(row.get("mismatch_count") == 0 and row.get("rows_audited", 0) > 0 for row in scoring_audits) else "failed",
                {"audits": scoring_audits},
                "Investigate scoring rule drift before publishing a report.",
            ),
            self.gate(
                "source_onboarding_available",
                "Local source onboarding evidence is available",
                "passed" if onboarding.get("source_count", 0) >= 2 else "warning",
                {"source_count": onboarding.get("source_count"), "output_dir": onboarding.get("output_dir")},
                "Refresh source onboarding if the maps folder changed.",
            ),
            self.gate(
                "source_import_guardrails_reviewed",
                "Reviewed source import guardrails are available",
                "passed" if source_import_guardrails.get("source_import_guardrails_version") == "source_import_guardrails_v001" and int(source_import_guardrails.get("guardrail_count") or 0) >= 8 and int(source_import_guardrails.get("reviewable_source_count") or 0) >= 1 else "failed",
                {
                    "version": source_import_guardrails.get("source_import_guardrails_version"),
                    "guardrail_count": source_import_guardrails.get("guardrail_count"),
                    "reviewable_source_count": source_import_guardrails.get("reviewable_source_count"),
                    "request_count": source_import_guardrails.get("request_count"),
                },
                "Create a reviewed source import request before onboarding new datasets.",
            ),
            self.gate(
                "postgis_planning_ready",
                "PostGIS planning option is documented without requiring live credentials",
                "passed" if postgis_status.get("connection_status") == "not_configured" and postgis_schema.get("table_count", 0) >= 10 else "warning",
                {"connection_status": postgis_status.get("connection_status"), "table_count": postgis_schema.get("table_count")},
                "Use this as a planning artifact until a real database is explicitly configured.",
            ),
            self.gate(
                "profile_mapper_contracts_valid",
                "Profile mapper contracts validate",
                "passed" if mapper.get("contract_count", 0) >= 6 and mapper.get("validation", {}).get("invalid_contract_count") == 0 else "failed",
                {"contract_count": mapper.get("contract_count"), "validation": mapper.get("validation")},
                "Fix mapper contract validation before adding more profiles.",
            ),
            self.gate(
                "contract_execution_adapters_ready",
                "Contract execution adapters have runnable local bindings",
                "passed" if contract_execution.get("executable_now_count", 0) >= 4 else "warning",
                {"adapter_count": contract_execution.get("adapter_count"), "executable_now_count": contract_execution.get("executable_now_count")},
                "Use dry-runs before queueing any profile runner.",
            ),
            self.gate(
                "template_authoring_and_authored_runner",
                "Authored profile flow is available for reusable analysis expansion",
                "passed" if template_authoring.get("blueprint_count", 0) >= 4 and authored_runner.get("authored_profile_runner_version") else "warning",
                {"blueprint_count": template_authoring.get("blueprint_count"), "authored_runner_version": authored_runner.get("authored_profile_runner_version")},
                "Use authored drafts as evidence audits before promotion.",
            ),
            self.gate(
                "controlled_queue_and_dataset_packages",
                "Execution queue and dataset packages are available for reproducible evidence",
                "passed" if execution_queue.get("executable_profile_count", 0) >= 4 and dataset_packages.get("dataset_package_version") else "warning",
                {"executable_profile_count": execution_queue.get("executable_profile_count"), "dataset_package_version": dataset_packages.get("dataset_package_version")},
                "Create dataset evidence packages for repeatable portfolio demos.",
            ),
            self.gate(
                "promotion_lifecycle_gates",
                "Profile promotion lifecycle has proposal, decision, apply proposal and regression preview evidence",
                "passed" if promotion.get("proposal_count", 0) > 0 and promotion.get("accepted_decision_count", 0) > 0 and promotion.get("config_apply_proposal_count", 0) > 0 and promotion.get("regression_preview_count", 0) > 0 else "warning",
                {
                    "proposal_count": promotion.get("proposal_count"),
                    "accepted_decision_count": promotion.get("accepted_decision_count"),
                    "config_apply_proposal_count": promotion.get("config_apply_proposal_count"),
                    "regression_preview_count": promotion.get("regression_preview_count"),
                    "policy": promotion.get("policy"),
                },
                "Run the promotion workflow before claiming profile-contract readiness.",
            ),
            self.gate(
                "local_validation_summary",
                "Latest validation summary is available for this app version",
                "passed" if validation_summary.get("passed") is True and validation_summary.get("app_version") == self.app_version else "warning",
                {"passed": validation_summary.get("passed"), "app_version": validation_summary.get("app_version")},
                "Run scripts/validate.ps1 after changing the app.",
            ),
            self.gate(
                "api_contract_summary",
                "API contract summary covers the release-readiness endpoints",
                "passed" if api_contract.get("passed") is True and api_contract.get("checked_endpoints", 0) >= 362 else "warning",
                {"passed": api_contract.get("passed"), "checked_endpoints": api_contract.get("checked_endpoints")},
                "Run scripts/test_api_contract.ps1 after validation.",
            ),
            self.gate(
                "release_readiness_ui_and_docs",
                "Release readiness UI and documentation are packaged",
                "passed" if self.ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "release_readiness_dashboard.md"),
                    "index": str(self.project_dir / "frontend" / "static" / "index.html"),
                    "app_js": str(self.project_dir / "frontend" / "static" / "app.js"),
                },
                "Keep the UI panel, docs and API route together.",
            ),
            self.gate(
                "bundle_review_checklist_ui_and_docs",
                "Bundle review checklist UI and documentation are packaged",
                "passed" if self.bundle_review_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "bundle_review_checklist.md"),
                    "backend": str(self.project_dir / "backend" / "bundle_review_checklist.py"),
                    "index": str(self.project_dir / "frontend" / "static" / "index.html"),
                    "app_js": str(self.project_dir / "frontend" / "static" / "app.js"),
                },
                "Keep the checklist UI panel, docs and API route together.",
            ),
            self.gate(
                "portfolio_narrative_export_ui_and_docs",
                "Portfolio narrative export UI and documentation are packaged",
                "passed" if self.portfolio_narrative_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "portfolio_narrative_export.md"),
                    "backend": str(self.project_dir / "backend" / "portfolio_narrative_export.py"),
                    "index": str(self.project_dir / "frontend" / "static" / "index.html"),
                    "app_js": str(self.project_dir / "frontend" / "static" / "app.js"),
                },
                "Keep the narrative export UI panel, docs and API route together.",
            ),
            self.gate(
                "portfolio_handoff_page_ui_and_docs",
                "Portfolio handoff page UI and documentation are packaged",
                "passed" if self.portfolio_handoff_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "portfolio_handoff_page.md"),
                    "backend": str(self.project_dir / "backend" / "portfolio_handoff_page.py"),
                    "index": str(self.project_dir / "frontend" / "static" / "index.html"),
                    "app_js": str(self.project_dir / "frontend" / "static" / "app.js"),
                },
                "Keep the handoff page UI panel, docs and API route together.",
            ),
            self.gate(
                "portfolio_evidence_gallery_ui_and_docs",
                "Portfolio evidence gallery UI and documentation are packaged",
                "passed" if self.portfolio_gallery_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "portfolio_evidence_gallery.md"),
                    "backend": str(self.project_dir / "backend" / "portfolio_evidence_gallery.py"),
                    "index": str(self.project_dir / "frontend" / "static" / "index.html"),
                    "app_js": str(self.project_dir / "frontend" / "static" / "app.js"),
                },
                "Keep the gallery UI panel, docs and API route together.",
            ),
            self.gate(
                "multi_pilot_comparison_ui_and_docs",
                "Multi-pilot comparison UI, docs and pilot evidence are packaged",
                "passed" if self.multi_pilot_ui_and_docs_present() and int(multi_pilot_comparison.get("ready_pilot_count") or 0) >= 2 else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "multi_pilot_comparison.md"),
                    "backend": str(self.project_dir / "backend" / "multi_pilot_comparison.py"),
                    "ready_pilot_count": multi_pilot_comparison.get("ready_pilot_count"),
                    "comparison_count": multi_pilot_comparison.get("comparison_count"),
                },
                "Build two route-aware pilot workspaces and keep the comparison panel, docs and API route together.",
            ),
            self.gate(
                "source_import_guardrails_ui_and_docs",
                "Source import guardrails UI and documentation are packaged",
                "passed" if self.source_import_guardrails_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "source_import_guardrails.md"),
                    "backend": str(self.project_dir / "backend" / "source_import_guardrails.py"),
                    "output_dir": source_import_guardrails.get("output_dir"),
                },
                "Keep the guardrails UI panel, docs and API route together.",
            ),
            self.gate(
                "source_handoff_ready",
                "Approved source handoff planner is available",
                "passed" if source_handoff.get("source_handoff_version") == "source_handoff_v001" else "failed",
                {
                    "version": source_handoff.get("source_handoff_version"),
                    "candidate_count": source_handoff.get("candidate_count"),
                    "handoff_count": source_handoff.get("handoff_count"),
                    "ready_handoff_count": source_handoff.get("ready_handoff_count"),
                    "output_dir": source_handoff.get("output_dir"),
                },
                "Connect approved source import requests to mapper plans, dry-runs and planned queue jobs.",
            ),
            self.gate(
                "source_handoff_ui_and_docs",
                "Source handoff UI and documentation are packaged",
                "passed" if self.source_handoff_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "source_handoff.md"),
                    "backend": str(self.project_dir / "backend" / "source_handoff.py"),
                    "output_dir": source_handoff.get("output_dir"),
                },
                "Keep the source handoff UI panel, docs and API route together.",
            ),
            self.gate(
                "source_handoff_execution_ready",
                "Controlled source handoff execution is available",
                "passed" if source_handoff_execution.get("source_handoff_execution_version") == "source_handoff_execution_v001" and int(source_handoff_execution.get("successful_execution_count") or 0) >= 1 else "failed",
                {
                    "version": source_handoff_execution.get("source_handoff_execution_version"),
                    "candidate_count": source_handoff_execution.get("candidate_count"),
                    "execution_count": source_handoff_execution.get("execution_count"),
                    "successful_execution_count": source_handoff_execution.get("successful_execution_count"),
                    "output_dir": source_handoff_execution.get("output_dir"),
                },
                "Execute at least one approved handoff and compare generated workspace outputs to handoff evidence.",
            ),
            self.gate(
                "source_handoff_execution_ui_and_docs",
                "Source handoff execution UI and documentation are packaged",
                "passed" if self.source_handoff_execution_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "source_handoff_execution.md"),
                    "backend": str(self.project_dir / "backend" / "source_handoff_execution.py"),
                    "output_dir": source_handoff_execution.get("output_dir"),
                },
                "Keep the controlled execution UI panel, docs and API route together.",
            ),
            self.gate(
                "execution_evidence_package_ready",
                "Execution evidence packages are available for reviewer handoff",
                "passed" if execution_evidence_package.get("execution_evidence_package_version") == "execution_evidence_package_v001" and int(execution_evidence_package.get("ready_package_count") or 0) >= 1 else "failed",
                {
                    "version": execution_evidence_package.get("execution_evidence_package_version"),
                    "candidate_count": execution_evidence_package.get("candidate_count"),
                    "package_count": execution_evidence_package.get("package_count"),
                    "ready_package_count": execution_evidence_package.get("ready_package_count"),
                    "output_dir": execution_evidence_package.get("output_dir"),
                },
                "Create at least one reviewer-ready package from a verified source handoff execution.",
            ),
            self.gate(
                "execution_evidence_package_ui_and_docs",
                "Execution evidence package UI and documentation are packaged",
                "passed" if self.execution_evidence_package_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "execution_evidence_package.md"),
                    "backend": str(self.project_dir / "backend" / "execution_evidence_package.py"),
                    "output_dir": execution_evidence_package.get("output_dir"),
                },
                "Keep the execution evidence package UI panel, docs and API route together.",
            ),
            self.gate(
                "execution_result_diff_ready",
                "Execution result diffs are available for reproducibility review",
                "passed" if execution_result_diff.get("execution_result_diff_version") == "execution_result_diff_v001" and int(execution_result_diff.get("ready_diff_count") or 0) >= 1 else "failed",
                {
                    "version": execution_result_diff.get("execution_result_diff_version"),
                    "package_count": execution_result_diff.get("package_count"),
                    "candidate_pair_count": execution_result_diff.get("candidate_pair_count"),
                    "diff_count": execution_result_diff.get("diff_count"),
                    "ready_diff_count": execution_result_diff.get("ready_diff_count"),
                    "output_dir": execution_result_diff.get("output_dir"),
                },
                "Create at least one reviewer-ready diff from two ready execution evidence packages.",
            ),
            self.gate(
                "execution_result_diff_ui_and_docs",
                "Execution result diff UI and documentation are packaged",
                "passed" if self.execution_result_diff_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "execution_result_diff.md"),
                    "backend": str(self.project_dir / "backend" / "execution_result_diff.py"),
                    "output_dir": execution_result_diff.get("output_dir"),
                },
                "Keep the execution result diff UI panel, docs and API route together.",
            ),
            self.gate(
                "execution_diff_gallery_ready",
                "Execution diff gallery indexes reproducibility evidence for reviewer scanning",
                "passed" if execution_diff_gallery.get("execution_diff_gallery_version") == "execution_diff_gallery_v001" and int(execution_diff_gallery.get("indexed_diff_count") or 0) >= 1 else "failed",
                {
                    "version": execution_diff_gallery.get("execution_diff_gallery_version"),
                    "indexed_diff_count": execution_diff_gallery.get("indexed_diff_count"),
                    "ready_diff_count": execution_diff_gallery.get("ready_diff_count"),
                    "ready_gallery_count": execution_diff_gallery.get("ready_gallery_count"),
                    "output_dir": execution_diff_gallery.get("output_dir"),
                },
                "Index at least one reviewer-ready execution result diff for portfolio review.",
            ),
            self.gate(
                "execution_diff_gallery_ui_and_docs",
                "Execution diff gallery UI and documentation are packaged",
                "passed" if self.execution_diff_gallery_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "execution_diff_gallery.md"),
                    "backend": str(self.project_dir / "backend" / "execution_diff_gallery.py"),
                    "output_dir": execution_diff_gallery.get("output_dir"),
                },
                "Keep the execution diff gallery UI panel, docs and API route together.",
            ),
            self.gate(
                "execution_diff_detail_ready",
                "Execution diff detail drilldowns are available for baseline investigation",
                "passed" if execution_diff_detail.get("execution_diff_detail_version") == "execution_diff_detail_v001" and int(execution_diff_detail.get("baseline_candidate_count") or 0) >= 1 and int(execution_diff_detail.get("ready_detail_count") or 0) >= 1 else "failed",
                {
                    "version": execution_diff_detail.get("execution_diff_detail_version"),
                    "baseline_candidate_count": execution_diff_detail.get("baseline_candidate_count"),
                    "preferred_baseline_id": execution_diff_detail.get("preferred_baseline_id"),
                    "detail_count": execution_diff_detail.get("detail_count"),
                    "ready_detail_count": execution_diff_detail.get("ready_detail_count"),
                    "output_dir": execution_diff_detail.get("output_dir"),
                },
                "Create at least one reviewer-ready diff drilldown from a baseline candidate.",
            ),
            self.gate(
                "execution_diff_detail_ui_and_docs",
                "Execution diff detail UI and documentation are packaged",
                "passed" if self.execution_diff_detail_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "execution_diff_detail.md"),
                    "backend": str(self.project_dir / "backend" / "execution_diff_detail.py"),
                    "output_dir": execution_diff_detail.get("output_dir"),
                },
                "Keep the baseline selector UI panel, docs and API route together.",
            ),
            self.gate(
                "reproducibility_audit_packet_ready",
                "Reproducibility audit packets bundle diff, detail, gallery and release evidence",
                "passed" if reproducibility_audit_packet.get("reproducibility_audit_packet_version") == "reproducibility_audit_packet_v001" and int(reproducibility_audit_packet.get("candidate_count") or 0) >= 1 and int(reproducibility_audit_packet.get("ready_packet_count") or 0) >= 1 else "failed",
                {
                    "version": reproducibility_audit_packet.get("reproducibility_audit_packet_version"),
                    "candidate_count": reproducibility_audit_packet.get("candidate_count"),
                    "packet_count": reproducibility_audit_packet.get("packet_count"),
                    "ready_packet_count": reproducibility_audit_packet.get("ready_packet_count"),
                    "output_dir": reproducibility_audit_packet.get("output_dir"),
                },
                "Create at least one reviewer-ready reproducibility audit packet from a ready execution diff detail.",
            ),
            self.gate(
                "reproducibility_audit_packet_ui_and_docs",
                "Reproducibility audit packet UI and documentation are packaged",
                "passed" if self.reproducibility_audit_packet_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "reproducibility_audit_packet.md"),
                    "backend": str(self.project_dir / "backend" / "reproducibility_audit_packet.py"),
                    "output_dir": reproducibility_audit_packet.get("output_dir"),
                },
                "Keep the audit packet UI panel, docs and API route together.",
            ),
            self.gate(
                "reviewer_audit_index_ready",
                "Reviewer audit index is available for packet and portfolio evidence navigation",
                "passed" if reviewer_audit_index.get("reviewer_audit_index_version") == "reviewer_audit_index_v001" and int(reviewer_audit_index.get("ready_packet_count") or 0) >= 1 and int(reviewer_audit_index.get("ready_index_count") or 0) >= 1 else "failed",
                {
                    "version": reviewer_audit_index.get("reviewer_audit_index_version"),
                    "ready_packet_count": reviewer_audit_index.get("ready_packet_count"),
                    "index_count": reviewer_audit_index.get("index_count"),
                    "ready_index_count": reviewer_audit_index.get("ready_index_count"),
                    "portfolio_link_count": reviewer_audit_index.get("portfolio_link_count"),
                    "output_dir": reviewer_audit_index.get("output_dir"),
                },
                "Create at least one reviewer-ready audit index from ready packets and portfolio links.",
            ),
            self.gate(
                "reviewer_audit_index_ui_and_docs",
                "Reviewer audit index UI and documentation are packaged",
                "passed" if self.reviewer_audit_index_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "reviewer_audit_index.md"),
                    "backend": str(self.project_dir / "backend" / "reviewer_audit_index.py"),
                    "output_dir": reviewer_audit_index.get("output_dir"),
                },
                "Keep the reviewer audit index UI panel, docs and API route together.",
            ),
            self.gate(
                "portfolio_export_launcher_ready",
                "Portfolio export launcher is available as a start-here reviewer entrypoint",
                "passed" if portfolio_export_launcher.get("portfolio_export_launcher_version") == "portfolio_export_launcher_v001" and int(portfolio_export_launcher.get("ready_launcher_count") or 0) >= 1 and int(portfolio_export_launcher.get("launch_target_count") or 0) >= 3 else "failed",
                {
                    "version": portfolio_export_launcher.get("portfolio_export_launcher_version"),
                    "launch_target_count": portfolio_export_launcher.get("launch_target_count"),
                    "launcher_count": portfolio_export_launcher.get("launcher_count"),
                    "ready_launcher_count": portfolio_export_launcher.get("ready_launcher_count"),
                    "output_dir": portfolio_export_launcher.get("output_dir"),
                },
                "Create at least one ready launcher from reviewer index, audit packet and portfolio artifacts.",
            ),
            self.gate(
                "portfolio_export_launcher_ui_and_docs",
                "Portfolio export launcher UI and documentation are packaged",
                "passed" if self.portfolio_export_launcher_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "portfolio_export_launcher.md"),
                    "backend": str(self.project_dir / "backend" / "portfolio_export_launcher.py"),
                    "output_dir": portfolio_export_launcher.get("output_dir"),
                },
                "Keep the launcher UI panel, docs and API route together.",
            ),
            self.gate(
                "portable_release_package_ready",
                "Portable release package is available for reviewer sharing",
                "passed" if portable_release_package.get("portable_release_package_version") == "portable_release_package_v001" and int(portable_release_package.get("ready_package_count") or 0) >= 1 and int(portable_release_package.get("latest_package_file_count") or 0) >= 5 else "failed",
                {
                    "version": portable_release_package.get("portable_release_package_version"),
                    "package_count": portable_release_package.get("package_count"),
                    "ready_package_count": portable_release_package.get("ready_package_count"),
                    "latest_package_file_count": portable_release_package.get("latest_package_file_count"),
                    "output_dir": portable_release_package.get("output_dir"),
                },
                "Create at least one ready portable release package from a ready launcher.",
            ),
            self.gate(
                "portable_release_package_ui_and_docs",
                "Portable release package UI and documentation are packaged",
                "passed" if self.portable_release_package_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "portable_release_package.md"),
                    "backend": str(self.project_dir / "backend" / "portable_release_package.py"),
                    "output_dir": portable_release_package.get("output_dir"),
                },
                "Keep the package UI panel, docs and API route together.",
            ),
            self.gate(
                "demo_script_pack_ready",
                "Demo script pack is available for repeatable portfolio walkthroughs",
                "passed" if demo_script_pack.get("demo_script_pack_version") == "demo_script_pack_v001" and int(demo_script_pack.get("ready_pack_count") or 0) >= 1 and int(demo_script_pack.get("screenshot_target_count") or 0) >= 6 else "failed",
                {
                    "version": demo_script_pack.get("demo_script_pack_version"),
                    "pack_count": demo_script_pack.get("pack_count"),
                    "ready_pack_count": demo_script_pack.get("ready_pack_count"),
                    "script_step_count": demo_script_pack.get("script_step_count"),
                    "screenshot_target_count": demo_script_pack.get("screenshot_target_count"),
                    "output_dir": demo_script_pack.get("output_dir"),
                },
                "Create at least one ready demo script pack from a portable release package.",
            ),
            self.gate(
                "demo_script_pack_ui_and_docs",
                "Demo script pack UI and documentation are packaged",
                "passed" if self.demo_script_pack_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "demo_script_pack.md"),
                    "backend": str(self.project_dir / "backend" / "demo_script_pack.py"),
                    "output_dir": demo_script_pack.get("output_dir"),
                },
                "Keep the demo script pack UI panel, docs and API route together.",
            ),
            self.gate(
                "visual_qa_snapshot_ledger_ready",
                "Visual QA snapshot ledger is available for demo screenshot review tracking",
                "passed" if visual_qa_ledger.get("visual_qa_snapshot_ledger_version") == "visual_qa_snapshot_ledger_v001" and int(visual_qa_ledger.get("screenshot_target_count") or 0) >= 6 else "failed",
                {
                    "version": visual_qa_ledger.get("visual_qa_snapshot_ledger_version"),
                    "ledger_count": visual_qa_ledger.get("ledger_count"),
                    "ready_ledger_count": visual_qa_ledger.get("ready_ledger_count"),
                    "screenshot_target_count": visual_qa_ledger.get("screenshot_target_count"),
                    "output_dir": visual_qa_ledger.get("output_dir"),
                },
                "Create a visual QA ledger from a ready demo script pack before final portfolio capture.",
            ),
            self.gate(
                "visual_qa_snapshot_ledger_ui_and_docs",
                "Visual QA snapshot ledger UI and documentation are packaged",
                "passed" if self.visual_qa_snapshot_ledger_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "visual_qa_snapshot_ledger.md"),
                    "backend": str(self.project_dir / "backend" / "visual_qa_snapshot_ledger.py"),
                    "output_dir": visual_qa_ledger.get("output_dir"),
                },
                "Keep the visual QA ledger UI panel, docs and API route together.",
            ),
            self.gate(
                "visual_baseline_comparison_ready",
                "Visual baseline comparison manifest is available for release-to-release demo target review",
                "passed" if visual_baseline_comparison.get("visual_baseline_comparison_version") == "visual_baseline_comparison_manifest_v001" and int(visual_baseline_comparison.get("baseline_candidate_count") or 0) >= 1 else "failed",
                {
                    "version": visual_baseline_comparison.get("visual_baseline_comparison_version"),
                    "comparison_count": visual_baseline_comparison.get("comparison_count"),
                    "ready_comparison_count": visual_baseline_comparison.get("ready_comparison_count"),
                    "baseline_candidate_count": visual_baseline_comparison.get("baseline_candidate_count"),
                    "latest_target_count": visual_baseline_comparison.get("latest_target_count"),
                    "output_dir": visual_baseline_comparison.get("output_dir"),
                },
                "Create a visual baseline comparison from two ready Visual QA ledgers.",
            ),
            self.gate(
                "visual_baseline_comparison_ui_and_docs",
                "Visual baseline comparison UI and documentation are packaged",
                "passed" if self.visual_baseline_comparison_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "visual_baseline_comparison.md"),
                    "backend": str(self.project_dir / "backend" / "visual_baseline_comparison.py"),
                    "output_dir": visual_baseline_comparison.get("output_dir"),
                },
                "Keep the visual baseline comparison UI panel, docs and API route together.",
            ),
            self.gate(
                "demo_artifact_completeness_ready",
                "Demo artifact completeness validator confirms required sharing artifacts are present",
                "passed" if demo_artifact_completeness.get("demo_artifact_completeness_version") == "demo_artifact_completeness_validator_v001" and int(demo_artifact_completeness.get("required_artifact_count") or 0) >= 12 and int(demo_artifact_completeness.get("missing_required_artifacts") or 0) == 0 and int(demo_artifact_completeness.get("invalid_required_artifacts") or 0) == 0 else "failed",
                {
                    "version": demo_artifact_completeness.get("demo_artifact_completeness_version"),
                    "artifact_count": demo_artifact_completeness.get("artifact_count"),
                    "required_artifact_count": demo_artifact_completeness.get("required_artifact_count"),
                    "missing_required_artifacts": demo_artifact_completeness.get("missing_required_artifacts"),
                    "invalid_required_artifacts": demo_artifact_completeness.get("invalid_required_artifacts"),
                    "ready_check_count": demo_artifact_completeness.get("ready_check_count"),
                    "output_dir": demo_artifact_completeness.get("output_dir"),
                },
                "Regenerate the missing demo, package, QA or comparison artifacts before sharing.",
            ),
            self.gate(
                "demo_artifact_completeness_ui_and_docs",
                "Demo artifact completeness UI and documentation are packaged",
                "passed" if self.demo_artifact_completeness_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "demo_artifact_completeness.md"),
                    "backend": str(self.project_dir / "backend" / "demo_artifact_completeness.py"),
                    "output_dir": demo_artifact_completeness.get("output_dir"),
                },
                "Keep the demo artifact completeness UI panel, docs and API route together.",
            ),
            self.gate(
                "visual_evidence_capture_ready",
                "Automated visual evidence capture has browser screenshots for Visual QA targets",
                "passed" if visual_evidence_capture.get("visual_evidence_capture_version") == "visual_evidence_capture_v001" and visual_evidence_capture.get("browser_available") is True and int(visual_evidence_capture.get("ready_capture_count") or 0) >= 1 and int(visual_evidence_capture.get("latest_captured_count") or 0) >= 6 else "failed",
                {
                    "version": visual_evidence_capture.get("visual_evidence_capture_version"),
                    "browser_available": visual_evidence_capture.get("browser_available"),
                    "target_count": visual_evidence_capture.get("target_count"),
                    "capture_count": visual_evidence_capture.get("capture_count"),
                    "ready_capture_count": visual_evidence_capture.get("ready_capture_count"),
                    "latest_captured_count": visual_evidence_capture.get("latest_captured_count"),
                    "output_dir": visual_evidence_capture.get("output_dir"),
                },
                "Run a visual evidence capture after creating a ready Visual QA ledger.",
            ),
            self.gate(
                "visual_evidence_capture_ui_and_docs",
                "Visual evidence capture UI and documentation are packaged",
                "passed" if self.visual_evidence_capture_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "visual_evidence_capture.md"),
                    "backend": str(self.project_dir / "backend" / "visual_evidence_capture.py"),
                    "output_dir": visual_evidence_capture.get("output_dir"),
                },
                "Keep visual evidence capture UI panel, docs and API routes together.",
            ),
            self.gate(
                "visual_evidence_review_diff_ready",
                "Visual evidence review diff compares ready screenshot capture sets",
                "passed" if visual_evidence_review_diff.get("visual_evidence_review_diff_version") == "visual_evidence_review_diff_v001" and int(visual_evidence_review_diff.get("ready_diff_count") or 0) >= 1 else "failed",
                {
                    "version": visual_evidence_review_diff.get("visual_evidence_review_diff_version"),
                    "capture_count": visual_evidence_review_diff.get("capture_count"),
                    "baseline_candidate_count": visual_evidence_review_diff.get("baseline_candidate_count"),
                    "ready_diff_count": visual_evidence_review_diff.get("ready_diff_count"),
                    "latest_changed_screenshots": visual_evidence_review_diff.get("latest_changed_screenshots"),
                    "output_dir": visual_evidence_review_diff.get("output_dir"),
                },
                "Create a visual evidence review diff after at least two ready captures exist.",
            ),
            self.gate(
                "visual_evidence_review_diff_ui_and_docs",
                "Visual evidence review diff UI and documentation are packaged",
                "passed" if self.visual_evidence_review_diff_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "visual_evidence_review_diff.md"),
                    "backend": str(self.project_dir / "backend" / "visual_evidence_review_diff.py"),
                    "output_dir": visual_evidence_review_diff.get("output_dir"),
                },
                "Keep visual evidence review diff UI panel, docs and API routes together.",
            ),
            self.gate(
                "visual_evidence_review_annotations_ready",
                "Visual evidence review annotations are available for reviewer notes",
                "passed" if visual_evidence_review_annotations.get("visual_evidence_review_annotations_version") == "visual_evidence_review_annotations_v001" and int(visual_evidence_review_annotations.get("ready_annotation_count") or 0) >= 1 else "failed",
                {
                    "version": visual_evidence_review_annotations.get("visual_evidence_review_annotations_version"),
                    "ready_diff_count": visual_evidence_review_annotations.get("ready_diff_count"),
                    "annotation_count": visual_evidence_review_annotations.get("annotation_count"),
                    "ready_annotation_count": visual_evidence_review_annotations.get("ready_annotation_count"),
                    "latest_pending_review_count": visual_evidence_review_annotations.get("latest_pending_review_count"),
                    "output_dir": visual_evidence_review_annotations.get("output_dir"),
                },
                "Create at least one annotation set from a ready visual evidence review diff.",
            ),
            self.gate(
                "visual_evidence_review_annotations_ui_and_docs",
                "Visual evidence review annotations UI and documentation are packaged",
                "passed" if self.visual_evidence_review_annotations_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "visual_evidence_review_annotations.md"),
                    "backend": str(self.project_dir / "backend" / "visual_evidence_review_annotations.py"),
                    "output_dir": visual_evidence_review_annotations.get("output_dir"),
                },
                "Keep visual evidence annotations UI panel, docs and API routes together.",
            ),
            self.gate(
                "visual_evidence_signoff_packet_ready",
                "Visual evidence sign-off packets are available for portfolio review",
                "passed" if visual_evidence_signoff_packet.get("visual_evidence_signoff_packet_version") == "visual_evidence_signoff_packet_v001" and int(visual_evidence_signoff_packet.get("ready_packet_count") or 0) >= 1 else "failed",
                {
                    "version": visual_evidence_signoff_packet.get("visual_evidence_signoff_packet_version"),
                    "ready_annotation_count": visual_evidence_signoff_packet.get("ready_annotation_count"),
                    "packet_count": visual_evidence_signoff_packet.get("packet_count"),
                    "ready_packet_count": visual_evidence_signoff_packet.get("ready_packet_count"),
                    "latest_signoff_status": visual_evidence_signoff_packet.get("latest_signoff_status"),
                    "checked_api_endpoints": visual_evidence_signoff_packet.get("checked_api_endpoints"),
                    "output_dir": visual_evidence_signoff_packet.get("output_dir"),
                },
                "Create at least one sign-off packet from a ready visual evidence annotation set.",
            ),
            self.gate(
                "visual_evidence_signoff_packet_ui_and_docs",
                "Visual evidence sign-off packet UI and documentation are packaged",
                "passed" if self.visual_evidence_signoff_packet_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "visual_evidence_signoff_packet.md"),
                    "backend": str(self.project_dir / "backend" / "visual_evidence_signoff_packet.py"),
                    "output_dir": visual_evidence_signoff_packet.get("output_dir"),
                },
                "Keep visual evidence sign-off packet UI panel, docs and API routes together.",
            ),
            self.gate(
                "final_reviewer_launch_checklist_ready",
                "Final reviewer launch checklists are available for portfolio walkthroughs",
                "passed" if final_reviewer_launch_checklist.get("final_reviewer_launch_checklist_version") == "final_reviewer_launch_checklist_v001" and int(final_reviewer_launch_checklist.get("ready_checklist_count") or 0) >= 1 else "failed",
                {
                    "version": final_reviewer_launch_checklist.get("final_reviewer_launch_checklist_version"),
                    "ready_signoff_packet_count": final_reviewer_launch_checklist.get("ready_signoff_packet_count"),
                    "checklist_count": final_reviewer_launch_checklist.get("checklist_count"),
                    "ready_checklist_count": final_reviewer_launch_checklist.get("ready_checklist_count"),
                    "latest_launch_status": final_reviewer_launch_checklist.get("latest_launch_status"),
                    "checked_api_endpoints": final_reviewer_launch_checklist.get("checked_api_endpoints"),
                    "output_dir": final_reviewer_launch_checklist.get("output_dir"),
                },
                "Create at least one final reviewer launch checklist from a ready sign-off packet.",
            ),
            self.gate(
                "final_reviewer_launch_checklist_ui_and_docs",
                "Final reviewer launch checklist UI and documentation are packaged",
                "passed" if self.final_reviewer_launch_checklist_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "final_reviewer_launch_checklist.md"),
                    "backend": str(self.project_dir / "backend" / "final_reviewer_launch_checklist.py"),
                    "output_dir": final_reviewer_launch_checklist.get("output_dir"),
                },
                "Keep final reviewer launch checklist UI panel, docs and API routes together.",
            ),
            self.gate(
                "recruiter_demo_brief_ready",
                "Recruiter-facing demo briefs are available for portfolio review",
                "passed" if recruiter_demo_brief.get("recruiter_demo_brief_version") == "recruiter_demo_brief_v001" and int(recruiter_demo_brief.get("ready_brief_count") or 0) >= 1 else "failed",
                {
                    "version": recruiter_demo_brief.get("recruiter_demo_brief_version"),
                    "ready_launch_checklist_count": recruiter_demo_brief.get("ready_launch_checklist_count"),
                    "brief_count": recruiter_demo_brief.get("brief_count"),
                    "ready_brief_count": recruiter_demo_brief.get("ready_brief_count"),
                    "latest_brief_status": recruiter_demo_brief.get("latest_brief_status"),
                    "checked_api_endpoints": recruiter_demo_brief.get("checked_api_endpoints"),
                    "output_dir": recruiter_demo_brief.get("output_dir"),
                },
                "Create at least one recruiter demo brief from a ready final launch checklist.",
            ),
            self.gate(
                "recruiter_demo_brief_ui_and_docs",
                "Recruiter-facing demo brief UI and documentation are packaged",
                "passed" if self.recruiter_demo_brief_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "recruiter_demo_brief.md"),
                    "backend": str(self.project_dir / "backend" / "recruiter_demo_brief.py"),
                    "output_dir": recruiter_demo_brief.get("output_dir"),
                },
                "Keep recruiter demo brief UI panel, docs and API routes together.",
            ),
            self.gate(
                "public_portfolio_package_ready",
                "Public portfolio interview packages are available for portfolio review",
                "passed" if public_portfolio_package.get("public_portfolio_interview_package_version") == "public_portfolio_interview_package_v001" and int(public_portfolio_package.get("ready_package_count") or 0) >= 1 else "failed",
                {
                    "version": public_portfolio_package.get("public_portfolio_interview_package_version"),
                    "ready_recruiter_demo_brief_count": public_portfolio_package.get("ready_recruiter_demo_brief_count"),
                    "package_count": public_portfolio_package.get("package_count"),
                    "ready_package_count": public_portfolio_package.get("ready_package_count"),
                    "latest_package_status": public_portfolio_package.get("latest_package_status"),
                    "checked_api_endpoints": public_portfolio_package.get("checked_api_endpoints"),
                    "output_dir": public_portfolio_package.get("output_dir"),
                },
                "Create at least one public portfolio package from a ready recruiter demo brief.",
            ),
            self.gate(
                "public_portfolio_package_ui_and_docs",
                "Public portfolio interview package UI and documentation are packaged",
                "passed" if self.public_portfolio_package_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "public_portfolio_interview_package.md"),
                    "backend": str(self.project_dir / "backend" / "public_portfolio_interview_package.py"),
                    "output_dir": public_portfolio_package.get("output_dir"),
                },
                "Keep public portfolio package UI panel, docs and API routes together.",
            ),
            self.gate(
                "demo_review_playbook_ready",
                "Demo review playbooks are available for final portfolio review",
                "passed" if demo_review_playbook.get("demo_review_playbook_version") == "demo_review_playbook_v001" and int(demo_review_playbook.get("ready_playbook_count") or 0) >= 1 else "failed",
                {
                    "version": demo_review_playbook.get("demo_review_playbook_version"),
                    "ready_public_portfolio_package_count": demo_review_playbook.get("ready_public_portfolio_package_count"),
                    "playbook_count": demo_review_playbook.get("playbook_count"),
                    "ready_playbook_count": demo_review_playbook.get("ready_playbook_count"),
                    "latest_playbook_status": demo_review_playbook.get("latest_playbook_status"),
                    "checked_api_endpoints": demo_review_playbook.get("checked_api_endpoints"),
                    "output_dir": demo_review_playbook.get("output_dir"),
                },
                "Create at least one demo review playbook from a ready public portfolio package.",
            ),
            self.gate(
                "demo_review_playbook_ui_and_docs",
                "Demo review playbook UI and documentation are packaged",
                "passed" if self.demo_review_playbook_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "demo_review_playbook.md"),
                    "backend": str(self.project_dir / "backend" / "demo_review_playbook.py"),
                    "output_dir": demo_review_playbook.get("output_dir"),
                },
                "Keep demo review playbook UI panel, docs and API routes together.",
            ),
            self.gate(
                "github_publication_bundle_ready",
                "GitHub-ready publication bundles are available for repository sharing",
                "passed" if github_publication_bundle.get("github_publication_bundle_version") == "github_publication_bundle_v001" and int(github_publication_bundle.get("ready_bundle_count") or 0) >= 1 else "failed",
                {
                    "version": github_publication_bundle.get("github_publication_bundle_version"),
                    "ready_demo_review_playbook_count": github_publication_bundle.get("ready_demo_review_playbook_count"),
                    "bundle_count": github_publication_bundle.get("bundle_count"),
                    "ready_bundle_count": github_publication_bundle.get("ready_bundle_count"),
                    "latest_bundle_status": github_publication_bundle.get("latest_bundle_status"),
                    "checked_api_endpoints": github_publication_bundle.get("checked_api_endpoints"),
                    "output_dir": github_publication_bundle.get("output_dir"),
                },
                "Create at least one GitHub-ready publication bundle from a ready demo review playbook.",
            ),
            self.gate(
                "github_publication_bundle_ui_and_docs",
                "GitHub-ready publication bundle UI and documentation are packaged",
                "passed" if self.github_publication_bundle_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "github_publication_bundle.md"),
                    "backend": str(self.project_dir / "backend" / "github_publication_bundle.py"),
                    "output_dir": github_publication_bundle.get("output_dir"),
                },
                "Keep GitHub publication bundle UI panel, docs and API routes together.",
            ),
            self.gate(
                "repository_publication_qa_ready",
                "Repository publication QA reviews are available before public sharing",
                "passed" if repository_publication_qa.get("repository_publication_qa_version") == "repository_publication_qa_v001" and int(repository_publication_qa.get("ready_review_count") or 0) >= 1 else "failed",
                {
                    "version": repository_publication_qa.get("repository_publication_qa_version"),
                    "ready_github_publication_bundle_count": repository_publication_qa.get("ready_github_publication_bundle_count"),
                    "review_count": repository_publication_qa.get("review_count"),
                    "ready_review_count": repository_publication_qa.get("ready_review_count"),
                    "latest_review_status": repository_publication_qa.get("latest_review_status"),
                    "checked_api_endpoints": repository_publication_qa.get("checked_api_endpoints"),
                    "output_dir": repository_publication_qa.get("output_dir"),
                },
                "Create at least one repository publication QA review from a ready GitHub publication bundle.",
            ),
            self.gate(
                "repository_publication_qa_ui_and_docs",
                "Repository publication QA UI and documentation are packaged",
                "passed" if self.repository_publication_qa_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "repository_publication_qa.md"),
                    "backend": str(self.project_dir / "backend" / "repository_publication_qa.py"),
                    "output_dir": repository_publication_qa.get("output_dir"),
                },
                "Keep repository publication QA UI panel, docs and API routes together.",
            ),
            self.gate(
                "repository_export_handoff_ready",
                "Repository export handoffs are available for public GitHub preparation",
                "passed" if repository_export_handoff.get("repository_export_handoff_version") == "repository_export_handoff_v001" and int(repository_export_handoff.get("ready_handoff_count") or 0) >= 1 else "failed",
                {
                    "version": repository_export_handoff.get("repository_export_handoff_version"),
                    "ready_repository_qa_count": repository_export_handoff.get("ready_repository_qa_count"),
                    "handoff_count": repository_export_handoff.get("handoff_count"),
                    "ready_handoff_count": repository_export_handoff.get("ready_handoff_count"),
                    "latest_handoff_status": repository_export_handoff.get("latest_handoff_status"),
                    "checked_api_endpoints": repository_export_handoff.get("checked_api_endpoints"),
                    "output_dir": repository_export_handoff.get("output_dir"),
                },
                "Create at least one repository export handoff from a ready repository QA review.",
            ),
            self.gate(
                "repository_export_handoff_ui_and_docs",
                "Repository export handoff UI and documentation are packaged",
                "passed" if self.repository_export_handoff_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "repository_export_handoff.md"),
                    "backend": str(self.project_dir / "backend" / "repository_export_handoff.py"),
                    "output_dir": repository_export_handoff.get("output_dir"),
                },
                "Keep repository export handoff UI panel, docs and API routes together.",
            ),
            self.gate(
                "repository_dry_run_review_ready",
                "Repository dry-run review subsystem can create final archive checks",
                "passed" if repository_dry_run_review.get("repository_dry_run_review_version") == "repository_dry_run_review_v001" and int(repository_dry_run_review.get("ready_handoff_count") or 0) >= 1 else "failed",
                {
                    "version": repository_dry_run_review.get("repository_dry_run_review_version"),
                    "ready_handoff_count": repository_dry_run_review.get("ready_handoff_count"),
                    "review_count": repository_dry_run_review.get("review_count"),
                    "ready_review_count": repository_dry_run_review.get("ready_review_count"),
                    "latest_review_status": repository_dry_run_review.get("latest_review_status"),
                    "latest_required_failed_count": repository_dry_run_review.get("latest_required_failed_count"),
                    "checked_api_endpoints": repository_dry_run_review.get("checked_api_endpoints"),
                    "output_dir": repository_dry_run_review.get("output_dir"),
                },
                "Keep repository dry-run review creation available from a ready export handoff; validation and API contract create concrete review artifacts.",
            ),
            self.gate(
                "repository_dry_run_review_ui_and_docs",
                "Repository dry-run review UI and documentation are packaged",
                "passed" if self.repository_dry_run_review_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "repository_dry_run_review.md"),
                    "backend": str(self.project_dir / "backend" / "repository_dry_run_review.py"),
                    "output_dir": repository_dry_run_review.get("output_dir"),
                },
                "Keep repository dry-run review UI panel, docs and API routes together.",
            ),
            self.gate(
                "repository_final_package_review_ready",
                "Repository final package review can verify redacted path evidence",
                "passed" if repository_final_package_review.get("repository_final_package_review_version") == "repository_final_package_review_v001" and int(repository_final_package_review.get("ready_dry_run_review_count") or 0) >= 1 else "failed",
                {
                    "version": repository_final_package_review.get("repository_final_package_review_version"),
                    "ready_dry_run_review_count": repository_final_package_review.get("ready_dry_run_review_count"),
                    "review_count": repository_final_package_review.get("review_count"),
                    "ready_review_count": repository_final_package_review.get("ready_review_count"),
                    "latest_review_status": repository_final_package_review.get("latest_review_status"),
                    "latest_required_failed_count": repository_final_package_review.get("latest_required_failed_count"),
                    "latest_public_path_issue_count": repository_final_package_review.get("latest_public_path_issue_count"),
                    "latest_redacted_path_count": repository_final_package_review.get("latest_redacted_path_count"),
                    "checked_api_endpoints": repository_final_package_review.get("checked_api_endpoints"),
                    "output_dir": repository_final_package_review.get("output_dir"),
                },
                "Create a final package review from a ready dry-run review before public sharing.",
            ),
            self.gate(
                "repository_final_package_review_ui_and_docs",
                "Repository final package review UI and documentation are packaged",
                "passed" if self.repository_final_package_review_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "repository_final_package_review.md"),
                    "backend": str(self.project_dir / "backend" / "repository_final_package_review.py"),
                    "output_dir": repository_final_package_review.get("output_dir"),
                },
                "Keep repository final package review UI panel, docs and API routes together.",
            ),
            self.gate(
                "public_readme_cleanup_review_ready",
                "Public README cleanup review can prepare repository-relative README and screenshot evidence",
                "passed" if public_readme_cleanup_review.get("public_readme_cleanup_review_version") == "public_readme_cleanup_review_v001" and int(public_readme_cleanup_review.get("ready_final_package_review_count") or 0) >= 1 else "failed",
                {
                    "version": public_readme_cleanup_review.get("public_readme_cleanup_review_version"),
                    "ready_final_package_review_count": public_readme_cleanup_review.get("ready_final_package_review_count"),
                    "review_count": public_readme_cleanup_review.get("review_count"),
                    "ready_review_count": public_readme_cleanup_review.get("ready_review_count"),
                    "latest_review_status": public_readme_cleanup_review.get("latest_review_status"),
                    "latest_required_failed_count": public_readme_cleanup_review.get("latest_required_failed_count"),
                    "latest_public_readme_issue_count": public_readme_cleanup_review.get("latest_public_readme_issue_count"),
                    "latest_screenshot_evidence_count": public_readme_cleanup_review.get("latest_screenshot_evidence_count"),
                    "checked_api_endpoints": public_readme_cleanup_review.get("checked_api_endpoints"),
                    "output_dir": public_readme_cleanup_review.get("output_dir"),
                },
                "Create a public README cleanup review from a ready final package review before public sharing.",
            ),
            self.gate(
                "public_readme_cleanup_review_ui_and_docs",
                "Public README cleanup review UI and documentation are packaged",
                "passed" if self.public_readme_cleanup_review_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "public_readme_cleanup_review.md"),
                    "backend": str(self.project_dir / "backend" / "public_readme_cleanup_review.py"),
                    "output_dir": public_readme_cleanup_review.get("output_dir"),
                },
                "Keep public README cleanup review UI panel, docs and API routes together.",
            ),
            self.gate(
                "public_repository_polish_package_ready",
                "Public repository polish package can prepare final manual sharing artifacts",
                "passed" if public_repository_polish_package.get("public_repository_polish_package_version") == "public_repository_polish_package_v001" and int(public_repository_polish_package.get("ready_cleanup_review_count") or 0) >= 1 else "failed",
                {
                    "version": public_repository_polish_package.get("public_repository_polish_package_version"),
                    "ready_cleanup_review_count": public_repository_polish_package.get("ready_cleanup_review_count"),
                    "package_count": public_repository_polish_package.get("package_count"),
                    "ready_package_count": public_repository_polish_package.get("ready_package_count"),
                    "latest_package_status": public_repository_polish_package.get("latest_package_status"),
                    "latest_required_failed_count": public_repository_polish_package.get("latest_required_failed_count"),
                    "latest_public_readme_issue_count": public_repository_polish_package.get("latest_public_readme_issue_count"),
                    "latest_screenshot_target_count": public_repository_polish_package.get("latest_screenshot_target_count"),
                    "checked_api_endpoints": public_repository_polish_package.get("checked_api_endpoints"),
                    "output_dir": public_repository_polish_package.get("output_dir"),
                },
                "Create a public repository polish package from a ready public README cleanup review before public sharing.",
            ),
            self.gate(
                "public_repository_polish_package_ui_and_docs",
                "Public repository polish package UI and documentation are packaged",
                "passed" if self.public_repository_polish_package_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "public_repository_polish_package.md"),
                    "backend": str(self.project_dir / "backend" / "public_repository_polish_package.py"),
                    "output_dir": public_repository_polish_package.get("output_dir"),
                },
                "Keep public repository polish package UI panel, docs and API routes together.",
            ),
            self.gate(
                "repository_export_checklist_ready",
                "Repository export checklist can prepare final GitHub-ready manual export evidence",
                "passed" if repository_export_checklist.get("repository_export_checklist_version") == "repository_export_checklist_v001" and int(repository_export_checklist.get("ready_polish_package_count") or 0) >= 1 else "failed",
                {
                    "version": repository_export_checklist.get("repository_export_checklist_version"),
                    "ready_polish_package_count": repository_export_checklist.get("ready_polish_package_count"),
                    "checklist_count": repository_export_checklist.get("checklist_count"),
                    "ready_checklist_count": repository_export_checklist.get("ready_checklist_count"),
                    "latest_checklist_status": repository_export_checklist.get("latest_checklist_status"),
                    "latest_required_failed_count": repository_export_checklist.get("latest_required_failed_count"),
                    "latest_screenshot_target_count": repository_export_checklist.get("latest_screenshot_target_count"),
                    "latest_screenshot_evidence_count": repository_export_checklist.get("latest_screenshot_evidence_count"),
                    "checked_api_endpoints": repository_export_checklist.get("checked_api_endpoints"),
                    "output_dir": repository_export_checklist.get("output_dir"),
                },
                "Create a repository export checklist from a ready public repository polish package before manual GitHub sharing.",
            ),
            self.gate(
                "repository_export_checklist_ui_and_docs",
                "Repository export checklist UI and documentation are packaged",
                "passed" if self.repository_export_checklist_ui_and_docs_present() else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "repository_export_checklist.md"),
                    "backend": str(self.project_dir / "backend" / "repository_export_checklist.py"),
                    "output_dir": repository_export_checklist.get("output_dir"),
                },
                "Keep repository export checklist UI panel, docs and API routes together.",
            ),
            self.gate(
                "comparison_map_exports_ui_and_docs",
                "Comparison map exports UI, docs and pilot evidence are packaged",
                "passed" if self.comparison_map_exports_ui_and_docs_present() and int(comparison_map_exports.get("ready_pilot_count") or 0) >= 2 else "failed",
                {
                    "docs": str(self.project_dir / "docs" / "comparison_map_exports.md"),
                    "backend": str(self.project_dir / "backend" / "comparison_map_exports.py"),
                    "ready_pilot_count": comparison_map_exports.get("ready_pilot_count"),
                    "export_count": comparison_map_exports.get("export_count"),
                },
                "Keep the map export UI panel, docs and API route together.",
            ),
        ]
        return gates

    def gate(self, gate_id: str, label: str, status: str, evidence: dict, recommendation: str) -> dict:
        return {
            "gate_id": gate_id,
            "label": label,
            "status": status,
            "passed": status == "passed",
            "evidence": evidence,
            "recommendation": recommendation,
        }

    def status_counts(self, gates: list[dict]) -> dict:
        counts: dict[str, int] = {"passed": 0, "warning": 0, "failed": 0, "blocked": 0}
        for gate in gates:
            status = str(gate.get("status") or "warning")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def readiness_level(self, counts: dict) -> str:
        if counts.get("failed", 0) > 0 or counts.get("blocked", 0) > 0:
            return "not_ready_for_release"
        if counts.get("warning", 0) > 0:
            return "ready_with_verification_warnings"
        return "ready_for_local_portfolio_demo"

    def group_counts(self, gates: list[dict]) -> dict:
        groups = {
            "data_and_claims": ["source_gis_read_only_policy", "approved_wording_policy", "source_onboarding_available", "source_import_guardrails_reviewed", "source_handoff_ready", "source_handoff_execution_ready", "execution_evidence_package_ready", "execution_result_diff_ready", "execution_diff_gallery_ready", "execution_diff_detail_ready", "reproducibility_audit_packet_ready", "reviewer_audit_index_ready", "portfolio_export_launcher_ready", "portable_release_package_ready", "demo_script_pack_ready", "visual_qa_snapshot_ledger_ready", "visual_baseline_comparison_ready", "demo_artifact_completeness_ready", "visual_evidence_capture_ready", "visual_evidence_review_diff_ready", "visual_evidence_review_annotations_ready", "visual_evidence_signoff_packet_ready", "final_reviewer_launch_checklist_ready", "recruiter_demo_brief_ready", "public_portfolio_package_ready", "demo_review_playbook_ready", "github_publication_bundle_ready", "repository_publication_qa_ready", "repository_export_handoff_ready", "repository_dry_run_review_ready", "repository_final_package_review_ready", "public_readme_cleanup_review_ready", "public_repository_polish_package_ready", "repository_export_checklist_ready"],
            "analytics": ["profile_dashboard_outputs", "scoring_audit_exact_match", "postgis_planning_ready"],
            "profile_contracts": ["profile_mapper_contracts_valid", "contract_execution_adapters_ready", "template_authoring_and_authored_runner", "promotion_lifecycle_gates"],
            "release_evidence": ["release_manifest_current", "product_architecture_current", "local_validation_summary", "api_contract_summary", "release_readiness_ui_and_docs", "bundle_review_checklist_ui_and_docs", "portfolio_narrative_export_ui_and_docs", "portfolio_handoff_page_ui_and_docs", "portfolio_evidence_gallery_ui_and_docs", "multi_pilot_comparison_ui_and_docs", "comparison_map_exports_ui_and_docs", "source_import_guardrails_ui_and_docs", "source_handoff_ui_and_docs", "source_handoff_execution_ui_and_docs", "execution_evidence_package_ui_and_docs", "execution_result_diff_ui_and_docs", "execution_diff_gallery_ui_and_docs", "execution_diff_detail_ui_and_docs", "reproducibility_audit_packet_ui_and_docs", "reviewer_audit_index_ui_and_docs", "portfolio_export_launcher_ui_and_docs", "portable_release_package_ui_and_docs", "demo_script_pack_ui_and_docs", "visual_qa_snapshot_ledger_ui_and_docs", "visual_baseline_comparison_ui_and_docs", "demo_artifact_completeness_ui_and_docs", "visual_evidence_capture_ui_and_docs", "visual_evidence_review_diff_ui_and_docs", "visual_evidence_review_annotations_ui_and_docs", "visual_evidence_signoff_packet_ui_and_docs", "final_reviewer_launch_checklist_ui_and_docs", "recruiter_demo_brief_ui_and_docs", "public_portfolio_package_ui_and_docs", "demo_review_playbook_ui_and_docs", "github_publication_bundle_ui_and_docs", "repository_publication_qa_ui_and_docs", "repository_export_handoff_ui_and_docs", "repository_dry_run_review_ui_and_docs", "repository_final_package_review_ui_and_docs", "public_readme_cleanup_review_ui_and_docs", "public_repository_polish_package_ui_and_docs", "repository_export_checklist_ui_and_docs"],
            "reproducibility": ["controlled_queue_and_dataset_packages", "execution_result_diff_ready", "execution_diff_gallery_ready", "execution_diff_detail_ready", "reproducibility_audit_packet_ready", "reviewer_audit_index_ready", "portfolio_export_launcher_ready", "portable_release_package_ready", "demo_script_pack_ready", "visual_qa_snapshot_ledger_ready", "visual_baseline_comparison_ready", "demo_artifact_completeness_ready", "visual_evidence_capture_ready", "visual_evidence_review_diff_ready", "visual_evidence_review_annotations_ready", "visual_evidence_signoff_packet_ready", "final_reviewer_launch_checklist_ready", "recruiter_demo_brief_ready", "public_portfolio_package_ready", "demo_review_playbook_ready", "github_publication_bundle_ready", "repository_publication_qa_ready", "repository_export_handoff_ready", "repository_dry_run_review_ready", "repository_final_package_review_ready", "public_readme_cleanup_review_ready", "public_repository_polish_package_ready", "repository_export_checklist_ready"],
        }
        result: dict[str, dict[str, int]] = {}
        by_id = {gate.get("gate_id"): gate for gate in gates}
        for group, gate_ids in groups.items():
            group_gates = [by_id[gate_id] for gate_id in gate_ids if gate_id in by_id]
            result[group] = self.status_counts(group_gates)
            result[group]["gate_count"] = len(group_gates)
        return result

    def required_next_actions(self, gates: list[dict]) -> list[str]:
        actions = []
        for gate in gates:
            if gate.get("status") != "passed":
                actions.append(f"{gate.get('gate_id')}: {gate.get('recommendation')}")
        return actions[:8]

    def ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "release_readiness_dashboard.md"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and "Release Readiness Dashboard" in docs.read_text(encoding="utf-8")
                and "releaseReadinessBody" in index.read_text(encoding="utf-8")
                and "loadReleaseReadiness" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def bundle_review_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "bundle_review_checklist.md"
        backend = self.project_dir / "backend" / "bundle_review_checklist.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Bundle Review Checklist" in docs.read_text(encoding="utf-8")
                and "bundleReviewChecklistBody" in index.read_text(encoding="utf-8")
                and "loadBundleReviewChecklist" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def portfolio_narrative_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "portfolio_narrative_export.md"
        backend = self.project_dir / "backend" / "portfolio_narrative_export.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Portfolio Narrative Export" in docs.read_text(encoding="utf-8")
                and "portfolioNarrativeBody" in index.read_text(encoding="utf-8")
                and "loadPortfolioNarrative" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def portfolio_handoff_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "portfolio_handoff_page.md"
        backend = self.project_dir / "backend" / "portfolio_handoff_page.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Portfolio Handoff Page" in docs.read_text(encoding="utf-8")
                and "portfolioHandoffBody" in index.read_text(encoding="utf-8")
                and "loadPortfolioHandoff" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def portfolio_gallery_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "portfolio_evidence_gallery.md"
        backend = self.project_dir / "backend" / "portfolio_evidence_gallery.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Portfolio Evidence Gallery" in docs.read_text(encoding="utf-8")
                and "portfolioEvidenceGalleryBody" in index.read_text(encoding="utf-8")
                and "loadPortfolioEvidenceGallery" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def multi_pilot_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "multi_pilot_comparison.md"
        backend = self.project_dir / "backend" / "multi_pilot_comparison.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Multi-Pilot Comparison" in docs.read_text(encoding="utf-8")
                and "multiPilotComparisonBody" in index.read_text(encoding="utf-8")
                and "loadMultiPilotComparison" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def source_import_guardrails_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "source_import_guardrails.md"
        backend = self.project_dir / "backend" / "source_import_guardrails.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Source Import Guardrails" in docs.read_text(encoding="utf-8")
                and "sourceImportGuardrailsBody" in index.read_text(encoding="utf-8")
                and "loadSourceImportGuardrails" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def source_handoff_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "source_handoff.md"
        backend = self.project_dir / "backend" / "source_handoff.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Source Handoff" in docs.read_text(encoding="utf-8")
                and "sourceHandoffBody" in index.read_text(encoding="utf-8")
                and "loadSourceHandoff" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def source_handoff_execution_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "source_handoff_execution.md"
        backend = self.project_dir / "backend" / "source_handoff_execution.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Source Handoff Execution" in docs.read_text(encoding="utf-8")
                and "sourceHandoffExecutionBody" in index.read_text(encoding="utf-8")
                and "loadSourceHandoffExecution" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def execution_evidence_package_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "execution_evidence_package.md"
        backend = self.project_dir / "backend" / "execution_evidence_package.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Execution Evidence Package" in docs.read_text(encoding="utf-8")
                and "executionEvidencePackageBody" in index.read_text(encoding="utf-8")
                and "loadExecutionEvidencePackage" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def execution_result_diff_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "execution_result_diff.md"
        backend = self.project_dir / "backend" / "execution_result_diff.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Execution Result Diff" in docs.read_text(encoding="utf-8")
                and "executionResultDiffBody" in index.read_text(encoding="utf-8")
                and "loadExecutionResultDiff" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def execution_diff_gallery_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "execution_diff_gallery.md"
        backend = self.project_dir / "backend" / "execution_diff_gallery.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Execution Diff Gallery" in docs.read_text(encoding="utf-8")
                and "executionDiffGalleryBody" in index.read_text(encoding="utf-8")
                and "loadExecutionDiffGallery" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def execution_diff_detail_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "execution_diff_detail.md"
        backend = self.project_dir / "backend" / "execution_diff_detail.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Execution Diff Detail" in docs.read_text(encoding="utf-8")
                and "executionDiffDetailBody" in index.read_text(encoding="utf-8")
                and "loadExecutionDiffDetail" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def reproducibility_audit_packet_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "reproducibility_audit_packet.md"
        backend = self.project_dir / "backend" / "reproducibility_audit_packet.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Reproducibility Audit Packet" in docs.read_text(encoding="utf-8")
                and "reproducibilityAuditPacketBody" in index.read_text(encoding="utf-8")
                and "loadReproducibilityAuditPacket" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def reviewer_audit_index_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "reviewer_audit_index.md"
        backend = self.project_dir / "backend" / "reviewer_audit_index.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Reviewer Audit Index" in docs.read_text(encoding="utf-8")
                and "reviewerAuditIndexBody" in index.read_text(encoding="utf-8")
                and "loadReviewerAuditIndex" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def portfolio_export_launcher_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "portfolio_export_launcher.md"
        backend = self.project_dir / "backend" / "portfolio_export_launcher.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Portfolio Export Launcher" in index.read_text(encoding="utf-8")
            and "portfolioExportLauncherBody" in app_js.read_text(encoding="utf-8")
            and "loadPortfolioExportLauncher" in app_js.read_text(encoding="utf-8")
        )

    def portable_release_package_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "portable_release_package.md"
        backend = self.project_dir / "backend" / "portable_release_package.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Portable Release Package" in index.read_text(encoding="utf-8")
            and "portableReleasePackageBody" in app_js.read_text(encoding="utf-8")
            and "loadPortableReleasePackage" in app_js.read_text(encoding="utf-8")
        )

    def demo_script_pack_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "demo_script_pack.md"
        backend = self.project_dir / "backend" / "demo_script_pack.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Demo Script Pack" in index.read_text(encoding="utf-8")
            and "demoScriptPackBody" in app_js.read_text(encoding="utf-8")
            and "loadDemoScriptPack" in app_js.read_text(encoding="utf-8")
        )

    def visual_qa_snapshot_ledger_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "visual_qa_snapshot_ledger.md"
        backend = self.project_dir / "backend" / "visual_qa_snapshot_ledger.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Visual QA Snapshot Ledger" in index.read_text(encoding="utf-8")
            and "visualQALedgerBody" in app_js.read_text(encoding="utf-8")
            and "loadVisualQALedger" in app_js.read_text(encoding="utf-8")
        )

    def visual_baseline_comparison_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "visual_baseline_comparison.md"
        backend = self.project_dir / "backend" / "visual_baseline_comparison.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Visual Baseline Comparison" in index.read_text(encoding="utf-8")
            and "visualBaselineComparisonBody" in app_js.read_text(encoding="utf-8")
            and "loadVisualBaselineComparison" in app_js.read_text(encoding="utf-8")
        )

    def visual_evidence_capture_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "visual_evidence_capture.md"
        backend = self.project_dir / "backend" / "visual_evidence_capture.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Visual Evidence Capture" in index.read_text(encoding="utf-8")
            and "visualEvidenceCaptureBody" in app_js.read_text(encoding="utf-8")
            and "loadVisualEvidenceCapture" in app_js.read_text(encoding="utf-8")
        )

    def visual_evidence_review_diff_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "visual_evidence_review_diff.md"
        backend = self.project_dir / "backend" / "visual_evidence_review_diff.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Visual Evidence Review Diff" in docs.read_text(encoding="utf-8")
            and "Visual Evidence Review Diff" in index.read_text(encoding="utf-8")
            and "visualEvidenceReviewDiff" in app_js.read_text(encoding="utf-8")
        )

    def visual_evidence_review_annotations_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "visual_evidence_review_annotations.md"
        backend = self.project_dir / "backend" / "visual_evidence_review_annotations.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Visual Evidence Review Annotations" in docs.read_text(encoding="utf-8")
            and "Visual Evidence Review Annotations" in index.read_text(encoding="utf-8")
            and "visualEvidenceReviewAnnotations" in app_js.read_text(encoding="utf-8")
        )

    def visual_evidence_signoff_packet_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "visual_evidence_signoff_packet.md"
        backend = self.project_dir / "backend" / "visual_evidence_signoff_packet.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Visual Evidence Sign-Off Packet" in docs.read_text(encoding="utf-8")
            and "Visual Evidence Sign-Off Packet" in index.read_text(encoding="utf-8")
            and "visualEvidenceSignoffPacket" in app_js.read_text(encoding="utf-8")
        )

    def final_reviewer_launch_checklist_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "final_reviewer_launch_checklist.md"
        backend = self.project_dir / "backend" / "final_reviewer_launch_checklist.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Final Reviewer Launch Checklist" in docs.read_text(encoding="utf-8")
            and "Final Reviewer Launch Checklist" in index.read_text(encoding="utf-8")
            and "finalReviewerLaunchChecklist" in app_js.read_text(encoding="utf-8")
        )

    def recruiter_demo_brief_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "recruiter_demo_brief.md"
        backend = self.project_dir / "backend" / "recruiter_demo_brief.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Recruiter-Facing Demo Brief" in docs.read_text(encoding="utf-8")
            and "Recruiter-Facing Demo Brief" in index.read_text(encoding="utf-8")
            and "recruiterDemoBrief" in app_js.read_text(encoding="utf-8")
        )


    def public_portfolio_package_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "public_portfolio_interview_package.md"
        backend = self.project_dir / "backend" / "public_portfolio_interview_package.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Public Portfolio Interview Package" in docs.read_text(encoding="utf-8")
            and "Public Portfolio Package" in index.read_text(encoding="utf-8")
            and "publicPortfolioPackage" in app_js.read_text(encoding="utf-8")
        )


    def demo_review_playbook_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "demo_review_playbook.md"
        backend = self.project_dir / "backend" / "demo_review_playbook.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Demo Review Playbook" in docs.read_text(encoding="utf-8")
            and "Demo Review Playbook" in index.read_text(encoding="utf-8")
            and "demoReviewPlaybook" in app_js.read_text(encoding="utf-8")
        )


    def github_publication_bundle_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "github_publication_bundle.md"
        backend = self.project_dir / "backend" / "github_publication_bundle.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "GitHub-ready Publication Bundle" in docs.read_text(encoding="utf-8")
            and "GitHub-ready Publication Bundle" in index.read_text(encoding="utf-8")
            and "githubPublicationBundle" in app_js.read_text(encoding="utf-8")
        )

    def repository_publication_qa_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "repository_publication_qa.md"
        backend = self.project_dir / "backend" / "repository_publication_qa.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Repository Publication QA" in docs.read_text(encoding="utf-8")
            and "Repository Publication QA" in index.read_text(encoding="utf-8")
            and "repositoryPublicationQa" in app_js.read_text(encoding="utf-8")
        )

    def repository_export_handoff_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "repository_export_handoff.md"
        backend = self.project_dir / "backend" / "repository_export_handoff.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Repository Export Handoff" in docs.read_text(encoding="utf-8")
            and "Repository Export Handoff" in index.read_text(encoding="utf-8")
            and "repositoryExportHandoff" in app_js.read_text(encoding="utf-8")
        )


    def repository_dry_run_review_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "repository_dry_run_review.md"
        backend = self.project_dir / "backend" / "repository_dry_run_review.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Repository Dry-Run Review" in docs.read_text(encoding="utf-8")
            and "Repository Dry-Run Review" in index.read_text(encoding="utf-8")
            and "repositoryDryRunReview" in app_js.read_text(encoding="utf-8")
        )

    def repository_final_package_review_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "repository_final_package_review.md"
        backend = self.project_dir / "backend" / "repository_final_package_review.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Repository Final Package Review" in docs.read_text(encoding="utf-8")
            and "Repository Final Package Review" in index.read_text(encoding="utf-8")
            and "repositoryFinalPackageReview" in app_js.read_text(encoding="utf-8")
        )

    def public_readme_cleanup_review_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "public_readme_cleanup_review.md"
        backend = self.project_dir / "backend" / "public_readme_cleanup_review.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Public README Cleanup Review" in docs.read_text(encoding="utf-8")
            and "Public README Cleanup Review" in index.read_text(encoding="utf-8")
            and "publicReadmeCleanupReview" in app_js.read_text(encoding="utf-8")
        )

    def public_repository_polish_package_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "public_repository_polish_package.md"
        backend = self.project_dir / "backend" / "public_repository_polish_package.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Final Public Repository Polish Package" in docs.read_text(encoding="utf-8")
            and "Public Repository Polish Package" in index.read_text(encoding="utf-8")
            and "publicRepositoryPolishPackage" in app_js.read_text(encoding="utf-8")
        )

    def repository_export_checklist_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "repository_export_checklist.md"
        backend = self.project_dir / "backend" / "repository_export_checklist.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Repository Export Checklist" in docs.read_text(encoding="utf-8")
            and "Repository Export Checklist" in index.read_text(encoding="utf-8")
            and "repositoryExportChecklist" in app_js.read_text(encoding="utf-8")
        )


    def demo_artifact_completeness_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "demo_artifact_completeness.md"

        backend = self.project_dir / "backend" / "demo_artifact_completeness.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        return (
            docs.exists()
            and backend.exists()
            and "Demo Artifact Completeness" in index.read_text(encoding="utf-8")
            and "demoArtifactCompletenessBody" in app_js.read_text(encoding="utf-8")
            and "loadDemoArtifactCompleteness" in app_js.read_text(encoding="utf-8")
        )

    def comparison_map_exports_ui_and_docs_present(self) -> bool:
        docs = self.project_dir / "docs" / "comparison_map_exports.md"
        backend = self.project_dir / "backend" / "comparison_map_exports.py"
        index = self.project_dir / "frontend" / "static" / "index.html"
        app_js = self.project_dir / "frontend" / "static" / "app.js"
        try:
            return (
                docs.exists()
                and backend.exists()
                and "Comparison Map Exports" in docs.read_text(encoding="utf-8")
                and "comparisonMapExportsBody" in index.read_text(encoding="utf-8")
                and "loadComparisonMapExports" in app_js.read_text(encoding="utf-8")
            )
        except OSError:
            return False

    def snapshot_markdown(self, snapshot: dict) -> str:
        overview = snapshot.get("overview", {})
        gates = overview.get("gates", [])
        lines = [
            "# GeoReview Studio Release Readiness Snapshot",
            "",
            f"Snapshot: `{snapshot.get('snapshot_id')}`",
            f"Created: `{snapshot.get('created_at')}`",
            f"Readiness level: `{snapshot.get('readiness_level')}`",
            "",
            "Approved review wording:",
            "",
            f"`{self.review_wording}`",
            "",
            "## Gate Summary",
            "",
            f"- Gate count: `{snapshot.get('gate_count')}`",
            f"- Failed gates: `{snapshot.get('failed_gate_count')}`",
            f"- Warning gates: `{snapshot.get('warning_gate_count')}`",
            "",
            "## Gates",
            "",
        ]
        for gate in gates:
            lines.append(f"- `{gate.get('gate_id')}`: `{gate.get('status')}` - {gate.get('label')}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            "The snapshot supports infrastructure review prioritization and data-quality evidence only.",
            "It does not label a location and does not predict crashes.",
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)


