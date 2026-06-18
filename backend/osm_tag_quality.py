from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


OSM_TAG_QUALITY_VERSION = "osm_tag_quality_v001"
DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID = "osm_tag_quality_kfar_saba_v001"

KEY_CATEGORIES = {
    "crossings",
    "traffic_signals",
    "schools",
    "kindergartens",
    "childcare_facilities",
    "bus_stops",
    "parks",
    "playgrounds",
    "major_roads",
    "residential_roads",
    "living_streets",
    "roads_with_sidewalk_tag",
    "roads_with_sidewalk_no",
    "roads_with_maxspeed_tag",
    "roads_with_lit_tag",
    "roads_with_lit_no",
    "traffic_calming_features",
    "footways",
    "pedestrian_streets",
}

KEY_TAGS = {
    "highway",
    "crossing",
    "crossing_ref",
    "tactile_paving",
    "kerb",
    "island",
    "crossing:island",
    "button_operated",
    "traffic_signals:sound",
    "amenity",
    "school",
    "operator",
    "name",
    "name:he",
    "name:en",
    "public_transport",
    "bus",
    "shelter",
    "bench",
    "route_ref",
    "network",
    "leisure",
    "landuse",
    "sidewalk",
    "sidewalk:left",
    "sidewalk:right",
    "footway",
    "maxspeed",
    "lanes",
    "lit",
    "traffic_calming",
    "surface",
    "smoothness",
    "access",
    "oneway",
    "cycleway",
    "cycleway:left",
    "cycleway:right",
    "bicycle",
    "segregated",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_token(value: object, fallback: str = "osm_tag_quality") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:120] or fallback


def is_key_evidence(row: dict) -> bool:
    category = str(row.get("category") or "")
    tag = str(row.get("tag_or_field") or "")
    value = str(row.get("value") or "")
    haystack = f"{category} {tag} {value}".lower()
    if category in KEY_CATEGORIES:
        return True
    return any(key.lower() in haystack for key in KEY_TAGS)


def quality_role(row: dict) -> str:
    notes = str(row.get("notes") or "").lower()
    category = str(row.get("category") or "")
    count = parse_int(row.get("count"))
    if "not preserved" in notes:
        return "simplified_schema_gap"
    if row.get("scope") == "kfar_saba_bbox_estimate":
        return "pilot_bbox_evidence"
    if category == "tag_presence":
        return "raw_osm_tag_presence"
    if count > 0 and category in KEY_CATEGORIES:
        return "mvp_evidence"
    if count == 0:
        return "zero_count_evidence"
    if count < 0:
        return "needs_interpretation"
    return "supporting_evidence"


def usefulness(row: dict) -> str:
    role = quality_role(row)
    if role in {"mvp_evidence", "pilot_bbox_evidence", "raw_osm_tag_presence"}:
        return "useful_for_mvp"
    if role == "simplified_schema_gap":
        return "useful_as_data_quality_warning"
    if role == "zero_count_evidence":
        return "limited_use_zero_or_missing_in_this_source"
    return "supporting_context"


