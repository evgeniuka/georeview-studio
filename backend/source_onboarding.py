from __future__ import annotations

import csv
import json
import sqlite3
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ONBOARDING_VERSION = "source_onboarding_v001"
SUPPORTED_EXTENSIONS = {".zip", ".osm.pbf", ".pbf", ".gpkg", ".shp", ".geojson", ".json"}
EXCLUDED_DIR_NAMES = {"analysis_output"}
# The app release folder itself is never a GIS source. On the original layout it
# lives under analysis_output and is excluded implicitly; exclude it explicitly so
# scans stay correct when the release folder sits directly under the maps root.
APP_RELEASE_DIR = Path(__file__).resolve().parents[1]
SAFE_ACCESS_REQUIRED_LAYERS = {
    "gis_osm_places_a_free_1",
    "gis_osm_roads_free_1",
    "gis_osm_traffic_free_1",
    "gis_osm_transport_free_1",
    "gis_osm_pois_free_1",
    "gis_osm_pois_a_free_1",
}


def slug(value: str) -> str:
    chars = []
    for char in value.lower():
        chars.append(char if char.isalnum() else "-")
    return "-".join(part for part in "".join(chars).split("-") if part) or "dataset"


def modified_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def shape_type_name(shape_type: int) -> str:
    return {
        0: "Null",
        1: "Point",
        3: "PolyLine",
        5: "Polygon",
        8: "MultiPoint",
        11: "PointZ",
        13: "PolyLineZ",
        15: "PolygonZ",
        18: "MultiPointZ",
        21: "PointM",
        23: "PolyLineM",
        25: "PolygonM",
        28: "MultiPointM",
        31: "MultiPatch",
    }.get(shape_type, f"shape_type_{shape_type}")


def dbf_record_count(data: bytes) -> int:
    if len(data) < 8:
        return 0
    return struct.unpack("<I", data[4:8])[0]


def shp_header(data: bytes) -> dict:
    if len(data) < 100:
        return {}
    shape_type = struct.unpack("<i", data[32:36])[0]
    min_x, min_y, max_x, max_y = struct.unpack("<4d", data[36:68])
    area_hint = max(0.0, (max_x - min_x) * (max_y - min_y))
    return {
        "shape_type": shape_type,
        "geometry_type": shape_type_name(shape_type),
        "bbox": {
            "min_x": round(min_x, 7),
            "min_y": round(min_y, 7),
            "max_x": round(max_x, 7),
            "max_y": round(max_y, 7),
        },
        "bbox_area_degrees": round(area_hint, 7),
    }


def prj_crs_hint(text: str) -> str:
    lowered = text.lower()
    if "wgs_1984" in lowered or "wgs 84" in lowered:
        return "EPSG:4326_or_WGS84"
    if "israel" in lowered and ("itm" in lowered or "transverse_mercator" in lowered):
        return "Israeli_projected_crs_hint"
    return "unknown_from_prj_text"


