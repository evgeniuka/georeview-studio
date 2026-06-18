from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


POSTGIS_BACKEND_PLANNER_VERSION = "postgis_backend_planner_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "postgis_plan") -> str:
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


class PostGISBackendPlanner:
    def __init__(self, schema_path: Path, output_root: Path, workspaces_dir: Path, onboarding: object, profile_dashboard: object, scoring_rules: object) -> None:
        self.schema_path = schema_path
        self.output_root = output_root
        self.workspaces_dir = workspaces_dir
        self.onboarding = onboarding
        self.profile_dashboard = profile_dashboard
        self.scoring_rules = scoring_rules
        self.plans_dir = output_root / "georeview_studio_postgis_plans"

    def status(self) -> dict:
        readiness = self.readiness()
        return {
            "ok": True,
            "postgis_backend_planner_version": POSTGIS_BACKEND_PLANNER_VERSION,
            "mode": "planning_only_no_database_connection",
            "connection_status": "not_configured",
            "schema_path": str(self.schema_path),
            "plans_dir": str(self.plans_dir),
            "readiness": readiness,
            "source_gis_modified": False,
        }

    def schema(self) -> dict:
        if not self.schema_path.exists():
            return {"ok": False, "error": "postgis_schema_not_found", "schema_path": str(self.schema_path), "source_gis_modified": False}
        sql = self.schema_path.read_text(encoding="utf-8")
        tables = re.findall(r"CREATE TABLE IF NOT EXISTS georeview\.([a-z_]+)", sql)
        indexes = re.findall(r"CREATE INDEX IF NOT EXISTS ([a-z_]+)", sql)
        extensions = re.findall(r"CREATE EXTENSION IF NOT EXISTS ([a-z_]+)", sql)
        return {
            "ok": True,
            "postgis_backend_planner_version": POSTGIS_BACKEND_PLANNER_VERSION,
            "schema_version": "postgis_schema_v001",
            "schema_path": str(self.schema_path),
            "table_count": len(tables),
            "tables": tables,
            "index_count": len(indexes),
            "indexes": indexes,
            "extensions": extensions,
            "sql": sql,
            "source_gis_modified": False,
        }

    def readiness(self) -> dict:
        schema = self.schema()
        source_status = self.onboarding.status()
        profile_overview = self.profile_dashboard.overview()
        profile_rows = sum(int(profile.get("result_count") or 0) for profile in profile_overview.get("profiles", []))
        workspace_count = len(list(self.workspaces_dir.glob("*/manifest.json"))) if self.workspaces_dir.exists() else 0
        blockers = ["database_connection_not_configured", "etl_loader_not_implemented"]
        return {
            "ok": True,
            "readiness_level": "ready_for_schema_review_not_database_execution",
            "supported_now": "partially_supported",
            "connection_status": "not_configured",
            "schema_available": schema.get("ok") is True,
            "schema_table_count": schema.get("table_count", 0),
            "source_count": source_status.get("source_count", 0),
            "workspace_count": workspace_count,
            "profile_count": profile_overview.get("implemented_profile_count", 0),
            "profile_result_rows": profile_rows,
            "estimated_initial_rows": self.estimated_initial_rows(profile_overview),
            "blockers": blockers,
            "recommended_next_action": "Review schema and migration plan, then implement a local ETL loader before connecting to a real PostGIS database.",
            "source_gis_modified": False,
        }

    def migration_plan(self, body: dict | None = None, write_files: bool = False) -> dict:
        body = body or {}
        scope = str(body.get("scope") or "kfar_saba_pilot")
        schema = self.schema()
        if schema.get("error"):
            return schema
        readiness = self.readiness()
        plan_id = self.next_plan_id(scope)
        phases = [
            {"phase": 1, "name": "schema_review", "output": "Review SQL schema and indexes.", "status": "ready"},
            {"phase": 2, "name": "local_csv_to_stage_tables", "output": "Load generated workspace CSV tables into staging tables.", "status": "planned"},
            {"phase": 3, "name": "geometry_cast_and_index", "output": "Cast WKT to PostGIS geometry and build GiST/GIN indexes.", "status": "planned"},
            {"phase": 4, "name": "profile_result_materialization", "output": "Materialize normalized profile result rows.", "status": "planned"},
            {"phase": 5, "name": "api_backend_switch", "output": "Add optional PostGIS query backend while keeping local CSV backend available.", "status": "planned"},
        ]
        plan = {
            "ok": True,
            "postgis_backend_planner_version": POSTGIS_BACKEND_PLANNER_VERSION,
            "plan_id": plan_id,
            "scope": scope,
            "created_at_utc": utc_now(),
            "schema_version": schema.get("schema_version"),
            "table_count": schema.get("table_count"),
            "index_count": schema.get("index_count"),
            "readiness": readiness,
            "phases": phases,
            "non_goals": [
                "No database connection is opened by this planner.",
                "No credentials or environment files are required.",
                "No source GIS files are modified.",
                "No public hosting or production deployment is configured.",
            ],
            "claim_boundaries": [
                "PostGIS improves storage and spatial-query scale.",
                "It does not change the meaning of infrastructure review indicators.",
                "It does not make the project a crash prediction model.",
                REVIEW_WORDING,
            ],
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
        for path in sorted(self.plans_dir.glob("postgis_plan_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("postgis_backend_planner_version") != POSTGIS_BACKEND_PLANNER_VERSION:
                continue
            plans.append(self.compact_plan(data))
            if len(plans) >= limit:
                break
        return plans

    def detail(self, plan_id: str) -> dict:
        path = self.plan_path(plan_id, ".json")
        if not path.exists() or not self.safe_plan_path(path):
            return {"ok": False, "error": "postgis_plan_not_found", "plan_id": plan_id, "source_gis_modified": False}
        data = read_json(path)
        if not data:
            return {"ok": False, "error": "postgis_plan_not_found", "plan_id": plan_id, "source_gis_modified": False}
        data["json_file"] = str(path)
        md_path = self.plan_path(plan_id, ".md")
        data["markdown_file"] = str(md_path) if md_path.exists() else ""
        return data

    @staticmethod
    def estimated_initial_rows(profile_overview: dict) -> dict:
        profiles = profile_overview.get("profiles", [])
        return {
            "source_datasets": 2,
            "dataset_layers": 20,
            "pedestrian_generators": 391,
            "crossings": 342,
            "road_segments": 2603,
            "profile_results": sum(int(profile.get("result_count") or 0) for profile in profiles),
            "analysis_runs": "current generated run registry",
        }

    @staticmethod
    def compact_plan(plan: dict) -> dict:
        return {
            "ok": True,
            "plan_id": plan.get("plan_id"),
            "scope": plan.get("scope"),
            "schema_version": plan.get("schema_version"),
            "table_count": plan.get("table_count"),
            "index_count": plan.get("index_count"),
            "created_at_utc": plan.get("created_at_utc"),
            "source_gis_modified": plan.get("source_gis_modified") is True,
        }

    @staticmethod
    def plan_markdown(plan: dict) -> str:
        lines = [
            "# PostGIS Migration Plan",
            "",
            f"Plan id: `{plan.get('plan_id')}`",
            f"Scope: `{plan.get('scope')}`",
            f"Schema: `{plan.get('schema_version')}`",
            "",
            "## Phases",
            "",
        ]
        for phase in plan.get("phases", []):
            lines.append(f"{phase.get('phase')}. `{phase.get('name')}` - {phase.get('output')} Status: {phase.get('status')}.")
        lines.extend([
            "",
            "## Non Goals",
            "",
        ])
        for item in plan.get("non_goals", []):
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## Claim Boundaries",
            "",
        ])
        for item in plan.get("claim_boundaries", []):
            lines.append(f"- {item}")
        return "\n".join(lines).rstrip() + "\n"

    def next_plan_id(self, scope: str) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"postgis_plan_{safe_token(scope)}_{safe_token(stamp)}"

    def plan_path(self, plan_id: str, suffix: str) -> Path:
        return self.plans_dir / f"{safe_token(plan_id)}{suffix}"

    def safe_plan_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.plans_dir.resolve())
            return True
        except ValueError:
            return False
