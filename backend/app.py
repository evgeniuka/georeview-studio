from __future__ import annotations

import csv
import json
import logging
import mimetypes
import os
import re
import sys

if sys.version_info < (3, 9):  # noqa: UP036 - runtime floor: str.removeprefix() is 3.9+
    raise SystemExit(
        "GeoReview Studio requires Python 3.9 or newer; "
        f"detected {sys.version_info.major}.{sys.version_info.minor}."
    )

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from analysis_profiles import SAFE_ACCESS_PROFILE_ID, AnalysisProfileRegistry
from analysis_runs import AnalysisRuns
from analysis_workflow import AnalysisWorkflow
from authored_profile_runner import DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID, AuthoredProfileRunner
from contract_execution import ContractExecutionAdapter
from execution_queue import ControlledExecutionQueue
from dataset_package import DatasetPackageBuilder
from park_playground_access_analyzer import DEFAULT_PARK_PLAYGROUND_WORKSPACE_ID, ParkPlaygroundAccessAnalyzer
from osm_tag_quality import DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID, OSMTagQualityAnalyzer
from pilot_area_catalog import DEFAULT_SOURCE_DATASET_ID, PilotAreaCatalog
from portfolio_report_builder import PortfolioReportBuilder
from postgis_backend import PostGISBackendPlanner
from profile_mapper import ProfileMapperRegistry
from profile_promotion import ProfilePromotionWizard
from profile_export_bundle import ProfileExportBundleBuilder
from preflight import SafeAccessPreflight
from profile_dashboard import ProfileDashboardStore
from local_intake import LocalIntakeWizard
from product_architecture import ProductArchitecture
from portfolio_demo import PortfolioDemoWalkthrough
from portfolio_evidence_bundle import PortfolioEvidenceBundleBuilder
from bundle_review_checklist import BundleReviewChecklist
from portfolio_narrative_export import PortfolioNarrativeExporter
from portfolio_handoff_page import PortfolioHandoffPageBuilder
from portfolio_evidence_gallery import PortfolioEvidenceGalleryBuilder
from multi_pilot_comparison import MultiPilotComparisonBuilder
from comparison_map_exports import ComparisonMapExportBuilder
from source_import_guardrails import SourceImportGuardrails
from source_handoff import SourceHandoffPlanner
from source_handoff_execution import SourceHandoffExecutionController
from execution_evidence_package import ExecutionEvidencePackageBuilder
from execution_result_diff import ExecutionResultDiffBuilder
from execution_diff_gallery import ExecutionDiffGalleryBuilder
from execution_diff_detail import ExecutionDiffDetailDrilldownBuilder
from reproducibility_audit_packet import ReproducibilityAuditPacketBuilder
from reviewer_audit_index import ReviewerAuditIndexBuilder
from portfolio_export_launcher import PortfolioExportLauncherBuilder
from portable_release_package import PortableReleasePackageBuilder
from demo_script_pack import DemoScriptPackBuilder
from visual_qa_snapshot_ledger import VisualQASnapshotLedgerBuilder
from visual_baseline_comparison import VisualBaselineComparisonManifestBuilder
from demo_artifact_completeness import DemoArtifactCompletenessValidator
from visual_evidence_capture import VisualEvidenceCaptureBuilder
from visual_evidence_review_diff import VisualEvidenceReviewDiffBuilder
from visual_evidence_review_annotations import VisualEvidenceReviewAnnotationsBuilder
from visual_evidence_signoff_packet import VisualEvidenceSignoffPacketBuilder
from final_reviewer_launch_checklist import FinalReviewerLaunchChecklistBuilder
from recruiter_demo_brief import RecruiterDemoBriefBuilder
from public_portfolio_interview_package import PublicPortfolioInterviewPackageBuilder
from demo_review_playbook import DemoReviewPlaybookBuilder
from github_publication_bundle import GitHubPublicationBundleBuilder
from repository_publication_qa import RepositoryPublicationQABuilder
from repository_export_handoff import RepositoryExportHandoffBuilder
from repository_dry_run_review import RepositoryDryRunReviewBuilder
from repository_final_package_review import RepositoryFinalPackageReviewBuilder
from public_readme_cleanup_review import PublicReadmeCleanupReviewBuilder
from public_repository_polish_package import PublicRepositoryPolishPackageBuilder
from repository_export_checklist import RepositoryExportChecklistBuilder
from release_readiness import ReleaseReadinessDashboard
from run_job_manager import RunJobManager
from review_decisions import ReviewDecisionStore
from scoring_rules import ScoringRulesStore
from route_network_analyzer import ROUTE_WORKSPACE_ID, RouteNetworkAnalyzer
from source_onboarding import SourceOnboarding
from transit_access_analyzer import DEFAULT_TRANSIT_WORKSPACE_ID, TransitAccessAnalyzer
from template_authoring import TemplateAuthoringWizard
from workspace_runner import WorkspaceRunner


APP_VERSION = "v083"
LOGGER = logging.getLogger("georeview")
MAX_REQUEST_BODY_BYTES = 8 * 1024 * 1024  # reject JSON request bodies larger than 8 MiB
APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
STATIC_DIR = PROJECT_DIR / "frontend" / "static"
PROJECT_MANIFEST_PATH = PROJECT_DIR / "project_manifest.json"
SCORING_RULES_CONFIG_PATH = PROJECT_DIR / "config" / "scoring_rules_v001.json"
POSTGIS_SCHEMA_PATH = PROJECT_DIR / "config" / "postgis_schema_v001.sql"
PROFILE_MAPPER_CONFIG_PATH = PROJECT_DIR / "config" / "profile_mapper_contracts_v001.json"


def infer_maps_root(project_dir: Path) -> Path:
    for parent in project_dir.parents:
        if parent.name == "analysis_output":
            return parent.parent
    return project_dir.parent


def is_within(path: Path, root: Path) -> bool:
    """True if path resolves to root itself or a descendant of root (traversal-safe)."""
    try:
        path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return False
    return True


# Product vs internal tooling surface. With GEOREVIEW_MODE=product only the core
# GIS-review endpoints (plus the static frontend) are served; the ~50 internal
# publication/QA "tooling layer" endpoints return 404. Default ("full") serves
# everything and is what the two test suites run against - so this gate is inert
# unless explicitly opted into. See docs/product_mode.md.
PRODUCT_MODE = os.environ.get("GEOREVIEW_MODE", "full").strip().lower() == "product"
PRODUCT_API_PREFIXES = (
    "/api/health",
    "/api/project-manifest",
    "/api/catalog/sources",
    "/api/templates",
    "/api/pilot-areas",
    "/api/dashboard-workspaces",
    "/api/workspace-registry",
    "/api/analysis-profiles",
    "/api/analysis-runs",
    "/api/runs",
    "/api/jobs",
    "/api/scoring-rules",
    "/api/profile-dashboard",
    "/api/profile-workspaces",
    "/api/preflight",
    "/api/analysis-workflow",
    "/api/osm-tag-quality",
    "/api/portfolio-reports",
)


def served_in_product_mode(path: str) -> bool:
    if not path.startswith("/api/"):
        return True
    return any(path == prefix or path.startswith(prefix + "/") for prefix in PRODUCT_API_PREFIXES)


# P4.1 first batch: data-driven GET dispatch for exact-path, single-statement arms.
# Each handler mirrors its former if/elif body byte-for-byte. Signature is uniform
# (self, segments, query) so the dispatcher can call every entry the same way.
ROUTE_TABLE_GET = {
    "/api/health": lambda self, segments, query: self.json_response({"ok": True, "app_version": APP_VERSION, "workspace_id": WORKSPACE_ID, "data_root_ok": OUTPUT_ROOT.exists(), "mode": "product" if PRODUCT_MODE else "full"}),
    "/api/project-manifest": lambda self, segments, query: self.json_or_error_response(project_manifest()),
    "/api/product-architecture": lambda self, segments, query: self.json_response(PRODUCT_ARCHITECTURE.blueprint()),
    "/api/product-architecture/variants": lambda self, segments, query: self.json_response(PRODUCT_ARCHITECTURE.variants()),
    "/api/product-architecture/roadmap": lambda self, segments, query: self.json_response(PRODUCT_ARCHITECTURE.roadmap()),
    "/api/release-readiness": lambda self, segments, query: self.json_response(RELEASE_READINESS.overview()),
    "/api/release-readiness/gates": lambda self, segments, query: self.json_response(RELEASE_READINESS.gates_response()),
    "/api/release-readiness/snapshots": lambda self, segments, query: self.json_response(RELEASE_READINESS.list_snapshots(parse_int(first(query, "limit", "20"), 20))),
    "/api/portfolio-demo": lambda self, segments, query: self.json_response(PORTFOLIO_DEMO.overview()),
    "/api/portfolio-demo/steps": lambda self, segments, query: self.json_response(PORTFOLIO_DEMO.steps_response()),
    "/api/portfolio-demo/snapshots": lambda self, segments, query: self.json_response(PORTFOLIO_DEMO.list_snapshots(parse_int(first(query, "limit", "20"), 20))),
    "/api/portfolio-evidence-bundle": lambda self, segments, query: self.json_response(PORTFOLIO_EVIDENCE_BUNDLE.status()),
    "/api/portfolio-evidence-bundle/bundles": lambda self, segments, query: self.json_response(PORTFOLIO_EVIDENCE_BUNDLE.list_bundles(parse_int(first(query, "limit", "20"), 20))),
    "/api/bundle-review-checklist": lambda self, segments, query: self.json_response(BUNDLE_REVIEW_CHECKLIST.status()),
    "/api/bundle-review-checklist/checklists": lambda self, segments, query: self.json_response(BUNDLE_REVIEW_CHECKLIST.list_checklists(parse_int(first(query, "limit", "20"), 20))),
    "/api/portfolio-narrative-export": lambda self, segments, query: self.json_response(PORTFOLIO_NARRATIVE_EXPORT.status()),
    "/api/portfolio-narrative-export/narratives": lambda self, segments, query: self.json_response(PORTFOLIO_NARRATIVE_EXPORT.list_narratives(parse_int(first(query, "limit", "20"), 20))),
    "/api/portfolio-handoff-page": lambda self, segments, query: self.json_response(PORTFOLIO_HANDOFF_PAGE.status()),
    "/api/portfolio-handoff-page/pages": lambda self, segments, query: self.json_response(PORTFOLIO_HANDOFF_PAGE.list_pages(parse_int(first(query, "limit", "20"), 20))),
    "/api/portfolio-evidence-gallery": lambda self, segments, query: self.json_response(PORTFOLIO_EVIDENCE_GALLERY.status()),
    "/api/portfolio-evidence-gallery/galleries": lambda self, segments, query: self.json_response(PORTFOLIO_EVIDENCE_GALLERY.list_galleries(parse_int(first(query, "limit", "20"), 20))),
    "/api/multi-pilot-comparison": lambda self, segments, query: self.json_response(MULTI_PILOT_COMPARISON.status()),
    "/api/multi-pilot-comparison/comparisons": lambda self, segments, query: self.json_response(MULTI_PILOT_COMPARISON.list_comparisons(parse_int(first(query, "limit", "20"), 20))),
    "/api/comparison-map-exports": lambda self, segments, query: self.json_response(COMPARISON_MAP_EXPORTS.status()),
    "/api/comparison-map-exports/exports": lambda self, segments, query: self.json_response(COMPARISON_MAP_EXPORTS.list_exports(parse_int(first(query, "limit", "20"), 20))),
    "/api/postgis-backend": lambda self, segments, query: self.json_or_error_response(POSTGIS_BACKEND.status()),
    "/api/postgis-backend/schema": lambda self, segments, query: self.json_or_error_response(POSTGIS_BACKEND.schema()),
    "/api/postgis-backend/migration-plan": lambda self, segments, query: self.json_or_error_response(POSTGIS_BACKEND.migration_plan({"scope": first(query, "scope", "kfar_saba_pilot")})),
    "/api/postgis-backend/plans": lambda self, segments, query: self.json_response(POSTGIS_BACKEND.list_plans(parse_int(first(query, "limit", "20"), 20))),
}


_DATA_ROOT_ENV = os.environ.get("GEOREVIEW_DATA_ROOT")
MAPS_ROOT = Path(_DATA_ROOT_ENV).expanduser().resolve() if _DATA_ROOT_ENV else infer_maps_root(PROJECT_DIR)
OUTPUT_ROOT = MAPS_ROOT / "analysis_output"
MVP_DIR = OUTPUT_ROOT / "kfar_saba_mvp"
PLAN_DIR = OUTPUT_ROOT / "georeview_studio_plan" / "v001_2026-05-27"
WORKSPACES_DIR = OUTPUT_ROOT / "georeview_studio_workspaces"
RUNS_DIR = OUTPUT_ROOT / "georeview_studio_runs"
PORTFOLIO_REPORTS_DIR = OUTPUT_ROOT / "georeview_studio_portfolio_reports"
DEFAULT_SOURCE_ZIP = MAPS_ROOT / "israel-and-palestine-260521-free.shp.zip"
WORKSPACE_ID = "template_001_safe_access_kfar_saba"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


class ApiBadRequest(Exception):
    pass


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def project_manifest() -> dict:
    manifest = read_json(PROJECT_MANIFEST_PATH)
    if not manifest:
        return {"error": "manifest_not_found", "path": str(PROJECT_MANIFEST_PATH)}
    return manifest


