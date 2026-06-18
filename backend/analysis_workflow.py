from __future__ import annotations

from typing import Protocol


WORKFLOW_VERSION = "analysis_workflow_v001"


class OnboardingLike(Protocol):
    def source_detail(self, dataset_id: str) -> dict:
        ...


class PilotCatalogLike(Protocol):
    def detail(self, osm_id: str) -> dict:
        ...


class PreflightLike(Protocol):
    def safe_access_pilot(
        self,
        pilot_osm_id: str,
        dataset_id: str = "",
        route_aware: bool = True,
        pbf_workspace_id: str = "",
        route_workspace_id: str = "",
    ) -> dict:
        ...


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


class AnalysisWorkflow:
    def __init__(
        self,
        onboarding: OnboardingLike,
        pilots: PilotCatalogLike,
        preflight: PreflightLike,
        default_dataset_id: str,
    ) -> None:
        self.onboarding = onboarding
        self.pilots = pilots
        self.preflight = preflight
        self.default_dataset_id = default_dataset_id

    def plan(self, body: dict) -> dict:
        template_id = str(body.get("template_id") or "safe_access")
        dataset_id = str(body.get("dataset_id") or self.default_dataset_id)
        pilot_osm_id = str(body.get("pilot_osm_id") or "").strip()
        route_aware = boolish(body.get("route_aware", True))

        if template_id != "safe_access":
            return {
                "ok": False,
                "error": "template_not_implemented",
                "template_id": template_id,
                "implemented_templates": ["safe_access"],
                "source_gis_modified": False,
            }
        if not pilot_osm_id:
            return {"ok": False, "error": "bad_request", "detail": "pilot_osm_id is required"}

        source = self.onboarding.source_detail(dataset_id)
        if "error" in source:
            return {"ok": False, **source, "source_gis_modified": False}

        pilot = self.pilots.detail(pilot_osm_id)
        if "error" in pilot:
            return {"ok": False, **pilot, "source_gis_modified": False}

        preflight = self.preflight.safe_access_pilot(
            pilot_osm_id=pilot_osm_id,
            dataset_id=dataset_id,
            route_aware=route_aware,
            pbf_workspace_id=str(body.get("workspace_id") or pilot.get("pbf_enriched_workspace_id") or ""),
            route_workspace_id=str(body.get("route_workspace_id") or pilot.get("route_aware_workspace_id") or ""),
        )
        if not preflight.get("ok"):
            return {"ok": False, "error": preflight.get("error", "preflight_failed"), "preflight": preflight}

        readiness = source.get("readiness", {})
        source_ready = "safe_access" in readiness.get("supported_templates", [])
        can_start = bool(source_ready and preflight.get("can_start_job"))
        job_payload = {
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "pilot_name": pilot.get("name") or pilot_osm_id,
            "workspace_id": preflight.get("workspaces", {}).get("pbf_enriched_workspace_id"),
            "route_workspace_id": preflight.get("workspaces", {}).get("route_aware_workspace_id"),
            "route_aware": route_aware,
            "template_id": template_id,
        }
        blockers = []
        if not source_ready:
            blockers.append("selected_source_does_not_support_safe_access_template")
        if not preflight.get("can_start_job"):
            blockers.append("pilot_preflight_not_ready")
        return {
            "ok": True,
            "workflow_version": WORKFLOW_VERSION,
            "template_id": template_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "route_aware": route_aware,
            "source": self.source_summary(source),
            "pilot": {
                "osm_id": pilot.get("osm_id"),
                "name": pilot.get("name"),
                "fclass": pilot.get("fclass"),
                "population": pilot.get("population"),
            },
            "preflight": preflight,
            "steps": self.steps(source_ready, preflight, can_start),
            "job_payload": job_payload,
            "can_start_job": can_start,
            "blockers": blockers,
            "recommended_action": "start_analysis_job" if can_start else "fix_blockers_before_start",
            "active_workspace_id": preflight.get("workspaces", {}).get("active_workspace_id"),
            "source_gis_modified": False,
        }

    @staticmethod
    def source_summary(source: dict) -> dict:
        readiness = source.get("readiness", {})
        return {
            "dataset_id": source.get("dataset_id"),
            "file_name": source.get("file_name"),
            "extension": source.get("extension"),
            "size_mb": source.get("size_mb"),
            "profile_status": source.get("profile_status"),
            "layer_count": len(source.get("layers", [])),
            "readiness_level": readiness.get("level"),
            "supported_templates": readiness.get("supported_templates", []),
            "blockers": readiness.get("blockers", []),
        }

    @staticmethod
    def steps(source_ready: bool, preflight: dict, can_start: bool) -> list[dict]:
        active_exists = preflight.get("workspaces", {}).get("active_workspace_exists")
        return [
            {
                "step": "source_onboarding",
                "status": "ready" if source_ready else "blocked",
                "evidence": "Selected source profile includes the safe_access template.",
            },
            {
                "step": "pilot_preflight",
                "status": "ready" if preflight.get("can_start_job") else "blocked",
                "evidence": preflight.get("required_layer_status"),
            },
            {
                "step": "background_job",
                "status": "ready_to_start" if can_start else "waiting",
                "evidence": preflight.get("estimate", {}).get("expected_operation"),
            },
            {
                "step": "dashboard_workspace",
                "status": "already_available" if active_exists else "will_be_created",
                "evidence": preflight.get("workspaces", {}).get("active_workspace_id"),
            },
        ]
