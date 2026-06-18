from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import median


PROFILE_DASHBOARD_CONTRACT_VERSION = "profile_dashboard_contract_v001"
SAFE_ACCESS_PROFILE_ID = "safe_access_pedestrian_review"
TRANSIT_PROFILE_ID = "transit_stop_walk_access"
PARK_PROFILE_ID = "park_playground_access"


def parse_number(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_bool(value: object) -> bool | None:
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def parse_flags(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in str(value).split(";") if item.strip()]


def unique_flags(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for item in group:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
    return result


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


class ProfileDashboardStore:
    def __init__(self, workspaces_dir: Path, review_wording: str) -> None:
        self.workspaces_dir = workspaces_dir
        self.review_wording = review_wording
        self.base_profile_order = [SAFE_ACCESS_PROFILE_ID, TRANSIT_PROFILE_ID, PARK_PROFILE_ID]
        self.base_profile_names = {
            SAFE_ACCESS_PROFILE_ID: "Safe Access pedestrian review",
            TRANSIT_PROFILE_ID: "Transit stop walk-access review",
            PARK_PROFILE_ID: "Park and playground access review",
        }
        self.base_workspace_ids = {
            SAFE_ACCESS_PROFILE_ID: "safe_access_kfar_saba_route_aware_v001",
            TRANSIT_PROFILE_ID: "transit_stop_walk_access_kfar_saba_v001",
            PARK_PROFILE_ID: "park_playground_access_kfar_saba_v001",
        }

    def overview(self) -> dict:
        profiles = []
        for profile_id in self.profile_order():
            summary = self.summary(profile_id)
            profiles.append({
                "profile_id": profile_id,
                "profile_name": self.profile_name_for(profile_id),
                "workspace_id": self.workspace_id_for(profile_id),
                "result_count": summary.get("result_count", 0),
                "high_priority_count": summary.get("high_priority_count", 0),
                "median_primary_score": summary.get("median_primary_score", 0),
                "top_result": summary.get("top_result", {}),
                "ready": summary.get("ok") is True,
                "profile_source": "authored_profile_workspace" if profile_id in self.authored_profile_index() else "implemented_runner",
            })
        authored_profiles = [profile for profile in profiles if profile.get("profile_source") == "authored_profile_workspace"]
        return {
            "ok": True,
            "contract_version": PROFILE_DASHBOARD_CONTRACT_VERSION,
            "profiles": profiles,
            "profile_count": len(profiles),
            "implemented_profile_count": len([profile for profile in profiles if profile.get("ready")]),
            "authored_profile_count": len(authored_profiles),
            "result_contract_fields": self.contract_fields(),
            "source_gis_modified": False,
        }

    def profiles(self) -> dict:
        overview = self.overview()
        return {
            "ok": True,
            "contract_version": PROFILE_DASHBOARD_CONTRACT_VERSION,
            "profiles": overview["profiles"],
            "source_gis_modified": False,
        }

    def summary(self, profile_id: str) -> dict:
        rows_payload = self.results(profile_id, limit=0)
        if not rows_payload.get("ok"):
            return rows_payload
        rows = rows_payload.get("rows", [])
        scores = [parse_int(row.get("primary_score")) for row in rows]
        entity_counts: dict[str, int] = {}
        for row in rows:
            entity_type = str(row.get("entity_type") or "unknown")
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        normalized_id = rows_payload["profile_id"]
        return {
            "ok": True,
            "contract_version": PROFILE_DASHBOARD_CONTRACT_VERSION,
            "profile_id": normalized_id,
            "profile_name": rows_payload["profile_name"],
            "workspace_id": rows_payload["workspace_id"],
            "profile_source": "authored_profile_workspace" if normalized_id in self.authored_profile_index() else "implemented_runner",
            "result_count": len(rows),
            "high_priority_count": sum(1 for score in scores if score >= 90),
            "median_primary_score": round(float(median(scores)), 1) if scores else 0,
            "max_primary_score": max(scores) if scores else 0,
            "entity_type_counts": dict(sorted(entity_counts.items())),
            "route_over_250m_count": sum(1 for row in rows if parse_number(row.get("route_nearest_crossing_m")) > 250),
            "no_mapped_crossing_150m_count": sum(1 for row in rows if "no_mapped_crossing_within_150m" in row.get("flags", [])),
            "top_result": rows[0] if rows else {},
            "source_gis_modified": False,
        }

    def results(self, profile_id: str, limit: int = 50, min_score: int = 0, only_flags: bool = False) -> dict:
        normalized_id = self.normalize_profile_id(profile_id)
        if not normalized_id:
            return {"ok": False, "error": "profile_dashboard_profile_not_found", "profile_id": profile_id, "source_gis_modified": False}
        if normalized_id == SAFE_ACCESS_PROFILE_ID:
            rows = self.safe_access_rows()
        elif normalized_id == TRANSIT_PROFILE_ID:
            rows = self.transit_rows()
        elif normalized_id == PARK_PROFILE_ID:
            rows = self.park_rows()
        else:
            rows = self.authored_rows(normalized_id)
        rows = [
            row for row in rows
            if parse_int(row.get("primary_score")) >= min_score and (not only_flags or bool(row.get("flags")))
        ]
        rows.sort(key=lambda row: (-parse_int(row.get("primary_score")), -parse_number(row.get("route_nearest_crossing_m")), str(row.get("name") or "")))
        if limit > 0:
            rows = rows[: max(1, min(limit, 500))]
        return {
            "ok": True,
            "contract_version": PROFILE_DASHBOARD_CONTRACT_VERSION,
            "profile_id": normalized_id,
            "profile_name": self.profile_name_for(normalized_id),
            "workspace_id": self.workspace_id_for(normalized_id),
            "profile_source": "authored_profile_workspace" if normalized_id in self.authored_profile_index() else "implemented_runner",
            "row_count": len(rows),
            "rows": rows,
            "source_gis_modified": False,
        }

    def profile_order(self) -> list[str]:
        authored = [profile_id for profile_id in self.authored_profile_index() if profile_id not in self.base_profile_order]
        return self.base_profile_order + sorted(authored)

    def authored_profile_index(self) -> dict[str, dict]:
        selected: dict[str, dict] = {}
        for manifest in self.authored_manifests():
            profile_id = str(manifest.get("profile_id") or "")
            if profile_id and profile_id not in selected:
                selected[profile_id] = manifest
        return selected

    def authored_manifests(self) -> list[dict]:
        manifests = []
        if not self.workspaces_dir.exists():
            return manifests
        for manifest_path in self.workspaces_dir.glob("*/manifest.json"):
            manifest = read_json(manifest_path)
            if manifest.get("authored_profile_workspace") and manifest.get("profile_workspace"):
                manifests.append(manifest)
        return sorted(manifests, key=lambda item: str(item.get("created_at_utc") or ""), reverse=True)

    def profile_name_for(self, profile_id: str) -> str:
        if profile_id in self.base_profile_names:
            return self.base_profile_names[profile_id]
        manifest = self.authored_profile_index().get(profile_id, {})
        template_id = manifest.get("template_id") or "authored draft"
        return f"Authored profile audit: {profile_id} ({template_id})"

    def workspace_id_for(self, profile_id: str) -> str:
        if profile_id in self.base_workspace_ids:
            return self.base_workspace_ids[profile_id]
        return str(self.authored_profile_index().get(profile_id, {}).get("workspace_id") or "")

    def safe_access_rows(self) -> list[dict]:
        workspace_id = self.base_workspace_ids[SAFE_ACCESS_PROFILE_ID]
        network_rows = read_csv_rows(self.table_file(workspace_id, "network_access_results"))
        risk_rows = read_csv_rows(self.table_file(workspace_id, "risk_assessment_results"))
        risk_by_id = {row.get("generator_id"): row for row in risk_rows}
        rows = []
        for row in network_rows:
            risk = risk_by_id.get(row.get("generator_id"), {})
            rows.append(self.contract_row(
                profile_id=SAFE_ACCESS_PROFILE_ID,
                workspace_id=workspace_id,
                result_id=row.get("generator_id"),
                osm_id=row.get("osm_id"),
                entity_type=row.get("generator_type"),
                name=row.get("name"),
                primary_score=parse_int(row.get("route_review_priority_score"), parse_int(risk.get("risk_score"))),
                secondary_score=parse_int(row.get("base_risk_score"), parse_int(risk.get("risk_score"))),
                score_label="route_review_priority_score",
                nearest_crossing_id=row.get("straight_nearest_crossing_id") or risk.get("nearest_crossing_id"),
                nearest_crossing_m=parse_number(row.get("straight_nearest_crossing_m"), parse_number(risk.get("nearest_crossing_m"))),
                route_nearest_crossing_id=row.get("route_nearest_crossing_id"),
                route_nearest_crossing_m=parse_number(row.get("route_nearest_crossing_m")),
                route_vs_straight_ratio=parse_number(row.get("route_vs_straight_ratio")),
                nearest_major_road_class=risk.get("nearest_major_road_class"),
                nearest_major_road_m=parse_number(risk.get("nearest_major_road_m")),
                crossing_within_150m=parse_bool(risk.get("crossing_within_150m")),
                major_road_within_150m=parse_bool(risk.get("major_road_within_150m")),
                flags=unique_flags(parse_flags(row.get("network_flags")), parse_flags(risk.get("risk_flags"))),
                data_quality_flags=unique_flags(parse_flags(row.get("data_quality_flags")), parse_flags(risk.get("data_quality_flags"))),
                review_wording=row.get("review_wording") or risk.get("review_wording"),
                geometry_wkt=row.get("geometry_wkt") or risk.get("geometry_wkt"),
                lon=parse_number(row.get("lon"), parse_number(risk.get("lon"))),
                lat=parse_number(row.get("lat"), parse_number(risk.get("lat"))),
                source_table="network_access_results",
                source_evidence="safe_access_route_aware_workspace",
            ))
        return rows

    def transit_rows(self) -> list[dict]:
        profile_id = TRANSIT_PROFILE_ID
        workspace_id = self.base_workspace_ids[profile_id]
        rows = []
        for row in read_csv_rows(self.table_file(workspace_id, "transit_stop_access_results")):
            rows.append(self.contract_row(
                profile_id=profile_id,
                workspace_id=workspace_id,
                result_id=row.get("transit_stop_id"),
                osm_id=row.get("osm_id"),
                entity_type="bus_stop",
                name=row.get("name"),
                primary_score=parse_int(row.get("transit_review_priority_score")),
                secondary_score=parse_int(row.get("base_risk_score")),
                score_label="transit_review_priority_score",
                nearest_crossing_id=row.get("nearest_crossing_id"),
                nearest_crossing_m=parse_number(row.get("nearest_crossing_m")),
                route_nearest_crossing_id=row.get("route_nearest_crossing_id"),
                route_nearest_crossing_m=parse_number(row.get("route_nearest_crossing_m")),
                route_vs_straight_ratio=parse_number(row.get("route_vs_straight_ratio")),
                nearest_major_road_class=row.get("nearest_major_road_class"),
                nearest_major_road_m=parse_number(row.get("nearest_major_road_m")),
                crossing_within_150m=parse_bool(row.get("crossing_within_150m")),
                major_road_within_150m=parse_bool(row.get("major_road_within_150m")),
                flags=parse_flags(row.get("transit_access_flags")),
                data_quality_flags=parse_flags(row.get("data_quality_flags")),
                review_wording=row.get("review_wording"),
                geometry_wkt=row.get("geometry_wkt"),
                lon=parse_number(row.get("lon")),
                lat=parse_number(row.get("lat")),
                source_table="transit_stop_access_results",
                source_evidence="transit_profile_workspace",
            ))
        return rows

    def park_rows(self) -> list[dict]:
        profile_id = PARK_PROFILE_ID
        workspace_id = self.base_workspace_ids[profile_id]
        rows = []
        for row in read_csv_rows(self.table_file(workspace_id, "park_playground_access_results")):
            rows.append(self.contract_row(
                profile_id=profile_id,
                workspace_id=workspace_id,
                result_id=row.get("public_space_id"),
                osm_id=row.get("osm_id"),
                entity_type=row.get("place_type"),
                name=row.get("name"),
                primary_score=parse_int(row.get("public_space_review_priority_score")),
                secondary_score=parse_int(row.get("base_risk_score")),
                score_label="public_space_review_priority_score",
                nearest_crossing_id=row.get("nearest_crossing_id"),
                nearest_crossing_m=parse_number(row.get("nearest_crossing_m")),
                route_nearest_crossing_id=row.get("route_nearest_crossing_id"),
                route_nearest_crossing_m=parse_number(row.get("route_nearest_crossing_m")),
                route_vs_straight_ratio=parse_number(row.get("route_vs_straight_ratio")),
                nearest_major_road_class=row.get("nearest_major_road_class"),
                nearest_major_road_m=parse_number(row.get("nearest_major_road_m")),
                crossing_within_150m=parse_bool(row.get("crossing_within_150m")),
                major_road_within_150m=parse_bool(row.get("major_road_within_150m")),
                flags=parse_flags(row.get("public_space_access_flags")),
                data_quality_flags=parse_flags(row.get("data_quality_flags")),
                review_wording=row.get("review_wording"),
                geometry_wkt=row.get("geometry_wkt"),
                lon=parse_number(row.get("lon")),
                lat=parse_number(row.get("lat")),
                source_table="park_playground_access_results",
                source_evidence="park_playground_profile_workspace",
            ))
        return rows

    def authored_rows(self, profile_id: str) -> list[dict]:
        manifest = self.authored_profile_index().get(profile_id, {})
        workspace_id = str(manifest.get("workspace_id") or "")
        rows = []
        for row in read_csv_rows(self.table_file(workspace_id, "authored_profile_results")):
            evidence_status = str(row.get("evidence_status") or "")
            data_quality_flags = parse_flags(row.get("data_quality_flags"))
            if evidence_status == "not_available_in_inspected_files" and "not_available_in_inspected_files" not in data_quality_flags:
                data_quality_flags.append("not_available_in_inspected_files")
            rows.append(self.contract_row(
                profile_id=profile_id,
                workspace_id=workspace_id,
                result_id=row.get("result_id"),
                osm_id="",
                entity_type=row.get("requirement_type"),
                name=row.get("tag_or_field"),
                primary_score=parse_int(row.get("primary_score"), min(100, parse_int(row.get("total_count")))),
                secondary_score=parse_int(row.get("total_count")),
                score_label=str(row.get("primary_metric") or "osm_tag_evidence_count"),
                nearest_crossing_id="",
                nearest_crossing_m=0,
                route_nearest_crossing_id="",
                route_nearest_crossing_m=0,
                route_vs_straight_ratio=0,
                nearest_major_road_class="",
                nearest_major_road_m=0,
                crossing_within_150m=None,
                major_road_within_150m=None,
                flags=parse_flags(row.get("flags")),
                data_quality_flags=data_quality_flags,
                review_wording=row.get("review_wording"),
                geometry_wkt="",
                lon=0,
                lat=0,
                source_table="authored_profile_results",
                source_evidence=row.get("example_values") or row.get("sources") or evidence_status,
            ))
        return rows

    def contract_row(
        self,
        *,
        profile_id: str,
        workspace_id: str,
        result_id: object,
        osm_id: object,
        entity_type: object,
        name: object,
        primary_score: int,
        secondary_score: int,
        score_label: str,
        nearest_crossing_id: object,
        nearest_crossing_m: float,
        route_nearest_crossing_id: object,
        route_nearest_crossing_m: float,
        route_vs_straight_ratio: float,
        nearest_major_road_class: object,
        nearest_major_road_m: float,
        crossing_within_150m: bool | None,
        major_road_within_150m: bool | None,
        flags: list[str],
        data_quality_flags: list[str],
        review_wording: object,
        geometry_wkt: object,
        lon: float,
        lat: float,
        source_table: str,
        source_evidence: object = "",
    ) -> dict:
        return {
            "profile_id": profile_id,
            "profile_name": self.profile_name_for(profile_id),
            "workspace_id": workspace_id,
            "result_id": str(result_id or ""),
            "osm_id": str(osm_id or ""),
            "entity_type": str(entity_type or "unknown"),
            "name": str(name or ""),
            "primary_score": primary_score,
            "secondary_score": secondary_score,
            "score_label": score_label,
            "nearest_crossing_id": str(nearest_crossing_id or ""),
            "nearest_crossing_m": round(nearest_crossing_m, 1),
            "route_nearest_crossing_id": str(route_nearest_crossing_id or ""),
            "route_nearest_crossing_m": round(route_nearest_crossing_m, 1),
            "route_vs_straight_ratio": round(route_vs_straight_ratio, 2),
            "nearest_major_road_class": str(nearest_major_road_class or ""),
            "nearest_major_road_m": round(nearest_major_road_m, 1),
            "crossing_within_150m": crossing_within_150m,
            "major_road_within_150m": major_road_within_150m,
            "flags": flags,
            "data_quality_flags": data_quality_flags,
            "review_wording": str(review_wording or self.review_wording),
            "geometry_wkt": str(geometry_wkt or ""),
            "lon": lon,
            "lat": lat,
            "source_table": source_table,
            "source_evidence": str(source_evidence or ""),
            "source_gis_modified": False,
        }

    def _resolve_stored_path(self, stored: str) -> Path:
        """Resolve a stored path, tolerating relocation of the artifact store.

        Manifests persist absolute paths. If the tree was moved (so the absolute
        path no longer exists), re-root the portion after the ``analysis_output``
        segment under the current store so the file is still found. On the
        original machine the stored path exists and is returned unchanged, so
        this is behaviour-preserving there.
        """
        path = Path(stored)
        if path.exists():
            return path
        parts = path.parts
        if "analysis_output" in parts:
            idx = len(parts) - 1 - list(reversed(parts)).index("analysis_output")
            tail = Path(*parts[idx + 1:]) if idx + 1 < len(parts) else Path()
            candidate = self.workspaces_dir.parent / tail
            if candidate.exists():
                return candidate
        return path

    def table_file(self, workspace_id: str, table_name: str) -> Path:
        workspace_dir = self.workspaces_dir / workspace_id
        manifest = read_json(workspace_dir / "manifest.json")
        for item in manifest.get("tables", []):
            if item.get("table") == table_name and item.get("file"):
                resolved = self._resolve_stored_path(str(item["file"]))
                if resolved.exists():
                    return resolved
                break
        return workspace_dir / "tables" / f"{table_name}.csv"

    def normalize_profile_id(self, profile_id: str) -> str:
        clean = str(profile_id or "").strip()
        aliases = {
            "safe_access": SAFE_ACCESS_PROFILE_ID,
            "safe_access_pedestrian_review": SAFE_ACCESS_PROFILE_ID,
            "transit_walk_access": TRANSIT_PROFILE_ID,
            "transit_stop_walk_access": TRANSIT_PROFILE_ID,
            "park_playground_access": PARK_PROFILE_ID,
            "public_space_access": PARK_PROFILE_ID,
        }
        if clean in aliases:
            return aliases[clean]
        authored = self.authored_profile_index()
        if clean in authored:
            return clean
        if clean in {"authored_profile_audit", "authored_draft_audit"} and authored:
            return next(iter(authored.keys()))
        return ""

    @staticmethod
    def contract_fields() -> list[str]:
        return [
            "profile_id",
            "workspace_id",
            "result_id",
            "osm_id",
            "entity_type",
            "name",
            "primary_score",
            "secondary_score",
            "score_label",
            "nearest_crossing_m",
            "route_nearest_crossing_m",
            "nearest_major_road_m",
            "flags",
            "data_quality_flags",
            "review_wording",
            "source_evidence",
            "lon",
            "lat",
            "source_table",
            "source_gis_modified",
        ]
