from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


CONTRACT_EXECUTION_VERSION = "contract_execution_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "contract_execution") -> str:
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


class ContractExecutionAdapter:
    def __init__(self, profile_mapper: object, output_root: Path, workspaces_dir: Path) -> None:
        self.profile_mapper = profile_mapper
        self.output_root = output_root
        self.workspaces_dir = workspaces_dir
        self.dry_runs_dir = output_root / "georeview_studio_contract_execution_dry_runs"

    def status(self) -> dict:
        adapters = self.adapters()
        mapper = self.profile_mapper.overview()
        executable = [adapter for adapter in adapters if adapter.get("execution_status") in {"dry_run_ready_existing_runner", "dry_run_ready_read_only_runner"}]
        return {
            "ok": True,
            "contract_execution_version": CONTRACT_EXECUTION_VERSION,
            "mode": "dry_run_only_no_source_mutation",
            "adapter_count": len(adapters),
            "executable_now_count": len(executable),
            "profile_mapper_contracts_version": mapper.get("profile_mapper_contracts_version"),
            "contract_count": mapper.get("contract_count"),
            "dry_runs_dir": str(self.dry_runs_dir),
            "adapters": adapters,
            "policy": {
                "dry_run_only": True,
                "source_gis_modified": False,
                "writes_only_small_plans_under_analysis_output": True,
                "no_credentials_required": True,
            },
            "next_engineering_step": "Convert the dry-run adapter matrix into a controlled execution queue for implemented runners.",
            "approved_review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }

    def adapters_response(self) -> dict:
        return {
            "ok": True,
            "contract_execution_version": CONTRACT_EXECUTION_VERSION,
            "adapters": self.adapters(),
            "source_gis_modified": False,
        }

    @staticmethod
    def adapters() -> list[dict]:
        return [
            {
                "profile_id": "safe_access_pedestrian_review",
                "adapter_id": "safe_access_workspace_runner",
                "backend_entrypoint": "WorkspaceRunner.ensure_workspace",
                "execution_status": "dry_run_ready_existing_runner",
                "writes_if_executed": ["generated workspace CSV", "workspace manifest", "quality reports"],
            },
            {
                "profile_id": "transit_stop_walk_access",
                "adapter_id": "transit_access_analyzer",
                "backend_entrypoint": "TransitAccessAnalyzer.ensure_workspace",
                "execution_status": "dry_run_ready_existing_runner",
                "writes_if_executed": ["profile workspace CSV", "profile manifest", "profile summary"],
            },
            {
                "profile_id": "park_playground_access",
                "adapter_id": "park_playground_access_analyzer",
                "backend_entrypoint": "ParkPlaygroundAccessAnalyzer.ensure_workspace",
                "execution_status": "dry_run_ready_existing_runner",
                "writes_if_executed": ["profile workspace CSV", "profile manifest", "profile summary"],
            },
            {
                "profile_id": "cycling_micromobility_access",
                "adapter_id": "planned_cycling_mapper",
                "backend_entrypoint": "",
                "execution_status": "blocked_runner_not_implemented",
                "writes_if_executed": [],
            },
            {
                "profile_id": "osm_tag_quality",
                "adapter_id": "osm_tag_quality_analyzer",
                "backend_entrypoint": "OSMTagQualityAnalyzer.ensure_workspace",
                "execution_status": "dry_run_ready_read_only_runner",
                "writes_if_executed": ["profile workspace CSV", "profile manifest", "tag quality report"],
            },
            {
                "profile_id": "generic_layer_inventory",
                "adapter_id": "planned_layer_inventory_audit",
                "backend_entrypoint": "",
                "execution_status": "planning_ready_no_runner",
                "writes_if_executed": [],
            },
        ]

    def dry_run(self, body: dict | None = None, write_files: bool = False) -> dict:
        body = body or {}
        profile_id = str(body.get("profile_id") or "safe_access_pedestrian_review")
        dataset_id = str(body.get("dataset_id") or "israel-and-palestine-260521-free-shp-zip")
        pilot_osm_id = str(body.get("pilot_osm_id") or "53796999")
        target_workspace_id = str(body.get("target_workspace_id") or self.default_workspace_id(profile_id))
        contract_payload = self.profile_mapper.contract(profile_id)
        if contract_payload.get("error"):
            return contract_payload
        compatibility = self.profile_mapper.compatibility(profile_id=profile_id, dataset_id=dataset_id)
        if compatibility.get("error"):
            return compatibility
        adapter = self.adapter_for_profile(profile_id)
        if not adapter:
            return {"ok": False, "error": "contract_execution_adapter_not_found", "profile_id": profile_id, "source_gis_modified": False}
        compatibility_row = compatibility.get("rows", [{}])[0]
        adapter_ready = adapter.get("execution_status") in {"dry_run_ready_existing_runner", "dry_run_ready_read_only_runner"}
        can_execute_now = bool(compatibility_row.get("can_plan") and adapter_ready)
        blockers = list(compatibility_row.get("blockers", []))
        if not adapter_ready:
            blockers.append(adapter.get("execution_status"))
        dry_run_id = self.next_dry_run_id(profile_id, dataset_id)
        steps = [
            {"step": 1, "name": "contract_validation", "status": "passed", "evidence": contract_payload.get("contract", {}).get("result_contract")},
            {"step": 2, "name": "source_compatibility", "status": "passed" if compatibility_row.get("can_plan") else "blocked", "evidence": compatibility_row.get("required_groups", [])},
            {"step": 3, "name": "runner_binding", "status": "passed" if adapter_ready else "blocked", "evidence": adapter.get("backend_entrypoint")},
            {"step": 4, "name": "workspace_target", "status": "planned", "evidence": target_workspace_id},
            {"step": 5, "name": "output_contract", "status": "planned", "evidence": contract_payload.get("contract", {}).get("canonical_outputs", [])},
            {"step": 6, "name": "read_only_policy", "status": "passed", "evidence": "source_gis_modified=false"},
        ]
        dry_run = {
            "ok": True,
            "contract_execution_version": CONTRACT_EXECUTION_VERSION,
            "dry_run_id": dry_run_id,
            "created_at_utc": utc_now(),
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "target_workspace_id": target_workspace_id,
            "adapter": adapter,
            "can_execute_now": can_execute_now,
            "dry_run_only": True,
            "would_call": adapter.get("backend_entrypoint"),
            "would_write": adapter.get("writes_if_executed", []),
            "would_not_modify": ["source GIS files", "credentials", "environment files", "public hosting settings"],
            "blockers": blockers,
            "steps": steps,
            "review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }
        if write_files:
            self.dry_runs_dir.mkdir(parents=True, exist_ok=True)
            json_path = self.dry_run_path(dry_run_id, ".json")
            md_path = self.dry_run_path(dry_run_id, ".md")
            json_path.write_text(json.dumps(dry_run, ensure_ascii=False, indent=2), encoding="utf-8")
            md_path.write_text(self.dry_run_markdown(dry_run), encoding="utf-8")
            dry_run["json_file"] = str(json_path)
            dry_run["markdown_file"] = str(md_path)
        return dry_run

    def list_dry_runs(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit or 20), 200))
        rows = []
        if not self.dry_runs_dir.exists():
            return rows
        for path in sorted(self.dry_runs_dir.glob("contract_execution_dry_run_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("contract_execution_version") != CONTRACT_EXECUTION_VERSION:
                continue
            rows.append({
                "ok": True,
                "dry_run_id": data.get("dry_run_id"),
                "profile_id": data.get("profile_id"),
                "dataset_id": data.get("dataset_id"),
                "target_workspace_id": data.get("target_workspace_id"),
                "can_execute_now": data.get("can_execute_now"),
                "created_at_utc": data.get("created_at_utc"),
                "source_gis_modified": data.get("source_gis_modified") is True,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, dry_run_id: str) -> dict:
        path = self.dry_run_path(dry_run_id, ".json")
        if not path.exists() or not self.safe_dry_run_path(path):
            return {"ok": False, "error": "contract_execution_dry_run_not_found", "dry_run_id": dry_run_id, "source_gis_modified": False}
        data = read_json(path)
        if not data:
            return {"ok": False, "error": "contract_execution_dry_run_not_found", "dry_run_id": dry_run_id, "source_gis_modified": False}
        data["json_file"] = str(path)
        md_path = self.dry_run_path(dry_run_id, ".md")
        data["markdown_file"] = str(md_path) if md_path.exists() else ""
        return data

    def adapter_for_profile(self, profile_id: str) -> dict:
        for adapter in self.adapters():
            if adapter.get("profile_id") == profile_id:
                return adapter
        return {}

    @staticmethod
    def default_workspace_id(profile_id: str) -> str:
        mapping = {
            "safe_access_pedestrian_review": "safe_access_kfar_saba_route_aware_v001",
            "transit_stop_walk_access": "transit_stop_walk_access_kfar_saba_v001",
            "park_playground_access": "park_playground_access_kfar_saba_v001",
            "osm_tag_quality": "osm_tag_quality_kfar_saba_v001",
        }
        return mapping.get(profile_id, f"{safe_token(profile_id)}_workspace_v001")

    @staticmethod
    def dry_run_markdown(dry_run: dict) -> str:
        lines = [
            "# Contract Execution Dry Run",
            "",
            f"Dry run id: `{dry_run.get('dry_run_id')}`",
            f"Profile: `{dry_run.get('profile_id')}`",
            f"Dataset: `{dry_run.get('dataset_id')}`",
            f"Can execute now: `{dry_run.get('can_execute_now')}`",
            "",
            "## Steps",
            "",
        ]
        for step in dry_run.get("steps", []):
            lines.append(f"{step.get('step')}. `{step.get('name')}` - Status: {step.get('status')}. Evidence: `{step.get('evidence')}`.")
        lines.extend([
            "",
            "## Boundaries",
            "",
            "- Dry run only.",
            "- Source GIS files are not modified.",
            f"- {REVIEW_WORDING}",
        ])
        return "\n".join(lines).rstrip() + "\n"

    def next_dry_run_id(self, profile_id: str, dataset_id: str) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"contract_execution_dry_run_{safe_token(profile_id)}_{safe_token(dataset_id)}_{safe_token(stamp)}"

    def dry_run_path(self, dry_run_id: str, suffix: str) -> Path:
        return self.dry_runs_dir / f"{safe_token(dry_run_id)}{suffix}"

    def safe_dry_run_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.dry_runs_dir.resolve())
            return True
        except ValueError:
            return False
