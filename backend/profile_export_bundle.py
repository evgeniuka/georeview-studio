from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROFILE_EXPORT_BUNDLE_VERSION = "profile_export_bundle_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "bundle") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:96] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def markdown_escape(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


class ProfileExportBundleBuilder:
    def __init__(self, reports_dir: Path, profile_dashboard: object, portfolio_reports: object) -> None:
        self.reports_dir = reports_dir
        self.profile_dashboard = profile_dashboard
        self.portfolio_reports = portfolio_reports

    def generate(self, body: dict | None = None) -> dict:
        body = body or {}
        overview = self.profile_dashboard.overview()
        if overview.get("error"):
            return overview
        profiles_payload = self.profile_dashboard.profiles()
        profiles = profiles_payload.get("profiles", [])
        samples = []
        summaries = []
        sample_limit = max(1, min(int(body.get("sample_limit") or 5), 20))
        for profile in profiles:
            profile_id = profile.get("profile_id")
            summary = self.profile_dashboard.summary(profile_id)
            result_payload = self.profile_dashboard.results(profile_id, limit=sample_limit, only_flags=False)
            summaries.append(summary)
            samples.append({
                "profile_id": profile_id,
                "row_count": result_payload.get("row_count", 0),
                "rows": result_payload.get("rows", []),
            })
        comparison = self.portfolio_reports.generate_profile_comparison(
            str(body.get("base_workspace_id") or "safe_access_kfar_saba_route_aware_v001"),
            list(body.get("profile_workspace_ids") or [
                "transit_stop_walk_access_kfar_saba_v001",
                "park_playground_access_kfar_saba_v001",
            ]),
        )
        bundle_id = self.next_bundle_id()
        bundle = {
            "ok": True,
            "profile_export_bundle_version": PROFILE_EXPORT_BUNDLE_VERSION,
            "bundle_id": bundle_id,
            "bundle_type": "profile_dashboard_export_bundle",
            "generated_at_utc": utc_now(),
            "profile_dashboard_contract_version": overview.get("contract_version"),
            "profile_count": len(profiles),
            "profiles": profiles,
            "profile_summaries": summaries,
            "profile_result_samples": samples,
            "comparison_report": {
                "ok": comparison.get("ok") is True,
                "report_id": comparison.get("report_id"),
                "report_type": comparison.get("report_type"),
                "download_url": comparison.get("download_url"),
            },
            "claim_boundaries": [
                "This bundle summarizes mapped infrastructure review indicators.",
                "It is not a crash prediction model.",
                "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
                REVIEW_WORDING,
            ],
            "source_gis_modified": False,
        }
        self.write_bundle(bundle, self.markdown(bundle))
        return self.response_payload(bundle)

    def list_bundles(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit or 20), 200))
        bundles = []
        if not self.reports_dir.exists():
            return bundles
        for path in sorted(self.reports_dir.glob("profile_dashboard_bundle_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("profile_export_bundle_version") != PROFILE_EXPORT_BUNDLE_VERSION:
                continue
            bundles.append(self.compact_bundle(data))
            if len(bundles) >= limit:
                break
        return bundles

    def detail(self, bundle_id: str) -> dict:
        json_path = self.bundle_path(bundle_id, ".json")
        if not json_path.exists():
            return {"error": "export_bundle_not_found", "bundle_id": bundle_id}
        data = read_json(json_path)
        if not data:
            return {"error": "export_bundle_not_found", "bundle_id": bundle_id}
        data["json_file"] = str(json_path)
        md_path = self.bundle_path(bundle_id, ".md")
        data["markdown_file"] = str(md_path) if md_path.exists() else ""
        data["download_url"] = f"/api/export-bundles/{bundle_id}/download"
        return data

    def bundle_file(self, bundle_id: str, suffix: str = ".md") -> dict:
        if suffix not in {".md", ".json"}:
            return {"error": "export_bundle_output_not_found", "bundle_id": bundle_id}
        path = self.bundle_path(bundle_id, suffix)
        if not path.exists() or not self.safe_bundle_path(path):
            return {"error": "export_bundle_output_not_found", "bundle_id": bundle_id}
        return {"ok": True, "path": path, "file_name": path.name}

    def write_bundle(self, bundle: dict, markdown: str) -> None:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        bundle_id = bundle["bundle_id"]
        self.bundle_path(bundle_id, ".json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        self.bundle_path(bundle_id, ".md").write_text(markdown, encoding="utf-8")

    def response_payload(self, bundle: dict) -> dict:
        payload = self.compact_bundle(bundle)
        payload.update({
            "ok": True,
            "json_file": str(self.bundle_path(bundle["bundle_id"], ".json")),
            "markdown_file": str(self.bundle_path(bundle["bundle_id"], ".md")),
        })
        return payload

    @staticmethod
    def compact_bundle(bundle: dict) -> dict:
        bundle_id = bundle.get("bundle_id")
        comparison = bundle.get("comparison_report", {})
        return {
            "ok": True,
            "bundle_id": bundle_id,
            "bundle_type": bundle.get("bundle_type"),
            "generated_at_utc": bundle.get("generated_at_utc"),
            "profile_count": bundle.get("profile_count"),
            "profile_dashboard_contract_version": bundle.get("profile_dashboard_contract_version"),
            "comparison_report_id": comparison.get("report_id"),
            "source_gis_modified": bundle.get("source_gis_modified") is True,
            "download_url": f"/api/export-bundles/{bundle_id}/download" if bundle_id else "",
        }

    def markdown(self, bundle: dict) -> str:
        lines = [
            "# GeoReview Studio Profile Dashboard Export Bundle",
            "",
            f"Generated: {bundle.get('generated_at_utc')}",
            "",
            "## Claim Boundaries",
            "",
        ]
        for item in bundle.get("claim_boundaries", []):
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## Profile Coverage",
            "",
            "| Profile | Results | Workspace |",
            "| --- | ---: | --- |",
        ])
        for profile in bundle.get("profiles", []):
            lines.append(
                f"| {markdown_escape(profile.get('profile_id'))} | {profile.get('result_count', '')} | {markdown_escape(profile.get('workspace_id'))} |"
            )
        comparison = bundle.get("comparison_report", {})
        if comparison.get("report_id"):
            lines.extend([
                "",
                "## Linked Comparison Report",
                "",
                f"- Report id: `{comparison.get('report_id')}`",
                f"- Download: `{comparison.get('download_url')}`",
            ])
        lines.extend([
            "",
            "## Result Samples",
            "",
        ])
        for sample in bundle.get("profile_result_samples", []):
            lines.extend([
                f"### {sample.get('profile_id')}",
                "",
                "| ID | Type | Name | Score | Flags |",
                "| --- | --- | --- | ---: | --- |",
            ])
            for row in sample.get("rows", [])[:5]:
                flags = ", ".join(str(item) for item in row.get("flags", []))
                lines.append(
                    f"| {markdown_escape(row.get('result_id'))} | {markdown_escape(row.get('entity_type'))} | {markdown_escape(row.get('name'))} | {row.get('primary_score', '')} | {markdown_escape(flags)} |"
                )
            lines.append("")
        lines.extend([
            "## Source Policy",
            "",
            "- Source GIS files are read-only.",
            "- Bundle JSON and Markdown are generated under `analysis_output/georeview_studio_portfolio_reports`.",
        ])
        return "\n".join(lines).rstrip() + "\n"

    def next_bundle_id(self) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"profile_dashboard_bundle_{safe_token(stamp)}"

    def bundle_path(self, bundle_id: str, suffix: str) -> Path:
        return self.reports_dir / f"{safe_token(bundle_id)}{suffix}"

    def safe_bundle_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.reports_dir.resolve())
            return True
        except ValueError:
            return False
