from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Protocol


PREFLIGHT_VERSION = "safe_access_preflight_v001"

REQUIRED_LAYERS = [
    {
        "layer": "gis_osm_places_a_free_1",
        "purpose": "Pilot area polygon discovery and clipping boundary.",
        "required": True,
    },
    {
        "layer": "gis_osm_roads_free_1",
        "purpose": "Road segments, road class, maxspeed, and oneway fields where available.",
        "required": True,
    },
    {
        "layer": "gis_osm_traffic_free_1",
        "purpose": "Point crossings, traffic signals, calming, and street-lamp evidence where mapped.",
        "required": True,
    },
    {
        "layer": "gis_osm_transport_free_1",
        "purpose": "Point bus stops and public transport stop evidence.",
        "required": True,
    },
    {
        "layer": "gis_osm_pois_free_1",
        "purpose": "Point schools, kindergartens, playgrounds, and other pedestrian generators.",
        "required": True,
    },
    {
        "layer": "gis_osm_pois_a_free_1",
        "purpose": "Polygon schools, kindergartens, playgrounds, and other pedestrian generators.",
        "required": True,
    },
    {
        "layer": "gis_osm_landuse_a_free_1",
        "purpose": "Park, recreation, and land-use context.",
        "required": False,
    },
]


class CatalogLike(Protocol):
    def source_files(self) -> list[dict]:
        ...

    def profile(self, dataset_id: str) -> dict:
        ...


class PilotCatalogLike(Protocol):
    def detail(self, osm_id: str) -> dict:
        ...


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


