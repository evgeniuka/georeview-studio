from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PORTABLE_RELEASE_PACKAGE_VERSION = "portable_release_package_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "portable_release_package", max_len: int = 120) -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:max_len] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def safe_call(fn: Callable[[], object], default: object) -> object:
    try:
        result = fn()
        return result if result is not None else default
    except Exception as exc:
        return {"error": "portable_release_package_probe_failed", "detail": repr(exc)}


class PortableReleasePackageBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        portfolio_export_launcher: object,
        reviewer_audit_index: object,
        reproducibility_audit_packet: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.portfolio_export_launcher = portfolio_export_launcher
        self.reviewer_audit_index = reviewer_audit_index
        self.reproducibility_audit_packet = reproducibility_audit_packet
        self.expected_api_endpoints = expected_api_endpoints
        self.packages_dir = output_root / "georeview_studio_portable_release_packages"

    def status(self) -> dict:
        launchers = self.launcher_rows(100)
        packages = self.list_packages(100)
        ready_packages = [row for row in packages if row.get("package_readiness") == "ready_to_share_portable_release"]
        launcher_status = safe_call(self.portfolio_export_launcher.status, {})
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "portable_release_package_version": PORTABLE_RELEASE_PACKAGE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "portable_zip_for_local_reviewer_demo",
            "output_dir": str(self.packages_dir),
            "launcher_count": len(launchers),
            "ready_launcher_count": len([row for row in launchers if row.get("launcher_readiness") == "ready_for_portfolio_launch"]),
            "package_count": len(packages),
            "ready_package_count": len(ready_packages),
            "latest_package_file_count": ready_packages[0].get("included_file_count", 0) if ready_packages else 0,
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_portable_package" if self.is_ready(launcher_status, launchers) else "waiting_for_portfolio_export_launcher",
            "package_policy": self.package_policy(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_package(self, body: dict | None = None) -> dict:
        body = body or {}
        target_limit = max(5, min(int(body.get("target_limit") or 30), 100))
        launcher_id = str(body.get("launcher_id") or "").strip()
        launcher = self.resolve_launcher(launcher_id)
        if launcher.get("error"):
            return launcher
        if launcher.get("launcher_readiness") != "ready_for_portfolio_launch":
            return self.error("portable_release_package_not_ready", "The selected launcher must be ready_for_portfolio_launch.")

        stamp = utc_now()
        package_id = f"portable_release_package_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        package_dir = self.package_dir(package_id)
        package_dir.mkdir(parents=True, exist_ok=True)
        zip_path = package_dir / f"{package_id}.zip"
        manifest_path = package_dir / "package_manifest.json"
        readme_path = package_dir / "README.md"
        latest_path = self.packages_dir / "latest_portable_release_package.json"

        candidate_files = self.collect_candidate_files(launcher, target_limit)
        if len(candidate_files) < 3:
            return self.error("portable_release_package_input_missing", "At least three small evidence files are required for the package.")

        readme_text = self.package_readme(package_id, launcher, candidate_files)
        package = {
            "ok": True,
            "portable_release_package_version": PORTABLE_RELEASE_PACKAGE_VERSION,
            "package_id": package_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Portable release package for local reviewer demo."),
            "app_version": self.app_version,
            "launcher_id": launcher.get("launcher_id"),
            "package_readiness": "ready_to_share_portable_release",
            "included_file_count": len(candidate_files) + 2,
            "included_files": candidate_files,
            "zip_size_bytes": 0,
            "package_policy": self.package_policy(),
            "validation_summary": self.validation_summary(),
            "api_contract": self.api_contract_summary(),
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "zip": str(zip_path),
                "manifest": str(manifest_path),
                "readme": str(readme_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, package)
        write_json(latest_path, package)
        readme_path.write_text(readme_text, encoding="utf-8", newline="\n")
        self.write_zip(zip_path, package, readme_text, candidate_files)
        package["zip_size_bytes"] = zip_path.stat().st_size
        write_json(manifest_path, package)
        write_json(latest_path, package)
        return {"ok": True, "package": package, "source_gis_modified": False, "mutates_config": False}

    def list_packages(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.packages_dir.exists():
            return rows
        manifests = sorted(
            self.packages_dir.glob("portable_release_package_*/package_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("portable_release_package_version") != PORTABLE_RELEASE_PACKAGE_VERSION:
                continue
            rows.append({
                "package_id": payload.get("package_id"),
                "created_at": payload.get("created_at"),
                "package_readiness": payload.get("package_readiness"),
                "launcher_id": payload.get("launcher_id"),
                "included_file_count": payload.get("included_file_count"),
                "zip_size_bytes": payload.get("zip_size_bytes"),
                "download_url": f"/api/portable-release-package/packages/{payload.get('package_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, package_id: str) -> dict:
        path = self.package_dir(package_id) / "package_manifest.json"
        if not path.exists() or not self.safe_package_path(path):
            return {"ok": False, "error": "portable_release_package_not_found", "package_id": package_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "portable_release_package_not_found", "package_id": package_id, "source_gis_modified": False}
        return payload

    def output_file(self, package_id: str, output_id: str = "zip") -> dict:
        detail = self.detail(package_id)
        if detail.get("error"):
            return detail
        if output_id not in {"zip", "portable_release_package"}:
            return {"ok": False, "error": "portable_release_package_output_not_found", "package_id": package_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("zip") or ""))
        if not path.exists() or not self.safe_package_path(path):
            return {"ok": False, "error": "portable_release_package_output_not_found", "package_id": package_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def resolve_launcher(self, launcher_id: str) -> dict:
        if launcher_id:
            detail = safe_call(lambda: self.portfolio_export_launcher.detail(launcher_id), {})
            return detail if isinstance(detail, dict) else self.error("portfolio_export_launcher_not_found", "Launcher detail failed.")
        launchers = self.launcher_rows(1)
        if not launchers:
            return self.error("portable_release_package_input_missing", "At least one ready portfolio export launcher is required.")
        detail = safe_call(lambda: self.portfolio_export_launcher.detail(str(launchers[0].get("launcher_id") or "")), {})
        return detail if isinstance(detail, dict) else self.error("portfolio_export_launcher_not_found", "Launcher detail failed.")

    def launcher_rows(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.portfolio_export_launcher.list_launchers(limit), [])
        return rows if isinstance(rows, list) else []

    def collect_candidate_files(self, launcher: dict, limit: int) -> list[dict]:
        files: list[dict] = []
        seen: set[str] = set()

        def add_path(path: Path, group: str, label: str) -> None:
            if len(files) >= limit:
                return
            if not self.eligible_path(path):
                return
            try:
                size = path.stat().st_size
            except OSError:
                return
            if size <= 0 or size > 2_500_000:
                return
            arcname = self.unique_arcname(f"evidence/{safe_token(group, 'evidence')}/{path.name}", seen)
            files.append({
                "group": group,
                "label": label,
                "source_path": str(path),
                "archive_path": arcname,
                "size_bytes": size,
            })

        for key, value in (launcher.get("files", {}) if isinstance(launcher.get("files"), dict) else {}).items():
            add_path(Path(str(value)), "portfolio_export_launcher", f"launcher_{key}")

        for summary_name in ["project_manifest.json", "validation_summary.json", "api_contract_summary.json"]:
            add_path(self.project_dir / summary_name, "release_summaries", summary_name)

        for target in launcher.get("primary_actions", []) + launcher.get("launch_targets", []):
            kind = str(target.get("kind") or "artifact")
            artifact_id = str(target.get("artifact_id") or "")
            direct_path = str(target.get("path") or "")
            if direct_path:
                add_path(Path(direct_path), kind, artifact_id)
            if kind == "reviewer_audit_index" and artifact_id:
                detail = safe_call(lambda artifact_id=artifact_id: self.reviewer_audit_index.detail(artifact_id), {})
                for key, value in (detail.get("files", {}) if isinstance(detail, dict) and isinstance(detail.get("files"), dict) else {}).items():
                    add_path(Path(str(value)), kind, f"{artifact_id}_{key}")
            if kind == "reproducibility_audit_packet" and artifact_id:
                detail = safe_call(lambda artifact_id=artifact_id: self.reproducibility_audit_packet.detail(artifact_id), {})
                for key, value in (detail.get("files", {}) if isinstance(detail, dict) and isinstance(detail.get("files"), dict) else {}).items():
                    if key == "directory":
                        continue
                    add_path(Path(str(value)), kind, f"{artifact_id}_{key}")

        return files[:limit]

    def write_zip(self, zip_path: Path, package: dict, readme_text: str, files: list[dict]) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_bytes = json.dumps(package, ensure_ascii=False, indent=2).encode("utf-8")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.md", readme_text)
            zf.writestr("package_manifest.json", manifest_bytes)
            for row in files:
                source = Path(str(row.get("source_path") or ""))
                if self.eligible_path(source) and source.exists() and source.is_file():
                    zf.write(source, str(row.get("archive_path") or source.name))

    def is_ready(self, launcher_status: object, launchers: list[dict]) -> bool:
        if not isinstance(launcher_status, dict):
            return False
        return (
            launcher_status.get("portfolio_export_launcher_version") == "portfolio_export_launcher_v001"
            and int(launcher_status.get("ready_launcher_count") or 0) >= 1
            and len(launchers) >= 1
        )

    def validation_summary(self) -> dict:
        data = read_json(self.project_dir / "validation_summary.json")
        return {
            "passed": data.get("passed"),
            "app_version": data.get("app_version"),
            "release_readiness_level": data.get("release_readiness_level"),
            "release_readiness_failed_gates": data.get("release_readiness_failed_gates"),
        }

    def api_contract_summary(self) -> dict:
        data = read_json(self.project_dir / "api_contract_summary.json")
        return {"passed": data.get("passed"), "checked_endpoints": data.get("checked_endpoints")}

    def package_readme(self, package_id: str, launcher: dict, files: list[dict]) -> str:
        lines = [
            "# Portable Release Package",
            "",
            f"- Package id: `{package_id}`",
            f"- App version: `{self.app_version}`",
            f"- Launcher id: `{launcher.get('launcher_id')}`",
            f"- Included evidence files: `{len(files)}`",
            "",
            "## How To Review",
            "",
            "1. Start with `package_manifest.json` to inspect package lineage, validation status and file inventory.",
            "2. Open the launcher Markdown or HTML under `evidence/portfolio_export_launcher/`.",
            "3. Review the audit index and audit packet files before discussing any mapped result.",
            "4. Keep infrastructure risk indicators separate from data-quality flags.",
            "",
            "## Claim Boundary",
            "",
            f"{self.review_wording}",
            "",
            "This package is a local reviewer artifact for infrastructure risk indicators and field-review prioritization. It is not a crash prediction artifact and it does not claim real-world outcomes.",
            "",
            "## Included Files",
            "",
        ]
        for row in files:
            lines.append(f"- `{row.get('archive_path')}` - `{row.get('group')}` - {row.get('size_bytes')} bytes")
        lines.extend([
            "",
            "## Source Data Policy",
            "",
            "- Source GIS files are not included.",
            "- Generated evidence files come from the local `analysis_output` folder or the packaged app summaries.",
            "- Missing OSM tags remain data-quality evidence unless an explicit mapped value is present.",
            "",
        ])
        return "\n".join(lines)

    def package_policy(self) -> dict:
        return {
            "includes_source_gis": False,
            "max_file_size_bytes": 2_500_000,
            "allowed_roots": [str(self.project_dir), str(self.output_root)],
            "purpose": "Small portable reviewer package for local portfolio demonstration.",
        }

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["infrastructure risk indicators", "data-quality flags", "field-review prioritization", "portable reviewer evidence"],
            "not_allowed": ["crash prediction", "proof of real-world absence from missing tags", "absolute safety claims"],
            "missing_tag_rule": "Missing OSM tags add data-quality flags, not risk points by default.",
        }

    def eligible_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            if not resolved.exists() or not resolved.is_file():
                return False
            allowed = [self.project_dir.resolve(), self.output_root.resolve()]
            return any(str(resolved).startswith(str(root)) for root in allowed)
        except OSError:
            return False

    @staticmethod
    def unique_arcname(name: str, seen: set[str]) -> str:
        normalized = name.replace("\\", "/")
        if normalized not in seen:
            seen.add(normalized)
            return normalized
        base, dot, suffix = normalized.rpartition(".")
        if not dot:
            base, suffix = normalized, ""
        for index in range(2, 1000):
            candidate = f"{base}_{index}.{suffix}" if suffix else f"{base}_{index}"
            if candidate not in seen:
                seen.add(candidate)
                return candidate
        raise RuntimeError("too many duplicate archive names")

    def package_dir(self, package_id: str) -> Path:
        return self.packages_dir / safe_token(package_id, "missing_package", 180)

    def safe_package_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.packages_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
