from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


class CatalogLike(Protocol):
    def source_files(self) -> list[dict]:
        ...


CANONICAL_TABLES = [
    {
        "file": "pedestrian_generators.csv",
        "table": "pedestrian_generators",
        "geometry": "Point",
        "role": "Schools, kindergartens, bus stops, parks, playgrounds, and other pedestrian generators.",
    },
    {
        "file": "crossings.csv",
        "table": "crossings",
        "geometry": "Point",
        "role": "Mapped pedestrian crossings and crossing detail fields available from inspected data.",
    },
    {
        "file": "road_segments.csv",
        "table": "road_segments",
        "geometry": "LineString",
        "role": "Road network segments with class, speed, one-way, sidewalk, and lighting fields where available.",
    },
    {
        "file": "risk_assessment_results.csv",
        "table": "risk_assessment_results",
        "geometry": "Point",
        "role": "Per-generator distance metrics, infrastructure risk flags, data-quality flags, and review wording.",
    },
    {
        "file": "risk_assessment_top20.csv",
        "table": "risk_assessment_top20",
        "geometry": "Point",
        "role": "Small priority review extract for portfolio/reporting workflows.",
    },
]


DATA_DICTIONARY_ROWS = [
    ["table", "field", "required", "reliability", "notes"],
    ["pedestrian_generators", "generator_id", "yes", "derived_stable", "Local generated identifier."],
    ["pedestrian_generators", "osm_id", "yes", "source_dependent", "OSM identifier from source data where available."],
    ["pedestrian_generators", "generator_type", "yes", "template_mapped", "school, kindergarten, bus_stop, park, playground, etc."],
    ["pedestrian_generators", "name", "no", "optional_osm_tag", "Name may be missing in OSM."],
    ["pedestrian_generators", "geometry_wkt", "yes", "derived", "WKT point geometry in analysis export."],
    ["crossings", "crossing_type", "yes", "source_dependent", "Crossing class or mapped value."],
    ["crossings", "has_signal_nearby", "yes", "derived", "Derived from nearby traffic signal features."],
    ["crossings", "tactile_paving", "no", "optional_osm_tag", "Missing tag is a data-quality gap only."],
    ["crossings", "kerb", "no", "optional_osm_tag", "Missing tag is a data-quality gap only."],
    ["road_segments", "highway_class", "yes", "source_dependent", "Mapped OSM/Geofabrik road class."],
    ["road_segments", "maxspeed", "no", "optional_osm_tag", "Missing tag is not a risk claim."],
    ["road_segments", "sidewalk", "no", "optional_osm_tag", "Only explicit sidewalk=no is treated as risk indicator."],
    ["road_segments", "lit", "no", "optional_osm_tag", "Only explicit lit=no is treated as risk indicator."],
    ["risk_assessment_results", "nearest_crossing_m", "yes", "derived_epsg2039", "Distance calculated in meters."],
    ["risk_assessment_results", "nearest_major_road_m", "yes", "derived_epsg2039", "Distance calculated in meters."],
    ["risk_assessment_results", "risk_score", "yes", "rule_based_v001", "Transparent prioritization score for field review."],
    ["risk_assessment_results", "risk_flags", "yes", "derived", "Infrastructure risk indicators; not a crash prediction."],
    ["risk_assessment_results", "data_quality_flags", "yes", "derived", "Missing/incomplete OSM evidence separated from risk score."],
    ["risk_assessment_results", "review_wording", "yes", "policy_required", "Approved wording for all candidate rows."],
]


