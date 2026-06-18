from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


AUTHORED_PROFILE_RUNNER_VERSION = "authored_profile_runner_v001"
DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID = "authored_profile_audit_kfar_saba_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."

GROUP_TAG_HINTS = {
    "roads": {"highway", "maxspeed", "lanes", "oneway", "sidewalk", "lit", "surface", "smoothness", "cycleway", "bicycle", "segregated"},
    "traffic": {"highway", "crossing", "crossing_ref", "traffic_calming", "tactile_paving", "kerb", "button_operated"},
    "transport": {"highway", "public_transport", "bus", "shelter", "bench", "route_ref", "network", "operator"},
    "pois": {"amenity", "leisure", "school", "operator", "name", "name:he", "name:en"},
    "places": {"name", "name:he", "name:en", "place"},
    "landuse": {"landuse", "leisure", "amenity"},
    "osm_pbf_enrichment": set(),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "authored_profile") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:120] or fallback


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


class AuthoredProfileRunner:
    def __init__(self, output_root: Path, workspaces_dir: Path, template_authoring: object, review_wording: str) -> None:
        self.output_root = output_root
        self.workspaces_dir = workspaces_dir
        self.template_authoring = template_authoring
        self.review_wording = review_wording
        self.tag_counts_path = output_root / "osm_tag_counts.csv"
        self.layer_summary_path = output_root / "layer_summary.csv"

    def status(self) -> dict:
        return {
            "ok": True,
            "authored_profile_runner_version": AUTHORED_PROFILE_RUNNER_VERSION,
            "mode": "read_only_draft_audit_runner",
            "draft_count": len(self.template_authoring.list_drafts(200)),
            "workspace_count": len(self.list_workspaces()),
            "tag_counts_exists": self.tag_counts_path.exists(),
            "layer_summary_exists": self.layer_summary_path.exists(),
            "default_workspace_id": DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID,
            "queue_endpoint": "/api/execution-queue/enqueue-authored-draft",
            "policy": {
                "runs_template_drafts_only": True,
                "produces_tag_and_layer_evidence": True,
                "does_not_promote_contract_config": True,
                "does_not_modify_source_gis": True,
                "does_not_claim_domain_specific_risk_score": True,
            },
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
        }

    def ensure_workspace(self, draft_id: str, workspace_id: str = "", dataset_id: str = "") -> dict:
        if not draft_id:
            return {"ok": False, "error": "authored_profile_draft_missing", "detail": "draft_id is required", "source_gis_modified": False}
        draft = self.template_authoring.detail(draft_id)
        if draft.get("error"):
            return draft
        compatibility = draft.get("compatibility", {})
        if compatibility.get("can_plan") is not True:
            return {
                "ok": False,
                "error": "authored_profile_not_ready",
                "draft_id": draft_id,
                "blockers": compatibility.get("blockers", []),
                "warnings": compatibility.get("warnings", []),
                "source_gis_modified": False,
            }
        tag_rows = read_csv_rows(self.tag_counts_path)
        layer_rows = read_csv_rows(self.layer_summary_path)
        if not tag_rows:
            return {"ok": False, "error": "authored_profile_source_missing", "tag_counts_file": str(self.tag_counts_path), "source_gis_modified": False}

        profile_id = str(draft.get("profile_id") or draft.get("contract", {}).get("profile_id") or "authored_profile")
        workspace_id = safe_token(workspace_id or f"authored_profile_{profile_id}_v001", DEFAULT_AUTHORED_PROFILE_WORKSPACE_ID)
        output_dir = self.workspaces_dir / workspace_id
        tables_dir = output_dir / "tables"
        reports_dir = output_dir / "reports"

        result_rows = self.result_rows_for_draft(draft, tag_rows)
        evidence_rows = self.evidence_rows_for_draft(draft, tag_rows)
        requirement_rows = self.layer_requirement_rows(draft)
        summary = self.summary_from_rows(workspace_id, draft, result_rows, evidence_rows, requirement_rows, layer_rows)

        result_path = tables_dir / "authored_profile_results.csv"
        evidence_path = tables_dir / "authored_profile_source_evidence.csv"
        requirements_path = tables_dir / "authored_profile_layer_requirements.csv"
        summary_path = reports_dir / "authored_profile_summary.json"
        report_path = reports_dir / "authored_profile_report.md"
        manifest_path = output_dir / "manifest.json"
        readme_path = output_dir / "README.md"

        write_csv(result_path, result_rows, [
            "result_id",
            "profile_id",
            "draft_id",
            "requirement_type",
            "tag_or_field",
            "evidence_status",
            "total_count",
            "positive_count_rows",
            "sources",
            "scopes",
            "example_values",
            "primary_metric",
            "primary_score",
            "flags",
            "data_quality_flags",
            "review_wording",
            "source_gis_modified",
        ])
        write_csv(evidence_path, evidence_rows, [
            "source",
            "scope",
            "category",
            "layer_or_element",
            "tag_or_field",
            "value",
            "count",
            "requirement_match",
            "notes",
        ])
        write_csv(requirements_path, requirement_rows, [
            "group",
            "requirement_type",
            "status",
            "evidence",
            "data_quality_flags",
        ])
        write_json(summary_path, {"ok": True, **summary})
        report_path.write_text(self.summary_markdown(summary, result_rows), encoding="utf-8")

        manifest = {
            "workspace_id": workspace_id,
            "profile_id": profile_id,
            "profile_workspace": True,
            "authored_profile_workspace": True,
            "draft_id": draft_id,
            "template_id": draft.get("template_id"),
            "dataset_id": dataset_id or draft.get("dataset_id"),
            "created_at_utc": utc_now(),
            "analyzer": AUTHORED_PROFILE_RUNNER_VERSION,
            "source_gis_modified": False,
            "source_files": {
                "tag_counts": str(self.tag_counts_path),
                "layer_summary": str(self.layer_summary_path),
                "template_draft": draft.get("json_file", ""),
            },
            "tables": [
                {"table": "authored_profile_results", "file": str(result_path), "rows": len(result_rows)},
                {"table": "authored_profile_source_evidence", "file": str(evidence_path), "rows": len(evidence_rows)},
                {"table": "authored_profile_layer_requirements", "file": str(requirements_path), "rows": len(requirement_rows)},
            ],
            "reports": {
                "workspace_summary": str(summary_path),
                "authored_profile_report": str(report_path),
            },
            "claim_boundaries": [
                "This runner executes authored drafts as tag and layer evidence audits.",
                "It does not mutate the profile mapper config.",
                "It does not produce a domain-specific risk score unless a dedicated runner is implemented.",
                "Missing OSM tags remain data-quality flags.",
                self.review_wording,
            ],
        }
        write_json(manifest_path, manifest)
        readme_path.write_text(
            "# Authored Profile Audit Workspace\n\n"
            "Read-only workspace generated from a Template Authoring draft. It reports tag and layer evidence for the draft contract.\n\n"
            "Missing tags are data-quality flags, not proof that infrastructure is absent.\n",
            encoding="utf-8",
        )
        return {
            "ok": True,
            "created": True,
            "workspace": {
                "manifest": manifest,
                "summary": {"ok": True, **summary},
            },
            "source_gis_modified": False,
        }

    def list_workspaces(self) -> list[dict]:
        rows = []
        if not self.workspaces_dir.exists():
            return rows
        for manifest_path in self.workspaces_dir.glob("*/manifest.json"):
            manifest = read_json(manifest_path)
            if not manifest.get("authored_profile_workspace"):
                continue
            summary = self.summary_for_workspace(str(manifest.get("workspace_id") or ""))
            counts = summary.get("counts", {}) if isinstance(summary, dict) else {}
            rows.append({
                "workspace_id": manifest.get("workspace_id"),
                "profile_id": manifest.get("profile_id"),
                "draft_id": manifest.get("draft_id"),
                "template_id": manifest.get("template_id"),
                "created_at_utc": manifest.get("created_at_utc"),
                "result_rows": counts.get("result_rows"),
                "tags_with_evidence": counts.get("tags_with_evidence"),
                "missing_required_tags": counts.get("missing_required_tags"),
                "source_gis_modified": False,
            })
        return sorted(rows, key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)

    def summary_for_workspace(self, workspace_id: str) -> dict:
        manifest = self.manifest(workspace_id)
        if "error" in manifest:
            return manifest
        summary_path = Path(manifest.get("reports", {}).get("workspace_summary", ""))
        if not summary_path.exists():
            return {"ok": False, "error": "profile_output_not_found", "workspace_id": workspace_id, "output_id": "workspace_summary", "source_gis_modified": False}
        return read_json(summary_path)

    def results(self, workspace_id: str, limit: int = 50) -> list[dict] | dict:
        output = self.output_file(workspace_id, "authored_profile_results")
        if "error" in output:
            return output
        return read_csv_rows(output["path"])[: max(1, min(int(limit or 50), 500))]

    def output_file(self, workspace_id: str, output_id: str) -> dict:
        manifest = self.manifest(workspace_id)
        if "error" in manifest:
            return manifest
        table_files = {str(item.get("table")): Path(item.get("file", "")) for item in manifest.get("tables", [])}
        report_files = {str(key): Path(value) for key, value in manifest.get("reports", {}).items()}
        candidates = {**table_files, **report_files}
        path = candidates.get(output_id)
        if not path or not path.exists():
            return {"ok": False, "error": "profile_output_not_found", "workspace_id": workspace_id, "output_id": output_id, "source_gis_modified": False}
        return {"ok": True, "path": path, "output_id": output_id, "source_gis_modified": False}

    def manifest(self, workspace_id: str) -> dict:
        manifest_path = self.workspaces_dir / safe_token(workspace_id) / "manifest.json"
        if not manifest_path.exists():
            return {"ok": False, "error": "profile_workspace_not_found", "workspace_id": workspace_id, "source_gis_modified": False}
        manifest = read_json(manifest_path)
        if not manifest.get("authored_profile_workspace"):
            return {"ok": False, "error": "profile_workspace_not_found", "workspace_id": workspace_id, "source_gis_modified": False}
        return manifest

    @staticmethod
    def draft_tags(draft: dict) -> tuple[list[str], list[str]]:
        requirements = draft.get("contract", {}).get("source_layer_requirements", {})
        required = [str(tag) for tag in requirements.get("required_tags", []) if tag]
        optional = [str(tag) for tag in requirements.get("optional_tags", []) if tag and str(tag) not in required]
        return required, optional

    @staticmethod
    def draft_groups(draft: dict) -> tuple[list[str], list[str]]:
        requirements = draft.get("contract", {}).get("source_layer_requirements", {})
        required = [str(group) for group in requirements.get("required_groups", []) if group]
        optional = [str(group) for group in requirements.get("optional_groups", []) if group and str(group) not in required]
        return required, optional

    def result_rows_for_draft(self, draft: dict, tag_rows: list[dict]) -> list[dict]:
        required_tags, optional_tags = self.draft_tags(draft)
        rows = []
        for requirement_type, tags in (("required_tag", required_tags), ("optional_tag", optional_tags)):
            for tag in tags:
                matches = [row for row in tag_rows if str(row.get("tag_or_field") or "") == tag or str(row.get("category") or "") == tag]
                positive = [row for row in matches if parse_int(row.get("count")) > 0]
                total = sum(parse_int(row.get("count")) for row in positive)
                flags = []
                quality_flags = []
                if total > 0:
                    status = "mapped_evidence_present"
                    flags.append("tag_evidence_present")
                else:
                    status = "not_available_in_inspected_files"
                    quality_flags.append("tag_not_found_in_inspected_audit_csv")
                    if requirement_type == "required_tag":
                        quality_flags.append("required_tag_missing_from_current_evidence")
                example_values = []
                for row in positive:
                    value = str(row.get("value") or "")
                    if value and value not in example_values:
                        example_values.append(value)
                    if len(example_values) >= 6:
                        break
                rows.append({
                    "result_id": f"{safe_token(draft.get('profile_id'))}_{safe_token(tag)}",
                    "profile_id": draft.get("profile_id"),
                    "draft_id": draft.get("draft_id"),
                    "requirement_type": requirement_type,
                    "tag_or_field": tag,
                    "evidence_status": status,
                    "total_count": total,
                    "positive_count_rows": len(positive),
                    "sources": ";".join(sorted({str(row.get("source") or "") for row in matches if row.get("source")})),
                    "scopes": ";".join(sorted({str(row.get("scope") or "") for row in matches if row.get("scope")})),
                    "example_values": "; ".join(example_values),
                    "primary_metric": "osm_tag_evidence_count",
                    "primary_score": min(100, total) if total > 0 else 0,
                    "flags": ";".join(flags),
                    "data_quality_flags": ";".join(quality_flags),
                    "review_wording": REVIEW_WORDING,
                    "source_gis_modified": "false",
                })
        rows.sort(key=lambda row: (row["requirement_type"] != "required_tag", -parse_int(row["total_count"]), row["tag_or_field"]))
        return rows

    def evidence_rows_for_draft(self, draft: dict, tag_rows: list[dict]) -> list[dict]:
        required_tags, optional_tags = self.draft_tags(draft)
        required_groups, optional_groups = self.draft_groups(draft)
        all_tags = set(required_tags + optional_tags)
        group_tags = set()
        for group in required_groups + optional_groups:
            group_tags.update(GROUP_TAG_HINTS.get(group, set()))
        result = []
        for row in tag_rows:
            tag = str(row.get("tag_or_field") or "")
            category = str(row.get("category") or "")
            match = ""
            if tag in all_tags or category in all_tags:
                match = "explicit_tag_requirement"
            elif tag in group_tags or category in group_tags:
                match = "layer_group_related_tag"
            if not match:
                continue
            next_row = dict(row)
            next_row["requirement_match"] = match
            result.append(next_row)
        result.sort(key=lambda row: (row.get("requirement_match") != "explicit_tag_requirement", -parse_int(row.get("count")), row.get("tag_or_field") or row.get("category")))
        return result[:1000]

    @staticmethod
    def layer_requirement_rows(draft: dict) -> list[dict]:
        compatibility = draft.get("compatibility", {})
        required_groups = compatibility.get("required_groups", [])
        optional_groups = draft.get("contract", {}).get("source_layer_requirements", {}).get("optional_groups", [])
        missing_required = set(compatibility.get("missing_required_groups", []))
        available_optional = set(compatibility.get("available_optional_groups", []))
        rows = []
        for group in required_groups:
            missing = group in missing_required
            rows.append({
                "group": group,
                "requirement_type": "required_group",
                "status": "missing" if missing else "available",
                "evidence": "template_authoring_compatibility",
                "data_quality_flags": "required_group_missing" if missing else "",
            })
        for group in optional_groups:
            available = group in available_optional
            rows.append({
                "group": group,
                "requirement_type": "optional_group",
                "status": "available" if available else "not_available_in_current_source",
                "evidence": "template_authoring_compatibility",
                "data_quality_flags": "" if available else "optional_group_not_detected",
            })
        return rows

    @staticmethod
    def summary_from_rows(workspace_id: str, draft: dict, result_rows: list[dict], evidence_rows: list[dict], requirement_rows: list[dict], layer_rows: list[dict]) -> dict:
        required = [row for row in result_rows if row.get("requirement_type") == "required_tag"]
        optional = [row for row in result_rows if row.get("requirement_type") == "optional_tag"]
        tags_with_evidence = [row for row in result_rows if parse_int(row.get("total_count")) > 0]
        missing_required = [row for row in required if parse_int(row.get("total_count")) == 0]
        missing_optional = [row for row in optional if parse_int(row.get("total_count")) == 0]
        return {
            "workspace_id": workspace_id,
            "profile_id": draft.get("profile_id"),
            "draft_id": draft.get("draft_id"),
            "template_id": draft.get("template_id"),
            "analyzer": AUTHORED_PROFILE_RUNNER_VERSION,
            "counts": {
                "result_rows": len(result_rows),
                "required_tags": len(required),
                "optional_tags": len(optional),
                "tags_with_evidence": len(tags_with_evidence),
                "missing_required_tags": len(missing_required),
                "missing_optional_tags": len(missing_optional),
                "source_evidence_rows": len(evidence_rows),
                "layer_requirement_rows": len(requirement_rows),
                "layer_summary_rows": len(layer_rows),
            },
            "evidence_highlights": [
                "Authored drafts can now be executed as read-only tag and layer evidence audits.",
                "The runner uses inspected audit CSV files under analysis_output.",
                "A dedicated domain runner is still required for real profile-specific scoring.",
            ],
            "limitations": [
                "This is not a crash prediction model.",
                "Missing OSM tags are data-quality flags, not proof that infrastructure is absent.",
                "Counts come from the existing inspected audit CSV files, not a fresh live OSM query.",
            ],
            "review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }

    @staticmethod
    def summary_markdown(summary: dict, result_rows: list[dict]) -> str:
        counts = summary.get("counts", {})
        lines = [
            "# Authored Profile Runner Report",
            "",
            f"Workspace: `{summary.get('workspace_id')}`",
            f"Profile: `{summary.get('profile_id')}`",
            f"Draft: `{summary.get('draft_id')}`",
            f"Analyzer: `{summary.get('analyzer')}`",
            "",
            "## Evidence Counts",
            "",
            f"- Result rows: {counts.get('result_rows')}",
            f"- Required tags: {counts.get('required_tags')}",
            f"- Optional tags: {counts.get('optional_tags')}",
            f"- Tags with evidence: {counts.get('tags_with_evidence')}",
            f"- Missing required tags: {counts.get('missing_required_tags')}",
            f"- Source evidence rows: {counts.get('source_evidence_rows')}",
            "",
            "## Interpretation",
            "",
            "- This runner executes authored drafts as tag/layer evidence audits.",
            "- Missing OSM tags are data-quality flags, not proof that infrastructure is absent.",
            "- Domain-specific scoring still requires a dedicated runner.",
            f"- {summary.get('review_wording')}",
            "",
            "## Top Result Rows",
            "",
        ]
        for row in result_rows[:20]:
            lines.append(f"- `{row.get('tag_or_field')}`: {row.get('total_count')} ({row.get('evidence_status')}).")
        return "\n".join(lines).rstrip() + "\n"
