from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


DATASET_PACKAGE_VERSION = "dataset_package_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "dataset_package") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:120] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
        "readiness_level": readiness.get("level"),
        "supported_templates": readiness.get("supported_templates", []),
        "blockers": readiness.get("blockers", []),
        "recommended_next_action": readiness.get("recommended_next_action"),
        "source_gis_modified": False,
    }


class DatasetPackageBuilder:
    def __init__(
        self,
        output_root: Path,
        onboarding: object,
        local_intake: object,
        template_authoring: object,
        execution_queue: object,
    ) -> None:
        self.output_root = output_root
        self.onboarding = onboarding
        self.local_intake = local_intake
        self.template_authoring = template_authoring
        self.execution_queue = execution_queue
        self.packages_dir = output_root / "georeview_studio_dataset_packages"

    def status(self) -> dict:
        sources = self.onboarding.sources()
        packages = self.list_packages(200)
        return {
            "ok": True,
            "dataset_package_version": DATASET_PACKAGE_VERSION,
            "mode": "reusable_dataset_evidence_package",
            "packages_dir": str(self.packages_dir),
            "source_count": len(sources),
            "package_count": len(packages),
            "recent_packages": packages[:5],
            "components": [
                "source_readiness",
                "local_intake_plan",
                "template_authoring_draft",
                "execution_queue_snapshot",
                "package_report",
            ],
            "policy": {
                "source_gis_read_only": True,
                "writes_only_under_analysis_output": True,
                "package_is_evidence_not_prediction": True,
                "missing_tags_are_data_quality_flags": True,
            },
            "approved_review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }

    def create(self, body: dict | None = None) -> dict:
        body = body or {}
        dataset_id = str(body.get("dataset_id") or "israel-and-palestine-260521-free-shp-zip")
        template_id = str(body.get("template_id") or "generic_osm_tag_coverage")
        queue_profile_id = str(body.get("queue_profile_id") or "osm_tag_quality")
        target_workspace_id = str(body.get("target_workspace_id") or self.execution_queue.contract_execution.default_workspace_id(queue_profile_id))
        source = self.onboarding.source_detail(dataset_id)
        if source.get("error"):
            return {**source, "source_gis_modified": False}

        package_id = self.next_package_id(dataset_id)
        package_dir = self.package_dir(package_id)
        source_readiness = {
            "ok": True,
            "dataset_package_version": DATASET_PACKAGE_VERSION,
            "source": compact_source(source),
            "layers": source.get("layers", [])[:30],
            "source_gis_modified": False,
        }
        intake_plan = self.local_intake.create_plan({"dataset_id": dataset_id})
        template_draft = self.template_authoring.draft({"template_id": template_id, "dataset_id": dataset_id}, write_files=True)
        queue_job = self.execution_queue.enqueue({
            "profile_id": queue_profile_id,
            "dataset_id": dataset_id,
            "target_workspace_id": target_workspace_id,
            "execute_now": True,
        }, body.get("runner") if callable(body.get("runner")) else body.get("_runner"))
        if not callable(body.get("_runner")):
            queue_job = {
                "ok": False,
                "error": "dataset_package_runner_not_bound",
                "detail": "Use create_with_runner from app integration.",
                "source_gis_modified": False,
            }

        return self.write_package(
            package_id,
            dataset_id,
            template_id,
            queue_profile_id,
            target_workspace_id,
            source_readiness,
            intake_plan,
            template_draft,
            queue_job,
        )

    def create_with_runner(self, body: dict | None, runner: object) -> dict:
        body = dict(body or {})
        body["_runner"] = runner
        return self.create(body)

    def write_package(
        self,
        package_id: str,
        dataset_id: str,
        template_id: str,
        queue_profile_id: str,
        target_workspace_id: str,
        source_readiness: dict,
        intake_plan: dict,
        template_draft: dict,
        queue_job: dict,
    ) -> dict:
        package_dir = self.package_dir(package_id)
        package_dir.mkdir(parents=True, exist_ok=True)
        source_path = package_dir / "source_readiness.json"
        intake_path = package_dir / "local_intake_plan.json"
        template_path = package_dir / "template_authoring_draft.json"
        queue_path = package_dir / "execution_queue_job.json"
        report_path = package_dir / "dataset_package_report.md"
        write_json(source_path, source_readiness)
        write_json(intake_path, intake_plan)
        write_json(template_path, template_draft)
        write_json(queue_path, queue_job)
        manifest = {
            "ok": True,
            "dataset_package_version": DATASET_PACKAGE_VERSION,
            "package_id": package_id,
            "created_at_utc": utc_now(),
            "dataset_id": dataset_id,
            "template_id": template_id,
            "queue_profile_id": queue_profile_id,
            "target_workspace_id": target_workspace_id,
            "source_file": source_readiness.get("source", {}).get("file_name"),
            "readiness_level": source_readiness.get("source", {}).get("readiness_level"),
            "layer_count": source_readiness.get("source", {}).get("layer_count"),
            "intake_plan_id": intake_plan.get("plan_id"),
            "template_draft_id": template_draft.get("draft_id"),
            "execution_queue_job_id": queue_job.get("job_id"),
            "execution_queue_status": queue_job.get("status"),
            "source_gis_modified": False,
            "files": {
                "manifest": str(package_dir / "manifest.json"),
                "source_readiness": str(source_path),
                "local_intake_plan": str(intake_path),
                "template_authoring_draft": str(template_path),
                "execution_queue_job": str(queue_path),
                "dataset_package_report": str(report_path),
            },
            "claim_boundaries": [
                "Dataset packages summarize inspected local evidence.",
                "They do not modify source GIS files.",
                "They do not predict crashes or prove real-world conditions.",
                "Missing OSM tags remain data-quality flags.",
                REVIEW_WORDING,
            ],
        }
        write_json(package_dir / "manifest.json", manifest)
        report_path.write_text(self.package_markdown(manifest), encoding="utf-8")
        return {**manifest, "package_dir": str(package_dir)}

    def list_packages(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit or 20), 200))
        rows = []
        if not self.packages_dir.exists():
            return rows
        for manifest_path in sorted(self.packages_dir.glob("*/manifest.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            manifest = read_json(manifest_path)
            if manifest.get("dataset_package_version") != DATASET_PACKAGE_VERSION:
                continue
            rows.append({
                "ok": True,
                "package_id": manifest.get("package_id"),
                "dataset_id": manifest.get("dataset_id"),
                "template_id": manifest.get("template_id"),
                "queue_profile_id": manifest.get("queue_profile_id"),
                "readiness_level": manifest.get("readiness_level"),
                "execution_queue_status": manifest.get("execution_queue_status"),
                "created_at_utc": manifest.get("created_at_utc"),
                "source_gis_modified": manifest.get("source_gis_modified") is True,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, package_id: str) -> dict:
        manifest_path = self.package_dir(package_id) / "manifest.json"
        if not manifest_path.exists() or not self.safe_package_path(manifest_path):
            return {"ok": False, "error": "dataset_package_not_found", "package_id": package_id, "source_gis_modified": False}
        manifest = read_json(manifest_path)
        if not manifest:
            return {"ok": False, "error": "dataset_package_not_found", "package_id": package_id, "source_gis_modified": False}
        return {
            **manifest,
            "package_dir": str(self.package_dir(package_id)),
            "source_readiness": read_json(Path(manifest.get("files", {}).get("source_readiness", ""))),
            "local_intake_plan": read_json(Path(manifest.get("files", {}).get("local_intake_plan", ""))),
            "template_authoring_draft": read_json(Path(manifest.get("files", {}).get("template_authoring_draft", ""))),
            "execution_queue_job": read_json(Path(manifest.get("files", {}).get("execution_queue_job", ""))),
        }

    def output_file(self, package_id: str, output_id: str = "dataset_package_report") -> dict:
        detail = self.detail(package_id)
        if detail.get("error"):
            return detail
        path = Path(detail.get("files", {}).get(output_id, ""))
        if not path.exists() or not self.safe_package_path(path):
            return {"ok": False, "error": "dataset_package_output_not_found", "package_id": package_id, "output_id": output_id, "source_gis_modified": False}
        return {"ok": True, "path": path, "output_id": output_id, "source_gis_modified": False}

    @staticmethod
    def package_markdown(manifest: dict) -> str:
        lines = [
            "# Dataset Evidence Package",
            "",
            f"Package id: `{manifest.get('package_id')}`",
            f"Dataset: `{manifest.get('dataset_id')}`",
            f"Source file: `{manifest.get('source_file')}`",
            f"Readiness: `{manifest.get('readiness_level')}`",
            f"Layer count: `{manifest.get('layer_count')}`",
            f"Template draft: `{manifest.get('template_draft_id')}`",
            f"Execution queue job: `{manifest.get('execution_queue_job_id')}`",
            f"Execution queue status: `{manifest.get('execution_queue_status')}`",
            "",
            "## Files",
            "",
        ]
        for key, value in manifest.get("files", {}).items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend(["", "## Boundaries", ""])
        for item in manifest.get("claim_boundaries", []):
            lines.append(f"- {item}")
        return "\n".join(lines).rstrip() + "\n"

    def next_package_id(self, dataset_id: str) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"dataset_package_{safe_token(dataset_id)}_{safe_token(stamp)}"

    def package_dir(self, package_id: str) -> Path:
        return self.packages_dir / safe_token(package_id)

    def safe_package_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.packages_dir.resolve())
            return True
        except ValueError:
            return False