class WorkspaceRunner:
    def __init__(
        self,
        output_root: Path,
        mvp_dir: Path,
        workspaces_dir: Path,
        review_wording: str,
        catalog: CatalogLike,
    ) -> None:
        self.output_root = output_root
        self.mvp_dir = mvp_dir
        self.workspaces_dir = workspaces_dir
        self.review_wording = review_wording
        self.catalog = catalog
        self.qgis_python = Path(r"C:\Program Files\QGIS 3.44.10\bin\python-qgis-ltr.bat")
        self.mapper_script = Path(__file__).resolve().parent / "generic_safe_access_mapper.py"

    def ensure_safe_access_kfar_saba(self, dataset_id: str) -> dict:
        source = self._find_source(dataset_id)
        if source is None:
            return {"ok": False, "error": "dataset_not_found", "dataset_id": dataset_id}

        required = [
            self.mvp_dir / "pedestrian_generators.csv",
            self.mvp_dir / "crossings.csv",
            self.mvp_dir / "road_segments.csv",
            self.mvp_dir / "risk_assessment_results.csv",
            self.mvp_dir / "risk_assessment_top20.csv",
            self.mvp_dir / "analysis_metadata.json",
            self.mvp_dir / "validation_summary.json",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            return {"ok": False, "error": "missing_upstream_outputs", "missing": missing}

        workspace_id = "safe_access_kfar_saba_v001"
        workspace_dir = self.workspaces_dir / workspace_id
        manifest_path = workspace_dir / "manifest.json"
        if manifest_path.exists():
            return {
                "ok": True,
                "created": False,
                "workspace": self.workspace_detail(workspace_id),
            }

        workspace_dir.mkdir(parents=True, exist_ok=True)
        tables_dir = workspace_dir / "tables"
        reports_dir = workspace_dir / "reports"
        tables_dir.mkdir(exist_ok=True)
        reports_dir.mkdir(exist_ok=True)

        copied_tables = []
        for table in CANONICAL_TABLES:
            source_file = self.mvp_dir / table["file"]
            target_file = tables_dir / table["file"]
            shutil.copy2(source_file, target_file)
            copied_tables.append({
                "table": table["table"],
                "file": str(target_file),
                "geometry": table["geometry"],
                "role": table["role"],
                "rows": self._count_csv_rows(target_file),
            })

        metadata = self._read_json(self.mvp_dir / "analysis_metadata.json")
        validation = self._read_json(self.mvp_dir / "validation_summary.json")
        summary = {
            "workspace_id": workspace_id,
            "template_id": "safe_access",
            "pilot_area": "Kfar Saba",
            "analysis_crs": validation.get("analysis_crs"),
            "review_wording": self.review_wording,
            "counts": metadata.get("counts", {}),
            "validation": validation,
            "scoring": metadata.get("scoring", {}),
        }
        self._write_json(reports_dir / "workspace_summary.json", summary)

        quality_report = {
            "workspace_id": workspace_id,
            "data_quality_principles": [
                "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
                "Risk flags are infrastructure risk indicators for field review prioritization.",
                "The workspace is not a crash prediction model.",
            ],
            "known_limitations": [
                "Pilot boundary is OSM/Geofabrik based, not an official municipal boundary.",
                "Sidewalk, lighting, kerb, tactile paving, and maxspeed tags are incomplete.",
                "The current runner uses the validated Kfar Saba MVP outputs as its canonical input.",
            ],
        }
        self._write_json(reports_dir / "quality_report.json", quality_report)
        self._write_csv(reports_dir / "data_dictionary.csv", DATA_DICTIONARY_ROWS)

        template_mapping = {
            "template_id": "safe_access",
            "source_dataset_id": dataset_id,
            "source_file_name": source.get("file_name"),
            "canonical_tables": copied_tables,
            "next_runner_step": "Replace this Kfar Saba adapter with a generic layer-to-canonical-table mapper for any compatible OSM/GIS input.",
        }
        self._write_json(reports_dir / "template_mapping.json", template_mapping)

        readme = (
            "# Safe Access Kfar Saba Workspace\n\n"
            "Generated by GeoReview Studio v003 from existing validated MVP outputs.\n\n"
            "This workspace contains canonical CSV tables for dashboard, reporting, and future API workflows.\n\n"
            f"Approved review wording: `{self.review_wording}`\n\n"
            "Source GIS files were not modified.\n"
        )
        (workspace_dir / "README.md").write_text(readme, encoding="utf-8")

        manifest = {
            "workspace_id": workspace_id,
            "template_id": "safe_access",
            "created_by": "GeoReview Studio v003 workspace runner",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_dataset_id": dataset_id,
            "source_file_name": source.get("file_name"),
            "source_path": source.get("path"),
            "source_gis_modified": False,
            "workspace_dir": str(workspace_dir),
            "tables_dir": str(tables_dir),
            "reports_dir": str(reports_dir),
            "tables": copied_tables,
            "reports": {
                "workspace_summary": str(reports_dir / "workspace_summary.json"),
                "quality_report": str(reports_dir / "quality_report.json"),
                "data_dictionary": str(reports_dir / "data_dictionary.csv"),
                "template_mapping": str(reports_dir / "template_mapping.json"),
            },
        }
        self._write_json(manifest_path, manifest)
        return {
            "ok": True,
            "created": True,
            "workspace": self.workspace_detail(workspace_id),
        }

    def build_safe_access_generic(
        self,
        dataset_id: str,
        pilot_osm_id: str = "53796999",
        pilot_name: str = "Kfar Saba",
        workspace_id: str = "safe_access_kfar_saba_pbf_enriched_v001",
    ) -> dict:
        source = self._find_source(dataset_id)
        if source is None:
            return {"ok": False, "error": "dataset_not_found", "dataset_id": dataset_id}
        if source.get("extension") != ".zip":
            return {
                "ok": False,
                "error": "unsupported_generic_mapper_source",
                "dataset_id": dataset_id,
                "supported": ["Geofabrik Free Shapefile ZIP"],
                "received_extension": source.get("extension"),
            }
        if not self.qgis_python.exists():
            return {
                "ok": False,
                "error": "missing_geospatial_runtime",
                "required_tool": str(self.qgis_python),
                "fallback": "Use the v003 registered workspace or run the mapper from an environment with geopandas/pyogrio/shapely.",
            }
        if not self.mapper_script.exists():
            return {"ok": False, "error": "missing_mapper_script", "path": str(self.mapper_script)}
        pbf_source = self._find_source_by_extension(".osm.pbf")
        if pbf_source is None:
            return {
                "ok": False,
                "error": "missing_pbf_enrichment_source",
                "required": ".osm.pbf source in inspected maps folder",
                "fallback": "Use v004 generic ZIP workspace without raw PBF enrichment.",
            }

        workspace_dir = self.workspaces_dir / workspace_id
        manifest_path = workspace_dir / "manifest.json"
        if manifest_path.exists():
            return {
                "ok": True,
                "created": False,
                "workspace": self.workspace_detail(workspace_id),
            }

        workspace_dir.mkdir(parents=True, exist_ok=True)
        result_path = workspace_dir / "mapper_result.json"
        mapper_args = [
            str(self.qgis_python),
            str(self.mapper_script),
            "--source-zip",
            str(source.get("path")),
            "--source-pbf",
            str(pbf_source.get("path")),
            "--workspace-dir",
            str(workspace_dir),
            "--workspace-id",
            workspace_id,
            "--source-dataset-id",
            dataset_id,
            "--source-file-name",
            str(source.get("file_name")),
            "--pilot-osm-id",
            str(pilot_osm_id),
            "--pilot-name",
            pilot_name,
            "--result-json",
            str(result_path),
        ]
        completed = subprocess.run(
            mapper_args,
            cwd=str(Path(__file__).resolve().parent),
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
        )
        if completed.returncode != 0:
            return {
                "ok": False,
                "error": "generic_mapper_failed",
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
                "workspace_dir": str(workspace_dir),
            }
        if not manifest_path.exists():
            return {
                "ok": False,
                "error": "generic_mapper_missing_manifest",
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
                "workspace_dir": str(workspace_dir),
            }
        return {
            "ok": True,
            "created": True,
            "workspace": self.workspace_detail(workspace_id),
            "mapper_stdout_tail": completed.stdout[-2000:],
        }

    def list_workspaces(self) -> list[dict]:
        if not self.workspaces_dir.exists():
            return []
        workspaces = []
        for path in sorted(self.workspaces_dir.iterdir()):
            if not path.is_dir():
                continue
            manifest_path = path / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = self._read_json(manifest_path)
            workspaces.append({
                "workspace_id": manifest.get("workspace_id", path.name),
                "template_id": manifest.get("template_id"),
                "source_dataset_id": manifest.get("source_dataset_id"),
                "created_at_utc": manifest.get("created_at_utc"),
                "workspace_dir": str(path),
                "table_count": len(manifest.get("tables", [])),
            })
        return workspaces

    def workspace_detail(self, workspace_id: str) -> dict:
        workspace_dir = self.workspaces_dir / workspace_id
        manifest_path = workspace_dir / "manifest.json"
        if not manifest_path.exists():
            return {"error": "workspace_not_found", "workspace_id": workspace_id}
        manifest = self._read_json(manifest_path)
        reports_dir = workspace_dir / "reports"
        return {
            "manifest": manifest,
            "summary": self._read_json(reports_dir / "workspace_summary.json"),
            "quality_report": self._read_json(reports_dir / "quality_report.json"),
            "files": self._list_files(workspace_dir),
        }

    def _find_source(self, dataset_id: str) -> dict | None:
        for source in self.catalog.source_files():
            if source.get("dataset_id") == dataset_id:
                return source
        return None

    def _find_source_by_extension(self, extension: str) -> dict | None:
        for source in self.catalog.source_files():
            if source.get("extension") == extension:
                return source
        return None

    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        # Atomic write: a concurrent reader on the threaded server must never see a
        # half-written JSON, so write to a temp sibling and os.replace() it in.
        tmp = path.with_name(f"{path.name}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    @staticmethod
    def _write_csv(path: Path, rows: list[list[str]]) -> None:
        tmp = path.with_name(f"{path.name}.tmp")
        with tmp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        os.replace(tmp, path)

    @staticmethod
    def _count_csv_rows(path: Path) -> int:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return max(0, sum(1 for _ in f) - 1)

    @staticmethod
    def _list_files(root: Path) -> list[dict]:
        files = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files.append({
                    "name": path.name,
                    "relative_path": str(path.relative_to(root)),
                    "size_bytes": path.stat().st_size,
                })
        return files
