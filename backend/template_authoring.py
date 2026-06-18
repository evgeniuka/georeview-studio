from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


TEMPLATE_AUTHORING_VERSION = "template_authoring_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."

TEMPLATE_BLUEPRINTS = [
    {
        "template_id": "cycling_micromobility_access",
        "profile_id": "cycling_micromobility_access",
        "name": "Cycling and micromobility infrastructure review",
        "domain": "cycling_access",
        "required_groups": ["roads"],
        "optional_groups": ["traffic", "osm_pbf_enrichment"],
        "required_tags": ["highway"],
        "optional_tags": ["cycleway", "cycleway:left", "cycleway:right", "bicycle", "segregated", "maxspeed", "lanes"],
        "canonical_outputs": ["cycling_access_candidates", "cycling_tag_coverage", "mixed_traffic_context"],
        "scoring_profile_id": "",
        "claim_boundaries": ["mapped cycling infrastructure indicators", "tag coverage indicators"],
    },
    {
        "template_id": "school_zone_walk_access",
        "profile_id": "school_zone_walk_access",
        "name": "School-zone walk-access review",
        "domain": "pedestrian_access",
        "required_groups": ["roads", "traffic", "pois"],
        "optional_groups": ["places", "transport", "osm_pbf_enrichment"],
        "required_tags": ["amenity", "highway"],
        "optional_tags": ["crossing", "maxspeed", "traffic_calming", "sidewalk", "lit", "tactile_paving"],
        "canonical_outputs": ["school_zone_review_candidates", "crossing_proximity", "tag_quality_flags"],
        "scoring_profile_id": "",
        "claim_boundaries": ["infrastructure review indicators near mapped education places"],
    },
    {
        "template_id": "bus_stop_crossing_access",
        "profile_id": "bus_stop_crossing_access",
        "name": "Bus-stop crossing access review",
        "domain": "public_transport_access",
        "required_groups": ["transport", "roads", "traffic"],
        "optional_groups": ["osm_pbf_enrichment"],
        "required_tags": ["highway", "public_transport"],
        "optional_tags": ["crossing", "shelter", "bench", "route_ref", "network", "sidewalk", "lit"],
        "canonical_outputs": ["bus_stop_crossing_access_results", "nearest_crossing_metrics", "stop_context_flags"],
        "scoring_profile_id": "",
        "claim_boundaries": ["mapped access indicators around public transport stops"],
    },
    {
        "template_id": "generic_osm_tag_coverage",
        "profile_id": "generic_osm_tag_coverage",
        "name": "Generic OSM tag coverage audit",
        "domain": "data_quality",
        "required_groups": [],
        "optional_groups": ["places", "roads", "traffic", "transport", "pois", "landuse", "osm_pbf_enrichment"],
        "required_tags": [],
        "optional_tags": ["highway", "amenity", "leisure", "public_transport", "sidewalk", "lit", "maxspeed"],
        "canonical_outputs": ["tag_quality_summary", "source_scope_summary"],
        "scoring_profile_id": "",
        "claim_boundaries": ["data-quality evidence", "tag coverage indicators"],
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "template_authoring") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:110] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def layer_names(source: dict) -> set[str]:
    return {str(layer.get("layer") or "").lower() for layer in source.get("layers", [])}


def group_available(group: str, layers: set[str], source: dict) -> bool:
    if group == "osm_pbf_enrichment":
        extension = str(source.get("extension") or "").lower()
        return extension in {".osm.pbf", ".pbf"} or any("pbf" in str(item).lower() for item in source.get("related_files", []))
    return any(group in layer for layer in layers)