class SourceOnboarding:
    def __init__(self, maps_root: Path, output_root: Path) -> None:
        self.maps_root = maps_root
        self.output_root = output_root
        self.catalog_dir = output_root / "georeview_studio_source_onboarding"
        self.catalog_path = self.catalog_dir / "source_onboarding_catalog.json"
        self.sources_csv_path = self.catalog_dir / "source_onboarding_sources.csv"

    def status(self) -> dict:
        cached = self.read_cache()
        if cached:
            return {
                "ok": True,
                "onboarding_version": cached.get("onboarding_version"),
                "cached": True,
                "created_at_utc": cached.get("created_at_utc"),
                "source_count": len(cached.get("sources", [])),
                "catalog_path": str(self.catalog_path),
                "sources_csv_path": str(self.sources_csv_path),
                "source_gis_modified": False,
            }
        scanned = self.scan()
        return {
            "ok": True,
            "onboarding_version": ONBOARDING_VERSION,
            "cached": False,
            "source_count": len(scanned.get("sources", [])),
            "catalog_path": str(self.catalog_path),
            "sources_csv_path": str(self.sources_csv_path),
            "source_gis_modified": False,
        }

    def refresh(self) -> dict:
        catalog = self.scan()
        self.catalog_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        self.write_sources_csv(catalog.get("sources", []))
        return {
            "ok": True,
            "created_at_utc": catalog["created_at_utc"],
            "source_count": len(catalog.get("sources", [])),
            "catalog_path": str(self.catalog_path),
            "sources_csv_path": str(self.sources_csv_path),
            "source_gis_modified": False,
        }

    def sources(self, use_cache: bool = True) -> list[dict]:
        cached = self.read_cache() if use_cache else {}
        if cached:
            return cached.get("sources", [])
        return self.scan().get("sources", [])

    def source_detail(self, dataset_id: str) -> dict:
        for source in self.sources():
            if source.get("dataset_id") == dataset_id:
                return source
        return {"error": "dataset_not_found", "dataset_id": dataset_id}

    def scan(self) -> dict:
        files = list(self.iter_source_files())
        pbf_available = any(path.suffix.lower() in {".pbf"} or path.name.lower().endswith(".osm.pbf") for path in files)
        sources = [self.profile_file(path, pbf_available) for path in files]
        return {
            "onboarding_version": ONBOARDING_VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "maps_root": str(self.maps_root),
            "output_root": str(self.output_root),
            "scan_mode": "read_only_source_scan",
            "source_gis_modified": False,
            "sources": sorted(sources, key=lambda item: item["file_name"]),
        }

    def iter_source_files(self) -> list[Path]:
        files = []
        for path in self.maps_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel_parts = path.relative_to(self.maps_root).parts
            except ValueError:
                rel_parts = path.parts
            if any(part in EXCLUDED_DIR_NAMES for part in rel_parts):
                continue
            if path.is_relative_to(APP_RELEASE_DIR):
                continue
            if self.extension_for(path) in SUPPORTED_EXTENSIONS:
                files.append(path)
        return files

    def profile_file(self, path: Path, pbf_available: bool) -> dict:
        extension = self.extension_for(path)
        stat = path.stat()
        profile = {
            "dataset_id": slug(path.name),
            "file_name": path.name,
            "path": str(path),
            "extension": extension,
            "size_mb": round(stat.st_size / 1024 / 1024, 3),
            "modified_utc": modified_utc(path),
            "likely_role": self.likely_role(path, extension),
            "profile_status": "inventory_only",
            "layers": [],
            "archive_member_count": 0,
            "readiness": {},
            "source_gis_modified": False,
        }
        if extension == ".zip":
            self.profile_zip(path, profile)
        elif extension in {".osm.pbf", ".pbf"}:
            self.profile_pbf(profile)
        elif extension == ".gpkg":
            self.profile_gpkg(path, profile)
        elif extension == ".shp":
            self.profile_shp(path, profile)
        elif extension in {".geojson", ".json"}:
            self.profile_geojson(path, profile)
        profile["readiness"] = self.readiness_for(profile, pbf_available)
        return profile

    def profile_zip(self, path: Path, profile: dict) -> None:
        try:
            with zipfile.ZipFile(path) as archive:
                members = [member for member in archive.infolist() if not member.is_dir()]
                profile["archive_member_count"] = len(members)
                profile["layers"] = self.shapefile_layers_from_zip(archive, members)
                profile["profile_status"] = "profiled_from_archive_headers"
        except zipfile.BadZipFile as exc:
            profile["profile_status"] = "zip_profile_failed"
            profile["profile_error"] = repr(exc)

    def shapefile_layers_from_zip(self, archive: zipfile.ZipFile, members: list[zipfile.ZipInfo]) -> list[dict]:
        grouped: dict[str, dict] = {}
        for member in members:
            suffix = Path(member.filename).suffix.lower()
            if suffix not in {".shp", ".dbf", ".prj", ".cpg", ".shx"}:
                continue
            stem = Path(member.filename).with_suffix("").name
            layer = grouped.setdefault(stem, {
                "layer": stem,
                "format": "shapefile_in_zip",
                "geometry_type": "unknown",
                "feature_count": None,
                "crs": "",
                "members": [],
            })
            layer["members"].append(Path(member.filename).name)
            try:
                if suffix == ".dbf":
                    layer["feature_count"] = dbf_record_count(archive.read(member.filename))
                elif suffix == ".shp":
                    header = shp_header(archive.read(member.filename)[:100])
                    layer.update(header)
                elif suffix == ".prj":
                    layer["crs"] = prj_crs_hint(archive.read(member.filename).decode("utf-8", errors="replace"))
            except Exception as exc:  # pragma: no cover - defensive local profile
                layer["profile_warning"] = repr(exc)
        layers = []
        for layer in grouped.values():
            layer["members"] = sorted(layer["members"])
            if layer["feature_count"] is None:
                layer["feature_count"] = 0
            layers.append(layer)
        return sorted(layers, key=lambda item: item["layer"])

    def profile_pbf(self, profile: dict) -> None:
        profile["profile_status"] = "raw_osm_pbf_detected"
        profile["layers"] = [
            {
                "layer": "osm_pbf_raw",
                "format": "osm_pbf",
                "geometry_type": "mixed",
                "feature_count": None,
                "crs": "EPSG:4326_expected",
                "purpose": "Raw OSM tag enrichment and future PostGIS/osm2pgsql ingestion.",
            }
        ]

    def profile_gpkg(self, path: Path, profile: dict) -> None:
        try:
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
                rows = conn.execute(
                    "select table_name, data_type, identifier, srs_id from gpkg_contents order by table_name"
                ).fetchall()
                profile["layers"] = [
                    {
                        "layer": row[0],
                        "format": "geopackage",
                        "geometry_type": row[1],
                        "feature_count": None,
                        "crs": f"srs_id:{row[3]}",
                        "identifier": row[2],
                    }
                    for row in rows
                ]
                profile["profile_status"] = "profiled_from_gpkg_metadata"
        except sqlite3.Error as exc:
            profile["profile_status"] = "gpkg_profile_failed"
            profile["profile_error"] = repr(exc)

    def profile_shp(self, path: Path, profile: dict) -> None:
        layer = {
            "layer": path.stem,
            "format": "shapefile",
            "geometry_type": "unknown",
            "feature_count": 0,
            "crs": "",
            "members": [],
        }
        for suffix in [".shp", ".dbf", ".shx", ".prj", ".cpg"]:
            candidate = path.with_suffix(suffix)
            if not candidate.exists():
                continue
            layer["members"].append(candidate.name)
            if suffix == ".shp":
                layer.update(shp_header(candidate.read_bytes()[:100]))
            elif suffix == ".dbf":
                layer["feature_count"] = dbf_record_count(candidate.read_bytes()[:32])
            elif suffix == ".prj":
                layer["crs"] = prj_crs_hint(candidate.read_text(encoding="utf-8", errors="replace"))
        profile["layers"] = [layer]
        profile["profile_status"] = "profiled_from_shapefile_headers"

    def profile_geojson(self, path: Path, profile: dict) -> None:
        profile["profile_status"] = "geojson_inventory_only"
        if path.stat().st_size > 50 * 1024 * 1024:
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            profile["profile_error"] = repr(exc)
            return
        geometry_type = "unknown"
        feature_count = 0
        if data.get("type") == "FeatureCollection":
            features = data.get("features") or []
            feature_count = len(features)
            if features:
                geometry = features[0].get("geometry") or {}
                geometry_type = geometry.get("type") or "unknown"
        elif data.get("type") == "Feature":
            feature_count = 1
            geometry_type = (data.get("geometry") or {}).get("type") or "unknown"
        profile["layers"] = [
            {
                "layer": path.stem,
                "format": "geojson",
                "geometry_type": geometry_type,
                "feature_count": feature_count,
                "crs": "unknown_from_current_data",
            }
        ]
        profile["profile_status"] = "profiled_from_geojson"

    def readiness_for(self, profile: dict, pbf_available: bool) -> dict:
        extension = profile.get("extension")
        layer_names = {layer.get("layer") for layer in profile.get("layers", [])}
        missing_layers = sorted(SAFE_ACCESS_REQUIRED_LAYERS - layer_names)
        if extension == ".zip" and not missing_layers:
            level = "ready_for_safe_access_selected_pilot"
            blockers = [] if pbf_available else ["raw_osm_pbf_missing_for_enrichment"]
            supported_templates = ["safe_access", "osm_quality", "generic_layer_inventory"]
        elif extension in {".osm.pbf", ".pbf"}:
            level = "ready_as_osm_tag_enrichment_source"
            blockers = ["needs_geofabrik_shapefile_zip_for_current_selected_pilot_mapper"]
            supported_templates = ["osm_quality", "tag_enrichment_source"]
        elif profile.get("layers"):
            level = "profiled_for_generic_layer_inventory"
            blockers = sorted(missing_layers) if extension == ".zip" else ["template_mapping_not_implemented_for_this_format"]
            supported_templates = ["generic_layer_inventory"]
        else:
            level = "inventory_only"
            blockers = ["layer_metadata_not_available_from_current_lightweight_scanner"]
            supported_templates = []
        return {
            "level": level,
            "safe_access_required_layers_present": not missing_layers,
            "missing_safe_access_layers": missing_layers,
            "pbf_available_in_maps_root": pbf_available,
            "blockers": blockers,
            "supported_templates": supported_templates,
            "recommended_next_action": self.recommended_next_action(level, blockers),
        }

    @staticmethod
    def recommended_next_action(level: str, blockers: list[str]) -> str:
        if level == "ready_for_safe_access_selected_pilot" and not blockers:
            return "Run selected-pilot preflight and then start a background Safe Access workspace job."
        if level == "ready_for_safe_access_selected_pilot":
            return "Add a matching .osm.pbf file if raw OSM tag enrichment is required."
        if level == "ready_as_osm_tag_enrichment_source":
            return "Pair this PBF with a compatible Geofabrik Shapefile ZIP or use it for tag-coverage analysis."
        if level == "profiled_for_generic_layer_inventory":
            return "Use the source profile for portfolio inventory, then implement a template mapper for this format."
        return "Keep as inventory evidence until a compatible parser or template mapper is added."

    @staticmethod
    def likely_role(path: Path, extension: str) -> str:
        name = path.name.lower()
        if extension == ".zip" and "free.shp" in name:
            return "geofabrik_free_shapefile_zip_candidate"
        if extension in {".osm.pbf", ".pbf"}:
            return "raw_osm_pbf_candidate"
        if extension == ".gpkg":
            return "geopackage_candidate"
        if extension == ".shp":
            return "standalone_shapefile_candidate"
        if extension in {".geojson", ".json"}:
            return "geojson_candidate"
        return "unknown_from_current_data"

    @staticmethod
    def extension_for(path: Path) -> str:
        name = path.name.lower()
        if name.endswith(".osm.pbf"):
            return ".osm.pbf"
        return path.suffix.lower()

    def read_cache(self) -> dict:
        if not self.catalog_path.exists():
            return {}
        try:
            return json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def write_sources_csv(self, sources: list[dict]) -> None:
        fieldnames = [
            "dataset_id",
            "file_name",
            "path",
            "extension",
            "size_mb",
            "modified_utc",
            "likely_role",
            "profile_status",
            "layer_count",
            "archive_member_count",
            "readiness_level",
            "supported_templates",
            "blockers",
            "source_gis_modified",
        ]
        with self.sources_csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for source in sources:
                readiness = source.get("readiness", {})
                writer.writerow({
                    "dataset_id": source.get("dataset_id"),
                    "file_name": source.get("file_name"),
                    "path": source.get("path"),
                    "extension": source.get("extension"),
                    "size_mb": source.get("size_mb"),
                    "modified_utc": source.get("modified_utc"),
                    "likely_role": source.get("likely_role"),
                    "profile_status": source.get("profile_status"),
                    "layer_count": len(source.get("layers", [])),
                    "archive_member_count": source.get("archive_member_count"),
                    "readiness_level": readiness.get("level"),
                    "supported_templates": ";".join(readiness.get("supported_templates", [])),
                    "blockers": ";".join(readiness.get("blockers", [])),
                    "source_gis_modified": source.get("source_gis_modified"),
                })