class OSMTagQualityAnalyzer:
    def __init__(self, output_root: Path, workspaces_dir: Path, review_wording: str) -> None:
        self.output_root = output_root
        self.workspaces_dir = workspaces_dir
        self.review_wording = review_wording
        self.tag_counts_path = output_root / "osm_tag_counts.csv"
        self.layer_summary_path = output_root / "layer_summary.csv"

    def status(self) -> dict:
        tag_rows = read_csv_rows(self.tag_counts_path)
        layer_rows = read_csv_rows(self.layer_summary_path)
        summary = self.summary_from_rows(tag_rows, layer_rows, DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID)
        return {
            "ok": bool(tag_rows),
            "osm_tag_quality_version": OSM_TAG_QUALITY_VERSION,
            "workspace_id": DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID,
            "tag_counts_file": str(self.tag_counts_path),
            "layer_summary_file": str(self.layer_summary_path),
            "tag_counts_exists": self.tag_counts_path.exists(),
            "layer_summary_exists": self.layer_summary_path.exists(),
            "summary": summary,
            "policy": {
                "read_only_source_gis": True,
                "writes_only_small_profile_workspace": True,
                "missing_tags_are_data_quality_flags": True,
                "no_crash_prediction": True,
            },
            "review_wording": self.review_wording,
            "source_gis_modified": False,
        }

    def summary(self) -> dict:
        tag_rows = read_csv_rows(self.tag_counts_path)
        layer_rows = read_csv_rows(self.layer_summary_path)
        if not tag_rows:
            return {"ok": False, "error": "osm_tag_quality_source_missing", "tag_counts_file": str(self.tag_counts_path), "source_gis_modified": False}
        return {
            "ok": True,
            **self.summary_from_rows(tag_rows, layer_rows, DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID),
        }

    def source_results(self, limit: int = 50) -> list[dict] | dict:
        tag_rows = read_csv_rows(self.tag_counts_path)
        if not tag_rows:
            return {"ok": False, "error": "osm_tag_quality_source_missing", "tag_counts_file": str(self.tag_counts_path), "source_gis_modified": False}
        return self.result_rows(tag_rows, limit)

    def ensure_workspace(self, workspace_id: str = DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID) -> dict:
        tag_rows = read_csv_rows(self.tag_counts_path)
        layer_rows = read_csv_rows(self.layer_summary_path)
        if not tag_rows:
            return {"ok": False, "error": "osm_tag_quality_source_missing", "tag_counts_file": str(self.tag_counts_path), "source_gis_modified": False}

        workspace_id = safe_token(workspace_id, DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID)
        output_dir = self.workspaces_dir / workspace_id
        tables_dir = output_dir / "tables"
        reports_dir = output_dir / "reports"
        quality_rows = self.quality_rows(tag_rows)
        presence_rows = self.tag_presence_rows(tag_rows)
        scope_rows = self.source_scope_rows(tag_rows, layer_rows)
        summary = self.summary_from_rows(tag_rows, layer_rows, workspace_id)

        quality_path = tables_dir / "tag_quality_summary.csv"
        presence_path = tables_dir / "tag_presence_summary.csv"
        scope_path = tables_dir / "source_scope_summary.csv"
        summary_path = reports_dir / "workspace_summary.json"
        markdown_path = reports_dir / "tag_quality_report.md"
        manifest_path = output_dir / "manifest.json"
        readme_path = output_dir / "README.md"

        write_csv(quality_path, quality_rows, [
            "source",
            "scope",
            "category",
            "layer_or_element",
            "tag_or_field",
            "value",
            "count",
            "quality_role",
            "usefulness",
            "is_key_evidence",
            "examples",
            "notes",
        ])
        write_csv(presence_path, presence_rows, [
            "tag_or_field",
            "source",
            "scope",
            "positive_count_rows",
            "total_count",
            "example_values",
            "usefulness",
        ])
        write_csv(scope_path, scope_rows, [
            "source",
            "scope",
            "row_count",
            "positive_count_rows",
            "zero_count_rows",
            "not_preserved_rows",
            "key_evidence_rows",
            "total_positive_count",
            "layer_summary_rows",
        ])
        write_json(summary_path, {"ok": True, **summary})
        markdown_path.write_text(self.summary_markdown(summary, quality_rows[:20]), encoding="utf-8")

        manifest = {
            "workspace_id": workspace_id,
            "profile_id": "osm_tag_quality",
            "profile_workspace": True,
            "created_at_utc": utc_now(),
            "analyzer": OSM_TAG_QUALITY_VERSION,
            "source_files": {
                "tag_counts": str(self.tag_counts_path),
                "layer_summary": str(self.layer_summary_path),
            },
            "source_gis_modified": False,
            "tables": [
                {"table": "tag_quality_summary", "file": str(quality_path), "rows": len(quality_rows)},
                {"table": "tag_presence_summary", "file": str(presence_path), "rows": len(presence_rows)},
                {"table": "source_scope_summary", "file": str(scope_path), "rows": len(scope_rows)},
            ],
            "reports": {
                "workspace_summary": str(summary_path),
                "tag_quality_report": str(markdown_path),
            },
        }
        write_json(manifest_path, manifest)
        readme_path.write_text(
            "# OSM Tag Quality Workspace\n\n"
            "Read-only profile workspace generated from inspected audit CSV files under analysis_output.\n\n"
            "This workspace reports OSM tag coverage and schema limitations. Missing tags are data-quality flags, not proof that infrastructure is absent.\n",
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

    def summary_for_workspace(self, workspace_id: str = DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID) -> dict:
        manifest = self.manifest(workspace_id)
        if "error" in manifest:
            return manifest
        summary_path = Path(manifest.get("reports", {}).get("workspace_summary", ""))
        if not summary_path.exists():
            return {"ok": False, "error": "profile_output_not_found", "workspace_id": workspace_id, "output_id": "workspace_summary", "source_gis_modified": False}
        return json.loads(summary_path.read_text(encoding="utf-8"))

    def results(self, workspace_id: str = DEFAULT_OSM_TAG_QUALITY_WORKSPACE_ID, limit: int = 50) -> list[dict] | dict:
        output = self.output_file(workspace_id, "tag_quality_summary")
        if "error" in output:
            return output
        return read_csv_rows(output["path"])[: max(1, min(int(limit or 50), 500))]

    def list_workspaces(self) -> list[dict]:
        rows = []
        if not self.workspaces_dir.exists():
            return rows
        for manifest_path in self.workspaces_dir.glob("*/manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("profile_id") != "osm_tag_quality" or not manifest.get("profile_workspace"):
                continue
            summary = self.summary_for_workspace(str(manifest.get("workspace_id") or ""))
            counts = summary.get("counts", {}) if isinstance(summary, dict) else {}
            rows.append({
                "workspace_id": manifest.get("workspace_id"),
                "profile_id": "osm_tag_quality",
                "base_workspace_id": "",
                "created_at_utc": manifest.get("created_at_utc"),
                "table_count": len(manifest.get("tables", [])),
                "tag_count_rows": counts.get("tag_count_rows"),
                "key_tag_count": counts.get("key_tag_count"),
                "shapefile_not_preserved_count": counts.get("shapefile_not_preserved_count"),
                "pbf_presence_rows": counts.get("pbf_presence_rows"),
                "source_gis_modified": False,
            })
        return rows

    def output_file(self, workspace_id: str, output_id: str) -> dict:
        manifest = self.manifest(workspace_id)
        if "error" in manifest:
            return manifest
        table_files = {
            str(item.get("table")): Path(item.get("file", ""))
            for item in manifest.get("tables", [])
        }
        report_files = {
            str(key): Path(value)
            for key, value in manifest.get("reports", {}).items()
        }
        candidates = {**table_files, **report_files}
        path = candidates.get(output_id)
        if not path or not path.exists():
            return {"ok": False, "error": "profile_output_not_found", "workspace_id": workspace_id, "output_id": output_id, "source_gis_modified": False}
        return {"ok": True, "path": path, "output_id": output_id, "source_gis_modified": False}

    def manifest(self, workspace_id: str) -> dict:
        manifest_path = self.workspaces_dir / safe_token(workspace_id) / "manifest.json"
        if not manifest_path.exists():
            return {"ok": False, "error": "profile_workspace_not_found", "workspace_id": workspace_id, "source_gis_modified": False}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("profile_id") != "osm_tag_quality" or not manifest.get("profile_workspace"):
            return {"ok": False, "error": "profile_workspace_not_found", "workspace_id": workspace_id, "source_gis_modified": False}
        return manifest

    @staticmethod
    def quality_rows(tag_rows: list[dict]) -> list[dict]:
        rows = []
        for row in tag_rows:
            next_row = dict(row)
            next_row["quality_role"] = quality_role(row)
            next_row["usefulness"] = usefulness(row)
            next_row["is_key_evidence"] = str(is_key_evidence(row)).lower()
            rows.append(next_row)
        rows.sort(key=lambda item: (
            item.get("usefulness") != "useful_for_mvp",
            item.get("source"),
            item.get("scope"),
            item.get("category"),
            -parse_int(item.get("count")),
        ))
        return rows

    @staticmethod
    def tag_presence_rows(tag_rows: list[dict]) -> list[dict]:
        grouped: dict[tuple[str, str, str], dict] = {}
        for row in tag_rows:
            if not is_key_evidence(row):
                continue
            key = (str(row.get("tag_or_field") or row.get("category") or ""), str(row.get("source") or ""), str(row.get("scope") or ""))
            bucket = grouped.setdefault(key, {
                "tag_or_field": key[0],
                "source": key[1],
                "scope": key[2],
                "positive_count_rows": 0,
                "total_count": 0,
                "example_values": [],
                "usefulness": "useful_for_mvp",
            })
            count = parse_int(row.get("count"))
            if count > 0:
                bucket["positive_count_rows"] += 1
                bucket["total_count"] += count
            value = str(row.get("value") or "")
            if value and len(bucket["example_values"]) < 5:
                bucket["example_values"].append(value)
        rows = []
        for bucket in grouped.values():
            bucket["example_values"] = "; ".join(bucket["example_values"])
            rows.append(bucket)
        rows.sort(key=lambda item: (-parse_int(item.get("total_count")), item.get("tag_or_field")))
        return rows

    @staticmethod
    def source_scope_rows(tag_rows: list[dict], layer_rows: list[dict]) -> list[dict]:
        grouped: dict[tuple[str, str], dict] = {}
        for row in tag_rows:
            key = (str(row.get("source") or ""), str(row.get("scope") or ""))
            bucket = grouped.setdefault(key, {
                "source": key[0],
                "scope": key[1],
                "row_count": 0,
                "positive_count_rows": 0,
                "zero_count_rows": 0,
                "not_preserved_rows": 0,
                "key_evidence_rows": 0,
                "total_positive_count": 0,
                "layer_summary_rows": 0,
            })
            count = parse_int(row.get("count"))
            bucket["row_count"] += 1
            if count > 0:
                bucket["positive_count_rows"] += 1
                bucket["total_positive_count"] += count
            if count == 0:
                bucket["zero_count_rows"] += 1
            if "not preserved" in str(row.get("notes") or "").lower():
                bucket["not_preserved_rows"] += 1
            if is_key_evidence(row):
                bucket["key_evidence_rows"] += 1
        geofabrik_layers = len([row for row in layer_rows if str(row.get("dataset") or "").endswith(".shp.zip")])
        for bucket in grouped.values():
            if bucket["source"] == "geofabrik_shapefile":
                bucket["layer_summary_rows"] = geofabrik_layers
        return sorted(grouped.values(), key=lambda item: (item["source"], item["scope"]))

    @staticmethod
    def summary_from_rows(tag_rows: list[dict], layer_rows: list[dict], workspace_id: str) -> dict:
        sources = sorted({str(row.get("source") or "") for row in tag_rows if row.get("source")})
        scopes = sorted({str(row.get("scope") or "") for row in tag_rows if row.get("scope")})
        pbf_presence_rows = [
            row for row in tag_rows
            if row.get("source") == "osm_pbf_raw" and row.get("category") == "tag_presence" and parse_int(row.get("count")) > 0
        ]
        key_rows = [row for row in tag_rows if is_key_evidence(row) and parse_int(row.get("count")) > 0]
        shapefile_gaps = [row for row in tag_rows if "not preserved" in str(row.get("notes") or "").lower()]
        kfar_rows = [row for row in tag_rows if row.get("scope") == "kfar_saba_bbox_estimate"]
        counts_by_category = {}
        for row in tag_rows:
            category = str(row.get("category") or "unknown")
            counts_by_category[category] = counts_by_category.get(category, 0) + 1
        return {
            "workspace_id": workspace_id,
            "profile_id": "osm_tag_quality",
            "analyzer": OSM_TAG_QUALITY_VERSION,
            "counts": {
                "tag_count_rows": len(tag_rows),
                "layer_summary_rows": len(layer_rows),
                "source_count": len(sources),
                "scope_count": len(scopes),
                "key_tag_count": len({str(row.get("tag_or_field") or row.get("category") or "") for row in key_rows}),
                "key_evidence_rows": len(key_rows),
                "pbf_presence_rows": len(pbf_presence_rows),
                "shapefile_not_preserved_count": len(shapefile_gaps),
                "kfar_saba_bbox_estimate_rows": len(kfar_rows),
            },
            "sources": sources,
            "scopes": scopes,
            "top_categories": dict(sorted(counts_by_category.items(), key=lambda item: (-item[1], item[0]))[:12]),
            "evidence_highlights": [
                "Raw OSM PBF preserves detailed tags that the simplified Geofabrik shapefile schema does not expose.",
                "Geofabrik shapefile layers are still useful for Kfar Saba pilot geometry, roads, traffic features, public transport, POIs and landuse.",
                "Kfar Saba rows in the audit are bbox estimates from an OSM place polygon, not official municipal boundary statistics.",
            ],
            "limitations": [
                "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
                "Counts are based on inspected audit CSV files, not a fresh live OSM query.",
                "This profile is an evidence audit, not a crash prediction model.",
            ],
            "review_wording": "This location has infrastructure risk indicators and should be reviewed on-site.",
            "source_gis_modified": False,
        }

    @staticmethod
    def result_rows(tag_rows: list[dict], limit: int = 50) -> list[dict]:
        rows = OSMTagQualityAnalyzer.quality_rows(tag_rows)
        return rows[: max(1, min(int(limit or 50), 500))]

    @staticmethod
    def summary_markdown(summary: dict, top_rows: list[dict]) -> str:
        counts = summary.get("counts", {})
        lines = [
            "# OSM Tag Quality Report",
            "",
            f"Workspace: `{summary.get('workspace_id')}`",
            f"Analyzer: `{summary.get('analyzer')}`",
            "",
            "## Evidence Counts",
            "",
            f"- Tag count rows: {counts.get('tag_count_rows')}",
            f"- Layer summary rows: {counts.get('layer_summary_rows')}",
            f"- Sources: {counts.get('source_count')}",
            f"- Scopes: {counts.get('scope_count')}",
            f"- Key evidence rows: {counts.get('key_evidence_rows')}",
            f"- Raw PBF tag-presence rows: {counts.get('pbf_presence_rows')}",
            f"- Shapefile simplified-schema gaps: {counts.get('shapefile_not_preserved_count')}",
            "",
            "## Interpretation",
            "",
            "- This profile reports OSM tag coverage and source schema limitations.",
            "- Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
            "- This is not a crash prediction model.",
            f"- {summary.get('review_wording')}",
            "",
            "## Top Evidence Rows",
            "",
        ]
        for row in top_rows:
            lines.append(
                f"- `{row.get('source')}` / `{row.get('scope')}` / `{row.get('category')}` / `{row.get('tag_or_field')}` = `{row.get('value')}`: {row.get('count')} ({row.get('quality_role')})."
            )
        return "\n".join(lines).rstrip() + "\n"