class TemplateAuthoringWizard:
    def __init__(self, config_path: Path, output_root: Path, onboarding: object) -> None:
        self.config_path = config_path
        self.output_root = output_root
        self.onboarding = onboarding
        self.drafts_dir = output_root / "georeview_studio_template_authoring"

    def status(self) -> dict:
        config = self.config()
        contracts = config.get("contracts", [])
        return {
            "ok": bool(config),
            "template_authoring_version": TEMPLATE_AUTHORING_VERSION,
            "mode": "draft_only_no_config_mutation",
            "config_path": str(self.config_path),
            "drafts_dir": str(self.drafts_dir),
            "existing_contract_count": len(contracts),
            "blueprint_count": len(TEMPLATE_BLUEPRINTS),
            "draft_count": len(self.list_drafts(200)),
            "policy": {
                "writes_only_drafts_under_analysis_output": True,
                "does_not_modify_profile_mapper_config": True,
                "does_not_modify_source_gis": True,
                "missing_tags_are_data_quality_flags": True,
            },
            "approved_review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }

    def options(self) -> dict:
        existing = self.existing_profile_ids()
        return {
            "ok": True,
            "template_authoring_version": TEMPLATE_AUTHORING_VERSION,
            "blueprints": [
                {
                    **blueprint,
                    "already_exists_in_profile_mapper": blueprint["profile_id"] in existing,
                    "recommended_first_action": "draft_contract",
                }
                for blueprint in TEMPLATE_BLUEPRINTS
            ],
            "claim_boundary": "Drafts describe profile requirements and expected outputs. They do not execute analysis and do not claim real-world safety conditions.",
            "source_gis_modified": False,
        }

    def draft(self, body: dict | None = None, write_files: bool = False) -> dict:
        body = body or {}
        template_id = str(body.get("template_id") or body.get("profile_id") or "cycling_micromobility_access")
        blueprint = self.blueprint(template_id)
        if not blueprint:
            blueprint = self.custom_blueprint(body)
        profile_id = safe_token(body.get("profile_id") or blueprint["profile_id"], "custom_profile")
        dataset_id = str(body.get("dataset_id") or "israel-and-palestine-260521-free-shp-zip")
        contract = self.contract_from_blueprint(blueprint, profile_id)
        source = self.safe_source(dataset_id)
        compatibility = self.compatibility(contract, source)
        draft_id = self.next_draft_id(profile_id, dataset_id)
        warnings = list(compatibility.get("warnings", []))
        if profile_id in self.existing_profile_ids():
            warnings.append("profile_id_already_exists_in_profile_mapper_config")
        draft = {
            "ok": True,
            "template_authoring_version": TEMPLATE_AUTHORING_VERSION,
            "draft_id": draft_id,
            "created_at_utc": utc_now(),
            "template_id": blueprint["template_id"],
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "contract": contract,
            "compatibility": compatibility,
            "warnings": warnings,
            "next_steps": [
                "Review required layer groups and optional OSM tags.",
                "Decide whether this profile needs a real runner or can remain a read-only audit.",
                "Add tests before promoting the draft into profile_mapper_contracts_v001.json.",
                "Keep missing tag evidence separate from infrastructure risk scoring.",
            ],
            "non_goals": [
                "No source GIS files are modified.",
                "No profile mapper config is modified automatically.",
                "No public hosting or external service is enabled.",
                "No crash prediction or absolute safety claim is introduced.",
            ],
            "review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }
        if write_files:
            self.drafts_dir.mkdir(parents=True, exist_ok=True)
            json_path = self.draft_path(draft_id, ".json")
            md_path = self.draft_path(draft_id, ".md")
            write_json(json_path, draft)
            md_path.write_text(self.draft_markdown(draft), encoding="utf-8")
            draft["json_file"] = str(json_path)
            draft["markdown_file"] = str(md_path)
        return draft

    def list_drafts(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit or 20), 200))
        rows = []
        if not self.drafts_dir.exists():
            return rows
        for path in sorted(self.drafts_dir.glob("template_authoring_draft_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("template_authoring_version") != TEMPLATE_AUTHORING_VERSION:
                continue
            rows.append({
                "ok": True,
                "draft_id": data.get("draft_id"),
                "template_id": data.get("template_id"),
                "profile_id": data.get("profile_id"),
                "dataset_id": data.get("dataset_id"),
                "can_plan": data.get("compatibility", {}).get("can_plan"),
                "warning_count": len(data.get("warnings", [])),
                "created_at_utc": data.get("created_at_utc"),
                "source_gis_modified": data.get("source_gis_modified") is True,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, draft_id: str) -> dict:
        path = self.draft_path(draft_id, ".json")
        if not path.exists() or not self.safe_draft_path(path):
            return {"ok": False, "error": "template_authoring_draft_not_found", "draft_id": draft_id, "source_gis_modified": False}
        data = read_json(path)
        if not data:
            return {"ok": False, "error": "template_authoring_draft_not_found", "draft_id": draft_id, "source_gis_modified": False}
        data["json_file"] = str(path)
        md_path = self.draft_path(draft_id, ".md")
        data["markdown_file"] = str(md_path) if md_path.exists() else ""
        return data

    def config(self) -> dict:
        return read_json(self.config_path)

    def existing_profile_ids(self) -> set[str]:
        return {str(contract.get("profile_id") or "") for contract in self.config().get("contracts", [])}

    @staticmethod
    def blueprint(template_id: str) -> dict:
        clean = str(template_id or "").strip()
        for blueprint in TEMPLATE_BLUEPRINTS:
            if clean in {blueprint["template_id"], blueprint["profile_id"]}:
                return dict(blueprint)
        return {}

    @staticmethod
    def custom_blueprint(body: dict) -> dict:
        profile_id = safe_token(body.get("profile_id") or "custom_gis_review_profile", "custom_gis_review_profile")
        return {
            "template_id": "custom",
            "profile_id": profile_id,
            "name": str(body.get("name") or "Custom GIS review profile"),
            "domain": str(body.get("domain") or "custom_gis_review"),
            "required_groups": list(body.get("required_groups") or []),
            "optional_groups": list(body.get("optional_groups") or ["roads", "traffic", "osm_pbf_enrichment"]),
            "required_tags": list(body.get("required_tags") or []),
            "optional_tags": list(body.get("optional_tags") or ["highway", "name"]),
            "canonical_outputs": list(body.get("canonical_outputs") or ["custom_review_results"]),
            "scoring_profile_id": str(body.get("scoring_profile_id") or ""),
            "claim_boundaries": list(body.get("claim_boundaries") or ["mapped infrastructure indicators"]),
        }

    @staticmethod
    def contract_from_blueprint(blueprint: dict, profile_id: str) -> dict:
        return {
            "profile_id": profile_id,
            "domain": blueprint["domain"],
            "status": "draft",
            "runner_status": "draft_not_implemented",
            "mapper_type": "draft_profile_contract",
            "source_layer_requirements": {
                "required_groups": blueprint["required_groups"],
                "optional_groups": blueprint["optional_groups"],
                "required_tags": blueprint["required_tags"],
                "optional_tags": blueprint["optional_tags"],
            },
            "canonical_outputs": blueprint["canonical_outputs"],
            "result_contract": "profile_dashboard_contract_v001",
            "scoring_profile_id": blueprint.get("scoring_profile_id", ""),
            "implementation_entrypoint": "",
            "claim_boundaries": blueprint["claim_boundaries"] + [REVIEW_WORDING],
            "missing_data_policy": "Missing OSM tags are data-quality flags, not proof that infrastructure is absent.",
        }

    def safe_source(self, dataset_id: str) -> dict:
        try:
            source = self.onboarding.source_detail(dataset_id)
            return source if isinstance(source, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def compatibility(contract: dict, source: dict) -> dict:
        layers = layer_names(source)
        requirements = contract.get("source_layer_requirements", {})
        required_groups = requirements.get("required_groups", [])
        optional_groups = requirements.get("optional_groups", [])
        missing_required = [group for group in required_groups if not group_available(group, layers, source)]
        available_optional = [group for group in optional_groups if group_available(group, layers, source)]
        warnings = []
        if source.get("error"):
            warnings.append(str(source.get("error")))
        if "osm_pbf_enrichment" in optional_groups and "osm_pbf_enrichment" not in available_optional:
            warnings.append("optional_pbf_enrichment_not_detected")
        return {
            "dataset_id": source.get("dataset_id"),
            "source_file": source.get("file_name"),
            "source_readiness": source.get("readiness", {}).get("level"),
            "required_groups": required_groups,
            "missing_required_groups": missing_required,
            "available_optional_groups": available_optional,
            "required_tags": requirements.get("required_tags", []),
            "optional_tags": requirements.get("optional_tags", []),
            "can_plan": not missing_required and not source.get("error"),
            "blockers": [f"missing_layer_group_{group}" for group in missing_required],
            "warnings": warnings,
            "source_gis_modified": False,
        }

    @staticmethod
    def draft_markdown(draft: dict) -> str:
        contract = draft.get("contract", {})
        compatibility = draft.get("compatibility", {})
        lines = [
            "# Template Authoring Draft",
            "",
            f"Draft id: `{draft.get('draft_id')}`",
            f"Profile: `{draft.get('profile_id')}`",
            f"Template: `{draft.get('template_id')}`",
            f"Can plan on selected dataset: `{compatibility.get('can_plan')}`",
            "",
            "## Required Layer Groups",
            "",
        ]
        for group in compatibility.get("required_groups", []):
            status = "missing" if group in compatibility.get("missing_required_groups", []) else "available"
            lines.append(f"- `{group}`: {status}")
        lines.extend(["", "## Optional Tags", ""])
        for tag in contract.get("source_layer_requirements", {}).get("optional_tags", []):
            lines.append(f"- `{tag}`")
        lines.extend(["", "## Canonical Outputs", ""])
        for output in contract.get("canonical_outputs", []):
            lines.append(f"- `{output}`")
        lines.extend(["", "## Boundaries", ""])
        for item in draft.get("non_goals", []):
            lines.append(f"- {item}")
        lines.append(f"- {REVIEW_WORDING}")
        return "\n".join(lines).rstrip() + "\n"

    def next_draft_id(self, profile_id: str, dataset_id: str) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"template_authoring_draft_{safe_token(profile_id)}_{safe_token(dataset_id)}_{safe_token(stamp)}"

    def draft_path(self, draft_id: str, suffix: str) -> Path:
        return self.drafts_dir / f"{safe_token(draft_id)}{suffix}"

    def safe_draft_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.drafts_dir.resolve())
            return True
        except ValueError:
            return False