def parse_number(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def slug(value: str) -> str:
    lowered = value.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "dataset"


def first(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key)
    return values[0] if values else default


def parse_json_array(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def split_columns(value: str, limit: int = 12) -> list[str]:
    columns = []
    for item in (value or "").split(";"):
        name = item.strip().split(":", 1)[0].strip()
        if name:
            columns.append(name)
    return columns[:limit]


def status_for_error(data: object, default_status: int = 200) -> int:
    if not isinstance(data, dict) or "error" not in data:
        return default_status
    if not data.get("error"):
        return default_status
    error = str(data.get("error"))
    if error in {"not_found", "static_not_found", "release_readiness_snapshot_not_found", "portfolio_demo_snapshot_not_found", "portfolio_evidence_bundle_not_found", "portfolio_evidence_bundle_output_not_found", "bundle_review_checklist_not_found", "bundle_review_checklist_output_not_found", "portfolio_narrative_not_found", "portfolio_narrative_output_not_found", "portfolio_handoff_page_not_found", "portfolio_handoff_page_output_not_found", "portfolio_evidence_gallery_not_found", "portfolio_evidence_gallery_output_not_found", "multi_pilot_comparison_not_found", "multi_pilot_comparison_output_not_found", "comparison_map_export_not_found", "comparison_map_export_output_not_found", "source_import_request_not_found", "source_import_review_output_not_found", "source_handoff_not_found", "source_handoff_output_not_found", "source_handoff_execution_not_found", "source_handoff_execution_output_not_found", "execution_evidence_package_not_found", "execution_evidence_package_output_not_found", "execution_result_diff_not_found", "execution_result_diff_output_not_found", "execution_diff_gallery_not_found", "execution_diff_gallery_output_not_found", "execution_diff_detail_not_found", "execution_diff_detail_output_not_found", "reproducibility_audit_packet_not_found", "reproducibility_audit_packet_output_not_found", "reviewer_audit_index_not_found", "reviewer_audit_index_output_not_found", "portfolio_export_launcher_not_found", "portfolio_export_launcher_output_not_found", "portable_release_package_not_found", "portable_release_package_output_not_found", "demo_script_pack_not_found", "demo_script_pack_output_not_found", "visual_qa_ledger_not_found", "visual_qa_ledger_output_not_found", "visual_baseline_comparison_not_found", "visual_baseline_comparison_output_not_found", "demo_artifact_completeness_check_not_found", "demo_artifact_completeness_output_not_found", "visual_evidence_capture_not_found", "visual_evidence_capture_output_not_found", "visual_evidence_review_diff_not_found", "visual_evidence_review_diff_output_not_found", "visual_evidence_review_annotations_not_found", "visual_evidence_review_annotations_output_not_found", "visual_evidence_signoff_packet_not_found", "visual_evidence_signoff_packet_output_not_found", "final_reviewer_launch_checklist_not_found", "final_reviewer_launch_checklist_output_not_found", "recruiter_demo_brief_not_found", "recruiter_demo_brief_output_not_found", "public_portfolio_package_not_found", "public_portfolio_package_output_not_found", "demo_review_playbook_not_found", "demo_review_playbook_output_not_found", "github_publication_bundle_not_found", "github_publication_bundle_output_not_found", "repository_publication_qa_not_found", "repository_publication_qa_output_not_found", "repository_export_handoff_not_found", "repository_export_handoff_output_not_found", "repository_dry_run_review_not_found", "repository_dry_run_review_output_not_found", "repository_final_package_review_not_found", "repository_final_package_review_output_not_found", "public_readme_cleanup_review_not_found", "public_readme_cleanup_review_output_not_found", "public_repository_polish_package_not_found", "public_repository_polish_package_output_not_found", "repository_export_checklist_not_found", "repository_export_checklist_output_not_found", "workspace_not_found", "dataset_not_found", "manifest_not_found", "base_workspace_not_found", "pilot_area_not_found", "job_not_found", "analysis_run_not_found", "analysis_output_not_found", "portfolio_report_not_found", "portfolio_report_output_not_found", "analysis_profile_not_found", "profile_workspace_not_found", "profile_output_not_found", "profile_dashboard_profile_not_found", "local_intake_path_not_found", "export_bundle_not_found", "export_bundle_output_not_found", "scoring_profile_not_found", "scoring_rules_not_found", "postgis_schema_not_found", "postgis_plan_not_found", "postgis_plan_output_not_found", "profile_mapper_config_not_found", "profile_mapper_contract_not_found", "profile_mapper_plan_not_found", "profile_mapper_plan_output_not_found", "contract_execution_adapter_not_found", "contract_execution_dry_run_not_found", "osm_tag_quality_source_missing", "template_authoring_draft_not_found", "execution_queue_job_not_found", "dataset_package_not_found", "dataset_package_output_not_found", "profile_promotion_candidate_not_found", "profile_promotion_proposal_not_found", "profile_acceptance_decision_not_found", "profile_application_plan_not_found", "profile_contract_diff_not_found", "profile_config_apply_proposal_not_found", "profile_contract_regression_preview_not_found"}:
        return 404
    if error in {"bad_request", "invalid_json", "unsupported_generic_mapper_source", "missing_network_input_tables", "missing_profile_input_tables", "analysis_not_ready", "template_not_implemented", "analysis_run_payload_missing", "portfolio_report_run_missing", "portfolio_profile_workspace_missing", "portfolio_compare_needs_runs", "profile_compare_needs_workspaces", "profile_runner_not_implemented", "local_intake_input_missing", "local_intake_path_invalid", "local_intake_path_outside_maps_root", "local_intake_analysis_output_not_allowed", "local_intake_unsupported_format", "source_import_input_missing", "source_import_decision_invalid", "source_import_request_not_ready", "source_handoff_input_missing", "source_handoff_no_approved_request", "source_handoff_not_approved", "source_handoff_not_ready", "source_handoff_execution_input_missing", "source_handoff_execution_ack_missing", "source_handoff_execution_not_ready", "execution_evidence_package_input_missing", "execution_evidence_package_not_ready", "execution_result_diff_input_missing", "execution_result_diff_not_ready", "execution_diff_gallery_input_missing", "execution_diff_gallery_not_ready", "execution_diff_detail_input_missing", "execution_diff_detail_not_ready", "reproducibility_audit_packet_input_missing", "reproducibility_audit_packet_not_ready", "reviewer_audit_index_input_missing", "reviewer_audit_index_not_ready", "portfolio_export_launcher_input_missing", "portfolio_export_launcher_not_ready", "portable_release_package_input_missing", "portable_release_package_not_ready", "demo_script_pack_input_missing", "demo_script_pack_not_ready", "visual_qa_ledger_input_missing", "visual_qa_ledger_not_ready", "visual_baseline_comparison_input_missing", "visual_baseline_comparison_not_ready", "demo_artifact_completeness_input_missing", "demo_artifact_completeness_not_ready", "visual_evidence_capture_input_missing", "visual_evidence_capture_not_ready", "visual_evidence_review_diff_input_missing", "visual_evidence_review_diff_not_ready", "visual_evidence_review_annotations_input_missing", "visual_evidence_review_annotations_not_ready", "visual_evidence_signoff_packet_input_missing", "visual_evidence_signoff_packet_not_ready", "final_reviewer_launch_checklist_input_missing", "final_reviewer_launch_checklist_not_ready", "recruiter_demo_brief_input_missing", "recruiter_demo_brief_not_ready", "public_portfolio_package_input_missing", "public_portfolio_package_not_ready", "demo_review_playbook_input_missing", "demo_review_playbook_not_ready", "github_publication_bundle_input_missing", "github_publication_bundle_not_ready", "repository_publication_qa_input_missing", "repository_publication_qa_not_ready", "repository_export_handoff_input_missing", "repository_export_handoff_not_ready", "repository_dry_run_review_input_missing", "repository_dry_run_review_not_ready", "repository_final_package_review_input_missing", "repository_final_package_review_not_ready", "public_readme_cleanup_review_input_missing", "public_readme_cleanup_review_not_ready", "public_repository_polish_package_input_missing", "public_repository_polish_package_not_ready", "repository_export_checklist_input_missing", "repository_export_checklist_not_ready", "profile_mapper_input_missing", "profile_mapper_contract_invalid", "execution_queue_profile_blocked", "dataset_package_runner_not_bound", "authored_profile_draft_missing", "authored_profile_not_ready", "profile_promotion_candidate_not_ready", "profile_promotion_workspace_missing", "profile_acceptance_decision_invalid", "profile_application_plan_not_ready", "profile_contract_diff_not_ready", "profile_config_apply_proposal_not_ready", "profile_contract_regression_preview_not_ready", "review_decisions_workspace_required", "review_decision_target_required", "review_decision_invalid_status"}:
        return 400
    if error in {"missing_geospatial_runtime", "missing_pbf_enrichment_source", "empty_network_proxy", "authored_profile_source_missing"}:
        return 503
    return 500


class DataStore:
    def __init__(self) -> None:
        self.generators = read_csv_rows(MVP_DIR / "pedestrian_generators.csv")
        self.crossings = read_csv_rows(MVP_DIR / "crossings.csv")
        self.roads = read_csv_rows(MVP_DIR / "road_segments.csv")
        self.risk = read_csv_rows(MVP_DIR / "risk_assessment_results.csv")
        self.top20 = read_csv_rows(MVP_DIR / "risk_assessment_top20.csv")
        self.validation = read_json(MVP_DIR / "validation_summary.json")
        self.metadata = read_json(MVP_DIR / "analysis_metadata.json")

    def summary(self) -> dict:
        counts = self.metadata.get("counts", {})
        scores: dict[str, int] = {}
        generator_types: dict[str, int] = {}
        for row in self.risk:
            score = str(parse_int(row.get("risk_score")))
            scores[score] = scores.get(score, 0) + 1
            kind = row.get("generator_type") or "unknown"
            generator_types[kind] = generator_types.get(kind, 0) + 1
        return {
            "workspace_id": WORKSPACE_ID,
            "project": "GeoReview Studio",
            "app_version": APP_VERSION,
            "template": "Safe Access Israel / Kfar Saba",
            "review_wording": REVIEW_WORDING,
            "analysis_crs": self.validation.get("analysis_crs"),
            "validation_passed": self.validation.get("passed"),
            "counts": counts,
            "score_distribution": dict(sorted(scores.items(), key=lambda item: int(item[0]))),
            "generator_types": dict(sorted(generator_types.items())),
            "sources": {
                "mvp_dir": str(MVP_DIR),
                "plan_dir": str(PLAN_DIR),
            },
        }

    def candidates(self, query: dict[str, list[str]]) -> list[dict]:
        limit = parse_int(first(query, "limit", "50"), 50)
        generator_type = first(query, "generator_type", "")
        min_score = parse_int(first(query, "min_score", "0"), 0)
        no_crossing = boolish(first(query, "no_crossing_150m", "false"))
        major_road = boolish(first(query, "major_road_150m", "false"))
        rows = []
        for row in self.risk:
            if generator_type and row.get("generator_type") != generator_type:
                continue
            if parse_int(row.get("risk_score")) < min_score:
                continue
            if no_crossing and str(row.get("crossing_within_150m")).lower() != "false":
                continue
            if major_road and str(row.get("major_road_within_150m")).lower() != "true":
                continue
            rows.append(normalize_candidate(row))
        rows.sort(key=lambda row: (-row["risk_score"], -row["nearest_crossing_m"]))
        return rows[: max(1, min(limit, 500))]

    def map_features(self) -> dict:
        candidates = [normalize_candidate(row) for row in self.risk]
        generators = [
            {
                "id": row.get("generator_id"),
                "type": row.get("generator_type"),
                "name": row.get("name") or "",
                "lon": parse_number(row.get("lon")),
                "lat": parse_number(row.get("lat")),
            }
            for row in self.generators
        ]
        crossings = [
            {
                "id": row.get("crossing_id"),
                "type": row.get("crossing_type"),
                "has_signal_nearby": boolish(row.get("has_signal_nearby")),
                "lon": parse_number(row.get("lon")),
                "lat": parse_number(row.get("lat")),
            }
            for row in self.crossings
        ]
        major_roads = [
            {
                "id": row.get("road_id"),
                "class": row.get("highway_class"),
                "name": row.get("name") or "",
                "lon": parse_number(row.get("lon")),
                "lat": parse_number(row.get("lat")),
            }
            for row in self.roads
            if row.get("highway_class") in {"motorway", "trunk", "primary", "secondary", "tertiary"}
        ]
        return {
            "workspace_id": WORKSPACE_ID,
            "candidates": candidates,
            "generators": generators,
            "crossings": crossings,
            "major_roads": major_roads,
        }


class WorkspaceDashboardStore:
    def __init__(self, workspaces_dir: Path) -> None:
        self.workspaces_dir = workspaces_dir

    def summary(self, workspace_id: str) -> dict:
        detail = self.detail(workspace_id)
        if "error" in detail:
            return detail
        risk = self.risk_rows(workspace_id)
        base_summary = detail.get("summary", {})
        counts = base_summary.get("counts", {})
        validation = base_summary.get("validation", {})
        scores: dict[str, int] = {}
        generator_types: dict[str, int] = {}
        for row in risk:
            score = str(parse_int(row.get("risk_score")))
            scores[score] = scores.get(score, 0) + 1
            kind = row.get("generator_type") or "unknown"
            generator_types[kind] = generator_types.get(kind, 0) + 1
        return {
            "workspace_id": workspace_id,
            "project": "GeoReview Studio",
            "app_version": APP_VERSION,
            "template": base_summary.get("template_id") or detail.get("manifest", {}).get("template_id"),
            "review_wording": base_summary.get("review_wording") or REVIEW_WORDING,
            "analysis_crs": base_summary.get("analysis_crs") or validation.get("analysis_crs"),
            "validation_passed": validation.get("passed"),
            "counts": counts,
            "score_distribution": dict(sorted(scores.items(), key=lambda item: int(item[0]))),
            "generator_types": dict(sorted(generator_types.items())),
            "sources": {
                "workspace_dir": str(self.workspace_dir(workspace_id)),
                "source_path": detail.get("manifest", {}).get("source_path", ""),
                "source_pbf": detail.get("manifest", {}).get("source_pbf", ""),
            },
            "route_aware_analysis": self.network_summary(workspace_id),
        }

    def candidates(self, workspace_id: str, query: dict[str, list[str]]) -> list[dict] | dict:
        if "error" in self.detail(workspace_id):
            return self.detail(workspace_id)
        limit = parse_int(first(query, "limit", "50"), 50)
        generator_type = first(query, "generator_type", "")
        min_score = parse_int(first(query, "min_score", "0"), 0)
        no_crossing = boolish(first(query, "no_crossing_150m", "false"))
        major_road = boolish(first(query, "major_road_150m", "false"))
        rows = []
        network_by_generator = self.network_by_generator(workspace_id)
        for row in self.risk_rows(workspace_id):
            if generator_type and row.get("generator_type") != generator_type:
                continue
            if parse_int(row.get("risk_score")) < min_score:
                continue
            if no_crossing and str(row.get("crossing_within_150m")).lower() != "false":
                continue
            if major_road and str(row.get("major_road_within_150m")).lower() != "true":
                continue
            candidate = normalize_candidate(row)
            enrich_candidate_with_network(candidate, network_by_generator.get(row.get("generator_id")))
            rows.append(candidate)
        rows.sort(key=lambda row: (-row.get("route_review_priority_score", row["risk_score"]), -row["risk_score"], -row["nearest_crossing_m"]))
        return rows[: max(1, min(limit, 500))]

    def network_access(self, workspace_id: str, query: dict[str, list[str]]) -> list[dict] | dict:
        if "error" in self.detail(workspace_id):
            return self.detail(workspace_id)
        limit = parse_int(first(query, "limit", "50"), 50)
        min_route_score = parse_int(first(query, "min_route_score", "0"), 0)
        only_flags = boolish(first(query, "only_flags", "false"))
        rows = []
        for row in self.network_rows(workspace_id):
            normalized = normalize_network_access(row)
            if normalized["route_review_priority_score"] < min_route_score:
                continue
            if only_flags and not normalized["network_flags"]:
                continue
            rows.append(normalized)
        rows.sort(
            key=lambda row: (
                -row["route_review_priority_score"],
                -row["route_nearest_crossing_m"],
                -row["route_vs_straight_ratio"],
            )
        )
        return rows[: max(1, min(limit, 500))]

    def map_features(self, workspace_id: str) -> dict:
        detail = self.detail(workspace_id)
        if "error" in detail:
            return detail
        risk = self.risk_rows(workspace_id)
        generators_rows = read_csv_rows(self.tables_dir(workspace_id) / "pedestrian_generators.csv")
        crossing_rows = read_csv_rows(self.tables_dir(workspace_id) / "crossings.csv")
        road_rows = read_csv_rows(self.tables_dir(workspace_id) / "road_segments.csv")
        network_by_generator = self.network_by_generator(workspace_id)
        candidates = []
        for row in risk:
            candidate = normalize_candidate(row)
            enrich_candidate_with_network(candidate, network_by_generator.get(row.get("generator_id")))
            candidates.append(candidate)
        generators = [
            {
                "id": row.get("generator_id"),
                "type": row.get("generator_type"),
                "name": row.get("name") or "",
                "lon": parse_number(row.get("lon")),
                "lat": parse_number(row.get("lat")),
            }
            for row in generators_rows
        ]
        crossings = [
            {
                "id": row.get("crossing_id"),
                "type": row.get("crossing_type"),
                "has_signal_nearby": boolish(row.get("has_signal_nearby")),
                "lon": parse_number(row.get("lon")),
                "lat": parse_number(row.get("lat")),
            }
            for row in crossing_rows
        ]
        major_roads = [
            {
                "id": row.get("road_id"),
                "class": row.get("highway_class"),
                "name": row.get("name") or "",
                "lon": parse_number(row.get("lon")),
                "lat": parse_number(row.get("lat")),
            }
            for row in road_rows
            if row.get("highway_class") in {"motorway", "trunk", "primary", "secondary", "tertiary"}
        ]
        return {
            "workspace_id": workspace_id,
            "candidates": candidates,
            "generators": generators,
            "crossings": crossings,
            "major_roads": major_roads,
        }

    def validation(self, workspace_id: str) -> dict:
        detail = self.detail(workspace_id)
        if "error" in detail:
            return detail
        return detail.get("summary", {}).get("validation", {})

    def detail(self, workspace_id: str) -> dict:
        manifest = self.workspace_dir(workspace_id) / "manifest.json"
        if not manifest.exists():
            return {"error": "workspace_not_found", "workspace_id": workspace_id}
        reports_dir = self.reports_dir(workspace_id)
        return {
            "manifest": read_json(manifest),
            "summary": read_json(reports_dir / "workspace_summary.json"),
            "quality_report": read_json(reports_dir / "quality_report.json"),
        }

    def risk_rows(self, workspace_id: str) -> list[dict]:
        return read_csv_rows(self.tables_dir(workspace_id) / "risk_assessment_results.csv")

    def network_rows(self, workspace_id: str) -> list[dict]:
        return read_csv_rows(self.tables_dir(workspace_id) / "network_access_results.csv")

    def network_by_generator(self, workspace_id: str) -> dict[str, dict]:
        return {
            row.get("generator_id"): row
            for row in self.network_rows(workspace_id)
            if row.get("generator_id")
        }

    def network_summary(self, workspace_id: str) -> dict:
        detail = self.detail(workspace_id)
        if "error" in detail:
            return {}
        summary = detail.get("summary", {}).get("route_aware_analysis")
        if isinstance(summary, dict) and summary:
            return summary
        return read_json(self.reports_dir(workspace_id) / "network_analysis_summary.json")

    def workspace_dir(self, workspace_id: str) -> Path:
        return self.workspaces_dir / workspace_id

    def tables_dir(self, workspace_id: str) -> Path:
        return self.workspace_dir(workspace_id) / "tables"

    def reports_dir(self, workspace_id: str) -> Path:
        return self.workspace_dir(workspace_id) / "reports"


class CatalogStore:
    def __init__(self) -> None:
        self.inventory = read_csv_rows(OUTPUT_ROOT / "data_inventory.csv")
        self.layers = read_csv_rows(OUTPUT_ROOT / "layer_summary.csv")
        self.tags = read_csv_rows(OUTPUT_ROOT / "osm_tag_counts.csv")
        self.tools = read_csv_rows(OUTPUT_ROOT / "tool_availability.csv")
        self.feasibility = read_csv_rows(OUTPUT_ROOT / "mvp_feasibility_matrix.csv")

    def source_files(self) -> list[dict]:
        sources = []
        for row in self.inventory:
            if row.get("scope") != "folder_file":
                continue
            file_name = row.get("file_name") or Path(row.get("path", "")).name
            source_id = slug(file_name)
            layers = [layer for layer in self.layers if layer.get("dataset") == file_name]
            archive_members = [
                member for member in self.inventory
                if member.get("scope") == "archive_member" and member.get("container") == row.get("path")
            ]
            sources.append({
                "dataset_id": source_id,
                "file_name": file_name,
                "path": row.get("path"),
                "extension": row.get("extension"),
                "size_mb": parse_number(row.get("size_mb")),
                "modified_utc": row.get("modified_utc"),
                "likely_role": row.get("likely_role"),
                "layer_count": len(layers),
                "archive_member_count": len(archive_members),
                "suitability": self.suitability(row.get("extension", "")),
                "profile_status": self.profile_status(row.get("extension", ""), len(layers)),
            })
        return sorted(sources, key=lambda item: item["file_name"])

    def profile(self, dataset_id: str) -> dict:
        sources = self.source_files()
        source = next((item for item in sources if item["dataset_id"] == dataset_id), None)
        if source is None:
            return {"error": "dataset_not_found", "dataset_id": dataset_id}
        source_layers = [layer for layer in self.layers if layer.get("dataset") == source["file_name"]]
        formatted_layers = [self.format_layer(layer) for layer in source_layers]
        return {
            "dataset": source,
            "layers": formatted_layers,
            "geometry_types": self.group_count(formatted_layers, "geometry_type"),
            "formats": self.group_count(formatted_layers, "format"),
            "tag_summary": self.tag_summary(source["extension"]),
            "template_readiness": self.safe_access_readiness(source),
            "tool_availability": self.tools,
        }

    def templates(self) -> list[dict]:
        return [
            {
                "template_id": "safe_access",
                "name": "Safe Access / pedestrian infrastructure review",
                "status": "implemented_for_kfar_saba",
                "input_needs": [
                    "pedestrian generators",
                    "crossings",
                    "traffic signals",
                    "road segments",
                    "optional sidewalk, lit, maxspeed, traffic calming tags",
                ],
                "outputs": [
                    "review candidates",
                    "distance metrics",
                    "risk flags",
                    "data quality flags",
                    "CSV export",
                    "local dashboard",
                ],
            },
            {
                "template_id": "osm_quality",
                "name": "OSM tag coverage audit",
                "status": "foundation_ready",
                "input_needs": ["OSM PBF, GeoPackage, Shapefile ZIP, or GeoJSON"],
                "outputs": ["layer inventory", "tag coverage", "missing-data flags"],
            },
            {
                "template_id": "transit_walk_access",
                "name": "Transit stop walk-access review",
                "status": "planned",
                "input_needs": ["bus stops", "crossings", "roads", "walkable network"],
                "outputs": ["stop access candidates", "crossing distance metrics"],
            },
        ]

    def safe_access_check(self, dataset_id: str) -> dict:
        profile = self.profile(dataset_id)
        if "error" in profile:
            return profile
        return {
            "dataset_id": dataset_id,
            "template_id": "safe_access",
            "readiness": profile["template_readiness"],
            "current_kfar_saba_workspace": DATA.summary(),
            "recommendation": (
                "Use this source as the input catalog, then run a city clip and template mapping step. "
                "For the current pilot, the Kfar Saba workspace is already computed and validated."
            ),
        }

    def format_layer(self, layer: dict) -> dict:
        return {
            "layer": layer.get("layer"),
            "format": layer.get("format"),
            "geometry_type": layer.get("geometry_type"),
            "crs": layer.get("crs"),
            "feature_count": parse_int(layer.get("feature_count")),
            "bbox_lonlat": layer.get("bbox_lonlat"),
            "columns": split_columns(layer.get("columns", "")),
            "main_use_for_project": layer.get("main_use_for_project"),
            "notes": layer.get("notes"),
        }

    def tag_summary(self, extension: str) -> dict:
        if extension == ".zip":
            preferred_sources = {"geofabrik_shapefile"}
        elif extension == ".osm.pbf":
            preferred_sources = {"osm_pbf_raw"}
        else:
            preferred_sources = {"geofabrik_shapefile", "osm_pbf_raw"}
        rows = [row for row in self.tags if row.get("source") in preferred_sources]
        categories: dict[str, dict] = {}
        for row in rows:
            category = row.get("category") or "unknown"
            item = categories.setdefault(category, {"category": category, "total_count": 0, "examples": []})
            item["total_count"] += parse_int(row.get("count"))
            value = row.get("value") or row.get("tag_or_field") or ""
            if value and len(item["examples"]) < 4:
                item["examples"].append(value)
        important = [
            "crossings",
            "traffic_signals",
            "schools",
            "kindergartens",
            "childcare_facilities",
            "bus_stops",
            "parks",
            "playgrounds",
            "major_roads",
            "residential_roads",
            "roads_with_sidewalk_tag",
            "roads_with_lit_tag",
            "traffic_calming_features",
        ]
        return {
            "source_filter": sorted(preferred_sources),
            "important_categories": [categories[key] for key in important if key in categories],
            "all_category_count": len(categories),
        }

    def safe_access_readiness(self, source: dict) -> dict:
        extension = source.get("extension")
        if extension == ".zip" and source.get("layer_count", 0) > 0:
            level = "strong_for_simplified_mvp"
            limitation = "Simplified Geofabrik layers are fast for MVP, but many detailed OSM tags are not preserved."
        elif extension == ".osm.pbf":
            level = "strong_for_tag_enrichment_partial_for_direct_dashboard"
            limitation = "Raw OSM PBF keeps rich tags, but needs an extraction step before dashboard analysis."
        else:
            level = "unknown_from_current_data"
            limitation = "Not available in inspected files for this extension."
        return {
            "level": level,
            "evidence": {
                "layer_count": source.get("layer_count"),
                "archive_member_count": source.get("archive_member_count"),
                "likely_role": source.get("likely_role"),
            },
            "limitation": limitation,
            "next_step": "Build a template mapper that converts source layers into canonical generator, crossing, road, and safety-feature tables.",
        }

    @staticmethod
    def suitability(extension: str) -> dict:
        by_extension = {
            ".zip": {
                "qgis": "yes",
                "python_geopandas": "yes_with_zip_or_extraction",
                "postgis": "yes_after_ogr2ogr_or_python_load",
            },
            ".osm.pbf": {
                "qgis": "yes_with_osm_driver",
                "python_geopandas": "partial_needs_gdal_osmium_or_conversion",
                "postgis": "yes_after_osm2pgsql_or_ogr2ogr",
            },
            ".gpkg": {
                "qgis": "yes",
                "python_geopandas": "yes",
                "postgis": "yes",
            },
            ".shp": {
                "qgis": "yes",
                "python_geopandas": "yes",
                "postgis": "yes",
            },
            ".geojson": {
                "qgis": "yes",
                "python_geopandas": "yes",
                "postgis": "yes",
            },
        }
        return by_extension.get(extension, {
            "qgis": "unknown_from_current_data",
            "python_geopandas": "unknown_from_current_data",
            "postgis": "unknown_from_current_data",
        })

    @staticmethod
    def profile_status(extension: str, layer_count: int) -> str:
        if layer_count > 0:
            return "profiled_from_audit"
        if extension == ".osm.pbf":
            return "profiled_from_osm_driver_and_tag_audit"
        return "inventory_only"

    @staticmethod
    def group_count(rows: list[dict], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = row.get(key) or "unknown"
            counts[value] = counts.get(value, 0) + 1
        return dict(sorted(counts.items()))


def normalize_candidate(row: dict) -> dict:
    return {
        "generator_id": row.get("generator_id"),
        "osm_id": row.get("osm_id"),
        "generator_type": row.get("generator_type"),
        "name": row.get("name") or "",
        "source_layer": row.get("source_layer") or "",
        "nearest_crossing_m": parse_number(row.get("nearest_crossing_m")),
        "nearest_major_road_m": parse_number(row.get("nearest_major_road_m")),
        "crossing_within_100m": boolish(row.get("crossing_within_100m")),
        "crossing_within_150m": boolish(row.get("crossing_within_150m")),
        "major_road_within_150m": boolish(row.get("major_road_within_150m")),
        "signals_within_50m": parse_int(row.get("signals_within_50m")),
        "traffic_calming_within_100m": parse_int(row.get("traffic_calming_within_100m")),
        "risk_score": parse_int(row.get("risk_score")),
        "risk_flags": parse_json_array(row.get("risk_flags", "[]")),
        "data_quality_flags": parse_json_array(row.get("data_quality_flags", "[]")),
        "review_wording": row.get("review_wording") or REVIEW_WORDING,
        "lon": parse_number(row.get("lon")),
        "lat": parse_number(row.get("lat")),
    }


def enrich_candidate_with_network(candidate: dict, network_row: dict | None) -> None:
    candidate["route_aware_available"] = bool(network_row)
    if not network_row:
        return
    candidate.update({
        "route_review_priority_score": parse_int(network_row.get("route_review_priority_score")),
        "route_nearest_crossing_id": network_row.get("route_nearest_crossing_id") or "",
        "route_nearest_crossing_m": parse_number(network_row.get("route_nearest_crossing_m")),
        "route_vs_straight_ratio": parse_number(network_row.get("route_vs_straight_ratio")),
        "route_gap_m": parse_number(network_row.get("route_gap_m")),
        "reachable_crossings": parse_int(network_row.get("reachable_crossings")),
        "network_status": network_row.get("network_status") or "",
        "network_flags": parse_json_array(network_row.get("network_flags", "[]")),
        "generator_network_attach_m": parse_number(network_row.get("generator_network_attach_m")),
    })


def normalize_network_access(row: dict) -> dict:
    return {
        "generator_id": row.get("generator_id"),
        "osm_id": row.get("osm_id"),
        "generator_type": row.get("generator_type"),
        "name": row.get("name") or "",
        "base_risk_score": parse_int(row.get("base_risk_score")),
        "route_review_priority_score": parse_int(row.get("route_review_priority_score")),
        "straight_nearest_crossing_id": row.get("straight_nearest_crossing_id") or "",
        "straight_nearest_crossing_m": parse_number(row.get("straight_nearest_crossing_m")),
        "route_nearest_crossing_id": row.get("route_nearest_crossing_id") or "",
        "route_nearest_crossing_m": parse_number(row.get("route_nearest_crossing_m")),
        "straight_distance_to_route_crossing_m": parse_number(row.get("straight_distance_to_route_crossing_m")),
        "route_vs_straight_ratio": parse_number(row.get("route_vs_straight_ratio")),
        "route_gap_m": parse_number(row.get("route_gap_m")),
        "reachable_crossings": parse_int(row.get("reachable_crossings")),
        "generator_network_attach_m": parse_number(row.get("generator_network_attach_m")),
        "generator_network_road_class": row.get("generator_network_road_class") or "",
        "crossing_network_attach_m": parse_number(row.get("crossing_network_attach_m")),
        "crossing_network_road_class": row.get("crossing_network_road_class") or "",
        "network_status": row.get("network_status") or "",
        "network_flags": parse_json_array(row.get("network_flags", "[]")),
        "data_quality_flags": parse_json_array(row.get("data_quality_flags", "[]")),
        "review_wording": row.get("review_wording") or REVIEW_WORDING,
        "lon": parse_number(row.get("lon")),
        "lat": parse_number(row.get("lat")),
    }


DATA = DataStore()
REVIEW_DECISIONS = ReviewDecisionStore(OUTPUT_ROOT / "georeview_studio_review_decisions" / "review_decisions.sqlite3")
CATALOG = CatalogStore()
RUNNER = WorkspaceRunner(
    output_root=OUTPUT_ROOT,
    mvp_dir=MVP_DIR,
    workspaces_dir=WORKSPACES_DIR,
    review_wording=REVIEW_WORDING,
    catalog=CATALOG,
)
DASHBOARDS = WorkspaceDashboardStore(WORKSPACES_DIR)
NETWORK = RouteNetworkAnalyzer(WORKSPACES_DIR, REVIEW_WORDING)
TRANSIT = TransitAccessAnalyzer(WORKSPACES_DIR, REVIEW_WORDING)
PARKS = ParkPlaygroundAccessAnalyzer(WORKSPACES_DIR, REVIEW_WORDING)
OSM_TAG_QUALITY = OSMTagQualityAnalyzer(OUTPUT_ROOT, WORKSPACES_DIR, REVIEW_WORDING)
PILOTS = PilotAreaCatalog(DEFAULT_SOURCE_ZIP, OUTPUT_ROOT)
JOBS = RunJobManager(RUNS_DIR)
PREFLIGHT = SafeAccessPreflight(CATALOG, PILOTS, WORKSPACES_DIR, DEFAULT_SOURCE_DATASET_ID)
ONBOARDING = SourceOnboarding(MAPS_ROOT, OUTPUT_ROOT)
ANALYSIS = AnalysisWorkflow(ONBOARDING, PILOTS, PREFLIGHT, DEFAULT_SOURCE_DATASET_ID)
ANALYSIS_RUNS = AnalysisRuns(RUNS_DIR, WORKSPACES_DIR)
PORTFOLIO_REPORTS = PortfolioReportBuilder(PORTFOLIO_REPORTS_DIR, ANALYSIS_RUNS, WORKSPACES_DIR)
PROFILES = AnalysisProfileRegistry(ONBOARDING, PILOTS, PREFLIGHT, DEFAULT_SOURCE_DATASET_ID)
PRODUCT_ARCHITECTURE = ProductArchitecture(PROFILES, ONBOARDING, project_manifest)
PROFILE_DASHBOARD = ProfileDashboardStore(WORKSPACES_DIR, REVIEW_WORDING)
LOCAL_INTAKE = LocalIntakeWizard(MAPS_ROOT, OUTPUT_ROOT, ONBOARDING, DEFAULT_SOURCE_DATASET_ID)
SOURCE_IMPORT_GUARDRAILS = SourceImportGuardrails(PROJECT_DIR, OUTPUT_ROOT, MAPS_ROOT, ONBOARDING, LOCAL_INTAKE, DEFAULT_SOURCE_DATASET_ID, REVIEW_WORDING)
PROFILE_EXPORT_BUNDLES = ProfileExportBundleBuilder(PORTFOLIO_REPORTS_DIR, PROFILE_DASHBOARD, PORTFOLIO_REPORTS)
SCORING_RULES = ScoringRulesStore(SCORING_RULES_CONFIG_PATH, PROFILE_DASHBOARD)
POSTGIS_BACKEND = PostGISBackendPlanner(POSTGIS_SCHEMA_PATH, OUTPUT_ROOT, WORKSPACES_DIR, ONBOARDING, PROFILE_DASHBOARD, SCORING_RULES)
PROFILE_MAPPER = ProfileMapperRegistry(PROFILE_MAPPER_CONFIG_PATH, OUTPUT_ROOT, ONBOARDING, PROFILES)
CONTRACT_EXECUTION = ContractExecutionAdapter(PROFILE_MAPPER, OUTPUT_ROOT, WORKSPACES_DIR)
TEMPLATE_AUTHORING = TemplateAuthoringWizard(PROFILE_MAPPER_CONFIG_PATH, OUTPUT_ROOT, ONBOARDING)
EXECUTION_QUEUE = ControlledExecutionQueue(CONTRACT_EXECUTION, OUTPUT_ROOT)
SOURCE_HANDOFF = SourceHandoffPlanner(OUTPUT_ROOT, SOURCE_IMPORT_GUARDRAILS, PROFILE_MAPPER, CONTRACT_EXECUTION, EXECUTION_QUEUE, REVIEW_WORDING)
SOURCE_HANDOFF_EXECUTION = SourceHandoffExecutionController(OUTPUT_ROOT, WORKSPACES_DIR, SOURCE_HANDOFF, EXECUTION_QUEUE, REVIEW_WORDING)
EXECUTION_EVIDENCE_PACKAGE = ExecutionEvidencePackageBuilder(PROJECT_DIR, OUTPUT_ROOT, WORKSPACES_DIR, APP_VERSION, project_manifest, REVIEW_WORDING, SOURCE_HANDOFF_EXECUTION, expected_api_endpoints=362)
EXECUTION_RESULT_DIFF = ExecutionResultDiffBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, EXECUTION_EVIDENCE_PACKAGE, expected_api_endpoints=362)
EXECUTION_DIFF_GALLERY = ExecutionDiffGalleryBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, EXECUTION_RESULT_DIFF, expected_api_endpoints=362)
EXECUTION_DIFF_DETAIL = ExecutionDiffDetailDrilldownBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, EXECUTION_RESULT_DIFF, EXECUTION_DIFF_GALLERY, expected_api_endpoints=362)
REPRODUCIBILITY_AUDIT_PACKET = ReproducibilityAuditPacketBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, EXECUTION_RESULT_DIFF, EXECUTION_DIFF_GALLERY, EXECUTION_DIFF_DETAIL, expected_api_endpoints=362)
REVIEWER_AUDIT_INDEX = ReviewerAuditIndexBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, REPRODUCIBILITY_AUDIT_PACKET, expected_api_endpoints=362)
PORTFOLIO_EXPORT_LAUNCHER = PortfolioExportLauncherBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, REVIEWER_AUDIT_INDEX, REPRODUCIBILITY_AUDIT_PACKET, expected_api_endpoints=362)
PORTABLE_RELEASE_PACKAGE = PortableReleasePackageBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, PORTFOLIO_EXPORT_LAUNCHER, REVIEWER_AUDIT_INDEX, REPRODUCIBILITY_AUDIT_PACKET, expected_api_endpoints=362)
DEMO_SCRIPT_PACK = DemoScriptPackBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, PORTABLE_RELEASE_PACKAGE, expected_api_endpoints=362)
VISUAL_QA_LEDGER = VisualQASnapshotLedgerBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, DEMO_SCRIPT_PACK, expected_api_endpoints=362)
VISUAL_BASELINE_COMPARISON = VisualBaselineComparisonManifestBuilder(PROJECT_DIR, OUTPUT_ROOT, APP_VERSION, project_manifest, REVIEW_WORDING, VISUAL_QA_LEDGER, expected_api_endpoints=362)
AUTHORED_PROFILE_RUNNER = AuthoredProfileRunner(OUTPUT_ROOT, WORKSPACES_DIR, TEMPLATE_AUTHORING, REVIEW_WORDING)
PROFILE_PROMOTION = ProfilePromotionWizard(OUTPUT_ROOT, WORKSPACES_DIR, TEMPLATE_AUTHORING, PROFILE_MAPPER_CONFIG_PATH, REVIEW_WORDING)
DATASET_PACKAGES = DatasetPackageBuilder(OUTPUT_ROOT, ONBOARDING, LOCAL_INTAKE, TEMPLATE_AUTHORING, EXECUTION_QUEUE)
RELEASE_READINESS = ReleaseReadinessDashboard(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {
        "product_architecture": PRODUCT_ARCHITECTURE,
        "profile_dashboard": PROFILE_DASHBOARD,
        "scoring_rules": SCORING_RULES,
        "postgis_backend": POSTGIS_BACKEND,
        "profile_mapper": PROFILE_MAPPER,
        "contract_execution": CONTRACT_EXECUTION,
        "template_authoring": TEMPLATE_AUTHORING,
        "execution_queue": EXECUTION_QUEUE,
        "dataset_packages": DATASET_PACKAGES,
        "authored_profile_runner": AUTHORED_PROFILE_RUNNER,
        "profile_promotion": PROFILE_PROMOTION,
        "onboarding": ONBOARDING,
        "source_import_guardrails": SOURCE_IMPORT_GUARDRAILS,
        "source_handoff": SOURCE_HANDOFF,
        "source_handoff_execution": SOURCE_HANDOFF_EXECUTION,
        "execution_evidence_package": EXECUTION_EVIDENCE_PACKAGE,
        "execution_result_diff": EXECUTION_RESULT_DIFF,
        "execution_diff_gallery": EXECUTION_DIFF_GALLERY,
        "execution_diff_detail": EXECUTION_DIFF_DETAIL,
        "reproducibility_audit_packet": REPRODUCIBILITY_AUDIT_PACKET,
        "reviewer_audit_index": REVIEWER_AUDIT_INDEX,
        "portfolio_export_launcher": PORTFOLIO_EXPORT_LAUNCHER,
        "portable_release_package": PORTABLE_RELEASE_PACKAGE,
        "demo_script_pack": DEMO_SCRIPT_PACK,
        "visual_qa_ledger": VISUAL_QA_LEDGER,
        "visual_baseline_comparison": VISUAL_BASELINE_COMPARISON,
    },
)
PORTFOLIO_DEMO = PortfolioDemoWalkthrough(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {
        "product_architecture": PRODUCT_ARCHITECTURE,
        "release_readiness": RELEASE_READINESS,
        "onboarding": ONBOARDING,
        "profile_dashboard": PROFILE_DASHBOARD,
        "scoring_rules": SCORING_RULES,
        "portfolio_reports": PORTFOLIO_REPORTS,
        "profile_export_bundles": PROFILE_EXPORT_BUNDLES,
        "profile_promotion": PROFILE_PROMOTION,
    },
)
PORTFOLIO_EVIDENCE_BUNDLE = PortfolioEvidenceBundleBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {
        "release_readiness": RELEASE_READINESS,
        "portfolio_demo": PORTFOLIO_DEMO,
        "portfolio_reports": PORTFOLIO_REPORTS,
        "profile_export_bundles": PROFILE_EXPORT_BUNDLES,
    },
)
BUNDLE_REVIEW_CHECKLIST = BundleReviewChecklist(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {"portfolio_evidence_bundle": PORTFOLIO_EVIDENCE_BUNDLE},
    expected_api_endpoints=362,
)
PORTFOLIO_NARRATIVE_EXPORT = PortfolioNarrativeExporter(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {
        "bundle_review_checklist": BUNDLE_REVIEW_CHECKLIST,
        "portfolio_evidence_bundle": PORTFOLIO_EVIDENCE_BUNDLE,
    },
    expected_api_endpoints=362,
)
PORTFOLIO_HANDOFF_PAGE = PortfolioHandoffPageBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {"portfolio_narrative_export": PORTFOLIO_NARRATIVE_EXPORT},
    expected_api_endpoints=362,
)
PORTFOLIO_EVIDENCE_GALLERY = PortfolioEvidenceGalleryBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {
        "portfolio_handoff_page": PORTFOLIO_HANDOFF_PAGE,
        "portfolio_narrative_export": PORTFOLIO_NARRATIVE_EXPORT,
        "portfolio_evidence_bundle": PORTFOLIO_EVIDENCE_BUNDLE,
        "bundle_review_checklist": BUNDLE_REVIEW_CHECKLIST,
        "portfolio_reports": PORTFOLIO_REPORTS,
        "release_readiness": RELEASE_READINESS,
        "profile_dashboard": PROFILE_DASHBOARD,
        "product_architecture": PRODUCT_ARCHITECTURE,
    },
    expected_api_endpoints=362,
)
MULTI_PILOT_COMPARISON = MultiPilotComparisonBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {
        "dashboards": DASHBOARDS,
        "pilots": PILOTS,
        "portfolio_evidence_gallery": PORTFOLIO_EVIDENCE_GALLERY,
    },
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["multi_pilot_comparison"] = MULTI_PILOT_COMPARISON

