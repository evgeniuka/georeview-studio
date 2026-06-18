from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from source_onboarding import SUPPORTED_EXTENSIONS


LOCAL_INTAKE_VERSION = "local_intake_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "item") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:96] or fallback


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def compact_source(source: dict) -> dict:
    readiness = source.get("readiness", {})
    return {
        "dataset_id": source.get("dataset_id"),
        "file_name": source.get("file_name"),
        "path": source.get("path"),
        "extension": source.get("extension"),
        "size_mb": source.get("size_mb"),
        "modified_utc": source.get("modified_utc"),
        "likely_role": source.get("likely_role"),
        "profile_status": source.get("profile_status"),
        "layer_count": len(source.get("layers", [])),
        "archive_member_count": source.get("archive_member_count", 0),
        "readiness_level": readiness.get("level"),
        "supported_templates": readiness.get("supported_templates", []),
        "blockers": readiness.get("blockers", []),
        "recommended_next_action": readiness.get("recommended_next_action"),
        "source_gis_modified": False,
    }


class LocalIntakeWizard:
    def __init__(self, maps_root: Path, output_root: Path, onboarding: object, default_dataset_id: str) -> None:
        self.maps_root = maps_root.resolve()
        self.output_root = output_root.resolve()
        self.onboarding = onboarding
        self.default_dataset_id = default_dataset_id
        self.intake_dir = self.output_root / "georeview_studio_local_intake"

    def status(self) -> dict:
        sources = self.onboarding.sources()
        return {
            "ok": True,
            "local_intake_version": LOCAL_INTAKE_VERSION,
            "maps_root": str(self.maps_root),
            "intake_dir": str(self.intake_dir),
            "mode": "reviewed_local_file_or_folder_intake",
            "source_count": len(sources),
            "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
            "default_dataset_id": self.default_dataset_id,
            "claim_boundaries": self.claim_boundaries(),
            "source_gis_modified": False,
        }

    def sources(self) -> dict:
        sources = [compact_source(source) for source in self.onboarding.sources()]
        return {
            "ok": True,
            "local_intake_version": LOCAL_INTAKE_VERSION,
            "sources": sources,
            "source_count": len(sources),
            "source_gis_modified": False,
        }

    def preview(self, body: dict | None = None) -> dict:
        body = body or {}
        dataset_id = str(body.get("dataset_id") or "").strip()
        requested_path = str(body.get("path") or "").strip()
        if dataset_id:
            return self.preview_dataset(dataset_id)
        if requested_path:
            return self.preview_path(requested_path)
        return {"error": "local_intake_input_missing", "detail": "dataset_id or path is required", "source_gis_modified": False}

    def create_plan(self, body: dict | None = None) -> dict:
        preview = self.preview(body)
        if preview.get("error"):
            return preview
        plan_id = self.next_plan_id(preview)
        plan = {
            "ok": True,
            "local_intake_version": LOCAL_INTAKE_VERSION,
            "plan_id": plan_id,
            "created_at_utc": utc_now(),
            "source_preview": preview,
            "recommended_next_actions": self.recommended_next_actions(preview),
            "claim_boundaries": self.claim_boundaries(),
            "review_wording": REVIEW_WORDING,
            "output_policy": "Generated intake plans are metadata only and are written under analysis_output.",
            "source_gis_modified": False,
        }
        self.intake_dir.mkdir(parents=True, exist_ok=True)
        plan_path = self.intake_dir / f"{plan_id}.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        response = dict(plan)
        response["plan_file"] = str(plan_path)
        return response

    def preview_dataset(self, dataset_id: str) -> dict:
        source = self.onboarding.source_detail(dataset_id)
        if source.get("error"):
            return source
        return {
            "ok": True,
            "local_intake_version": LOCAL_INTAKE_VERSION,
            "input_type": "registered_dataset",
            "dataset_id": dataset_id,
            "source": compact_source(source),
            "layers": source.get("layers", [])[:25],
            "readiness": source.get("readiness", {}),
            "recommended_next_actions": self.recommended_next_actions({"source": compact_source(source), "readiness": source.get("readiness", {})}),
            "source_gis_modified": False,
        }

    def preview_path(self, requested_path: str) -> dict:
        resolved = self.resolve_requested_path(requested_path)
        if isinstance(resolved, dict):
            return resolved
        if resolved.is_dir():
            return self.preview_directory(resolved)
        if not resolved.is_file():
            return {"error": "local_intake_path_not_found", "path": str(resolved), "source_gis_modified": False}
        return self.preview_file(resolved)

    def resolve_requested_path(self, requested_path: str) -> Path | dict:
        try:
            resolved = Path(requested_path).expanduser().resolve(strict=False)
        except OSError as exc:
            return {"error": "local_intake_path_invalid", "detail": repr(exc), "source_gis_modified": False}
        if not is_relative_to(resolved, self.maps_root):
            return {
                "error": "local_intake_path_outside_maps_root",
                "path": str(resolved),
                "maps_root": str(self.maps_root),
                "source_gis_modified": False,
            }
        if is_relative_to(resolved, self.output_root):
            return {
                "error": "local_intake_analysis_output_not_allowed",
                "path": str(resolved),
                "detail": "Intake reads source GIS candidates only; generated analysis_output files are excluded.",
                "source_gis_modified": False,
            }
        if not resolved.exists():
            return {"error": "local_intake_path_not_found", "path": str(resolved), "source_gis_modified": False}
        return resolved

    def preview_directory(self, path: Path) -> dict:
        registered = []
        for source in self.onboarding.sources():
            source_path = Path(source.get("path", "")).resolve(strict=False)
            if is_relative_to(source_path, path):
                registered.append(compact_source(source))
        supported_count = 0
        for child in path.rglob("*"):
            if child.is_file() and self.onboarding.extension_for(child) in SUPPORTED_EXTENSIONS:
                supported_count += 1
        return {
            "ok": True,
            "local_intake_version": LOCAL_INTAKE_VERSION,
            "input_type": "directory",
            "path": str(path),
            "supported_file_count": supported_count,
            "registered_source_count": len(registered),
            "sources": registered,
            "recommended_next_actions": self.recommended_next_actions({"sources": registered, "supported_file_count": supported_count}),
            "source_gis_modified": False,
        }

    def preview_file(self, path: Path) -> dict:
        extension = self.onboarding.extension_for(path)
        if extension not in SUPPORTED_EXTENSIONS:
            return {
                "error": "local_intake_unsupported_format",
                "path": str(path),
                "extension": extension,
                "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
                "source_gis_modified": False,
            }
        for source in self.onboarding.sources():
            if Path(source.get("path", "")).resolve(strict=False) == path:
                return {
                    "ok": True,
                    "local_intake_version": LOCAL_INTAKE_VERSION,
                    "input_type": "registered_file",
                    "source": compact_source(source),
                    "layers": source.get("layers", [])[:25],
                    "readiness": source.get("readiness", {}),
                    "recommended_next_actions": self.recommended_next_actions({"source": compact_source(source), "readiness": source.get("readiness", {})}),
                    "source_gis_modified": False,
                }
        pbf_available = any(str(source.get("extension")) in {".pbf", ".osm.pbf"} for source in self.onboarding.sources())
        profiled = self.onboarding.profile_file(path, pbf_available)
        return {
            "ok": True,
            "local_intake_version": LOCAL_INTAKE_VERSION,
            "input_type": "ad_hoc_file_profile",
            "source": compact_source(profiled),
            "layers": profiled.get("layers", [])[:25],
            "readiness": profiled.get("readiness", {}),
            "recommended_next_actions": self.recommended_next_actions({"source": compact_source(profiled), "readiness": profiled.get("readiness", {})}),
            "source_gis_modified": False,
        }

    @staticmethod
    def recommended_next_actions(preview: dict) -> list[str]:
        readiness = preview.get("readiness") or preview.get("source", {}).get("readiness") or {}
        level = readiness.get("level") or preview.get("source", {}).get("readiness_level") or ""
        if level == "ready_for_safe_access_selected_pilot":
            return [
                "Run selected-pilot preflight.",
                "Create or reuse a route-aware Safe Access workspace.",
                "Generate the profile dashboard export bundle for portfolio evidence.",
            ]
        if level == "ready_as_osm_tag_enrichment_source":
            return [
                "Pair this PBF with a compatible Geofabrik Shapefile ZIP.",
                "Use it for extra OSM tag evidence where the current mapper supports enrichment.",
            ]
        if preview.get("input_type") == "directory":
            if preview.get("registered_source_count", 0) > 0:
                return ["Select one registered source dataset from this directory and preview readiness."]
            return ["Add a supported GIS source file under this directory or use generic layer inventory."]
        return [
            "Use generic layer inventory first.",
            "Implement a profile mapper before running domain analytics on this source.",
        ]

    @staticmethod
    def claim_boundaries() -> list[str]:
        return [
            "Local intake profiles source evidence only.",
            "It does not modify source GIS files.",
            "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
            REVIEW_WORDING,
        ]

    def next_plan_id(self, preview: dict) -> str:
        source = preview.get("source", {})
        seed = source.get("dataset_id") or preview.get("dataset_id") or preview.get("input_type") or "intake"
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"local_intake_plan_{safe_token(seed)}_{safe_token(stamp)}"
