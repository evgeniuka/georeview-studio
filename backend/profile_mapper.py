from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROFILE_MAPPER_VERSION = "profile_mapper_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "profile_mapper_plan") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:96] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def layer_names(source: dict) -> set[str]:
    return {str(layer.get("layer") or "").lower() for layer in source.get("layers", [])}


def group_available(group: str, layers: set[str], source: dict) -> bool:
    if group == "osm_pbf_enrichment":
        extension = str(source.get("extension") or "").lower()
        return extension in {".osm.pbf", ".pbf"} or any("pbf" in str(item).lower() for item in source.get("related_files", []))
    return any(group in layer for layer in layers)


class ProfileMapperRegistry:
    def __init__(self, config_path: Path, output_root: Path, onboarding: object, profiles: object) -> None:
        self.config_path = config_path
        self.output_root = output_root
        self.onboarding = onboarding
        self.profiles = profiles
        self.plans_dir = output_root / "georeview_studio_profile_mapper_plans"

    def config(self) -> dict:
        return read_json(self.config_path)

    def overview(self) -> dict:
        config = self.config()
        if not config:
            return {"ok": False, "error": "profile_mapper_config_not_found", "config_path": str(self.config_path), "source_gis_modified": False}
        contracts = config.get("contracts", [])
        validation = self.validate_contracts(contracts, config.get("required_contract_fields", []))
        implemented = [item for item in contracts if item.get("status") == "implemented"]
        ready = [item for item in contracts if item.get("status") in {"implemented", "profile_ready"}]
        return {
            "ok": True,
            "profile_mapper_version": PROFILE_MAPPER_VERSION,
            "profile_mapper_contracts_version": config.get("profile_mapper_contracts_version"),
            "contract_policy": config.get("contract_policy"),
            "config_path": str(self.config_path),
            "plans_dir": str(self.plans_dir),
            "contract_count": len(contracts),
            "implemented_contract_count": len(implemented),
            "ready_or_implemented_contract_count": len(ready),
            "required_contract_fields": config.get("required_contract_fields", []),
            "canonical_result_fields": config.get("canonical_result_fields", []),
            "contracts": [self.compact_contract(item) for item in contracts],
            "validation": validation,
            "sdk_status": "implemented_contract_planning_layer",
            "next_engineering_step": "Add an execution adapter that maps a validated contract to a workspace builder without editing core app routes.",
            "approved_review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }

    def contracts(self) -> dict:
        config = self.config()
        if not config:
            return {"ok": False, "error": "profile_mapper_config_not_found", "source_gis_modified": False}
        return {
            "ok": True,
            "profile_mapper_version": PROFILE_MAPPER_VERSION,
            "profile_mapper_contracts_version": config.get("profile_mapper_contracts_version"),
            "contracts": config.get("contracts", []),
            "source_gis_modified": False,
        }

    def contract(self, profile_id: str) -> dict:
        contract = self.find_contract(profile_id)
        if not contract:
            return {"ok": False, "error": "profile_mapper_contract_not_found", "profile_id": profile_id, "source_gis_modified": False}
        return {
            "ok": True,
            "profile_mapper_version": PROFILE_MAPPER_VERSION,
            "contract": contract,
            "source_gis_modified": False,
        }

    def compatibility(self, profile_id: str = "", dataset_id: str = "") -> dict:
        config = self.config()
        if not config:
            return {"ok": False, "error": "profile_mapper_config_not_found", "source_gis_modified": False}
        dataset_id = dataset_id or str(config.get("default_dataset_id") or "")
        source = self.onboarding.source_detail(dataset_id)
        if "error" in source:
            return {"ok": False, **source, "source_gis_modified": False}
        contracts = config.get("contracts", [])
        if profile_id:
            selected = self.find_contract(profile_id)
            if not selected:
                return {"ok": False, "error": "profile_mapper_contract_not_found", "profile_id": profile_id, "source_gis_modified": False}
            contracts = [selected]
        rows = [self.compatibility_row(contract, source) for contract in contracts]
        return {
            "ok": True,
            "profile_mapper_version": PROFILE_MAPPER_VERSION,
            "dataset_id": dataset_id,
            "source_file": source.get("file_name"),
            "source_readiness": source.get("readiness", {}).get("level"),
            "contract_count": len(rows),
            "compatible_contract_count": sum(1 for row in rows if row.get("can_plan")),
            "rows": rows,
            "source_gis_modified": False,
        }

    def mapper_plan(self, body: dict | None = None, write_files: bool = False) -> dict:
        body = body or {}
        config = self.config()
        if not config:
            return {"ok": False, "error": "profile_mapper_config_not_found", "source_gis_modified": False}
        profile_id = str(body.get("profile_id") or "safe_access_pedestrian_review")
        dataset_id = str(body.get("dataset_id") or config.get("default_dataset_id") or "")
        contract = self.find_contract(profile_id)
        if not contract:
            return {"ok": False, "error": "profile_mapper_contract_not_found", "profile_id": profile_id, "source_gis_modified": False}
        compatibility = self.compatibility(profile_id, dataset_id)
        if not compatibility.get("ok"):
            return compatibility
        row = compatibility.get("rows", [{}])[0]
        plan_id = self.next_plan_id(profile_id, dataset_id)
        phases = [
            {"phase": 1, "name": "contract_validation", "status": "ready", "output": "Validate required contract fields and canonical result fields."},
            {"phase": 2, "name": "source_compatibility", "status": "ready" if row.get("can_plan") else "blocked", "output": "Check source layer groups against contract requirements."},
            {"phase": 3, "name": "canonical_mapping", "status": "implemented" if contract.get("status") == "implemented" else "planned", "output": "Map source evidence into canonical outputs."},
            {"phase": 4, "name": "scoring_link", "status": "ready" if contract.get("scoring_profile_id") else "optional", "output": "Link normalized result rows to scoring rules where available."},
            {"phase": 5, "name": "dashboard_contract", "status": "ready", "output": "Expose rows through profile_dashboard_contract_v001."},
        ]
        plan = {
            "ok": True,
            "profile_mapper_version": PROFILE_MAPPER_VERSION,
            "profile_mapper_contracts_version": config.get("profile_mapper_contracts_version"),
            "plan_id": plan_id,
            "created_at_utc": utc_now(),
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "contract_status": contract.get("status"),
            "runner_status": contract.get("runner_status"),
            "mapper_type": contract.get("mapper_type"),
            "can_plan": row.get("can_plan"),
            "blockers": row.get("blockers", []),
            "warnings": row.get("warnings", []),
            "canonical_outputs": contract.get("canonical_outputs", []),
            "result_contract": contract.get("result_contract"),
            "phases": phases,
            "non_goals": [
                "No source GIS files are modified.",
                "No browser upload or public hosting is enabled.",
                "No database credentials are read.",
                "No crash prediction or absolute safety claim is introduced.",
            ],
            "claim_boundaries": contract.get("claim_boundaries", []) + [REVIEW_WORDING],
            "missing_data_policy": contract.get("missing_data_policy"),
            "source_gis_modified": False,
        }
        if write_files:
            self.plans_dir.mkdir(parents=True, exist_ok=True)
            json_path = self.plan_path(plan_id, ".json")
            md_path = self.plan_path(plan_id, ".md")
            json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            md_path.write_text(self.plan_markdown(plan), encoding="utf-8")
            plan["json_file"] = str(json_path)
            plan["markdown_file"] = str(md_path)
        return plan

    def list_plans(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit or 20), 200))
        plans = []
        if not self.plans_dir.exists():
            return plans
        for path in sorted(self.plans_dir.glob("profile_mapper_plan_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("profile_mapper_version") != PROFILE_MAPPER_VERSION:
                continue
            plans.append({
                "ok": True,
                "plan_id": data.get("plan_id"),
                "profile_id": data.get("profile_id"),
                "dataset_id": data.get("dataset_id"),
                "contract_status": data.get("contract_status"),
                "can_plan": data.get("can_plan"),
                "created_at_utc": data.get("created_at_utc"),
                "source_gis_modified": data.get("source_gis_modified") is True,
            })
            if len(plans) >= limit:
                break
        return plans

    def detail(self, plan_id: str) -> dict:
        path = self.plan_path(plan_id, ".json")
        if not path.exists() or not self.safe_plan_path(path):
            return {"ok": False, "error": "profile_mapper_plan_not_found", "plan_id": plan_id, "source_gis_modified": False}
        data = read_json(path)
        if not data:
            return {"ok": False, "error": "profile_mapper_plan_not_found", "plan_id": plan_id, "source_gis_modified": False}
        data["json_file"] = str(path)
        md_path = self.plan_path(plan_id, ".md")
        data["markdown_file"] = str(md_path) if md_path.exists() else ""
        return data

    def find_contract(self, profile_id: str) -> dict:
        for contract in self.config().get("contracts", []):
            if contract.get("profile_id") == profile_id:
                return contract
        return {}

    @staticmethod
    def compact_contract(contract: dict) -> dict:
        requirements = contract.get("source_layer_requirements", {})
        return {
            "profile_id": contract.get("profile_id"),
            "domain": contract.get("domain"),
            "status": contract.get("status"),
            "runner_status": contract.get("runner_status"),
            "mapper_type": contract.get("mapper_type"),
            "required_groups": requirements.get("required_groups", []),
            "optional_groups": requirements.get("optional_groups", []),
            "canonical_outputs": contract.get("canonical_outputs", []),
            "result_contract": contract.get("result_contract"),
            "scoring_profile_id": contract.get("scoring_profile_id"),
        }

    @staticmethod
    def validate_contracts(contracts: list[dict], required_fields: list[str]) -> dict:
        rows = []
        valid_count = 0
        for contract in contracts:
            missing = [field for field in required_fields if field not in contract]
            is_valid = not missing
            if is_valid:
                valid_count += 1
            rows.append({
                "profile_id": contract.get("profile_id"),
                "valid": is_valid,
                "missing_fields": missing,
            })
        return {
            "contract_count": len(contracts),
            "valid_contract_count": valid_count,
            "invalid_contract_count": len(contracts) - valid_count,
            "rows": rows,
        }

    @staticmethod
    def compatibility_row(contract: dict, source: dict) -> dict:
        layers = layer_names(source)
        requirements = contract.get("source_layer_requirements", {})
        required_groups = requirements.get("required_groups", [])
        optional_groups = requirements.get("optional_groups", [])
        missing_required = [group for group in required_groups if not group_available(group, layers, source)]
        available_optional = [group for group in optional_groups if group_available(group, layers, source)]
        warnings = []
        if "osm_pbf_enrichment" in optional_groups and "osm_pbf_enrichment" not in available_optional:
            warnings.append("optional_pbf_enrichment_not_detected")
        if contract.get("status") == "planned":
            warnings.append("contract_runner_not_implemented")
        can_plan = not missing_required
        can_run = can_plan and contract.get("status") == "implemented"
        blockers = [f"missing_layer_group_{group}" for group in missing_required]
        if contract.get("runner_status") == "not_yet_implemented":
            blockers.append("profile_runner_not_implemented")
            can_run = False
        return {
            "profile_id": contract.get("profile_id"),
            "domain": contract.get("domain"),
            "contract_status": contract.get("status"),
            "runner_status": contract.get("runner_status"),
            "required_groups": required_groups,
            "missing_required_groups": missing_required,
            "available_optional_groups": available_optional,
            "required_tags": requirements.get("required_tags", []),
            "optional_tags": requirements.get("optional_tags", []),
            "can_plan": can_plan,
            "can_run": can_run,
            "blockers": blockers,
            "warnings": warnings,
            "source_gis_modified": False,
        }

    @staticmethod
    def plan_markdown(plan: dict) -> str:
        lines = [
            "# Profile Mapper Plan",
            "",
            f"Plan id: `{plan.get('plan_id')}`",
            f"Profile: `{plan.get('profile_id')}`",
            f"Dataset: `{plan.get('dataset_id')}`",
            f"Can plan: `{plan.get('can_plan')}`",
            "",
            "## Phases",
            "",
        ]
        for phase in plan.get("phases", []):
            lines.append(f"{phase.get('phase')}. `{phase.get('name')}` - {phase.get('output')} Status: {phase.get('status')}.")
        lines.extend(["", "## Claim Boundaries", ""])
        for item in plan.get("claim_boundaries", []):
            lines.append(f"- {item}")
        lines.extend(["", "## Missing Data Policy", "", str(plan.get("missing_data_policy") or "")])
        return "\n".join(lines).rstrip() + "\n"

    def next_plan_id(self, profile_id: str, dataset_id: str) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"profile_mapper_plan_{safe_token(profile_id)}_{safe_token(dataset_id)}_{safe_token(stamp)}"

    def plan_path(self, plan_id: str, suffix: str) -> Path:
        return self.plans_dir / f"{safe_token(plan_id)}{suffix}"

    def safe_plan_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.plans_dir.resolve())
            return True
        except ValueError:
            return False