COMPARISON_MAP_EXPORTS = ComparisonMapExportBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {"multi_pilot_comparison": MULTI_PILOT_COMPARISON},
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["comparison_map_exports"] = COMPARISON_MAP_EXPORTS

DEMO_ARTIFACT_COMPLETENESS = DemoArtifactCompletenessValidator(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    {
        "portfolio_evidence_bundle": PORTFOLIO_EVIDENCE_BUNDLE,
        "bundle_review_checklist": BUNDLE_REVIEW_CHECKLIST,
        "portfolio_narrative_export": PORTFOLIO_NARRATIVE_EXPORT,
        "portfolio_handoff_page": PORTFOLIO_HANDOFF_PAGE,
        "portfolio_evidence_gallery": PORTFOLIO_EVIDENCE_GALLERY,
        "portable_release_package": PORTABLE_RELEASE_PACKAGE,
        "demo_script_pack": DEMO_SCRIPT_PACK,
        "visual_qa_ledger": VISUAL_QA_LEDGER,
        "visual_baseline_comparison": VISUAL_BASELINE_COMPARISON,
    },
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["demo_artifact_completeness"] = DEMO_ARTIFACT_COMPLETENESS

VISUAL_EVIDENCE_CAPTURE = VisualEvidenceCaptureBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    VISUAL_QA_LEDGER,
    DEMO_ARTIFACT_COMPLETENESS,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["visual_evidence_capture"] = VISUAL_EVIDENCE_CAPTURE

VISUAL_EVIDENCE_REVIEW_DIFF = VisualEvidenceReviewDiffBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    VISUAL_EVIDENCE_CAPTURE,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["visual_evidence_review_diff"] = VISUAL_EVIDENCE_REVIEW_DIFF

VISUAL_EVIDENCE_REVIEW_ANNOTATIONS = VisualEvidenceReviewAnnotationsBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    VISUAL_EVIDENCE_REVIEW_DIFF,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["visual_evidence_review_annotations"] = VISUAL_EVIDENCE_REVIEW_ANNOTATIONS

VISUAL_EVIDENCE_SIGNOFF_PACKET = VisualEvidenceSignoffPacketBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    VISUAL_EVIDENCE_REVIEW_ANNOTATIONS,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["visual_evidence_signoff_packet"] = VISUAL_EVIDENCE_SIGNOFF_PACKET

FINAL_REVIEWER_LAUNCH_CHECKLIST = FinalReviewerLaunchChecklistBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    VISUAL_EVIDENCE_SIGNOFF_PACKET,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["final_reviewer_launch_checklist"] = FINAL_REVIEWER_LAUNCH_CHECKLIST

RECRUITER_DEMO_BRIEF = RecruiterDemoBriefBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    FINAL_REVIEWER_LAUNCH_CHECKLIST,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["recruiter_demo_brief"] = RECRUITER_DEMO_BRIEF

PUBLIC_PORTFOLIO_PACKAGE = PublicPortfolioInterviewPackageBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    RECRUITER_DEMO_BRIEF,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["public_portfolio_package"] = PUBLIC_PORTFOLIO_PACKAGE
DEMO_REVIEW_PLAYBOOK = DemoReviewPlaybookBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    PUBLIC_PORTFOLIO_PACKAGE,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["demo_review_playbook"] = DEMO_REVIEW_PLAYBOOK
GITHUB_PUBLICATION_BUNDLE = GitHubPublicationBundleBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    DEMO_REVIEW_PLAYBOOK,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["github_publication_bundle"] = GITHUB_PUBLICATION_BUNDLE
REPOSITORY_PUBLICATION_QA = RepositoryPublicationQABuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    GITHUB_PUBLICATION_BUNDLE,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["repository_publication_qa"] = REPOSITORY_PUBLICATION_QA
REPOSITORY_EXPORT_HANDOFF = RepositoryExportHandoffBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    REPOSITORY_PUBLICATION_QA,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["repository_export_handoff"] = REPOSITORY_EXPORT_HANDOFF
REPOSITORY_DRY_RUN_REVIEW = RepositoryDryRunReviewBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    REPOSITORY_EXPORT_HANDOFF,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["repository_dry_run_review"] = REPOSITORY_DRY_RUN_REVIEW
REPOSITORY_FINAL_PACKAGE_REVIEW = RepositoryFinalPackageReviewBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    REPOSITORY_DRY_RUN_REVIEW,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["repository_final_package_review"] = REPOSITORY_FINAL_PACKAGE_REVIEW
PUBLIC_README_CLEANUP_REVIEW = PublicReadmeCleanupReviewBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    REPOSITORY_FINAL_PACKAGE_REVIEW,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["public_readme_cleanup_review"] = PUBLIC_README_CLEANUP_REVIEW
PUBLIC_REPOSITORY_POLISH_PACKAGE = PublicRepositoryPolishPackageBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    PUBLIC_README_CLEANUP_REVIEW,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["public_repository_polish_package"] = PUBLIC_REPOSITORY_POLISH_PACKAGE
REPOSITORY_EXPORT_CHECKLIST = RepositoryExportChecklistBuilder(
    PROJECT_DIR,
    OUTPUT_ROOT,
    APP_VERSION,
    project_manifest,
    REVIEW_WORDING,
    PUBLIC_REPOSITORY_POLISH_PACKAGE,
    VISUAL_EVIDENCE_CAPTURE,
    expected_api_endpoints=362,
)
RELEASE_READINESS.dependencies["repository_export_checklist"] = REPOSITORY_EXPORT_CHECKLIST


def preflight_from_query(query: dict[str, list[str]]) -> dict:
    return PREFLIGHT.safe_access_pilot(
        pilot_osm_id=first(query, "pilot_osm_id", ""),
        dataset_id=first(query, "dataset_id", ""),
        route_aware=boolish(first(query, "route_aware", "true")),
        pbf_workspace_id=first(query, "workspace_id", ""),
        route_workspace_id=first(query, "route_workspace_id", ""),
    )


def preflight_from_body(body: dict) -> dict:
    return PREFLIGHT.safe_access_pilot(
        pilot_osm_id=str(body.get("pilot_osm_id") or ""),
        dataset_id=str(body.get("dataset_id") or ""),
        route_aware=boolish(body.get("route_aware", True)),
        pbf_workspace_id=str(body.get("workspace_id") or ""),
        route_workspace_id=str(body.get("route_workspace_id") or ""),
    )


def analysis_plan_from_query(query: dict[str, list[str]]) -> dict:
    return ANALYSIS.plan({
        "dataset_id": first(query, "dataset_id", DEFAULT_SOURCE_DATASET_ID),
        "pilot_osm_id": first(query, "pilot_osm_id", ""),
        "template_id": first(query, "template_id", "safe_access"),
        "route_aware": first(query, "route_aware", "true"),
    })


def profiles_from_query(query: dict[str, list[str]]) -> dict:
    return PROFILES.list_profiles(
        dataset_id=first(query, "dataset_id", DEFAULT_SOURCE_DATASET_ID),
        pilot_osm_id=first(query, "pilot_osm_id", ""),
        route_aware=first(query, "route_aware", "true"),
    )


def profile_detail_from_query(profile_id: str, query: dict[str, list[str]]) -> dict:
    return PROFILES.detail(
        profile_id,
        dataset_id=first(query, "dataset_id", DEFAULT_SOURCE_DATASET_ID),
        pilot_osm_id=first(query, "pilot_osm_id", ""),
        route_aware=first(query, "route_aware", "true"),
    )


def profile_readiness_from_query(profile_id: str, query: dict[str, list[str]]) -> dict:
    return PROFILES.readiness(
        profile_id,
        dataset_id=first(query, "dataset_id", DEFAULT_SOURCE_DATASET_ID),
        pilot_osm_id=first(query, "pilot_osm_id", ""),
        route_aware=first(query, "route_aware", "true"),
    )


def profile_dashboard_results_from_query(profile_id: str, query: dict[str, list[str]]) -> dict:
    return PROFILE_DASHBOARD.results(
        profile_id,
        limit=parse_int(first(query, "limit", "50"), 50),
        min_score=parse_int(first(query, "min_score", "0"), 0),
        only_flags=boolish(first(query, "only_flags", "false")),
    )


def plan_analysis_profile(profile_id: str, body: dict) -> dict:
    if profile_id not in {SAFE_ACCESS_PROFILE_ID, "safe_access"}:
        readiness = PROFILES.readiness(
            profile_id,
            dataset_id=str(body.get("dataset_id") or DEFAULT_SOURCE_DATASET_ID),
            pilot_osm_id=str(body.get("pilot_osm_id") or ""),
            route_aware=body.get("route_aware", True),
        )
        if "error" in readiness:
            return readiness
        return {
            "ok": False,
            "error": "profile_runner_not_implemented",
            "profile_id": profile_id,
            "readiness": readiness,
            "source_gis_modified": False,
        }
    payload = dict(body)
    payload["template_id"] = "safe_access"
    return ANALYSIS.plan(payload)


def list_profile_runners() -> dict:
    return {
        "ok": True,
        "runners": [
            {
                "profile_id": SAFE_ACCESS_PROFILE_ID,
                "runner_status": "implemented_for_selected_pilot",
                "run_endpoint": f"/api/profile-runners/{SAFE_ACCESS_PROFILE_ID}/run",
                "output_kind": "safe_access_workspace",
            },
            {
                "profile_id": "transit_stop_walk_access",
                "runner_status": "implemented_from_safe_access_workspace",
                "run_endpoint": "/api/profile-runners/transit_stop_walk_access/run",
                "output_kind": "profile_workspace",
                "default_workspace_id": DEFAULT_TRANSIT_WORKSPACE_ID,
            },
            {
                "profile_id": "park_playground_access",
                "runner_status": "implemented_from_safe_access_workspace",
                "run_endpoint": "/api/profile-runners/park_playground_access/run",
                "output_kind": "profile_workspace",
                "default_workspace_id": DEFAULT_PARK_PLAYGROUND_WORKSPACE_ID,
            },
            {
                "profile_id": "osm_tag_quality",
                "runner_status": "implemented_read_only_profile",
                "run_endpoint": "/api/profile-runners/osm_tag_quality/run",
                "output_kind": "profile_workspace",
                "default_workspace_id": DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID,
            },
            {
                "profile_id": "authored_profile_audit",
                "runner_status": "implemented_read_only_draft_runner",
                "run_endpoint": "/api/authored-profile-runner/run",
                "queue_endpoint": "/api/execution-queue/enqueue-authored-draft",
                "output_kind": "authored_profile_workspace",
                "default_workspace_id": DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID,
            },
        ],
        "source_gis_modified": False,
    }


def run_profile(profile_id: str, body: dict) -> dict:
    if profile_id in {SAFE_ACCESS_PROFILE_ID, "safe_access"}:
        payload = dict(body)
        payload["template_id"] = "safe_access"
        return build_pilot_workspace(payload)
    if profile_id in {"transit_stop_walk_access", "transit_walk_access"}:
        return TRANSIT.ensure_workspace(
            base_workspace_id=str(body.get("base_workspace_id") or ROUTE_WORKSPACE_ID),
            workspace_id=str(body.get("workspace_id") or DEFAULT_TRANSIT_WORKSPACE_ID),
        )
    if profile_id in {"park_playground_access", "public_space_access"}:
        return PARKS.ensure_workspace(
            base_workspace_id=str(body.get("base_workspace_id") or ROUTE_WORKSPACE_ID),
            workspace_id=str(body.get("workspace_id") or DEFAULT_PARK_PLAYGROUND_WORKSPACE_ID),
        )
    if profile_id in {"osm_tag_quality", "osm_quality"}:
        return OSM_TAG_QUALITY.ensure_workspace(
            workspace_id=str(body.get("workspace_id") or DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID),
        )
    if profile_id in {"authored_profile_audit", "authored_draft_audit"}:
        return run_authored_profile(str(body.get("draft_id") or ""), body)
    readiness = PROFILES.readiness(
        profile_id,
        dataset_id=str(body.get("dataset_id") or DEFAULT_SOURCE_DATASET_ID),
        pilot_osm_id=str(body.get("pilot_osm_id") or ""),
        route_aware=body.get("route_aware", True),
    )
    return {
        "ok": False,
        "error": "profile_runner_not_implemented",
        "profile_id": profile_id,
        "readiness": readiness,
        "source_gis_modified": False,
    }


def profile_manifest(workspace_id: str) -> dict:
    clean_workspace_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(workspace_id or ""))[:120]
    manifest = read_json(WORKSPACES_DIR / clean_workspace_id / "manifest.json")
    if not manifest or not manifest.get("profile_workspace"):
        return {"error": "profile_workspace_not_found", "workspace_id": workspace_id}
    return manifest


