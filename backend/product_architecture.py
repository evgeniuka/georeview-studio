from __future__ import annotations

from typing import Callable


PRODUCT_ARCHITECTURE_VERSION = "product_architecture_v001"


class ProductArchitecture:
    def __init__(self, profiles: object, onboarding: object, manifest_reader: Callable[[], dict]) -> None:
        self.profiles = profiles
        self.onboarding = onboarding
        self.manifest_reader = manifest_reader

    def blueprint(self) -> dict:
        manifest = self.safe_manifest()
        profile_payload = self.safe_profiles()
        source_status = self.safe_source_status()
        profiles = profile_payload.get("profiles", [])
        implemented_profiles = [item for item in profiles if item.get("status") == "implemented"]
        runnable_profiles = [item for item in profiles if item.get("can_run") is True]
        return {
            "ok": True,
            "product_architecture_version": PRODUCT_ARCHITECTURE_VERSION,
            "product_name": "GeoReview Studio",
            "recommended_variant_id": "universal_gis_review_studio",
            "positioning": "Local-first GIS review workbench for infrastructure risk indicators, data-quality evidence, and portfolio-grade reproducible analysis.",
            "current_version": manifest.get("version"),
            "current_evidence": {
                "source_count": source_status.get("source_count", 0),
                "analysis_profile_count": len(profiles),
                "implemented_profile_count": len(implemented_profiles),
                "runnable_profile_count": len(runnable_profiles),
                "implemented_profiles": [item.get("profile_id") for item in implemented_profiles],
                "default_pilot": "Kfar Saba",
                "default_dataset_id": profile_payload.get("dataset_id"),
            },
            "top_project_variants": self.variant_rows(),
            "architecture_layers": self.architecture_layers(),
            "canonical_pipeline": self.pipeline(),
            "dashboard_modules": self.dashboard_modules(),
            "canonical_tables": self.canonical_tables(),
            "upload_and_ingestion_strategy": self.upload_strategy(),
            "roadmap": self.roadmap_rows(),
            "claim_boundaries": self.claim_boundaries(),
            "best_next_development_step": "Review the v083 Figma-aligned dashboard in a browser, then capture updated portfolio screenshots before public repository export.",
            "approved_review_wording": "This location has infrastructure risk indicators and should be reviewed on-site.",
            "source_gis_modified": False,
        }

    def variants(self) -> dict:
        return {
            "ok": True,
            "product_architecture_version": PRODUCT_ARCHITECTURE_VERSION,
            "recommended_variant_id": "universal_gis_review_studio",
            "variants": self.variant_rows(),
            "source_gis_modified": False,
        }

    def roadmap(self) -> dict:
        return {
            "ok": True,
            "product_architecture_version": PRODUCT_ARCHITECTURE_VERSION,
            "roadmap": self.roadmap_rows(),
            "validation_gates": [
                "source GIS files remain read-only",
                "every profile separates infrastructure indicators from data-quality flags",
                "distance calculations use a projected CRS for metric analysis",
                "generated reports include source evidence and approved review wording",
                "API contract tests cover every public endpoint",
            ],
            "source_gis_modified": False,
        }

    def implementation_plan(self, body: dict | None = None) -> dict:
        body = body or {}
        target_version = str(body.get("target_version") or "v083")
        focus = str(body.get("focus") or "figma_aligned_dashboard_polish")
        return {
            "ok": True,
            "product_architecture_version": PRODUCT_ARCHITECTURE_VERSION,
            "target_version": target_version,
            "focus": focus,
            "milestones": [
                {"step": "first_screen_reframe", "output": "Place overview metrics, map and review queue before advanced operations.", "validation": "Initial viewport shows actual GIS review surfaces."},
                {"step": "control_hierarchy", "output": "Keep primary workflow visible and hide advanced evidence operations behind an explicit toggle.", "validation": "Control sidebar stays scannable on desktop and mobile."},
                {"step": "responsive_polish", "output": "Improve spacing, wrapping, palette and map framing.", "validation": "Buttons and text fit without overlapping."},
                {"step": "release_gate", "output": "Update release metadata, roadmap and tests for v083.", "validation": "Frontend syntax and API contract remain stable."},
            ],
            "source_gis_modified": False,
        }

    def variant_rows(self) -> list[dict]:
        return [
            {
                "variant_id": "universal_gis_review_studio",
                "name": "GeoReview Studio: Universal OSM/GIS Review Workbench",
                "portfolio_strength": "strongest",
                "why": "Shows data engineering, GIS inspection, reusable profile architecture, API design, dashboards, validation and reports.",
                "current_fit": "best continuation of the existing source onboarding, profile registry, runners and portfolio reports.",
                "mvp_scope": ["local GIS source scan", "profile readiness", "three implemented Kfar Saba profiles", "dashboard", "Markdown/JSON reports"],
            },
            {
                "variant_id": "safe_access_israel",
                "name": "Safe Access Israel: Pedestrian Infrastructure Review",
                "portfolio_strength": "high domain clarity",
                "why": "Easy to explain through schools, bus stops, crossings, roads and field-review prioritization.",
                "current_fit": "best first profile and strongest domain story.",
                "mvp_scope": ["Kfar Saba pilot", "nearest crossing metrics", "major-road proximity", "risk indicators", "field-review export"],
            },
            {
                "variant_id": "open_mobility_evidence_lab",
                "name": "Open Mobility Evidence Lab",
                "portfolio_strength": "broad civic-tech path",
                "why": "Can grow into transit, cycling, micromobility and public-space access evidence.",
                "current_fit": "good expansion theme after the universal workbench contract is stable.",
                "mvp_scope": ["profile comparison", "multi-profile evidence", "data-quality dashboards", "portfolio case studies"],
            },
        ]

    def architecture_layers(self) -> list[dict]:
        return [
            {"layer": "source_onboarding", "status": "implemented", "responsibility": "scan local GIS files read-only and profile source readiness"},
            {"layer": "layer_profiler", "status": "implemented", "responsibility": "summarize layers, schemas, CRS, counts and important OSM tag evidence"},
            {"layer": "canonical_normalizer", "status": "implemented_for_safe_access", "responsibility": "map source layers into canonical review tables"},
            {"layer": "profile_registry", "status": "implemented", "responsibility": "publish profile metadata, input needs, readiness and runner status"},
            {"layer": "profile_runners", "status": "implemented_for_three_profiles", "responsibility": "generate Safe Access, Transit and Park profile workspaces"},
            {"layer": "scoring_rule_registry", "status": "implemented", "responsibility": "publish versioned JSON scoring rules and audit actual profile scores"},
            {"layer": "run_registry", "status": "implemented", "responsibility": "track jobs, reruns, active workspaces and output files"},
            {"layer": "dashboard_api", "status": "implemented_for_local_app", "responsibility": "serve metrics, candidates, map features and profile outputs"},
            {"layer": "report_builder", "status": "implemented", "responsibility": "write Markdown and JSON evidence reports"},
            {"layer": "local_intake", "status": "implemented_metadata_only", "responsibility": "review selected local GIS files and folders and write only small intake plans"},
            {"layer": "source_import_guardrails", "status": "implemented_review_gate", "responsibility": "turn local intake previews into approval-gated metadata-only import review packets"},
            {"layer": "source_handoff", "status": "implemented_planned_handoff", "responsibility": "connect approved source import decisions to mapper plans, contract dry-runs and planned queue jobs"},
            {"layer": "source_handoff_execution", "status": "implemented_controlled_execution", "responsibility": "execute approved handoffs explicitly and compare generated workspace outputs to handoff evidence"},
            {"layer": "execution_evidence_package", "status": "implemented_reviewer_package", "responsibility": "package verified handoff execution lineage, outputs and release evidence for reviewer handoff"},
            {"layer": "execution_result_diff", "status": "implemented_reproducibility_diff", "responsibility": "compare reviewer-ready execution packages for repeat-run and cross-scope review"},
            {"layer": "execution_diff_gallery", "status": "implemented_reviewer_gallery", "responsibility": "index execution result diffs into classification, scope and review-priority evidence"},
            {"layer": "execution_diff_detail", "status": "implemented_baseline_drilldown", "responsibility": "select reproducibility baselines and inspect table-level diff evidence"},
            {"layer": "reproducibility_audit_packet", "status": "implemented_packet_layer", "responsibility": "bundle diff detail, result diff, gallery and validation evidence into one reviewer packet"},
            {"layer": "reviewer_audit_index", "status": "implemented_reviewer_index", "responsibility": "index audit packets and portfolio handoff evidence for reviewer navigation"},
            {"layer": "portfolio_export_launcher", "status": "implemented_start_here_launcher", "responsibility": "open the best reviewer index, audit packet and portfolio artifacts from one local entrypoint"},
            {"layer": "portable_release_package", "status": "implemented_portable_package", "responsibility": "package launcher and reviewer evidence into a small local ZIP without source GIS data"},
            {"layer": "demo_script_pack", "status": "implemented_walkthrough_pack", "responsibility": "turn release evidence into a repeatable portfolio walkthrough and screenshot smoke plan"},
            {"layer": "visual_qa_snapshot_ledger", "status": "implemented_visual_qa_tracking", "responsibility": "track manual screenshot capture status, observations and follow-up notes across releases"},
            {"layer": "visual_baseline_comparison_manifest", "status": "implemented_baseline_comparison", "responsibility": "compare visual QA ledgers and identify demo target deltas across releases"},
            {"layer": "demo_artifact_completeness_validator", "status": "implemented_completeness_gate", "responsibility": "verify required demo, package, QA and comparison artifacts before sharing"},
            {"layer": "automated_visual_evidence_capture", "status": "implemented_browser_capture", "responsibility": "capture browser screenshots for Visual QA ledger targets and package contact sheets"},
            {"layer": "visual_evidence_review_diff", "status": "implemented_review_diff", "responsibility": "compare captured screenshot sets and flag target-level visual changes"},
            {"layer": "visual_evidence_review_annotations", "status": "implemented_annotation_review", "responsibility": "record reviewer decisions and notes for visual evidence diff targets"},
            {"layer": "visual_evidence_signoff_packet", "status": "implemented_signoff_packet", "responsibility": "package annotations with validation and API evidence for final local portfolio sign-off"},
            {"layer": "final_reviewer_launch_checklist", "status": "implemented_final_launch_checklist", "responsibility": "turn sign-off packets into compact launch steps and must-say reviewer notes"},
            {"layer": "recruiter_demo_brief", "status": "implemented_recruiter_brief", "responsibility": "turn launch checklists into a one-page portfolio story and evidence brief"},
            {"layer": "public_portfolio_package", "status": "implemented_public_package", "responsibility": "turn recruiter briefs into public README, interview walkthrough and architecture package artifacts"},
            {"layer": "demo_review_playbook", "status": "implemented_demo_review_flow", "responsibility": "turn public packages into final demo agendas, sharing checklists and reviewer question prep"},
            {"layer": "github_publication_bundle", "status": "implemented_publication_bundle", "responsibility": "turn demo review playbooks into GitHub-ready README, case study, repository manifest and ZIP artifacts"},
            {"layer": "repository_publication_qa", "status": "implemented_repository_publication_qa", "responsibility": "verify GitHub-ready bundle contents, claim boundaries, source GIS exclusion and public sharing walkthrough evidence"},
            {"layer": "repository_export_handoff", "status": "implemented_repository_export_handoff", "responsibility": "turn repository QA reviews into include/exclude file plans, screenshot references, license decisions and handoff ZIP artifacts"},
            {"layer": "repository_dry_run_review", "status": "implemented_repository_dry_run_review", "responsibility": "simulate public repository archive contents, hard-exclude source GIS, and package final sharing checklist evidence"},
            {"layer": "repository_final_package_review", "status": "implemented_repository_final_package_review", "responsibility": "verify repository-relative paths, redacted local path evidence, source GIS exclusion and final public package instructions"},
            {"layer": "public_readme_cleanup_review", "status": "implemented_public_readme_cleanup_review", "responsibility": "prepare public README path cleanup evidence and repository-relative screenshot checklist"},
            {"layer": "postgis_runtime", "status": "implemented_planning_option", "responsibility": "publish schema, readiness, row estimates and migration phases for larger-region storage"},
            {"layer": "profile_mapper_sdk", "status": "implemented_contract_planning_layer", "responsibility": "define reusable profile contracts, source compatibility checks and mapper plans"},
            {"layer": "contract_execution_adapter", "status": "implemented_dry_run_layer", "responsibility": "bind validated profile contracts to existing or planned backend runners without mutating source GIS"},
            {"layer": "osm_tag_quality_runner", "status": "implemented_read_only_profile", "responsibility": "turn inspected OSM tag audit CSV files into profile workspace tables and reports"},
            {"layer": "template_authoring_wizard", "status": "implemented_draft_only", "responsibility": "create reviewed profile contract drafts without mutating source GIS or mapper config"},
            {"layer": "controlled_execution_queue", "status": "implemented_local_queue", "responsibility": "execute allowlisted validated profile contracts and persist queue job records"},
            {"layer": "dataset_package_builder", "status": "implemented_evidence_package", "responsibility": "package source readiness, intake, template draft and queue evidence for reuse"},
            {"layer": "authored_profile_runner", "status": "implemented_read_only_draft_runner", "responsibility": "execute authored drafts as tag and layer evidence audits through the controlled queue"},
            {"layer": "authored_dashboard_contract", "status": "implemented_dynamic_profile_dashboard", "responsibility": "normalize authored audit workspaces into the shared profile dashboard and portfolio export contract"},
            {"layer": "profile_promotion_wizard", "status": "implemented_proposal_only", "responsibility": "turn successful authored audits into manual-review profile contract proposals without mutating config"},
            {"layer": "proposal_acceptance_workflow", "status": "implemented_decision_ledger", "responsibility": "record approve/reject decisions for promotion proposals without applying config changes"},
            {"layer": "profile_contract_diff_review", "status": "implemented_review_artifact", "responsibility": "compare current and proposed mapper contracts before any explicit config-change task"},
            {"layer": "accepted_contract_application_plan", "status": "implemented_planning_only", "responsibility": "generate guarded application plans and patch previews for approved profile proposals without mutating config"},
            {"layer": "guarded_config_apply_proposal", "status": "implemented_proposal_only", "responsibility": "generate approval-gated proposed mapper config previews without mutating config"},
            {"layer": "profile_contract_regression_preview", "status": "implemented_preview_only", "responsibility": "validate proposed mapper config previews against contract invariants before any real config mutation"},
            {"layer": "release_readiness_dashboard", "status": "implemented_evidence_dashboard", "responsibility": "summarize release gates, validation state, API coverage and demo readiness without mutating source GIS"},
            {"layer": "guided_portfolio_demo", "status": "implemented_demo_layer", "responsibility": "turn data, profiles, reports and readiness gates into a guided portfolio walkthrough"},
            {"layer": "shareable_portfolio_evidence_bundle", "status": "implemented_bundle_layer", "responsibility": "package generated demo, readiness, validation, reports and sample outputs for portfolio review"},
            {"layer": "bundle_review_checklist", "status": "implemented_review_gate_layer", "responsibility": "turn evidence bundles into guided review checks and remediation actions before sharing"},
            {"layer": "portfolio_narrative_export", "status": "implemented_narrative_layer", "responsibility": "turn checked evidence bundles into reviewer-facing case study and talk-track artifacts"},
            {"layer": "portfolio_handoff_page", "status": "implemented_handoff_layer", "responsibility": "render reviewer-facing narrative evidence as a compact standalone HTML page"},
            {"layer": "portfolio_evidence_gallery", "status": "implemented_gallery_layer", "responsibility": "index handoff pages, narratives, bundles and reports into one standalone local gallery"},
            {"layer": "multi_pilot_comparison", "status": "implemented_comparison_layer", "responsibility": "compare route-aware pilot workspaces with the same Safe Access contract"},
            {"layer": "comparison_map_exports", "status": "implemented_map_export_layer", "responsibility": "render pilot comparison workspaces into portable SVG, HTML and CSV map evidence"},
        ]

    def pipeline(self) -> list[dict]:
        return [
            {"stage": 1, "name": "local_source_scan", "input": "maps folder", "output": "source catalog", "status": "implemented"},
            {"stage": 2, "name": "source_profile", "input": "GIS files", "output": "layer and tag evidence", "status": "implemented"},
            {"stage": 3, "name": "source_import_guardrails", "input": "local intake preview", "output": "manual review packet and approval decision", "status": "implemented_review_gate"},
            {"stage": 4, "name": "source_handoff", "input": "approved source import decision", "output": "mapper plan, dry-run and planned queue job", "status": "implemented_planned_handoff"},
            {"stage": 5, "name": "source_handoff_execution", "input": "ready source handoff", "output": "executed queue job and workspace comparison evidence", "status": "implemented_controlled_execution"},
            {"stage": 6, "name": "execution_evidence_package", "input": "verified handoff execution", "output": "reviewer-ready execution evidence package", "status": "implemented_reviewer_package"},
            {"stage": 7, "name": "execution_result_diff", "input": "two reviewer-ready execution evidence packages", "output": "diff JSON and Markdown evidence", "status": "implemented_reproducibility_diff"},
            {"stage": 8, "name": "execution_diff_gallery", "input": "execution result diff artifacts", "output": "reviewer-facing diff gallery JSON and Markdown", "status": "implemented_reviewer_gallery"},
            {"stage": 9, "name": "execution_diff_detail", "input": "selected execution diff and baseline candidate", "output": "table/output/quality drilldown JSON and Markdown", "status": "implemented_baseline_drilldown"},
            {"stage": 10, "name": "reproducibility_audit_packet", "input": "ready drilldown, result diff and gallery evidence", "output": "packet manifest and Markdown audit summary", "status": "implemented_packet_layer"},
            {"stage": 11, "name": "reviewer_audit_index", "input": "ready audit packets and portfolio artifacts", "output": "reviewer index JSON, Markdown and HTML", "status": "implemented_reviewer_index"},
            {"stage": 12, "name": "portfolio_export_launcher", "input": "reviewer index, audit packets and portfolio artifacts", "output": "start-here launcher JSON, Markdown and HTML", "status": "implemented_start_here_launcher"},
            {"stage": 13, "name": "portable_release_package", "input": "ready launcher and selected reviewer evidence", "output": "portable ZIP, package manifest and package README", "status": "implemented_portable_package"},
            {"stage": 14, "name": "demo_script_pack", "input": "portable release package and app smoke targets", "output": "demo script, screenshot smoke plan and contact sheet", "status": "implemented_walkthrough_pack"},
            {"stage": 15, "name": "visual_qa_snapshot_ledger", "input": "demo script pack screenshot targets", "output": "visual QA ledger JSON, Markdown and HTML contact sheet", "status": "implemented_visual_qa_tracking"},
            {"stage": 16, "name": "visual_baseline_comparison_manifest", "input": "two visual QA ledgers", "output": "target delta manifest and Markdown reviewer summary", "status": "implemented_baseline_comparison"},
            {"stage": 17, "name": "demo_artifact_completeness_validator", "input": "release summaries and generated reviewer artifacts", "output": "completeness manifest and Markdown reviewer report", "status": "implemented_completeness_gate"},
            {"stage": 18, "name": "automated_visual_evidence_capture", "input": "Visual QA ledger targets and local browser runtime", "output": "PNG screenshots, contact sheet and capture manifest", "status": "implemented_browser_capture"},
            {"stage": 19, "name": "visual_evidence_review_diff", "input": "Two ready visual evidence capture sets", "output": "screenshot hash diff, side-by-side HTML review and manifest", "status": "implemented_review_diff"},
            {"stage": 20, "name": "visual_evidence_review_annotations", "input": "Ready visual evidence review diff", "output": "target-level annotation manifest, Markdown and HTML", "status": "implemented_annotation_review"},
            {"stage": 21, "name": "visual_evidence_signoff_packet", "input": "Ready visual evidence annotations plus validation and API evidence", "output": "sign-off packet JSON, Markdown and HTML", "status": "implemented_signoff_packet"},
            {"stage": 22, "name": "final_reviewer_launch_checklist", "input": "Ready sign-off packet plus validation and API evidence", "output": "final launch checklist JSON, Markdown and HTML", "status": "implemented_final_launch_checklist"},
            {"stage": 23, "name": "recruiter_demo_brief", "input": "Ready final launch checklist plus validation and API evidence", "output": "recruiter-facing brief JSON, Markdown and HTML", "status": "implemented_recruiter_brief"},
            {"stage": 24, "name": "public_portfolio_package", "input": "Ready recruiter demo brief plus validation and API evidence", "output": "public README, interview walkthrough, HTML and manifest", "status": "implemented_public_package"},
            {"stage": 25, "name": "demo_review_playbook", "input": "Ready public portfolio package plus validation and API evidence", "output": "demo agenda, final sharing checklist, HTML and manifest", "status": "implemented_demo_review_flow"},
            {"stage": 26, "name": "github_publication_bundle", "input": "Ready demo review playbook plus validation and API evidence", "output": "README export, case study, repository manifest, HTML and ZIP", "status": "implemented_publication_bundle"},
            {"stage": 27, "name": "repository_publication_qa", "input": "Ready GitHub publication bundle plus validation and API evidence", "output": "repository QA manifest, checklist, sharing walkthrough, HTML and ZIP", "status": "implemented_repository_publication_qa"},
            {"stage": 28, "name": "repository_export_handoff", "input": "Ready repository publication QA plus validation and API evidence", "output": "repository export handoff, file plan, screenshot/license checklist, HTML and ZIP", "status": "implemented_repository_export_handoff"},
            {"stage": 29, "name": "repository_dry_run_review", "input": "Ready repository export handoff plus validation and API evidence", "output": "repository dry-run review, archive preview, final public sharing checklist, HTML and ZIP", "status": "implemented_repository_dry_run_review"},
            {"stage": 30, "name": "repository_final_package_review", "input": "Ready repository dry-run review plus validation and API evidence", "output": "final package review, redacted path evidence, publication checklist, HTML and ZIP", "status": "implemented_repository_final_package_review"},
            {"stage": 31, "name": "public_readme_cleanup_review", "input": "Ready final package review plus validation and API evidence", "output": "public README draft, path cleanup checks, screenshot checklist, HTML and ZIP", "status": "implemented_public_readme_cleanup_review"},
            {"stage": 4, "name": "pilot_preflight", "input": "dataset and pilot polygon", "output": "run readiness", "status": "implemented"},
            {"stage": 4, "name": "canonical_workspace", "input": "source layers", "output": "normalized CSV/JSON workspace", "status": "implemented_for_safe_access"},
            {"stage": 5, "name": "profile_runner", "input": "workspace and profile_id", "output": "profile result table", "status": "implemented_for_three_profiles"},
            {"stage": 6, "name": "dashboard", "input": "workspace outputs", "output": "local review UI", "status": "implemented"},
            {"stage": 7, "name": "portfolio_report", "input": "run/profile evidence", "output": "Markdown/JSON report", "status": "implemented"},
            {"stage": 8, "name": "export_bundle", "input": "profile dashboard evidence", "output": "profile dashboard Markdown/JSON bundle", "status": "implemented"},
            {"stage": 9, "name": "score_audit", "input": "profile rows and scoring rules JSON", "output": "expected-vs-actual score audit", "status": "implemented"},
            {"stage": 10, "name": "postgis_backend_plan", "input": "canonical tables and schema SQL", "output": "larger-region database migration plan", "status": "implemented_planning_option"},
            {"stage": 11, "name": "profile_mapper_contract", "input": "profile contract JSON and source evidence", "output": "compatibility checks and mapper plan", "status": "implemented_contract_planning_layer"},
            {"stage": 12, "name": "contract_execution_dry_run", "input": "mapper contract, source compatibility and adapter matrix", "output": "dry-run execution evidence", "status": "implemented_dry_run_layer"},
            {"stage": 13, "name": "osm_tag_quality_profile", "input": "osm_tag_counts.csv and layer_summary.csv", "output": "tag quality workspace", "status": "implemented_read_only_profile"},
            {"stage": 14, "name": "template_authoring", "input": "profile blueprint and source readiness", "output": "draft profile mapper contract", "status": "implemented_draft_only"},
            {"stage": 15, "name": "controlled_execution_queue", "input": "contract dry-run and allowlisted runner", "output": "execution queue job record", "status": "implemented_local_queue"},
            {"stage": 16, "name": "dataset_evidence_package", "input": "source readiness, intake plan, template draft and queue job", "output": "portable dataset package", "status": "implemented_evidence_package"},
            {"stage": 17, "name": "authored_profile_runner", "input": "template draft and inspected audit CSVs", "output": "authored profile audit workspace", "status": "implemented_read_only_draft_runner"},
            {"stage": 18, "name": "authored_dashboard_contract", "input": "authored profile audit workspace", "output": "normalized profile dashboard rows and portfolio reports", "status": "implemented_dynamic_profile_dashboard"},
            {"stage": 19, "name": "profile_promotion", "input": "authored profile audit workspace", "output": "reviewable profile contract proposal", "status": "implemented_proposal_only"},
            {"stage": 20, "name": "proposal_acceptance", "input": "promotion proposal", "output": "manual approve/reject decision record", "status": "implemented_decision_ledger"},
            {"stage": 21, "name": "contract_diff_review", "input": "promotion proposal and current mapper config", "output": "categorized profile contract diff artifact", "status": "implemented_review_artifact"},
            {"stage": 22, "name": "application_plan", "input": "approved promotion decision", "output": "guarded config application plan", "status": "implemented_planning_only"},
            {"stage": 23, "name": "guarded_config_apply_proposal", "input": "application plan and contract diff", "output": "proposed mapper config preview and approval checklist", "status": "implemented_proposal_only"},
            {"stage": 24, "name": "profile_contract_regression_preview", "input": "guarded apply proposal and proposed config preview", "output": "contract regression gate report", "status": "implemented_preview_only"},
            {"stage": 25, "name": "release_readiness_dashboard", "input": "release gates, validation summaries and lifecycle evidence", "output": "portfolio demo readiness report", "status": "implemented_evidence_dashboard"},
            {"stage": 26, "name": "guided_portfolio_demo", "input": "architecture, source evidence, profile outputs, reports and readiness", "output": "ordered demo walkthrough and snapshot", "status": "implemented_demo_layer"},
            {"stage": 27, "name": "shareable_portfolio_evidence_bundle", "input": "guided demo, readiness, validation, reports and sample outputs", "output": "shareable evidence bundle", "status": "implemented_bundle_layer"},
            {"stage": 28, "name": "bundle_review_checklist", "input": "shareable evidence bundle", "output": "checklist report and remediation actions", "status": "implemented_review_gate_layer"},
            {"stage": 29, "name": "portfolio_narrative_export", "input": "ready checklist and evidence bundle", "output": "reviewer-facing case study Markdown/JSON", "status": "implemented_narrative_layer"},
            {"stage": 30, "name": "portfolio_handoff_page", "input": "ready narrative export", "output": "standalone local HTML handoff page", "status": "implemented_handoff_layer"},
            {"stage": 31, "name": "portfolio_evidence_gallery", "input": "handoff pages, narratives, bundles and reports", "output": "standalone local HTML evidence gallery", "status": "implemented_gallery_layer"},
            {"stage": 32, "name": "multi_pilot_comparison", "input": "route-aware pilot workspaces", "output": "JSON, Markdown and HTML comparison evidence", "status": "implemented_comparison_layer"},
            {"stage": 33, "name": "comparison_map_exports", "input": "network access, crossings and roads tables", "output": "portable SVG, HTML and CSV map evidence", "status": "implemented_map_export_layer"},
        ]

    def dashboard_modules(self) -> list[dict]:
        return [
            {"module": "source_onboarding", "purpose": "source readiness and blocker review"},
            {"module": "local_intake", "purpose": "review a selected local path and create a metadata intake plan"},
            {"module": "source_import_guardrails", "purpose": "create and approve metadata-only source import review packets"},
            {"module": "source_handoff", "purpose": "turn approved source imports into mapper plans, dry-runs and planned queue jobs"},
            {"module": "source_handoff_execution", "purpose": "execute approved handoffs and compare workspace outputs to handoff evidence"},
            {"module": "execution_evidence_package", "purpose": "package verified execution lineage, workspace outputs and release evidence for reviewer handoff"},
            {"module": "execution_result_diff", "purpose": "compare execution packages by lineage, output rows, quality checks and API evidence"},
            {"module": "execution_diff_gallery", "purpose": "scan execution diffs by classification, scope, readiness and review priority"},
            {"module": "execution_diff_detail", "purpose": "select a reproducibility baseline and inspect table/output/quality details"},
            {"module": "reproducibility_audit_packet", "purpose": "create one reviewer packet from diff detail, diff gallery and release evidence"},
            {"module": "reviewer_audit_index", "purpose": "index packets and portfolio evidence links for reviewer navigation"},
            {"module": "portfolio_export_launcher", "purpose": "open the best reviewer artifacts from one start-here panel"},
            {"module": "portable_release_package", "purpose": "create a small reviewer ZIP from launcher and evidence artifacts"},
            {"module": "demo_script_pack", "purpose": "create a repeatable demo talk track and screenshot smoke checklist"},
            {"module": "visual_qa_snapshot_ledger", "purpose": "track screenshot capture status, observations and review follow-ups"},
            {"module": "visual_baseline_comparison_manifest", "purpose": "compare QA ledgers and highlight release-to-release demo target changes"},
            {"module": "demo_artifact_completeness_validator", "purpose": "verify required demo artifacts before local portfolio sharing"},
            {"module": "automated_visual_evidence_capture", "purpose": "capture browser screenshots for visual QA targets"},
            {"module": "visual_evidence_review_diff", "purpose": "compare screenshot evidence sets for reviewer visual QA"},
            {"module": "visual_evidence_review_annotations", "purpose": "record reviewer decisions and notes for visual diff targets"},
            {"module": "visual_evidence_signoff_packet", "purpose": "package visual annotations with validation and API evidence for final reviewer sign-off"},
            {"module": "final_reviewer_launch_checklist", "purpose": "create launch steps, must-say lines and evidence links from sign-off packets"},
            {"module": "recruiter_demo_brief", "purpose": "create a one-page project story, proof points and claim boundaries for portfolio review"},
            {"module": "public_portfolio_package", "purpose": "create public README, interview walkthrough and architecture explanation package"},
            {"module": "demo_review_playbook", "purpose": "create final demo agenda, sharing checklist and reviewer question prep"},
            {"module": "github_publication_bundle", "purpose": "create GitHub-ready README export, case study, repository manifest and ZIP"},
            {"module": "analysis_profiles", "purpose": "profile capability and readiness review"},
            {"module": "profile_runners", "purpose": "run implemented secondary profiles"},
            {"module": "scoring_rules", "purpose": "inspect scoring rules and verify actual profile scores"},
            {"module": "postgis_backend", "purpose": "review larger-region schema readiness and migration phases"},
            {"module": "profile_mapper_sdk", "purpose": "review reusable profile contracts and mapper compatibility"},
            {"module": "contract_execution", "purpose": "dry-run profile contract execution and runner binding evidence"},
            {"module": "osm_tag_quality", "purpose": "review tag coverage, simplified-schema gaps and PBF enrichment evidence"},
            {"module": "template_authoring", "purpose": "draft new GIS review profile contracts from controlled blueprints"},
            {"module": "execution_queue", "purpose": "enqueue and inspect controlled local profile contract executions"},
            {"module": "dataset_packages", "purpose": "create reusable evidence packages for selected datasets"},
            {"module": "authored_profile_runner", "purpose": "run authored draft profiles as read-only evidence audits"},
            {"module": "authored_profile_dashboard", "purpose": "review authored audit results through the same normalized dashboard contract"},
            {"module": "profile_promotion", "purpose": "create manual-review contract proposals from successful authored audits"},
            {"module": "proposal_acceptance", "purpose": "record approve/reject review decisions without applying config changes"},
            {"module": "profile_contract_diff_review", "purpose": "review added, removed, changed and unchanged profile contract fields"},
            {"module": "application_plan", "purpose": "generate guarded config patch previews for accepted promotion proposals"},
            {"module": "guarded_config_apply_proposal", "purpose": "review proposed mapper config previews and hash gates before explicit config change"},
            {"module": "profile_contract_regression_preview", "purpose": "check proposed mapper config contract invariants before any real config mutation"},
            {"module": "release_readiness", "purpose": "summarize gates for local portfolio demo readiness"},
            {"module": "portfolio_demo", "purpose": "guide an 8-minute portfolio walkthrough over the available evidence"},
            {"module": "portfolio_evidence_bundle", "purpose": "create a shareable review bundle from generated evidence artifacts"},
            {"module": "bundle_review_checklist", "purpose": "review bundle completeness and remediation actions before sharing"},
            {"module": "portfolio_narrative_export", "purpose": "generate a compact reviewer-facing portfolio narrative from checked evidence"},
            {"module": "portfolio_handoff_page", "purpose": "render the portfolio narrative as a standalone local HTML page"},
            {"module": "portfolio_evidence_gallery", "purpose": "index portfolio artifacts into one reviewer-facing local gallery"},
            {"module": "multi_pilot_comparison", "purpose": "compare Kfar Saba and Raanana route-aware Safe Access workspaces"},
            {"module": "comparison_map_exports", "purpose": "create side-by-side map exports from route-aware comparison workspaces"},
            {"module": "map_and_candidates", "purpose": "review mapped infrastructure indicators"},
            {"module": "portfolio_reports", "purpose": "generate evidence packages"},
            {"module": "product_architecture", "purpose": "show product variants, pipeline and roadmap"},
        ]

    def canonical_tables(self) -> list[dict]:
        return [
            {"table": "source_datasets", "geometry": "none", "status": "implemented as catalog/onboarding metadata"},
            {"table": "dataset_layers", "geometry": "none", "status": "implemented as layer summary"},
            {"table": "source_import_reviews", "geometry": "none", "status": "implemented as guardrail review artifacts under analysis_output"},
            {"table": "source_import_decisions", "geometry": "none", "status": "implemented as manual approval ledger artifacts under analysis_output"},
            {"table": "source_handoffs", "geometry": "none", "status": "implemented as planned handoff artifacts under analysis_output"},
            {"table": "source_handoff_executions", "geometry": "none", "status": "implemented as controlled execution comparison artifacts under analysis_output"},
            {"table": "execution_evidence_packages", "geometry": "none", "status": "implemented as reviewer-ready execution evidence artifacts under analysis_output"},
            {"table": "execution_result_diffs", "geometry": "none", "status": "implemented as reproducibility diff artifacts under analysis_output"},
            {"table": "execution_diff_galleries", "geometry": "none", "status": "implemented as reviewer-facing diff gallery artifacts under analysis_output"},
            {"table": "execution_diff_details", "geometry": "none", "status": "implemented as baseline drilldown artifacts under analysis_output"},
            {"table": "reproducibility_audit_packets", "geometry": "none", "status": "implemented as packet manifests under analysis_output"},
            {"table": "reviewer_audit_indexes", "geometry": "none", "status": "implemented as reviewer index artifacts under analysis_output"},
            {"table": "portfolio_export_launchers", "geometry": "none", "status": "implemented as start-here launcher artifacts under analysis_output"},
            {"table": "portable_release_packages", "geometry": "none", "status": "implemented as ZIP package manifests under analysis_output"},
            {"table": "demo_script_packs", "geometry": "none", "status": "implemented as walkthrough manifests under analysis_output"},
            {"table": "visual_qa_ledgers", "geometry": "none", "status": "implemented as visual QA manifests under analysis_output"},
            {"table": "visual_baseline_comparisons", "geometry": "none", "status": "implemented as QA ledger comparison manifests under analysis_output"},
            {"table": "demo_artifact_completeness_checks", "geometry": "none", "status": "implemented as artifact completeness manifests under analysis_output"},
            {"table": "visual_evidence_captures", "geometry": "none", "status": "implemented as screenshot manifests and contact sheets under analysis_output"},
            {"table": "visual_evidence_review_annotations", "geometry": "none", "status": "implemented as reviewer annotation manifests under analysis_output"},
            {"table": "visual_evidence_signoff_packets", "geometry": "none", "status": "implemented as reviewer sign-off packet manifests under analysis_output"},
            {"table": "final_reviewer_launch_checklists", "geometry": "none", "status": "implemented as final launch checklist manifests under analysis_output"},
            {"table": "recruiter_demo_briefs", "geometry": "none", "status": "implemented as recruiter demo brief manifests under analysis_output"},
            {"table": "public_portfolio_packages", "geometry": "none", "status": "implemented as public portfolio package manifests under analysis_output"},
            {"table": "demo_review_playbooks", "geometry": "none", "status": "implemented as demo review playbook manifests under analysis_output"},
            {"table": "github_publication_bundles", "geometry": "none", "status": "implemented as GitHub publication bundle manifests under analysis_output"},
            {"table": "pedestrian_generators", "geometry": "point", "status": "implemented for Safe Access"},
            {"table": "crossings", "geometry": "point", "status": "implemented for Safe Access"},
            {"table": "road_segments", "geometry": "line", "status": "implemented for Safe Access"},
            {"table": "transit_stops", "geometry": "point", "status": "implemented through Transit profile"},
            {"table": "public_spaces", "geometry": "point/polygon-derived point", "status": "implemented through Park profile"},
            {"table": "risk_assessment_results", "geometry": "point reference", "status": "implemented"},
            {"table": "network_access_results", "geometry": "point reference", "status": "implemented for route-aware workspace"},
            {"table": "analysis_runs", "geometry": "none", "status": "implemented"},
            {"table": "portfolio_reports", "geometry": "none", "status": "implemented"},
            {"table": "postgis_profile_results", "geometry": "point", "status": "planned schema for larger-region backend"},
            {"table": "tag_quality_summary", "geometry": "none", "status": "implemented through OSM tag quality profile"},
            {"table": "authored_profile_results", "geometry": "none", "status": "implemented through authored profile audit runner"},
            {"table": "profile_promotion_proposals", "geometry": "none", "status": "implemented as proposal artifacts under analysis_output"},
            {"table": "profile_acceptance_decisions", "geometry": "none", "status": "implemented as decision ledger artifacts under analysis_output"},
            {"table": "profile_contract_diffs", "geometry": "none", "status": "implemented as review artifacts under analysis_output"},
            {"table": "profile_application_plans", "geometry": "none", "status": "implemented as planning artifacts under analysis_output"},
            {"table": "profile_config_apply_proposals", "geometry": "none", "status": "implemented as guarded proposal artifacts under analysis_output"},
            {"table": "profile_contract_regression_previews", "geometry": "none", "status": "implemented as preview artifacts under analysis_output"},
            {"table": "release_readiness_snapshots", "geometry": "none", "status": "implemented as readiness snapshot artifacts under analysis_output"},
            {"table": "portfolio_demo_snapshots", "geometry": "none", "status": "implemented as walkthrough snapshot artifacts under analysis_output"},
            {"table": "portfolio_evidence_bundles", "geometry": "none", "status": "implemented as shareable evidence artifacts under analysis_output"},
            {"table": "bundle_review_checklists", "geometry": "none", "status": "implemented as review checklist artifacts under analysis_output"},
            {"table": "portfolio_narratives", "geometry": "none", "status": "implemented as narrative export artifacts under analysis_output"},
            {"table": "portfolio_handoff_pages", "geometry": "none", "status": "implemented as standalone HTML handoff artifacts under analysis_output"},
            {"table": "portfolio_evidence_galleries", "geometry": "none", "status": "implemented as standalone HTML gallery artifacts under analysis_output"},
            {"table": "multi_pilot_comparisons", "geometry": "none", "status": "implemented as cross-pilot comparison artifacts under analysis_output"},
            {"table": "comparison_map_exports", "geometry": "none", "status": "implemented as HTML, SVG and CSV map artifacts under analysis_output"},
        ]

    def upload_strategy(self) -> dict:
        return {
            "current_state": "Local maps folder scan, reviewed local intake plans, approval-gated source import guardrails, approved source handoffs, controlled handoff execution evidence, reviewer-ready execution evidence packages, execution result diffs, execution diff galleries, baseline drilldowns, reproducibility audit packets, reviewer audit indexes, portfolio export launchers, portable release packages and demo script packs are implemented; browser upload is intentionally not implemented.",
            "reason": "The project must keep source GIS files read-only and needs explicit file-size, storage and review rules before accepting arbitrary uploads.",
            "safe_next_step": "Build a demo artifact completeness validator over release packages and visual comparisons.",
            "accepted_future_formats": ["GeoPackage", "Shapefile ZIP", "OSM PBF", "GeoJSON"],
            "required_gates": ["format detection", "size estimate", "CRS detection", "layer count", "tag availability", "profile readiness", "source_gis_modified=false"],
        }

    def roadmap_rows(self) -> list[dict]:
        return [
            {"release": "v023", "theme": "product architecture evidence", "status": "completed", "deliverable": "API, UI and docs for universal GIS workbench direction"},
            {"release": "v024", "theme": "profile selector dashboard", "status": "completed", "deliverable": "one dashboard table contract across Safe Access, Transit and Park profiles"},
            {"release": "v025", "theme": "local intake wizard and export bundle", "status": "completed", "deliverable": "reviewed local file/folder intake plus profile dashboard report bundle"},
            {"release": "v026", "theme": "configurable scoring", "status": "completed", "deliverable": "profile scoring rules stored as versioned JSON with exact-match audit"},
            {"release": "v027", "theme": "larger-region backend option", "status": "completed", "deliverable": "PostGIS-oriented schema, readiness API and migration plan"},
            {"release": "v028", "theme": "profile mapper SDK", "status": "completed", "deliverable": "template contracts, compatibility checks and mapper plans for adding GIS review profiles"},
            {"release": "v029", "theme": "contract execution adapter", "status": "completed", "deliverable": "dry-run runner binding and execution evidence for validated profile contracts"},
            {"release": "v030", "theme": "OSM tag quality runner", "status": "completed", "deliverable": "read-only profile workspace from inspected OSM tag and layer audit CSVs"},
            {"release": "v031", "theme": "template authoring wizard", "status": "completed", "deliverable": "draft-only creation of reviewed profile mapper contracts"},
            {"release": "v032", "theme": "controlled execution queue", "status": "completed", "deliverable": "convert validated dry-runs into queued local runner actions"},
            {"release": "v033", "theme": "dataset evidence packages", "status": "completed", "deliverable": "package local intake, template draft and queue outputs for selected datasets"},
            {"release": "v034", "theme": "authored profile runner", "status": "completed", "deliverable": "run authored draft contracts as read-only tag and layer evidence audit workspaces"},
            {"release": "v035", "theme": "authored dashboard contract", "status": "completed", "deliverable": "promote authored audit outputs into normalized profile dashboard rows and portfolio reports"},
            {"release": "v036", "theme": "profile promotion wizard", "status": "completed", "deliverable": "turn a successful authored audit into a reviewed reusable profile contract proposal"},
            {"release": "v037", "theme": "proposal acceptance workflow", "status": "completed", "deliverable": "review, approve or reject promotion proposals before any config update"},
            {"release": "v038", "theme": "accepted contract application plan", "status": "completed", "deliverable": "generate a guarded implementation plan for approved profile contract changes"},
            {"release": "v039", "theme": "profile contract diff review", "status": "completed", "deliverable": "interactive review of contract field changes before any explicit config apply task"},
            {"release": "v040", "theme": "guarded config apply proposal", "status": "completed", "deliverable": "approval-gated proposed mapper config preview without mutating config"},
            {"release": "v041", "theme": "profile contract regression preview", "status": "completed", "deliverable": "validate proposed mapper config against contract invariants before any real apply task"},
            {"release": "v042", "theme": "release readiness dashboard", "status": "completed", "deliverable": "summarize release, validation, API and promotion lifecycle gates into one readiness panel"},
            {"release": "v043", "theme": "guided portfolio demo walkthrough", "status": "completed", "deliverable": "turn release readiness, datasets, profile outputs and reports into a guided demo narrative"},
            {"release": "v044", "theme": "shareable portfolio evidence bundle", "status": "completed", "deliverable": "package guided demo, readiness snapshot, reports and selected CSV evidence into one review bundle"},
            {"release": "v045", "theme": "bundle review checklist", "status": "completed", "deliverable": "add missing-evidence diagnostics and remediation actions for evidence bundles"},
            {"release": "v046", "theme": "portfolio narrative export", "status": "completed", "deliverable": "turn checked evidence bundles into a polished reviewer-facing narrative package"},
            {"release": "v047", "theme": "portfolio handoff page", "status": "completed", "deliverable": "render narrative exports as a compact local HTML handoff page"},
            {"release": "v048", "theme": "portfolio evidence gallery", "status": "completed", "deliverable": "index handoff pages, narratives, bundles and reports into one local gallery"},
            {"release": "v049", "theme": "multi-pilot comparison workspaces", "status": "completed", "deliverable": "compare Kfar Saba and Raanana route-aware Safe Access outputs with shared evidence contracts"},
            {"release": "v050", "theme": "comparison map exports", "status": "completed", "deliverable": "render pilot comparison candidates and metrics into portable map evidence"},
            {"release": "v051", "theme": "reviewed source import guardrails", "status": "completed", "deliverable": "turn local intake previews into approval-gated metadata-only import review packets"},
            {"release": "v052", "theme": "approved source handoff", "status": "completed", "deliverable": "connect approved source import requests to profile mapper plans and controlled execution queue options"},
            {"release": "v053", "theme": "controlled handoff execution", "status": "completed", "deliverable": "launch an approved planned handoff and compare generated workspace outputs to handoff evidence"},
            {"release": "v054", "theme": "execution evidence packaging", "status": "completed", "deliverable": "package controlled execution comparisons into reviewer-ready evidence bundles"},
            {"release": "v055", "theme": "execution result diffing", "status": "completed", "deliverable": "compare packaged execution evidence across repeat runs, profiles and pilots"},
            {"release": "v056", "theme": "execution diff gallery", "status": "completed", "deliverable": "render execution diffs into a reviewer-facing local gallery"},
            {"release": "v057", "theme": "diff detail drilldown", "status": "completed", "deliverable": "select reproducibility baselines and inspect table-level differences"},
            {"release": "v058", "theme": "reproducibility audit packet", "status": "completed", "deliverable": "bundle baseline, drilldown and gallery evidence into one reviewer packet"},
            {"release": "v059", "theme": "reviewer audit index", "status": "completed", "deliverable": "index audit packets with demo and handoff links for portfolio review"},
            {"release": "v060", "theme": "portfolio export launcher", "status": "completed", "deliverable": "open best handoff, packet and reviewer index artifacts from one local panel"},
            {"release": "v061", "theme": "portable release package", "status": "completed", "deliverable": "package launcher evidence into a small reviewer-ready ZIP"},
            {"release": "v062", "theme": "demo script and screenshot pack", "status": "completed", "deliverable": "create a repeatable reviewer walkthrough script and local screenshot smoke evidence"},
            {"release": "v063", "theme": "visual QA snapshot ledger", "status": "completed", "deliverable": "track demo screenshot captures, observations and release-to-release visual review notes"},
            {"release": "v064", "theme": "visual baseline comparison manifest", "status": "completed", "deliverable": "compare manual visual QA ledgers across releases and identify changed review targets"},
            {"release": "v065", "theme": "demo artifact completeness validator", "status": "completed", "deliverable": "verify release package, walkthrough, QA ledger and baseline comparison are all ready before sharing"},
            {"release": "v066", "theme": "automated visual evidence capture", "status": "completed", "deliverable": "capture browser screenshots for QA ledger targets and attach them to reviewer evidence"},
            {"release": "v067", "theme": "visual evidence review diffs", "status": "completed", "deliverable": "compare captured screenshot sets and flag changed targets for manual review"},
            {"release": "v068", "theme": "visual evidence review annotations", "status": "completed", "deliverable": "record reviewer decisions and acceptance notes for visual evidence diffs"},
            {"release": "v069", "theme": "visual evidence sign-off packet", "status": "completed", "deliverable": "package annotations, validation and API evidence into a final reviewer sign-off artifact"},
            {"release": "v070", "theme": "final reviewer launch checklist", "status": "completed", "deliverable": "turn sign-off packets into a compact launch checklist for portfolio walkthroughs"},
            {"release": "v071", "theme": "recruiter-facing demo brief", "status": "completed", "deliverable": "summarize the launch checklist into a one-page reviewer/recruiter brief"},
            {"release": "v072", "theme": "public portfolio README and interview package", "status": "completed", "deliverable": "turn the recruiter brief into a concise public-facing project package"},
            {"release": "v073", "theme": "demo review playbook and sharing checklist", "status": "completed", "deliverable": "turn the public package into a final interview and publication review flow"},
            {"release": "v074", "theme": "GitHub-ready publication bundle", "status": "completed", "deliverable": "package final playbook and public README into a shareable repository handoff"},
            {"release": "v075", "theme": "repository QA and sharing walkthrough", "status": "completed", "deliverable": "verify publication bundle contents and add final public sharing checks"},
            {"release": "v076", "theme": "repository export handoff", "status": "completed", "deliverable": "prepare final repository QA export, screenshot references and license decision checklist"},
            {"release": "v077", "theme": "public repository dry run", "status": "completed", "deliverable": "simulate final GitHub repository structure and visual evidence references without publishing"},
            {"release": "v078", "theme": "final repository package review", "status": "completed", "deliverable": "prepare redacted path review and final packaging instructions without publishing"},
            {"release": "v079", "theme": "public README path cleanup", "status": "completed", "deliverable": "prepare curated public README/docs evidence and screenshot references without publishing"},
            {"release": "v080", "theme": "final public repository polish", "status": "completed", "deliverable": "turn cleaned README and screenshot checklist into final public repository package instructions"},
            {"release": "v081", "theme": "repository export checklist", "status": "completed", "deliverable": "prepare final manual repository export checklist after screenshots are captured"},
            {"release": "v082", "theme": "UX/UI landing repair", "status": "completed", "deliverable": "make the first viewport dashboard-first and reviewer-ready"},
            {"release": "v083", "theme": "Figma-aligned dashboard polish", "status": "current", "deliverable": "align the local dashboard layout, review queue and selected-candidate panel with the v083 Figma target"},
            {"release": "v084", "theme": "manual publication handoff", "status": "next", "deliverable": "prepare the final human-controlled GitHub sharing checklist without automatic publishing"},
        ]

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["infrastructure risk indicators", "data-quality flags", "field-review prioritization", "mapped OSM evidence"],
            "not_allowed": ["crash prediction", "proof of real-world absence from missing tags", "absolute safety claims"],
            "missing_tag_rule": "Missing OSM tags add data-quality flags, not risk points by default.",
        }

    def safe_manifest(self) -> dict:
        try:
            manifest = self.manifest_reader()
            return manifest if isinstance(manifest, dict) else {}
        except Exception:
            return {}

    def safe_source_status(self) -> dict:
        try:
            status = self.onboarding.status()
            return status if isinstance(status, dict) else {}
        except Exception:
            return {}

    def safe_profiles(self) -> dict:
        try:
            payload = self.profiles.list_profiles(
                dataset_id="israel-and-palestine-260521-free-shp-zip",
                pilot_osm_id="53796999",
                route_aware=True,
            )
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {"profiles": []}