class SafeAccessPreflight:
    def __init__(
        self,
        catalog: CatalogLike,
        pilots: PilotCatalogLike,
        workspaces_dir: Path,
        default_dataset_id: str,
    ) -> None:
        self.catalog = catalog
        self.pilots = pilots
        self.workspaces_dir = workspaces_dir
        self.default_dataset_id = default_dataset_id

    def safe_access_pilot(
        self,
        pilot_osm_id: str,
        dataset_id: str = "",
        route_aware: bool = True,
        pbf_workspace_id: str = "",
        route_workspace_id: str = "",
    ) -> dict:
        pilot_osm_id = str(pilot_osm_id or "").strip()
        if not pilot_osm_id:
            return {"ok": False, "error": "bad_request", "detail": "pilot_osm_id is required"}

        pilot = self.pilots.detail(pilot_osm_id)
        if "error" in pilot:
            return {"ok": False, **pilot}

        selected_dataset_id = dataset_id or pilot.get("source_dataset_id") or self.default_dataset_id
        profile = self.catalog.profile(selected_dataset_id)
        if "error" in profile:
            return {"ok": False, **profile, "pilot": pilot}

        source = profile.get("dataset", {})
        required_layers = self.required_layer_status(profile.get("layers", []))
        missing_required = [item["layer"] for item in required_layers if item["required"] and not item["present"]]
        pbf_sources = [source_file for source_file in self.catalog.source_files() if source_file.get("extension") == ".osm.pbf"]
        pbf_source = pbf_sources[0] if pbf_sources else None

        pbf_workspace = pbf_workspace_id or str(pilot.get("pbf_enriched_workspace_id") or "")
        route_workspace = route_workspace_id or str(pilot.get("route_aware_workspace_id") or "")
        pbf_exists = self.workspace_exists(pbf_workspace)
        route_exists = self.workspace_exists(route_workspace)
        active_workspace_id = route_workspace if route_aware else pbf_workspace
        active_exists = self.workspace_exists(active_workspace_id)

        bbox = self.pilot_bbox(pilot)
        estimate = self.estimate_runtime(pilot, bbox, pbf_exists, route_exists, route_aware)
        can_start_job = (
            source.get("extension") == ".zip"
            and not missing_required
            and pbf_source is not None
            and bool(pbf_workspace)
            and (not route_aware or bool(route_workspace))
        )

        return {
            "ok": True,
            "preflight_version": PREFLIGHT_VERSION,
            "template_id": "safe_access",
            "pilot": self.pilot_summary(pilot, bbox),
            "dataset": source,
            "required_layers": required_layers,
            "required_layer_status": "ready" if not missing_required else "missing_required_layers",
            "missing_required_layers": missing_required,
            "pbf_enrichment": {
                "required_by_current_mapper": True,
                "available": pbf_source is not None,
                "source": pbf_source,
            },
            "workspaces": {
                "pbf_enriched_workspace_id": pbf_workspace,
                "route_aware_workspace_id": route_workspace,
                "pbf_enriched_exists": pbf_exists,
                "route_aware_exists": route_exists,
                "active_workspace_id": active_workspace_id,
                "active_workspace_exists": active_exists,
                "active_workspace_summary": self.workspace_summary(active_workspace_id),
            },
            "estimate": estimate,
            "warnings": self.warnings(source, missing_required, pbf_source, route_aware, pbf_exists, route_exists),
            "claim_boundaries": [
                "Pilot areas are OSM/Geofabrik place polygons, not official municipal boundaries.",
                "Route-aware metrics are road-network proxy indicators, not verified walking routes.",
                "Infrastructure flags prioritize field review and do not make crash-risk claims.",
                "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
            ],
            "can_start_job": can_start_job,
            "source_gis_modified": False,
        }

    def required_layer_status(self, layers: list[dict]) -> list[dict]:
        by_name = {layer.get("layer"): layer for layer in layers}
        statuses = []
        for expected in REQUIRED_LAYERS:
            layer = by_name.get(expected["layer"], {})
            statuses.append({
                "layer": expected["layer"],
                "purpose": expected["purpose"],
                "required": expected["required"],
                "present": bool(layer),
                "geometry_type": layer.get("geometry_type", ""),
                "feature_count": layer.get("feature_count", 0),
                "crs": layer.get("crs", ""),
            })
        return statuses

    def pilot_summary(self, pilot: dict, bbox: dict) -> dict:
        return {
            "osm_id": str(pilot.get("osm_id") or ""),
            "name": pilot.get("name") or "",
            "fclass": pilot.get("fclass") or "",
            "population": parse_int(pilot.get("population")),
            "source_dataset_id": pilot.get("source_dataset_id") or self.default_dataset_id,
            "source_layer": pilot.get("source_layer") or "",
            "bbox": bbox,
            "source_gis_modified": False,
        }

    def pilot_bbox(self, pilot: dict) -> dict:
        min_lon = parse_float(pilot.get("bbox_min_lon"))
        min_lat = parse_float(pilot.get("bbox_min_lat"))
        max_lon = parse_float(pilot.get("bbox_max_lon"))
        max_lat = parse_float(pilot.get("bbox_max_lat"))
        width_km = max(0.0, (max_lon - min_lon) * 111.32 * math.cos(math.radians((min_lat + max_lat) / 2)))
        height_km = max(0.0, (max_lat - min_lat) * 110.57)
        return {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
            "approx_width_km": round(width_km, 2),
            "approx_height_km": round(height_km, 2),
            "approx_area_km2": round(width_km * height_km, 2),
        }

    def estimate_runtime(self, pilot: dict, bbox: dict, pbf_exists: bool, route_exists: bool, route_aware: bool) -> dict:
        population = parse_int(pilot.get("population"))
        area_km2 = parse_float(bbox.get("approx_area_km2"))
        if route_aware and route_exists:
            runtime_class = "instant"
            operation = "reuse_existing_route_aware_workspace"
        elif not route_aware and pbf_exists:
            runtime_class = "instant"
            operation = "reuse_existing_pbf_enriched_workspace"
        elif route_aware and pbf_exists:
            runtime_class = "small"
            operation = "build_route_aware_workspace_from_existing_pbf_workspace"
        elif population > 250000 or area_km2 > 250:
            runtime_class = "large"
            operation = "build_pbf_enriched_workspace_then_optional_route_aware_workspace"
        elif population > 100000 or area_km2 > 100:
            runtime_class = "medium"
            operation = "build_pbf_enriched_workspace_then_optional_route_aware_workspace"
        else:
            runtime_class = "small"
            operation = "build_pbf_enriched_workspace_then_optional_route_aware_workspace"
        return {
            "runtime_class": runtime_class,
            "expected_operation": operation,
            "basis": {
                "population": population,
                "approx_area_km2": area_km2,
                "pbf_workspace_exists": pbf_exists,
                "route_workspace_exists": route_exists,
                "route_aware_requested": route_aware,
            },
            "note": "Estimate uses catalog metadata and existing workspace manifests only.",
        }

    def warnings(
        self,
        source: dict,
        missing_required: list[str],
        pbf_source: dict | None,
        route_aware: bool,
        pbf_exists: bool,
        route_exists: bool,
    ) -> list[str]:
        warnings = [
            "Pilot boundary source is OSM/Geofabrik, not an official municipal boundary.",
        ]
        if source.get("extension") != ".zip":
            warnings.append("The current selected-pilot mapper expects the Geofabrik Free Shapefile ZIP.")
        if missing_required:
            warnings.append(f"Required source layers are missing: {', '.join(missing_required)}.")
        if pbf_source is None:
            warnings.append("Raw PBF enrichment requires an .osm.pbf file in the inspected maps folder.")
        if not pbf_exists:
            warnings.append("First PBF-enriched build may take minutes because the pilot workspace does not exist yet.")
        if route_aware and not route_exists:
            warnings.append("Route-aware analysis may add time because the route workspace does not exist yet.")
        if route_aware:
            warnings.append("Route-aware metrics are road-network proxy indicators, not verified pedestrian routes.")
        return warnings

    def workspace_exists(self, workspace_id: str) -> bool:
        return bool(workspace_id) and (self.workspaces_dir / workspace_id / "manifest.json").exists()

    def workspace_summary(self, workspace_id: str) -> dict:
        if not workspace_id:
            return {}
        workspace_dir = self.workspaces_dir / workspace_id
        manifest = read_json(workspace_dir / "manifest.json")
        summary = read_json(workspace_dir / "reports" / "workspace_summary.json")
        if not manifest:
            return {}
        return {
            "workspace_id": manifest.get("workspace_id", workspace_id),
            "template_id": manifest.get("template_id"),
            "source_dataset_id": manifest.get("source_dataset_id"),
            "created_at_utc": manifest.get("created_at_utc"),
            "counts": summary.get("counts", {}),
            "route_aware_analysis": summary.get("route_aware_analysis", {}),
        }