def run_authored_profile(draft_id: str, body: dict) -> dict:
    return AUTHORED_PROFILE_RUNNER.ensure_workspace(
        draft_id=draft_id,
        workspace_id=str(body.get("workspace_id") or body.get("target_workspace_id") or DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID),
        dataset_id=str(body.get("dataset_id") or DEFAULT_SOURCE_DATASET_ID),
    )


def list_profile_workspaces() -> list[dict]:
    rows = TRANSIT.list_workspaces() + PARKS.list_workspaces() + OSM_TAG_QUALITY.list_workspaces() + AUTHORED_PROFILE_RUNNER.list_workspaces()
    return sorted(rows, key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)


def profile_workspace_summary(workspace_id: str) -> dict:
    manifest = profile_manifest(workspace_id)
    if "error" in manifest:
        return manifest
    if manifest.get("authored_profile_workspace"):
        return AUTHORED_PROFILE_RUNNER.summary_for_workspace(workspace_id)
    if manifest.get("profile_id") == "transit_stop_walk_access":
        return TRANSIT.summary_for_workspace(workspace_id)
    if manifest.get("profile_id") == "park_playground_access":
        return PARKS.summary_for_workspace(workspace_id)
    if manifest.get("profile_id") == "osm_tag_quality":
        return OSM_TAG_QUALITY.summary_for_workspace(workspace_id)
    return {"error": "profile_workspace_not_found", "workspace_id": workspace_id}


