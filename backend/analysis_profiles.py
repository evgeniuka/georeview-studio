from __future__ import annotations

from typing import Protocol


ANALYSIS_PROFILES_VERSION = "analysis_profiles_v002"
SAFE_ACCESS_PROFILE_ID = "safe_access_pedestrian_review"


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


def layer_names(source: dict) -> set[str]:
    return {str(layer.get("layer") or "") for layer in source.get("layers", [])}


def has_any(layers: set[str], *needles: str) -> bool:
    lowered = " ".join(layers).lower()
    return any(needle in lowered for needle in needles)


def capability_flags(source: dict) -> dict:
    layers = layer_names(source)
    readiness = source.get("readiness", {})
    supported = set(readiness.get("supported_templates", []))
    return {
        "has_places": has_any(layers, "places"),
        "has_roads": has_any(layers, "roads"),
        "has_traffic": has_any(layers, "traffic"),
        "has_transport": has_any(layers, "transport"),
        "has_pois": has_any(layers, "pois"),
        "has_landuse": has_any(layers, "landuse"),
        "has_pofw": has_any(layers, "pofw"),
        "has_osm_pbf": str(source.get("extension")) in {".osm.pbf", ".pbf"},
        "supports_safe_access": "safe_access" in supported,
        "supports_osm_quality": "osm_quality" in supported,
        "supports_generic_inventory": "generic_layer_inventory" in supported,
    }


PROFILE_DEFINITIONS = [
    {
        "profile_id": SAFE_ACCESS_PROFILE_ID,
        "legacy_template_id": "safe_access",
        "name": "Safe Access / pedestrian infrastructure review",
        "domain": "pedestrian_access",
        "status": "implemented",
        "runner_status": "implemented_for_selected_pilot",
        "description": "Prioritizes pedestrian infrastructure field-review candidates around schools, childcare, transit stops, parks, playgrounds, crossings, and major roads.",
        "input_needs": [
            "places or pilot polygon",
            "roads",
            "traffic/crossing points",
            "transport stops",
            "POIs and landuse polygons",
            "optional raw OSM PBF enrichment tags",
        ],
        "outputs": [
            "pedestrian_generators",
            "crossings",
            "road_segments",
            "risk_assessment_results",
            "network_access_results when route-aware is enabled",
            "portfolio reports",
        ],
    },
    {
        "profile_id": "transit_stop_walk_access",
        "legacy_template_id": "transit_walk_access",
        "name": "Transit stop walk-access review",
        "domain": "public_transport_access",
        "status": "implemented",
        "runner_status": "implemented_from_safe_access_workspace",
        "description": "Reviews mapped walking access indicators around bus stops and public-transport platforms.",
        "input_needs": ["transport stops", "roads", "crossings", "traffic signals"],
        "outputs": ["transit_stop_access_results", "nearest crossing metrics", "route-aware crossing metrics", "data-quality flags"],
    },
    {
        "profile_id": "park_playground_access",
        "legacy_template_id": "park_playground_access",
        "name": "Park and playground access review",
        "domain": "public_space_access",
        "status": "implemented",
        "runner_status": "implemented_from_safe_access_workspace",
        "description": "Reviews mapped crossings and major-road context around parks, playgrounds, and recreation grounds.",
        "input_needs": ["landuse/leisure polygons", "POIs", "roads", "crossings"],
        "outputs": ["public-space access candidates", "crossing proximity", "major-road context"],
    },
    {
        "profile_id": "cycling_micromobility_access",
        "legacy_template_id": "cycling_micromobility_access",
        "name": "Cycling and micromobility infrastructure review",
        "domain": "cycling_access",
        "status": "planned",
        "runner_status": "not_yet_implemented",
        "description": "Reviews mapped cycleway, bicycle, segregated, and road-class evidence for cycling infrastructure continuity.",
        "input_needs": ["roads", "cycleway tags", "bicycle tags", "crossings"],
        "outputs": ["cycling continuity indicators", "mixed-traffic context", "tag coverage gaps"],
    },
    {
        "profile_id": "osm_tag_quality",
        "legacy_template_id": "osm_quality",
        "name": "OSM tag quality audit",
        "domain": "data_quality",
        "status": "implemented",
        "runner_status": "implemented_read_only_profile",
        "description": "Audits layer inventory and key OSM tag coverage before deciding whether a domain analysis is appropriate.",
        "input_needs": ["any supported GIS/OSM source"],
        "outputs": ["layer inventory", "tag coverage summary", "profile readiness evidence"],
    },
    {
        "profile_id": "generic_layer_inventory",
        "legacy_template_id": "generic_layer_inventory",
        "name": "Generic GIS layer inventory",
        "domain": "data_inventory",
        "status": "profile_ready",
        "runner_status": "read_only_profile_available",
        "description": "Lists layers, geometry types, feature counts, CRS, and basic source suitability.",
        "input_needs": ["any supported GIS source"],
        "outputs": ["source profile", "layer summary", "format suitability"],
    },
]