def profile_workspace_results(workspace_id: str, limit: int = 50) -> list[dict] | dict:
    manifest = profile_manifest(workspace_id)
    if "error" in manifest:
        return manifest
    if manifest.get("authored_profile_workspace"):
        return AUTHORED_PROFILE_RUNNER.results(workspace_id, limit)
    if manifest.get("profile_id") == "transit_stop_walk_access":
        return TRANSIT.results(workspace_id, limit)
    if manifest.get("profile_id") == "park_playground_access":
        return PARKS.results(workspace_id, limit)
    if manifest.get("profile_id") == "osm_tag_quality":
        return OSM_TAG_QUALITY.results(workspace_id, limit)
    return {"error": "profile_workspace_not_found", "workspace_id": workspace_id}


def profile_workspace_output_file(workspace_id: str, output_id: str) -> dict:
    manifest = profile_manifest(workspace_id)
    if "error" in manifest:
        return manifest
    if manifest.get("authored_profile_workspace"):
        return AUTHORED_PROFILE_RUNNER.output_file(workspace_id, output_id)
    if manifest.get("profile_id") == "transit_stop_walk_access":
        return TRANSIT.output_file(workspace_id, output_id)
    if manifest.get("profile_id") == "park_playground_access":
        return PARKS.output_file(workspace_id, output_id)
    if manifest.get("profile_id") == "osm_tag_quality":
        return OSM_TAG_QUALITY.output_file(workspace_id, output_id)
    return {"error": "profile_output_not_found", "workspace_id": workspace_id, "output_id": output_id}


def start_analysis_workflow(body: dict) -> dict:
    plan = ANALYSIS.plan(body)
    if not plan.get("ok"):
        return plan
    if not plan.get("can_start_job"):
        return {"ok": False, "error": "analysis_not_ready", "plan": plan}
    job = JOBS.start("analysis_workflow_safe_access", plan["job_payload"], build_pilot_workspace)
    return {
        "ok": True,
        "plan": plan,
        "job": job,
        "source_gis_modified": False,
    }


def rerun_analysis_run(run_id: str) -> dict:
    payload = ANALYSIS_RUNS.rerun_payload(run_id)
    if "error" in payload:
        return payload
    job = JOBS.start("analysis_workflow_safe_access", payload, build_pilot_workspace)
    return {
        "ok": True,
        "source_run_id": run_id,
        "job": job,
        "source_gis_modified": False,
    }


def generate_portfolio_report(body: dict) -> dict:
    run_id = str(body.get("run_id") or "").strip()
    if not run_id:
        return {"error": "portfolio_report_run_missing", "detail": "run_id is required"}
    return PORTFOLIO_REPORTS.generate_from_run(run_id)


def compare_portfolio_runs(body: dict) -> dict:
    run_ids = body.get("run_ids", [])
    if not isinstance(run_ids, list):
        return {"error": "portfolio_compare_needs_runs", "detail": "run_ids must be a list"}
    return PORTFOLIO_REPORTS.compare_runs([str(run_id) for run_id in run_ids])


def generate_profile_workspace_report(body: dict) -> dict:
    workspace_id = str(body.get("workspace_id") or "").strip()
    if not workspace_id:
        return {"error": "portfolio_profile_workspace_missing", "detail": "workspace_id is required"}
    return PORTFOLIO_REPORTS.generate_from_profile_workspace(workspace_id)


def generate_profile_comparison_report(body: dict) -> dict:
    base_workspace_id = str(body.get("base_workspace_id") or ROUTE_WORKSPACE_ID)
    raw_workspace_ids = body.get("profile_workspace_ids")
    if isinstance(raw_workspace_ids, list) and raw_workspace_ids:
        profile_workspace_ids = [str(workspace_id) for workspace_id in raw_workspace_ids]
    else:
        transit = TRANSIT.ensure_workspace(base_workspace_id, DEFAULT_TRANSIT_WORKSPACE_ID)
        if not transit.get("ok"):
            return transit
        parks = PARKS.ensure_workspace(base_workspace_id, DEFAULT_PARK_PLAYGROUND_WORKSPACE_ID)
        if not parks.get("ok"):
            return parks
        profile_workspace_ids = [DEFAULT_TRANSIT_WORKSPACE_ID, DEFAULT_PARK_PLAYGROUND_WORKSPACE_ID]
    return PORTFOLIO_REPORTS.generate_profile_comparison(base_workspace_id, profile_workspace_ids)


def build_pilot_workspace(body: dict, log=None) -> dict:
    log = log or (lambda _message: None)
    pilot_osm_id = str(body.get("pilot_osm_id") or "").strip()
    if not pilot_osm_id:
        return {"ok": False, "error": "bad_request", "detail": "pilot_osm_id is required"}
    pilot = PILOTS.detail(pilot_osm_id)
    if "error" in pilot:
        return {"ok": False, **pilot}
    log(f"Pilot selected: {pilot.get('name')} ({pilot_osm_id}).")
    dataset_id = str(body.get("dataset_id") or pilot.get("source_dataset_id") or DEFAULT_SOURCE_DATASET_ID)
    pilot_name = str(body.get("pilot_name") or pilot.get("name") or pilot_osm_id)
    pbf_workspace_id = str(body.get("workspace_id") or pilot.get("pbf_enriched_workspace_id"))
    route_workspace_id = str(body.get("route_workspace_id") or pilot.get("route_aware_workspace_id"))
    include_route = boolish(body.get("route_aware", True))

    log(f"Building or reusing PBF-enriched workspace: {pbf_workspace_id}.")
    generic_run = RUNNER.build_safe_access_generic(dataset_id, pilot_osm_id, pilot_name, pbf_workspace_id)
    if not generic_run.get("ok"):
        log(f"PBF-enriched workspace failed: {generic_run.get('error', 'unknown error')}.")
        return {
            "ok": False,
            "error": generic_run.get("error", "pilot_workspace_build_failed"),
            "pilot": pilot,
            "generic_run": generic_run,
        }
    log(f"PBF-enriched workspace ready: {pbf_workspace_id}.")
    result = {
        "ok": True,
        "pilot": pilot,
        "pbf_workspace": generic_run,
        "route_workspace": None,
        "active_workspace_id": pbf_workspace_id,
    }
    if include_route:
        log(f"Building or reusing route-aware workspace: {route_workspace_id}.")
        route_run = NETWORK.ensure_route_aware_workspace(pbf_workspace_id, route_workspace_id)
        result["route_workspace"] = route_run
        if not route_run.get("ok"):
            result["ok"] = False
            result["error"] = route_run.get("error", "route_workspace_build_failed")
            log(f"Route-aware workspace failed: {result['error']}.")
            return result
        result["active_workspace_id"] = route_workspace_id
        log(f"Route-aware workspace ready: {route_workspace_id}.")
    else:
        log("Route-aware workspace skipped by request.")
    log(f"Active workspace: {result['active_workspace_id']}.")
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = f"GeoReviewStudio/{APP_VERSION}"

    @staticmethod
    def is_client_abort(exc: BaseException) -> bool:
        abort_numbers = {32, 10053, 10054, 10058}
        return (
            isinstance(exc, (BrokenPipeError, ConnectionAbortedError, ConnectionResetError))
            or getattr(exc, "errno", None) in abort_numbers
            or getattr(exc, "winerror", None) in abort_numbers
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        segments = [segment for segment in path.split("/") if segment]
        if PRODUCT_MODE and not served_in_product_mode(path):
            self.json_response({"error": "not_found", "path": path}, status=404)
            return
        try:
            handler = ROUTE_TABLE_GET.get(path)
            if handler is not None:
                handler(self, segments, query)
                return
            if len(segments) == 4 and segments[:3] == ["api", "release-readiness", "snapshots"]:
                self.json_or_error_response(RELEASE_READINESS.snapshot_detail(segments[3]))
            elif len(segments) == 4 and segments[:3] == ["api", "portfolio-demo", "snapshots"]:
                self.json_or_error_response(PORTFOLIO_DEMO.snapshot_detail(segments[3]))
            elif len(segments) == 5 and segments[:3] == ["api", "portfolio-evidence-bundle", "bundles"] and segments[4] == "download":
                self.portfolio_evidence_bundle_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "portfolio-evidence-bundle", "bundles"]:
                self.json_or_error_response(PORTFOLIO_EVIDENCE_BUNDLE.detail(segments[3]))
            elif len(segments) == 5 and segments[:3] == ["api", "bundle-review-checklist", "checklists"] and segments[4] == "download":
                self.bundle_review_checklist_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "bundle-review-checklist", "checklists"]:
                self.json_or_error_response(BUNDLE_REVIEW_CHECKLIST.detail(segments[3]))
            elif len(segments) == 5 and segments[:3] == ["api", "portfolio-narrative-export", "narratives"] and segments[4] == "download":
                self.portfolio_narrative_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "portfolio-narrative-export", "narratives"]:
                self.json_or_error_response(PORTFOLIO_NARRATIVE_EXPORT.detail(segments[3]))
            elif len(segments) == 5 and segments[:3] == ["api", "portfolio-handoff-page", "pages"] and segments[4] == "download":
                self.portfolio_handoff_page_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "portfolio-handoff-page", "pages"]:
                self.json_or_error_response(PORTFOLIO_HANDOFF_PAGE.detail(segments[3]))
            elif len(segments) == 5 and segments[:3] == ["api", "portfolio-evidence-gallery", "galleries"] and segments[4] == "download":
                self.portfolio_evidence_gallery_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "portfolio-evidence-gallery", "galleries"]:
                self.json_or_error_response(PORTFOLIO_EVIDENCE_GALLERY.detail(segments[3]))
            elif len(segments) == 5 and segments[:3] == ["api", "multi-pilot-comparison", "comparisons"] and segments[4] == "download":
                self.multi_pilot_comparison_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "multi-pilot-comparison", "comparisons"]:
                self.json_or_error_response(MULTI_PILOT_COMPARISON.detail(segments[3]))
            elif len(segments) == 5 and segments[:3] == ["api", "comparison-map-exports", "exports"] and segments[4] == "download":
                self.comparison_map_export_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "comparison-map-exports", "exports"]:
                self.json_or_error_response(COMPARISON_MAP_EXPORTS.detail(segments[3]))
            elif len(segments) == 3 and segments[:2] == ["api", "postgis-backend"]:
                self.json_or_error_response(POSTGIS_BACKEND.detail(segments[2]))
            elif path == "/api/profile-mapper":
                self.json_or_error_response(PROFILE_MAPPER.overview())
            elif path == "/api/profile-mapper/contracts":
                self.json_or_error_response(PROFILE_MAPPER.contracts())
            elif len(segments) == 4 and segments[:3] == ["api", "profile-mapper", "contracts"]:
                self.json_or_error_response(PROFILE_MAPPER.contract(segments[3]))
            elif path == "/api/profile-mapper/compatibility":
                self.json_or_error_response(PROFILE_MAPPER.compatibility(
                    profile_id=first(query, "profile_id", ""),
                    dataset_id=first(query, "dataset_id", ""),
                ))
            elif path == "/api/profile-mapper/plan":
                self.json_or_error_response(PROFILE_MAPPER.mapper_plan({
                    "profile_id": first(query, "profile_id", "safe_access_pedestrian_review"),
                    "dataset_id": first(query, "dataset_id", ""),
                }))
            elif path == "/api/profile-mapper/plans":
                self.json_response(PROFILE_MAPPER.list_plans(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "profile-mapper", "plans"]:
                self.json_or_error_response(PROFILE_MAPPER.detail(segments[3]))
            elif path == "/api/dataset-packages":
                self.json_or_error_response(DATASET_PACKAGES.status())
            elif path == "/api/dataset-packages/packages":
                self.json_response(DATASET_PACKAGES.list_packages(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "dataset-packages", "packages"]:
                self.json_or_error_response(DATASET_PACKAGES.detail(segments[3]))
            elif len(segments) == 5 and segments[:3] == ["api", "dataset-packages", "packages"] and segments[4] == "download":
                self.dataset_package_response(segments[3])
            elif path == "/api/execution-queue":
                self.json_or_error_response(EXECUTION_QUEUE.status())
            elif path == "/api/execution-queue/jobs":
                self.json_response(EXECUTION_QUEUE.list_jobs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "execution-queue", "jobs"]:
                self.json_or_error_response(EXECUTION_QUEUE.detail(segments[3]))
            elif path == "/api/authored-profile-runner":
                self.json_or_error_response(AUTHORED_PROFILE_RUNNER.status())
            elif path == "/api/authored-profile-runner/workspaces":
                self.json_response(AUTHORED_PROFILE_RUNNER.list_workspaces())
            elif path == "/api/profile-promotion":
                self.json_or_error_response(PROFILE_PROMOTION.status())
            elif path == "/api/profile-promotion/candidates":
                self.json_response(PROFILE_PROMOTION.candidates(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "profile-promotion", "candidates"]:
                self.json_or_error_response(PROFILE_PROMOTION.candidate(segments[3]))
            elif path == "/api/profile-promotion/review-queue":
                self.json_response(PROFILE_PROMOTION.review_queue(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/profile-promotion/decisions":
                self.json_response(PROFILE_PROMOTION.list_decisions(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/profile-promotion/diff-candidates":
                self.json_response(PROFILE_PROMOTION.contract_diff_candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/profile-promotion/contract-diffs":
                self.json_response(PROFILE_PROMOTION.list_contract_diffs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "profile-promotion", "contract-diffs"]:
                self.json_or_error_response(PROFILE_PROMOTION.contract_diff_detail(segments[3]))
            elif path == "/api/profile-promotion/application-candidates":
                self.json_response(PROFILE_PROMOTION.application_candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/profile-promotion/apply-candidates":
                self.json_response(PROFILE_PROMOTION.config_apply_candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/profile-promotion/regression-candidates":
                self.json_response(PROFILE_PROMOTION.contract_regression_candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/profile-promotion/regression-previews":
                self.json_response(PROFILE_PROMOTION.list_contract_regression_previews(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "profile-promotion", "regression-previews"]:
                self.json_or_error_response(PROFILE_PROMOTION.contract_regression_preview_detail(segments[3]))
            elif path == "/api/profile-promotion/config-apply-proposals":
                self.json_response(PROFILE_PROMOTION.list_config_apply_proposals(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "profile-promotion", "config-apply-proposals"]:
                self.json_or_error_response(PROFILE_PROMOTION.config_apply_proposal_detail(segments[3]))
            elif path == "/api/profile-promotion/application-plans":
                self.json_response(PROFILE_PROMOTION.list_application_plans(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "profile-promotion", "application-plans"]:
                self.json_or_error_response(PROFILE_PROMOTION.application_plan_detail(segments[3]))
            elif path == "/api/profile-promotion/proposals":
                self.json_response(PROFILE_PROMOTION.list_proposals(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "profile-promotion", "proposals"] and segments[4] == "decision":
                self.json_or_error_response(PROFILE_PROMOTION.latest_decision(segments[3]))
            elif len(segments) == 4 and segments[:3] == ["api", "profile-promotion", "proposals"]:
                self.json_or_error_response(PROFILE_PROMOTION.detail(segments[3]))
            elif path == "/api/template-authoring":
                self.json_or_error_response(TEMPLATE_AUTHORING.status())
            elif path == "/api/template-authoring/options":
                self.json_or_error_response(TEMPLATE_AUTHORING.options())
            elif path == "/api/template-authoring/drafts":
                self.json_response(TEMPLATE_AUTHORING.list_drafts(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "template-authoring", "drafts"]:
                self.json_or_error_response(TEMPLATE_AUTHORING.detail(segments[3]))
            elif path == "/api/osm-tag-quality":
                self.json_or_error_response(OSM_TAG_QUALITY.status())
            elif path == "/api/osm-tag-quality/summary":
                self.json_or_error_response(OSM_TAG_QUALITY.summary())
            elif path == "/api/osm-tag-quality/results":
                self.json_or_error_response(OSM_TAG_QUALITY.source_results(parse_int(first(query, "limit", "50"), 50)))
            elif path == "/api/contract-execution":
                self.json_or_error_response(CONTRACT_EXECUTION.status())
            elif path == "/api/contract-execution/adapters":
                self.json_or_error_response(CONTRACT_EXECUTION.adapters_response())
            elif path == "/api/contract-execution/dry-run":
                self.json_or_error_response(CONTRACT_EXECUTION.dry_run({
                    "profile_id": first(query, "profile_id", "safe_access_pedestrian_review"),
                    "dataset_id": first(query, "dataset_id", "israel-and-palestine-260521-free-shp-zip"),
                    "pilot_osm_id": first(query, "pilot_osm_id", "53796999"),
                }))
            elif path == "/api/contract-execution/dry-runs":
                self.json_response(CONTRACT_EXECUTION.list_dry_runs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 4 and segments[:3] == ["api", "contract-execution", "dry-runs"]:
                self.json_or_error_response(CONTRACT_EXECUTION.detail(segments[3]))
            elif path == "/api/workspaces":
                self.json_response([
                    {
                        "workspace_id": WORKSPACE_ID,
                        "name": "Safe Access Israel / Kfar Saba",
                        "template": "safe_access",
                        "validation_passed": DATA.validation.get("passed"),
                    }
                ])
            elif path == f"/api/workspaces/{WORKSPACE_ID}/summary":
                self.json_response(DATA.summary())
            elif path == f"/api/workspaces/{WORKSPACE_ID}/candidates":
                self.json_response(DATA.candidates(query))
            elif path == f"/api/workspaces/{WORKSPACE_ID}/map-features":
                self.json_response(DATA.map_features())
            elif path == f"/api/workspaces/{WORKSPACE_ID}/validation":
                self.json_response(DATA.validation)
            elif path == "/api/catalog/sources":
                self.json_response(CATALOG.source_files())
            elif len(segments) == 4 and segments[:3] == ["api", "catalog", "sources"]:
                self.json_or_error_response(CATALOG.profile(segments[3]))
            elif path == "/api/catalog/tag-summary":
                self.json_response(CATALOG.tag_summary(first(query, "extension", "")))
            elif path == "/api/source-onboarding":
                self.json_response(ONBOARDING.status())
            elif path == "/api/source-onboarding/sources":
                self.json_response(ONBOARDING.sources())
            elif path == "/api/local-intake":
                self.json_response(LOCAL_INTAKE.status())
            elif path == "/api/local-intake/sources":
                self.json_response(LOCAL_INTAKE.sources())
            elif path == "/api/source-import-guardrails":
                self.json_response(SOURCE_IMPORT_GUARDRAILS.status())
            elif path == "/api/source-import-guardrails/requests":
                self.json_response(SOURCE_IMPORT_GUARDRAILS.list_requests(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "source-import-guardrails", "requests"] and segments[4] == "download":
                self.source_import_guardrails_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "source-import-guardrails", "requests"]:
                self.json_or_error_response(SOURCE_IMPORT_GUARDRAILS.detail(segments[3]))
            elif path == "/api/source-handoff":
                self.json_response(SOURCE_HANDOFF.status())
            elif path == "/api/source-handoff/candidates":
                self.json_response(SOURCE_HANDOFF.candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/source-handoff/handoffs":
                self.json_response(SOURCE_HANDOFF.list_handoffs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "source-handoff", "handoffs"] and segments[4] == "download":
                self.source_handoff_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "source-handoff", "handoffs"]:
                self.json_or_error_response(SOURCE_HANDOFF.detail(segments[3]))
            elif path == "/api/source-handoff-execution":
                self.json_response(SOURCE_HANDOFF_EXECUTION.status())
            elif path == "/api/source-handoff-execution/candidates":
                self.json_response(SOURCE_HANDOFF_EXECUTION.candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/source-handoff-execution/executions":
                self.json_response(SOURCE_HANDOFF_EXECUTION.list_executions(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "source-handoff-execution", "executions"] and segments[4] == "download":
                self.source_handoff_execution_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "source-handoff-execution", "executions"]:
                self.json_or_error_response(SOURCE_HANDOFF_EXECUTION.detail(segments[3]))
            elif path == "/api/execution-evidence-package":
                self.json_response(EXECUTION_EVIDENCE_PACKAGE.status())
            elif path == "/api/execution-evidence-package/candidates":
                self.json_response(EXECUTION_EVIDENCE_PACKAGE.candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/execution-evidence-package/packages":
                self.json_response(EXECUTION_EVIDENCE_PACKAGE.list_packages(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "execution-evidence-package", "packages"] and segments[4] == "download":
                self.execution_evidence_package_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "execution-evidence-package", "packages"]:
                self.json_or_error_response(EXECUTION_EVIDENCE_PACKAGE.detail(segments[3]))
            elif path == "/api/execution-result-diff":
                self.json_response(EXECUTION_RESULT_DIFF.status())
            elif path == "/api/execution-result-diff/candidates":
                self.json_response(EXECUTION_RESULT_DIFF.candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/execution-result-diff/diffs":
                self.json_response(EXECUTION_RESULT_DIFF.list_diffs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "execution-result-diff", "diffs"] and segments[4] == "download":
                self.execution_result_diff_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "execution-result-diff", "diffs"]:
                self.json_or_error_response(EXECUTION_RESULT_DIFF.detail(segments[3]))
            elif path == "/api/execution-diff-gallery":
                self.json_response(EXECUTION_DIFF_GALLERY.status())
            elif path == "/api/execution-diff-gallery/items":
                self.json_response(EXECUTION_DIFF_GALLERY.items(
                    limit=parse_int(first(query, "limit", "20"), 20),
                    classification=first(query, "classification", ""),
                    readiness=first(query, "readiness", ""),
                    scope=first(query, "scope", ""),
                ))
            elif path == "/api/execution-diff-gallery/galleries":
                self.json_response(EXECUTION_DIFF_GALLERY.list_galleries(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "execution-diff-gallery", "galleries"] and segments[4] == "download":
                self.execution_diff_gallery_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "execution-diff-gallery", "galleries"]:
                self.json_or_error_response(EXECUTION_DIFF_GALLERY.detail(segments[3]))
            elif path == "/api/execution-diff-detail":
                self.json_response(EXECUTION_DIFF_DETAIL.status())
            elif path == "/api/execution-diff-detail/baselines":
                self.json_response(EXECUTION_DIFF_DETAIL.baselines(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/execution-diff-detail/inspect":
                self.json_or_error_response(EXECUTION_DIFF_DETAIL.inspect_diff(
                    first(query, "diff_id", ""),
                    first(query, "baseline_diff_id", ""),
                ))
            elif path == "/api/execution-diff-detail/drilldowns":
                self.json_response(EXECUTION_DIFF_DETAIL.list_drilldowns(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "execution-diff-detail", "drilldowns"] and segments[4] == "download":
                self.execution_diff_detail_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "execution-diff-detail", "drilldowns"]:
                self.json_or_error_response(EXECUTION_DIFF_DETAIL.detail(segments[3]))
            elif path == "/api/reproducibility-audit-packet":
                self.json_response(REPRODUCIBILITY_AUDIT_PACKET.status())
            elif path == "/api/reproducibility-audit-packet/candidates":
                self.json_response(REPRODUCIBILITY_AUDIT_PACKET.candidates(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/reproducibility-audit-packet/packets":
                self.json_response(REPRODUCIBILITY_AUDIT_PACKET.list_packets(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "reproducibility-audit-packet", "packets"] and segments[4] == "download":
                self.reproducibility_audit_packet_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "reproducibility-audit-packet", "packets"]:
                self.json_or_error_response(REPRODUCIBILITY_AUDIT_PACKET.detail(segments[3]))
            elif path == "/api/reviewer-audit-index":
                self.json_response(REVIEWER_AUDIT_INDEX.status())
            elif path == "/api/reviewer-audit-index/indexes":
                self.json_response(REVIEWER_AUDIT_INDEX.list_indexes(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "reviewer-audit-index", "indexes"] and segments[4] == "download":
                self.reviewer_audit_index_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "reviewer-audit-index", "indexes"]:
                self.json_or_error_response(REVIEWER_AUDIT_INDEX.detail(segments[3]))
            elif path == "/api/portfolio-export-launcher":
                self.json_response(PORTFOLIO_EXPORT_LAUNCHER.status())
            elif path == "/api/portfolio-export-launcher/launchers":
                self.json_response(PORTFOLIO_EXPORT_LAUNCHER.list_launchers(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "portfolio-export-launcher", "launchers"] and segments[4] == "download":
                self.portfolio_export_launcher_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "portfolio-export-launcher", "launchers"]:
                self.json_or_error_response(PORTFOLIO_EXPORT_LAUNCHER.detail(segments[3]))
            elif path == "/api/portable-release-package":
                self.json_response(PORTABLE_RELEASE_PACKAGE.status())
            elif path == "/api/portable-release-package/packages":
                self.json_response(PORTABLE_RELEASE_PACKAGE.list_packages(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "portable-release-package", "packages"] and segments[4] == "download":
                self.portable_release_package_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "portable-release-package", "packages"]:
                self.json_or_error_response(PORTABLE_RELEASE_PACKAGE.detail(segments[3]))
            elif path == "/api/demo-script-pack":
                self.json_response(DEMO_SCRIPT_PACK.status())
            elif path == "/api/demo-script-pack/packs":
                self.json_response(DEMO_SCRIPT_PACK.list_packs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "demo-script-pack", "packs"] and segments[4] == "download":
                self.demo_script_pack_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "demo-script-pack", "packs"]:
                self.json_or_error_response(DEMO_SCRIPT_PACK.detail(segments[3]))
            elif path == "/api/visual-qa-snapshot-ledger":
                self.json_response(VISUAL_QA_LEDGER.status())
            elif path == "/api/visual-qa-snapshot-ledger/ledgers":
                self.json_response(VISUAL_QA_LEDGER.list_ledgers(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "visual-qa-snapshot-ledger", "ledgers"] and segments[4] == "download":
                self.visual_qa_ledger_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "visual-qa-snapshot-ledger", "ledgers"]:
                self.json_or_error_response(VISUAL_QA_LEDGER.detail(segments[3]))
            elif path == "/api/visual-baseline-comparison":
                self.json_response(VISUAL_BASELINE_COMPARISON.status())
            elif path == "/api/visual-baseline-comparison/comparisons":
                self.json_response(VISUAL_BASELINE_COMPARISON.list_comparisons(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "visual-baseline-comparison", "comparisons"] and segments[4] == "download":
                self.visual_baseline_comparison_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "visual-baseline-comparison", "comparisons"]:
                self.json_or_error_response(VISUAL_BASELINE_COMPARISON.detail(segments[3]))
            elif path == "/api/demo-artifact-completeness":
                self.json_response(DEMO_ARTIFACT_COMPLETENESS.status())
            elif path == "/api/demo-artifact-completeness/checks":
                self.json_response(DEMO_ARTIFACT_COMPLETENESS.list_checks(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "demo-artifact-completeness", "checks"] and segments[4] == "download":
                self.demo_artifact_completeness_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "demo-artifact-completeness", "checks"]:
                self.json_or_error_response(DEMO_ARTIFACT_COMPLETENESS.detail(segments[3]))
            elif path == "/api/visual-evidence-capture":
                self.json_response(VISUAL_EVIDENCE_CAPTURE.status())
            elif path == "/api/visual-evidence-capture/captures":
                self.json_response(VISUAL_EVIDENCE_CAPTURE.list_captures(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "visual-evidence-capture", "captures"] and segments[4] == "download":
                self.visual_evidence_capture_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "visual-evidence-capture", "captures"]:
                self.json_or_error_response(VISUAL_EVIDENCE_CAPTURE.detail(segments[3]))
            elif path == "/api/visual-evidence-review-diff":
                self.json_response(VISUAL_EVIDENCE_REVIEW_DIFF.status())
            elif path == "/api/visual-evidence-review-diff/diffs":
                self.json_response(VISUAL_EVIDENCE_REVIEW_DIFF.list_diffs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "visual-evidence-review-diff", "diffs"] and segments[4] == "download":
                self.visual_evidence_review_diff_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "visual-evidence-review-diff", "diffs"]:
                self.json_or_error_response(VISUAL_EVIDENCE_REVIEW_DIFF.detail(segments[3]))
            elif path == "/api/visual-evidence-review-annotations":
                self.json_response(VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.status())
            elif path == "/api/visual-evidence-review-annotations/annotations":
                self.json_response(VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.list_annotations(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "visual-evidence-review-annotations", "annotations"] and segments[4] == "download":
                self.visual_evidence_review_annotations_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "visual-evidence-review-annotations", "annotations"]:
                self.json_or_error_response(VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.detail(segments[3]))
            elif path == "/api/visual-evidence-signoff-packet":
                self.json_response(VISUAL_EVIDENCE_SIGNOFF_PACKET.status())
            elif path == "/api/visual-evidence-signoff-packet/packets":
                self.json_response(VISUAL_EVIDENCE_SIGNOFF_PACKET.list_packets(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "visual-evidence-signoff-packet", "packets"] and segments[4] == "download":
                self.visual_evidence_signoff_packet_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "visual-evidence-signoff-packet", "packets"]:
                self.json_or_error_response(VISUAL_EVIDENCE_SIGNOFF_PACKET.detail(segments[3]))
            elif path == "/api/final-reviewer-launch-checklist":
                self.json_response(FINAL_REVIEWER_LAUNCH_CHECKLIST.status())
            elif path == "/api/final-reviewer-launch-checklist/checklists":
                self.json_response(FINAL_REVIEWER_LAUNCH_CHECKLIST.list_checklists(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "final-reviewer-launch-checklist", "checklists"] and segments[4] == "download":
                self.final_reviewer_launch_checklist_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "final-reviewer-launch-checklist", "checklists"]:
                self.json_or_error_response(FINAL_REVIEWER_LAUNCH_CHECKLIST.detail(segments[3]))
            elif path == "/api/recruiter-demo-brief":
                self.json_response(RECRUITER_DEMO_BRIEF.status())
            elif path == "/api/recruiter-demo-brief/briefs":
                self.json_response(RECRUITER_DEMO_BRIEF.list_briefs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "recruiter-demo-brief", "briefs"] and segments[4] == "download":
                self.recruiter_demo_brief_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "recruiter-demo-brief", "briefs"]:
                self.json_or_error_response(RECRUITER_DEMO_BRIEF.detail(segments[3]))
            elif path == "/api/public-portfolio-package":
                self.json_response(PUBLIC_PORTFOLIO_PACKAGE.status())
            elif path == "/api/public-portfolio-package/packages":
                self.json_response(PUBLIC_PORTFOLIO_PACKAGE.list_packages(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "public-portfolio-package", "packages"] and segments[4] == "download":
                self.public_portfolio_package_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "public-portfolio-package", "packages"]:
                self.json_or_error_response(PUBLIC_PORTFOLIO_PACKAGE.detail(segments[3]))
            elif path == "/api/demo-review-playbook":
                self.json_response(DEMO_REVIEW_PLAYBOOK.status())
            elif path == "/api/demo-review-playbook/playbooks":
                self.json_response(DEMO_REVIEW_PLAYBOOK.list_playbooks(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "demo-review-playbook", "playbooks"] and segments[4] == "download":
                self.demo_review_playbook_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "demo-review-playbook", "playbooks"]:
                self.json_or_error_response(DEMO_REVIEW_PLAYBOOK.detail(segments[3]))
            elif path == "/api/github-publication-bundle":
                self.json_response(GITHUB_PUBLICATION_BUNDLE.status())
            elif path == "/api/github-publication-bundle/bundles":
                self.json_response(GITHUB_PUBLICATION_BUNDLE.list_bundles(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "github-publication-bundle", "bundles"] and segments[4] == "download":
                self.github_publication_bundle_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "github-publication-bundle", "bundles"]:
                self.json_or_error_response(GITHUB_PUBLICATION_BUNDLE.detail(segments[3]))
            elif path == "/api/repository-publication-qa":
                self.json_response(REPOSITORY_PUBLICATION_QA.status())
            elif path == "/api/repository-publication-qa/reviews":
                self.json_response(REPOSITORY_PUBLICATION_QA.list_reviews(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "repository-publication-qa", "reviews"] and segments[4] == "download":
                self.repository_publication_qa_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "repository-publication-qa", "reviews"]:
                self.json_or_error_response(REPOSITORY_PUBLICATION_QA.detail(segments[3]))
            elif path == "/api/repository-export-handoff":
                self.json_response(REPOSITORY_EXPORT_HANDOFF.status())
            elif path == "/api/repository-export-handoff/handoffs":
                self.json_response(REPOSITORY_EXPORT_HANDOFF.list_handoffs(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "repository-export-handoff", "handoffs"] and segments[4] == "download":
                self.repository_export_handoff_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "repository-export-handoff", "handoffs"]:
                self.json_or_error_response(REPOSITORY_EXPORT_HANDOFF.detail(segments[3]))
            elif path == "/api/repository-dry-run-review":
                self.json_response(REPOSITORY_DRY_RUN_REVIEW.status())
            elif path == "/api/repository-dry-run-review/reviews":
                self.json_response(REPOSITORY_DRY_RUN_REVIEW.list_reviews(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "repository-dry-run-review", "reviews"] and segments[4] == "download":
                self.repository_dry_run_review_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "repository-dry-run-review", "reviews"]:
                self.json_or_error_response(REPOSITORY_DRY_RUN_REVIEW.detail(segments[3]))
            elif path == "/api/repository-final-package-review":
                self.json_response(REPOSITORY_FINAL_PACKAGE_REVIEW.status())
            elif path == "/api/repository-final-package-review/reviews":
                self.json_response(REPOSITORY_FINAL_PACKAGE_REVIEW.list_reviews(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "repository-final-package-review", "reviews"] and segments[4] == "download":
                self.repository_final_package_review_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "repository-final-package-review", "reviews"]:
                self.json_or_error_response(REPOSITORY_FINAL_PACKAGE_REVIEW.detail(segments[3]))
            elif path == "/api/public-readme-cleanup-review":
                self.json_response(PUBLIC_README_CLEANUP_REVIEW.status())
            elif path == "/api/public-readme-cleanup-review/reviews":
                self.json_response(PUBLIC_README_CLEANUP_REVIEW.list_reviews(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "public-readme-cleanup-review", "reviews"] and segments[4] == "download":
                self.public_readme_cleanup_review_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "public-readme-cleanup-review", "reviews"]:
                self.json_or_error_response(PUBLIC_README_CLEANUP_REVIEW.detail(segments[3]))
            elif path == "/api/public-repository-polish-package":
                self.json_response(PUBLIC_REPOSITORY_POLISH_PACKAGE.status())
            elif path == "/api/public-repository-polish-package/packages":
                self.json_response(PUBLIC_REPOSITORY_POLISH_PACKAGE.list_packages(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "public-repository-polish-package", "packages"] and segments[4] == "download":
                self.public_repository_polish_package_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "public-repository-polish-package", "packages"]:
                self.json_or_error_response(PUBLIC_REPOSITORY_POLISH_PACKAGE.detail(segments[3]))
            elif path == "/api/repository-export-checklist":
                self.json_response(REPOSITORY_EXPORT_CHECKLIST.status())
            elif path == "/api/repository-export-checklist/checklists":
                self.json_response(REPOSITORY_EXPORT_CHECKLIST.list_checklists(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 5 and segments[:3] == ["api", "repository-export-checklist", "checklists"] and segments[4] == "download":
                self.repository_export_checklist_response(segments[3])
            elif len(segments) == 4 and segments[:3] == ["api", "repository-export-checklist", "checklists"]:
                self.json_or_error_response(REPOSITORY_EXPORT_CHECKLIST.detail(segments[3]))
            elif len(segments) == 4 and segments[:3] == ["api", "source-onboarding", "sources"]:
                self.json_or_error_response(ONBOARDING.source_detail(segments[3]))
            elif path == "/api/analysis-workflow/plan":
                self.json_or_error_response(analysis_plan_from_query(query))
            elif path == "/api/analysis-profiles":
                self.json_or_error_response(profiles_from_query(query))
            elif path == "/api/profile-dashboard":
                self.json_response(PROFILE_DASHBOARD.overview())
            elif path == "/api/profile-dashboard/profiles":
                self.json_response(PROFILE_DASHBOARD.profiles())
            elif path == "/api/scoring-rules":
                self.json_or_error_response(SCORING_RULES.overview())
            elif len(segments) == 4 and segments[:2] == ["api", "profile-dashboard"] and segments[3] == "summary":
                self.json_or_error_response(PROFILE_DASHBOARD.summary(segments[2]))
            elif len(segments) == 3 and segments[:2] == ["api", "scoring-rules"]:
                self.json_or_error_response(SCORING_RULES.profile(segments[2]))
            elif len(segments) == 4 and segments[:2] == ["api", "scoring-rules"] and segments[3] == "audit":
                self.json_or_error_response(SCORING_RULES.audit(
                    segments[2],
                    limit=parse_int(first(query, "limit", "50"), 50),
                    min_score=parse_int(first(query, "min_score", "0"), 0),
                    only_mismatches=boolish(first(query, "only_mismatches", "false")),
                ))
            elif len(segments) == 4 and segments[:2] == ["api", "profile-dashboard"] and segments[3] == "results":
                self.json_or_error_response(profile_dashboard_results_from_query(segments[2], query))
            elif len(segments) == 3 and segments[:2] == ["api", "analysis-profiles"]:
                self.json_or_error_response(profile_detail_from_query(segments[2], query))
            elif len(segments) == 4 and segments[:2] == ["api", "analysis-profiles"] and segments[3] == "readiness":
                self.json_or_error_response(profile_readiness_from_query(segments[2], query))
            elif path == "/api/profile-runners":
                self.json_response(list_profile_runners())
            elif path == "/api/profile-workspaces":
                self.json_response(list_profile_workspaces())
            elif len(segments) == 4 and segments[:2] == ["api", "profile-workspaces"] and segments[3] == "summary":
                self.json_or_error_response(profile_workspace_summary(segments[2]))
            elif len(segments) == 4 and segments[:2] == ["api", "profile-workspaces"] and segments[3] == "results":
                self.json_or_error_response(profile_workspace_results(segments[2], parse_int(first(query, "limit", "50"), 50)))
            elif len(segments) == 5 and segments[:2] == ["api", "profile-workspaces"] and segments[3] == "download":
                self.profile_output_response(segments[2], segments[4])
            elif path == "/api/analysis-runs":
                self.json_response(ANALYSIS_RUNS.list(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 3 and segments[:2] == ["api", "analysis-runs"]:
                self.json_or_error_response(ANALYSIS_RUNS.detail(segments[2]))
            elif len(segments) == 4 and segments[:2] == ["api", "analysis-runs"] and segments[3] == "outputs":
                self.json_or_error_response(ANALYSIS_RUNS.outputs(segments[2]))
            elif len(segments) == 5 and segments[:2] == ["api", "analysis-runs"] and segments[3] == "outputs":
                self.analysis_output_response(segments[2], segments[4])
            elif path == "/api/portfolio-reports":
                self.json_response(PORTFOLIO_REPORTS.list_reports(parse_int(first(query, "limit", "20"), 20)))
            elif path == "/api/export-bundles":
                self.json_response(PROFILE_EXPORT_BUNDLES.list_bundles(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 3 and segments[:2] == ["api", "export-bundles"]:
                self.json_or_error_response(PROFILE_EXPORT_BUNDLES.detail(segments[2]))
            elif len(segments) == 4 and segments[:2] == ["api", "export-bundles"] and segments[3] == "download":
                self.export_bundle_response(segments[2])
            elif len(segments) == 3 and segments[:2] == ["api", "portfolio-reports"]:
                self.json_or_error_response(PORTFOLIO_REPORTS.detail(segments[2]))
            elif len(segments) == 4 and segments[:2] == ["api", "portfolio-reports"] and segments[3] == "download":
                self.portfolio_report_response(segments[2])
            elif path == "/api/templates":
                self.json_response(CATALOG.templates())
            elif len(segments) == 4 and segments[:2] == ["api", "templates"] and segments[3] == "check":
                dataset_id = first(query, "dataset_id", "")
                self.json_or_error_response(CATALOG.safe_access_check(dataset_id))
            elif path == "/api/workspace-registry":
                self.json_response(RUNNER.list_workspaces())
            elif len(segments) == 3 and segments[:2] == ["api", "workspace-registry"]:
                self.json_or_error_response(RUNNER.workspace_detail(segments[2]))
            elif path == "/api/pilot-areas":
                self.json_response(PILOTS.list_pilots(query))
            elif path == "/api/pilot-areas/metadata":
                self.json_response(PILOTS.metadata())
            elif len(segments) == 3 and segments[:2] == ["api", "pilot-areas"]:
                self.json_or_error_response(PILOTS.detail(segments[2]))
            elif path == "/api/preflight/safe-access-pilot":
                self.json_or_error_response(preflight_from_query(query))
            elif path == "/api/jobs":
                self.json_response(JOBS.list(parse_int(first(query, "limit", "20"), 20)))
            elif len(segments) == 3 and segments[:2] == ["api", "jobs"]:
                self.json_or_error_response(JOBS.detail(segments[2]))
            elif path == "/api/dashboard-workspaces":
                self.json_response(RUNNER.list_workspaces())
            elif len(segments) == 4 and segments[:2] == ["api", "dashboard-workspaces"]:
                workspace_id = segments[2]
                action = segments[3]
                if action == "summary":
                    self.json_or_error_response(DASHBOARDS.summary(workspace_id))
                elif action == "candidates":
                    self.json_or_error_response(DASHBOARDS.candidates(workspace_id, query))
                elif action == "network-access":
                    self.json_or_error_response(DASHBOARDS.network_access(workspace_id, query))
                elif action == "map-features":
                    self.json_or_error_response(DASHBOARDS.map_features(workspace_id))
                elif action == "validation":
                    self.json_or_error_response(DASHBOARDS.validation(workspace_id))
                elif action == "review-decisions":
                    self.json_or_error_response(REVIEW_DECISIONS.list_for_workspace(workspace_id))
                else:
                    self.json_response({"error": "not_found", "path": path}, status=404)
            elif path.startswith("/api/"):
                self.json_response({"error": "not_found", "path": path}, status=404)
            else:
                self.static_response(path)
        except Exception as exc:  # pragma: no cover - visible local error response
            if self.is_client_abort(exc):
                return
            LOGGER.exception("GET %s failed", path)
            self.json_response({"error": "server_error"}, status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if PRODUCT_MODE and not served_in_product_mode(path):
            self.json_response({"error": "not_found", "path": path}, status=404)
            return
        try:
            body = self.read_json_body()
            review_segments = [segment for segment in path.split("/") if segment]
            if (
                len(review_segments) == 4
                and review_segments[0] == "api"
                and review_segments[1] == "dashboard-workspaces"
                and review_segments[3] == "review-decisions"
            ):
                self.json_or_error_response(REVIEW_DECISIONS.set_decision(review_segments[2], body))
                return
            if path == "/api/runs/safe-access-kfar-saba":
                dataset_id = str(body.get("dataset_id") or "israel-and-palestine-260521-free-shp-zip")
                self.json_or_error_response(RUNNER.ensure_safe_access_kfar_saba(dataset_id))
            elif path == "/api/runs/safe-access-generic":
                dataset_id = str(body.get("dataset_id") or "israel-and-palestine-260521-free-shp-zip")
                pilot_osm_id = str(body.get("pilot_osm_id") or "53796999")
                pilot_name = str(body.get("pilot_name") or "Kfar Saba")
                workspace_id = str(body.get("workspace_id") or "safe_access_kfar_saba_pbf_enriched_v001")
                self.json_or_error_response(RUNNER.build_safe_access_generic(dataset_id, pilot_osm_id, pilot_name, workspace_id))
            elif path == "/api/runs/route-aware-kfar-saba":
                base_workspace_id = str(body.get("base_workspace_id") or "safe_access_kfar_saba_pbf_enriched_v001")
                workspace_id = str(body.get("workspace_id") or ROUTE_WORKSPACE_ID)
                self.json_or_error_response(NETWORK.ensure_route_aware_workspace(base_workspace_id, workspace_id))
            elif path == "/api/runs/safe-access-pilot":
                self.json_or_error_response(build_pilot_workspace(body))
            elif path == "/api/preflight/safe-access-pilot":
                self.json_or_error_response(preflight_from_body(body))
            elif path == "/api/source-onboarding/refresh":
                self.json_response(ONBOARDING.refresh())
            elif path == "/api/local-intake/preview":
                self.json_or_error_response(LOCAL_INTAKE.preview(body))
            elif path == "/api/local-intake/plan":
                self.json_or_error_response(LOCAL_INTAKE.create_plan(body))
            elif path == "/api/source-import-guardrails/preview":
                self.json_or_error_response(SOURCE_IMPORT_GUARDRAILS.preview(body))
            elif path == "/api/source-import-guardrails/request":
                self.json_or_error_response(SOURCE_IMPORT_GUARDRAILS.create_request(body))
            elif path == "/api/source-handoff/create":
                self.json_or_error_response(SOURCE_HANDOFF.create_handoff(body))
            elif path == "/api/source-handoff-execution/execute":
                self.json_or_error_response(SOURCE_HANDOFF_EXECUTION.execute_handoff(body, run_profile))
            elif path == "/api/execution-evidence-package/create":
                self.json_or_error_response(EXECUTION_EVIDENCE_PACKAGE.create_package(body))
            elif path == "/api/execution-result-diff/create":
                self.json_or_error_response(EXECUTION_RESULT_DIFF.create_diff(body))
            elif path == "/api/execution-diff-gallery/create":
                self.json_or_error_response(EXECUTION_DIFF_GALLERY.create_gallery(body))
            elif path == "/api/execution-diff-detail/create":
                self.json_or_error_response(EXECUTION_DIFF_DETAIL.create_drilldown(body))
            elif path == "/api/reproducibility-audit-packet/create":
                self.json_or_error_response(REPRODUCIBILITY_AUDIT_PACKET.create_packet(body))
            elif path == "/api/reviewer-audit-index/create":
                self.json_or_error_response(REVIEWER_AUDIT_INDEX.create_index(body))
            elif path == "/api/portfolio-export-launcher/create":
                self.json_or_error_response(PORTFOLIO_EXPORT_LAUNCHER.create_launcher(body))
            elif path == "/api/portable-release-package/create":
                self.json_or_error_response(PORTABLE_RELEASE_PACKAGE.create_package(body))
            elif path == "/api/demo-script-pack/create":
                self.json_or_error_response(DEMO_SCRIPT_PACK.create_pack(body))
            elif path == "/api/visual-qa-snapshot-ledger/create":
                self.json_or_error_response(VISUAL_QA_LEDGER.create_ledger(body))
            elif path == "/api/visual-baseline-comparison/create":
                self.json_or_error_response(VISUAL_BASELINE_COMPARISON.create_comparison(body))
            elif path == "/api/demo-artifact-completeness/create":
                self.json_or_error_response(DEMO_ARTIFACT_COMPLETENESS.create_check(body))
            elif path == "/api/visual-evidence-capture/create":
                self.json_or_error_response(VISUAL_EVIDENCE_CAPTURE.create_capture(body))
            elif path == "/api/visual-evidence-review-diff/create":
                self.json_or_error_response(VISUAL_EVIDENCE_REVIEW_DIFF.create_diff(body))
            elif path == "/api/visual-evidence-review-annotations/create":
                self.json_or_error_response(VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.create_annotations(body))
            elif path == "/api/visual-evidence-signoff-packet/create":
                self.json_or_error_response(VISUAL_EVIDENCE_SIGNOFF_PACKET.create_packet(body))
            elif path == "/api/final-reviewer-launch-checklist/create":
                self.json_or_error_response(FINAL_REVIEWER_LAUNCH_CHECKLIST.create_checklist(body))
            elif path == "/api/recruiter-demo-brief/create":
                self.json_or_error_response(RECRUITER_DEMO_BRIEF.create_brief(body))
            elif path == "/api/public-portfolio-package/create":
                self.json_or_error_response(PUBLIC_PORTFOLIO_PACKAGE.create_package(body))
            elif path == "/api/demo-review-playbook/create":
                self.json_or_error_response(DEMO_REVIEW_PLAYBOOK.create_playbook(body))
            elif path == "/api/github-publication-bundle/create":
                self.json_or_error_response(GITHUB_PUBLICATION_BUNDLE.create_bundle(body))
            elif path == "/api/repository-publication-qa/create":
                self.json_or_error_response(REPOSITORY_PUBLICATION_QA.create_review(body))
            elif path == "/api/repository-export-handoff/create":
                self.json_or_error_response(REPOSITORY_EXPORT_HANDOFF.create_handoff(body))
            elif path == "/api/repository-dry-run-review/create":
                self.json_or_error_response(REPOSITORY_DRY_RUN_REVIEW.create_review(body))
            elif path == "/api/repository-final-package-review/create":
                self.json_or_error_response(REPOSITORY_FINAL_PACKAGE_REVIEW.create_review(body))
            elif path == "/api/public-readme-cleanup-review/create":
                self.json_or_error_response(PUBLIC_README_CLEANUP_REVIEW.create_review(body))
            elif path == "/api/public-repository-polish-package/create":
                self.json_or_error_response(PUBLIC_REPOSITORY_POLISH_PACKAGE.create_package(body))
            elif path == "/api/repository-export-checklist/create":
                self.json_or_error_response(REPOSITORY_EXPORT_CHECKLIST.create_checklist(body))
            elif path == "/api/analysis-workflow/plan":
                self.json_or_error_response(ANALYSIS.plan(body))
            elif path == "/api/analysis-workflow/start":
                self.json_or_error_response(start_analysis_workflow(body), default_status=202)
            elif path == "/api/product-architecture/implementation-plan":
                self.json_response(PRODUCT_ARCHITECTURE.implementation_plan(body))
            elif path == "/api/release-readiness/snapshot":
                self.json_or_error_response(RELEASE_READINESS.create_snapshot(body))
            elif path == "/api/portfolio-demo/snapshot":
                self.json_or_error_response(PORTFOLIO_DEMO.create_snapshot(body))
            elif path == "/api/portfolio-evidence-bundle/create":
                self.json_or_error_response(PORTFOLIO_EVIDENCE_BUNDLE.create_bundle(body))
            elif path == "/api/bundle-review-checklist/create":
                self.json_or_error_response(BUNDLE_REVIEW_CHECKLIST.create_checklist(body))
            elif path == "/api/portfolio-narrative-export/create":
                self.json_or_error_response(PORTFOLIO_NARRATIVE_EXPORT.create_narrative(body))
            elif path == "/api/portfolio-handoff-page/create":
                self.json_or_error_response(PORTFOLIO_HANDOFF_PAGE.create_page(body))
            elif path == "/api/portfolio-evidence-gallery/create":
                self.json_or_error_response(PORTFOLIO_EVIDENCE_GALLERY.create_gallery(body))
            elif path == "/api/multi-pilot-comparison/create":
                self.json_or_error_response(MULTI_PILOT_COMPARISON.create_comparison(body))
            elif path == "/api/comparison-map-exports/create":
                self.json_or_error_response(COMPARISON_MAP_EXPORTS.create_export(body))
            elif path == "/api/postgis-backend/migration-plan":
                self.json_or_error_response(POSTGIS_BACKEND.migration_plan(body, write_files=True))
            elif path == "/api/profile-mapper/plan":
                self.json_or_error_response(PROFILE_MAPPER.mapper_plan(body, write_files=True))
            elif path == "/api/contract-execution/dry-run":
                self.json_or_error_response(CONTRACT_EXECUTION.dry_run(body, write_files=True))
            elif path == "/api/template-authoring/draft":
                self.json_or_error_response(TEMPLATE_AUTHORING.draft(body, write_files=True))
            elif path == "/api/execution-queue/enqueue":
                self.json_or_error_response(EXECUTION_QUEUE.enqueue(body, run_profile))
            elif path == "/api/execution-queue/enqueue-authored-draft":
                self.json_or_error_response(EXECUTION_QUEUE.enqueue_authored_draft(body, TEMPLATE_AUTHORING, run_authored_profile))
            elif path == "/api/authored-profile-runner/run":
                self.json_or_error_response(run_authored_profile(str(body.get("draft_id") or ""), body))
            elif path == "/api/profile-promotion/propose":
                self.json_or_error_response(PROFILE_PROMOTION.propose(body))
            elif path == "/api/profile-promotion/contract-diff":
                self.json_or_error_response(PROFILE_PROMOTION.create_contract_diff(body))
            elif path == "/api/profile-promotion/application-plan":
                self.json_or_error_response(PROFILE_PROMOTION.create_application_plan(body))
            elif path == "/api/profile-promotion/config-apply-proposal":
                self.json_or_error_response(PROFILE_PROMOTION.create_config_apply_proposal(body))
            elif path == "/api/profile-promotion/regression-preview":
                self.json_or_error_response(PROFILE_PROMOTION.create_contract_regression_preview(body))
            elif len([segment for segment in path.split("/") if segment]) == 5:
                segments = [segment for segment in path.split("/") if segment]
                if segments[:3] == ["api", "source-import-guardrails", "requests"] and segments[4] == "decision":
                    self.json_or_error_response(SOURCE_IMPORT_GUARDRAILS.decide(segments[3], body))
                elif segments[:3] == ["api", "profile-promotion", "proposals"] and segments[4] == "decision":
                    self.json_or_error_response(PROFILE_PROMOTION.decide(segments[3], body))
                else:
                    self.json_response({"error": "not_found", "path": path}, status=404)
            elif path == "/api/dataset-packages/create":
                self.json_or_error_response(DATASET_PACKAGES.create_with_runner(body, run_profile))
            elif len([segment for segment in path.split("/") if segment]) == 4:
                segments = [segment for segment in path.split("/") if segment]
                if segments[:2] == ["api", "analysis-profiles"] and segments[3] == "plan":
                    self.json_or_error_response(plan_analysis_profile(segments[2], body))
                elif segments[:2] == ["api", "profile-runners"] and segments[3] == "run":
                    self.json_or_error_response(run_profile(segments[2], body))
                elif segments[:2] == ["api", "analysis-runs"] and segments[3] == "rerun":
                    self.json_or_error_response(rerun_analysis_run(segments[2]), default_status=202)
                elif segments[:2] == ["api", "scoring-rules"] and segments[3] == "audit":
                    self.json_or_error_response(SCORING_RULES.audit(
                        segments[2],
                        limit=parse_int(body.get("limit"), 50),
                        min_score=parse_int(body.get("min_score"), 0),
                        only_mismatches=boolish(body.get("only_mismatches", False)),
                    ))
                else:
                    self.json_response({"error": "not_found", "path": path}, status=404)
            elif path == "/api/portfolio-reports/from-run":
                self.json_or_error_response(generate_portfolio_report(body))
            elif path == "/api/export-bundles/profile-dashboard":
                self.json_or_error_response(PROFILE_EXPORT_BUNDLES.generate(body))
            elif path == "/api/portfolio-reports/from-profile-workspace":
                self.json_or_error_response(generate_profile_workspace_report(body))
            elif path == "/api/portfolio-reports/profile-comparison":
                self.json_or_error_response(generate_profile_comparison_report(body))
            elif path == "/api/portfolio-reports/compare":
                self.json_or_error_response(compare_portfolio_runs(body))
            elif path == "/api/jobs/safe-access-pilot":
                self.json_response(JOBS.start("safe_access_pilot", body, build_pilot_workspace), status=202)
            elif path.startswith("/api/"):
                self.json_response({"error": "not_found", "path": path}, status=404)
            else:
                self.json_response({"error": "not_found", "path": path}, status=404)
        except ApiBadRequest as exc:
            self.json_response({"error": "bad_request", "detail": str(exc)}, status=400)
        except Exception as exc:  # pragma: no cover - visible local error response
            if self.is_client_abort(exc):
                return
            LOGGER.exception("POST %s failed", path)
            self.json_response({"error": "server_error"}, status=500)

    def log_message(self, fmt: str, *args: object) -> None:
        LOGGER.info("%s - %s", self.address_string(), fmt % args)

    def json_response(self, data: object, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            if self.is_client_abort(exc):
                return
            raise

    def json_or_error_response(self, data: object, default_status: int = 200) -> None:
        self.json_response(data, status=status_for_error(data, default_status))

    def analysis_output_response(self, run_id: str, output_id: str) -> None:
        result = ANALYSIS_RUNS.output_file(run_id, output_id)
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if path.suffix == ".json":
            content_type = "application/json; charset=utf-8"
        elif path.suffix == ".csv":
            content_type = "text/csv; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def portfolio_report_response(self, report_id: str) -> None:
        result = PORTFOLIO_REPORTS.report_file(report_id, ".md")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def export_bundle_response(self, bundle_id: str) -> None:
        result = PROFILE_EXPORT_BUNDLES.bundle_file(bundle_id, ".md")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def dataset_package_response(self, package_id: str) -> None:
        result = DATASET_PACKAGES.output_file(package_id, "dataset_package_report")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def portfolio_evidence_bundle_response(self, bundle_id: str) -> None:
        result = PORTFOLIO_EVIDENCE_BUNDLE.output_file(bundle_id, "portfolio_evidence_bundle_report")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def bundle_review_checklist_response(self, checklist_id: str) -> None:
        result = BUNDLE_REVIEW_CHECKLIST.output_file(checklist_id, "bundle_review_checklist_report")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def portfolio_narrative_response(self, narrative_id: str) -> None:
        result = PORTFOLIO_NARRATIVE_EXPORT.output_file(narrative_id, "portfolio_narrative_report")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def portfolio_handoff_page_response(self, page_id: str) -> None:
        result = PORTFOLIO_HANDOFF_PAGE.output_file(page_id, "portfolio_handoff_page")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def portfolio_evidence_gallery_response(self, gallery_id: str) -> None:
        result = PORTFOLIO_EVIDENCE_GALLERY.output_file(gallery_id, "portfolio_evidence_gallery")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def multi_pilot_comparison_response(self, comparison_id: str) -> None:
        result = MULTI_PILOT_COMPARISON.output_file(comparison_id, "multi_pilot_comparison")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def source_import_guardrails_response(self, request_id: str) -> None:
        result = SOURCE_IMPORT_GUARDRAILS.output_file(request_id, "source_import_review")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def source_handoff_response(self, handoff_id: str) -> None:
        result = SOURCE_HANDOFF.output_file(handoff_id, "source_handoff")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def source_handoff_execution_response(self, execution_id: str) -> None:
        result = SOURCE_HANDOFF_EXECUTION.output_file(execution_id, "source_handoff_execution")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def execution_evidence_package_response(self, package_id: str) -> None:
        result = EXECUTION_EVIDENCE_PACKAGE.output_file(package_id, "execution_evidence_package")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def execution_result_diff_response(self, diff_id: str) -> None:
        result = EXECUTION_RESULT_DIFF.output_file(diff_id, "execution_result_diff")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def execution_diff_gallery_response(self, gallery_id: str) -> None:
        result = EXECUTION_DIFF_GALLERY.output_file(gallery_id, "execution_diff_gallery")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def execution_diff_detail_response(self, detail_id: str) -> None:
        result = EXECUTION_DIFF_DETAIL.output_file(detail_id, "execution_diff_detail")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def reviewer_audit_index_response(self, index_id: str) -> None:
        result = REVIEWER_AUDIT_INDEX.output_file(index_id, "reviewer_audit_index")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def portfolio_export_launcher_response(self, launcher_id: str) -> None:
        result = PORTFOLIO_EXPORT_LAUNCHER.output_file(launcher_id, "portfolio_export_launcher")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def portable_release_package_response(self, package_id: str) -> None:
        result = PORTABLE_RELEASE_PACKAGE.output_file(package_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def demo_script_pack_response(self, pack_id: str) -> None:
        result = DEMO_SCRIPT_PACK.output_file(pack_id, "demo_script")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def visual_qa_ledger_response(self, ledger_id: str) -> None:
        result = VISUAL_QA_LEDGER.output_file(ledger_id, "markdown")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def visual_baseline_comparison_response(self, comparison_id: str) -> None:
        result = VISUAL_BASELINE_COMPARISON.output_file(comparison_id, "markdown")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def visual_evidence_capture_response(self, capture_id: str) -> None:
        result = VISUAL_EVIDENCE_CAPTURE.output_file(capture_id, "contact_sheet")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def visual_evidence_review_diff_response(self, diff_id: str) -> None:
        result = VISUAL_EVIDENCE_REVIEW_DIFF.output_file(diff_id, "html")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def visual_evidence_review_annotations_response(self, annotation_id: str) -> None:
        result = VISUAL_EVIDENCE_REVIEW_ANNOTATIONS.output_file(annotation_id, "html")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def visual_evidence_signoff_packet_response(self, packet_id: str) -> None:
        result = VISUAL_EVIDENCE_SIGNOFF_PACKET.output_file(packet_id, "html")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def final_reviewer_launch_checklist_response(self, checklist_id: str) -> None:
        result = FINAL_REVIEWER_LAUNCH_CHECKLIST.output_file(checklist_id, "html")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def recruiter_demo_brief_response(self, brief_id: str) -> None:
        result = RECRUITER_DEMO_BRIEF.output_file(brief_id, "html")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def public_portfolio_package_response(self, package_id: str) -> None:
        result = PUBLIC_PORTFOLIO_PACKAGE.output_file(package_id, "html")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def demo_review_playbook_response(self, playbook_id: str) -> None:
        result = DEMO_REVIEW_PLAYBOOK.output_file(playbook_id, "html")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def github_publication_bundle_response(self, bundle_id: str) -> None:
        result = GITHUB_PUBLICATION_BUNDLE.output_file(bundle_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


    def demo_artifact_completeness_response(self, check_id: str) -> None:
        result = DEMO_ARTIFACT_COMPLETENESS.output_file(check_id, "markdown")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def repository_publication_qa_response(self, review_id: str) -> None:
        result = REPOSITORY_PUBLICATION_QA.output_file(review_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def repository_export_handoff_response(self, handoff_id: str) -> None:
        result = REPOSITORY_EXPORT_HANDOFF.output_file(handoff_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def repository_dry_run_review_response(self, review_id: str) -> None:
        result = REPOSITORY_DRY_RUN_REVIEW.output_file(review_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def repository_final_package_review_response(self, review_id: str) -> None:
        result = REPOSITORY_FINAL_PACKAGE_REVIEW.output_file(review_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def public_readme_cleanup_review_response(self, review_id: str) -> None:
        result = PUBLIC_README_CLEANUP_REVIEW.output_file(review_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def public_repository_polish_package_response(self, package_id: str) -> None:
        result = PUBLIC_REPOSITORY_POLISH_PACKAGE.output_file(package_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def repository_export_checklist_response(self, checklist_id: str) -> None:
        result = REPOSITORY_EXPORT_CHECKLIST.output_file(checklist_id, "zip")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def reproducibility_audit_packet_response(self, packet_id: str) -> None:
        result = REPRODUCIBILITY_AUDIT_PACKET.output_file(packet_id, "packet_summary")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def comparison_map_export_response(self, export_id: str) -> None:
        result = COMPARISON_MAP_EXPORTS.output_file(export_id, "comparison_map_export")
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def profile_output_response(self, workspace_id: str, output_id: str) -> None:
        result = profile_workspace_output_file(workspace_id, output_id)
        if "error" in result:
            self.json_or_error_response(result)
            return
        path = result["path"]
        content = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if path.suffix == ".json":
            content_type = "application/json; charset=utf-8"
        elif path.suffix == ".csv":
            content_type = "text/csv; charset=utf-8"
        elif path.suffix == ".md":
            content_type = "text/markdown; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def read_json_body(self) -> dict:
        length = parse_int(self.headers.get("Content-Length"), 0)
        if length <= 0:
            return {}
        if length > MAX_REQUEST_BODY_BYTES:
            raise ApiBadRequest(f"request body too large (limit {MAX_REQUEST_BODY_BYTES} bytes)")
        body = self.rfile.read(length).decode("utf-8")
        if not body.strip():
            return {}
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ApiBadRequest(f"invalid JSON body at character {exc.pos}") from exc
        return parsed if isinstance(parsed, dict) else {}

    def static_response(self, path: str) -> None:
        if path in {"", "/"}:
            rel = "index.html"
        else:
            rel = path.lstrip("/")
        target = (STATIC_DIR / rel).resolve()
        if not is_within(target, STATIC_DIR) or not target.exists() or target.is_dir():
            self.json_response({"error": "static_not_found"}, status=404)
            return
        content = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif target.suffix in {".html", ".css"}:
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("GEOREVIEW_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    host = os.environ.get("GEOREVIEW_HOST", "127.0.0.1")
    port = parse_int(os.environ.get("GEOREVIEW_PORT"), 8847)
    server = ThreadingHTTPServer((host, port), Handler)
    LOGGER.info("GeoReview Studio %s running at http://%s:%d", APP_VERSION, host, port)
    LOGGER.info("Workspace: %s | data root: %s", WORKSPACE_ID, MAPS_ROOT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down (keyboard interrupt)")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