class AnalysisProfileRegistry:
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

    def list_profiles(self, dataset_id: str = "", pilot_osm_id: str = "", route_aware: object = True) -> dict:
        dataset_id = dataset_id or self.default_dataset_id
        profiles = []
        for definition in PROFILE_DEFINITIONS:
            readiness = self.readiness(definition["profile_id"], dataset_id, pilot_osm_id, route_aware)
            profiles.append({
                **self.compact_definition(definition),
                "readiness_level": readiness.get("readiness_level"),
                "can_plan": readiness.get("can_plan") is True,
                "can_run": readiness.get("can_run") is True,
                "blockers": readiness.get("blockers", []),
            })
        return {
            "ok": True,
            "analysis_profiles_version": ANALYSIS_PROFILES_VERSION,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "profiles": profiles,
            "source_gis_modified": False,
        }

    def detail(self, profile_id: str, dataset_id: str = "", pilot_osm_id: str = "", route_aware: object = True) -> dict:
        definition = self.definition(profile_id)
        if not definition:
            return {"error": "analysis_profile_not_found", "profile_id": profile_id}
        return {
            "ok": True,
            "analysis_profiles_version": ANALYSIS_PROFILES_VERSION,
            **definition,
            "readiness": self.readiness(profile_id, dataset_id or self.default_dataset_id, pilot_osm_id, route_aware),
            "source_gis_modified": False,
        }

    def readiness(self, profile_id: str, dataset_id: str = "", pilot_osm_id: str = "", route_aware: object = True) -> dict:
        definition = self.definition(profile_id)
        if not definition:
            return {"error": "analysis_profile_not_found", "profile_id": profile_id}
        dataset_id = dataset_id or self.default_dataset_id
        source = self.onboarding.source_detail(dataset_id)
        if "error" in source:
            return {"ok": False, **source, "profile_id": profile_id, "source_gis_modified": False}
        flags = capability_flags(source)
        if profile_id == SAFE_ACCESS_PROFILE_ID:
            return self.safe_access_readiness(definition, source, flags, pilot_osm_id, route_aware)
        if profile_id == "transit_stop_walk_access":
            required = ["has_transport", "has_roads", "has_traffic"]
            return self.profile_readiness(definition, source, flags, required, can_plan=True, can_run=True)
        if profile_id == "park_playground_access":
            required = ["has_landuse", "has_pois", "has_roads", "has_traffic"]
            return self.profile_readiness(definition, source, flags, required, can_plan=True, can_run=True)
        if profile_id == "cycling_micromobility_access":
            required = ["has_roads"]
            result = self.profile_readiness(definition, source, flags, required, can_plan=False)
            result["blockers"].append("cycleway_tag_extraction_runner_not_implemented")
            return result
        if profile_id == "osm_tag_quality":
            required = []
            return self.profile_readiness(definition, source, flags, required, can_plan=True, can_run=bool(source.get("layers")))
        if profile_id == "generic_layer_inventory":
            required = []
            return self.profile_readiness(definition, source, flags, required, can_plan=True, can_run=bool(source.get("layers")))
        return {"error": "analysis_profile_not_found", "profile_id": profile_id}

    def safe_access_readiness(self, definition: dict, source: dict, flags: dict, pilot_osm_id: str, route_aware: object) -> dict:
        blockers = []
        if not flags["supports_safe_access"]:
            blockers.append("source_does_not_support_safe_access")
        preflight = {}
        pilot = {}
        if pilot_osm_id:
            pilot = self.pilots.detail(pilot_osm_id)
            if "error" in pilot:
                blockers.append("pilot_area_not_found")
            else:
                preflight = self.preflight.safe_access_pilot(
                    pilot_osm_id=pilot_osm_id,
                    dataset_id=source.get("dataset_id") or self.default_dataset_id,
                    route_aware=boolish(route_aware),
                )
                if not preflight.get("can_start_job"):
                    blockers.append("safe_access_preflight_not_ready")
        else:
            blockers.append("pilot_area_required_for_safe_access_run")
        can_run = flags["supports_safe_access"] and bool(pilot_osm_id) and not blockers
        readiness_level = "ready_to_run" if can_run else "ready_to_plan" if flags["supports_safe_access"] else "not_ready"
        return {
            "ok": True,
            "profile_id": definition["profile_id"],
            "legacy_template_id": definition["legacy_template_id"],
            "dataset_id": source.get("dataset_id"),
            "readiness_level": readiness_level,
            "can_plan": flags["supports_safe_access"],
            "can_run": can_run,
            "implemented_runner": True,
            "blockers": blockers,
            "evidence": {
                "source_file": source.get("file_name"),
                "source_readiness": source.get("readiness", {}).get("level"),
                "layer_count": len(source.get("layers", [])),
                "capabilities": flags,
                "pilot": {
                    "osm_id": pilot.get("osm_id"),
                    "name": pilot.get("name"),
                    "fclass": pilot.get("fclass"),
                } if pilot and "error" not in pilot else {},
                "preflight_can_start_job": preflight.get("can_start_job"),
                "active_workspace_id": preflight.get("workspaces", {}).get("active_workspace_id") if preflight else "",
            },
            "recommended_next_action": "start_analysis_job" if can_run else "select_pilot_area_or_fix_source",
            "source_gis_modified": False,
        }

    @staticmethod
    def profile_readiness(
        definition: dict,
        source: dict,
        flags: dict,
        required_flags: list[str],
        can_plan: bool,
        can_run: bool = False,
    ) -> dict:
        missing = [flag for flag in required_flags if not flags.get(flag)]
        blockers = []
        if missing:
            blockers.extend(f"missing_{flag.removeprefix('has_')}" for flag in missing)
        if definition.get("runner_status") == "not_yet_implemented":
            blockers.append("profile_runner_not_implemented")
        evidence_present = not missing
        return {
            "ok": True,
            "profile_id": definition["profile_id"],
            "legacy_template_id": definition["legacy_template_id"],
            "dataset_id": source.get("dataset_id"),
            "readiness_level": "profile_evidence_available" if evidence_present else "not_ready",
            "can_plan": bool(can_plan and evidence_present),
            "can_run": bool(can_run and evidence_present and not blockers),
            "implemented_runner": definition.get("runner_status") not in {"not_yet_implemented"},
            "blockers": blockers,
            "evidence": {
                "source_file": source.get("file_name"),
                "source_readiness": source.get("readiness", {}).get("level"),
                "layer_count": len(source.get("layers", [])),
                "capabilities": flags,
                "required_flags": required_flags,
                "missing_required_flags": missing,
            },
            "recommended_next_action": "inspect_profile_evidence" if evidence_present else "provide_required_layers",
            "source_gis_modified": False,
        }

    @staticmethod
    def compact_definition(definition: dict) -> dict:
        return {
            "profile_id": definition["profile_id"],
            "legacy_template_id": definition["legacy_template_id"],
            "name": definition["name"],
            "domain": definition["domain"],
            "status": definition["status"],
            "runner_status": definition["runner_status"],
            "description": definition["description"],
            "input_needs": definition["input_needs"],
            "outputs": definition["outputs"],
        }

    @staticmethod
    def definition(profile_id: str) -> dict:
        clean = str(profile_id or "").strip()
        for definition in PROFILE_DEFINITIONS:
            if clean in {definition["profile_id"], definition["legacy_template_id"]}:
                return dict(definition)
        return {}
