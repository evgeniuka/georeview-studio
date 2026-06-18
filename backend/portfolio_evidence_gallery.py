from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PORTFOLIO_EVIDENCE_GALLERY_VERSION = "portfolio_evidence_gallery_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "portfolio_evidence_gallery") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:140] or fallback


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
        return {"error": "portfolio_gallery_probe_failed", "detail": repr(exc)}


class PortfolioEvidenceGalleryBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        dependencies: dict[str, object],
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.dependencies = dependencies
        self.expected_api_endpoints = expected_api_endpoints
        self.galleries_dir = output_root / "georeview_studio_portfolio_evidence_galleries"

    def status(self) -> dict:
        manifest = safe_call(self.manifest_reader, {})
        evidence = self.collect_existing_evidence(limit=12)
        latest_gallery = self.list_galleries(1)
        return {
            "ok": True,
            "portfolio_evidence_gallery_version": PORTFOLIO_EVIDENCE_GALLERY_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "expected_api_endpoints": self.expected_api_endpoints,
            "gallery_count": len(self.list_galleries(500)),
            "latest_gallery_id": latest_gallery[0].get("gallery_id") if latest_gallery else "",
            "artifact_counts": evidence.get("artifact_counts", {}),
            "default_action": "create_portfolio_evidence_gallery",
            "output_dir": str(self.galleries_dir),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_gallery(self, body: dict | None = None) -> dict:
        body = body or {}
        if body.get("create_handoff_page", True):
            self.ensure_handoff_page(body)
        evidence = self.collect_existing_evidence(limit=int(body.get("limit") or 12))
        readiness = self.gallery_readiness(evidence)
        stamp = utc_now()
        gallery_id = f"portfolio_evidence_gallery_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        gallery = {
            "ok": True,
            "gallery_id": gallery_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Local portfolio evidence gallery."),
            "portfolio_evidence_gallery_version": PORTFOLIO_EVIDENCE_GALLERY_VERSION,
            "app_version": self.app_version,
            "gallery_readiness": readiness,
            "artifact_counts": evidence.get("artifact_counts", {}),
            "readiness_summary": evidence.get("readiness_summary", {}),
            "latest_handoff_page_id": (evidence.get("handoff_pages") or [{}])[0].get("page_id", ""),
            "latest_narrative_id": (evidence.get("narratives") or [{}])[0].get("narrative_id", ""),
            "latest_bundle_id": (evidence.get("bundles") or [{}])[0].get("bundle_id", ""),
            "report_count": len(evidence.get("portfolio_reports", [])),
            "evidence": evidence,
            "approved_review_wording": self.review_wording,
            "claim_boundary": "Portfolio gallery indexes evidence artifacts for infrastructure review indicators; it is not a crash prediction artifact.",
            "source_gis_modified": False,
            "mutates_config": False,
        }
        gallery_dir = self.galleries_dir / gallery_id
        json_path = gallery_dir / f"{gallery_id}.json"
        html_path = gallery_dir / "index.html"
        latest_path = self.galleries_dir / "latest_portfolio_evidence_gallery.json"
        gallery["files"] = {"json": str(json_path), "html": str(html_path), "latest": str(latest_path), "directory": str(gallery_dir)}
        write_json(json_path, gallery)
        write_json(latest_path, gallery)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(self.gallery_html(gallery), encoding="utf-8", newline="\n")
        return {"ok": True, "gallery": gallery, "source_gis_modified": False, "mutates_config": False}

    def ensure_handoff_page(self, body: dict) -> dict:
        handoff = self.dependencies.get("portfolio_handoff_page")
        if not handoff:
            return {}
        if body.get("reuse_latest", True):
            rows = safe_call(lambda: handoff.list_pages(1), [])
            if isinstance(rows, list) and rows:
                detail = safe_call(lambda: handoff.detail(str(rows[0].get("page_id") or "")), {})
                if isinstance(detail, dict) and detail.get("handoff_readiness") == "ready_for_portfolio_handoff":
                    return detail
        result = safe_call(
            lambda: handoff.create_page({
                "created_by": str(body.get("created_by") or "portfolio_evidence_gallery"),
                "notes": "Gallery-created portfolio handoff page.",
                "create_narrative": body.get("create_narrative", True),
                "create_checklist": body.get("create_checklist", True),
                "create_bundle": body.get("create_bundle", True),
                "reuse_latest": body.get("reuse_latest", True),
            }),
            {},
        )
        return result.get("page", {}) if isinstance(result, dict) else {}

    def collect_existing_evidence(self, limit: int = 12) -> dict:
        handoff = self.dependencies.get("portfolio_handoff_page")
        narratives = self.dependencies.get("portfolio_narrative_export")
        bundles = self.dependencies.get("portfolio_evidence_bundle")
        checklists = self.dependencies.get("bundle_review_checklist")
        reports = self.dependencies.get("portfolio_reports")
        release = self.dependencies.get("release_readiness")
        dashboard = self.dependencies.get("profile_dashboard")
        architecture = self.dependencies.get("product_architecture")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        validation = read_json(self.project_dir / "validation_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        handoff_pages = safe_call(lambda: handoff.list_pages(limit), []) if handoff else []
        narrative_rows = safe_call(lambda: narratives.list_narratives(limit), []) if narratives else []
        bundle_rows = safe_call(lambda: bundles.list_bundles(limit), []) if bundles else []
        checklist_rows = safe_call(lambda: checklists.list_checklists(limit), []) if checklists else []
        report_rows = safe_call(lambda: reports.list_reports(limit), []) if reports else []
        release_overview = safe_call(release.overview, {}) if release else {}
        dashboard_overview = safe_call(dashboard.overview, {}) if dashboard else {}
        architecture_overview = safe_call(architecture.blueprint, {}) if architecture else {}
        evidence = {
            "manifest": manifest if isinstance(manifest, dict) else {},
            "validation_summary": validation,
            "api_contract_summary": api_contract,
            "readiness_summary": release_overview.get("summary", {}) if isinstance(release_overview, dict) else {},
            "profile_dashboard_summary": {
                "implemented_profile_count": dashboard_overview.get("implemented_profile_count") if isinstance(dashboard_overview, dict) else 0,
                "authored_profile_count": dashboard_overview.get("authored_profile_count") if isinstance(dashboard_overview, dict) else 0,
            },
            "product_architecture_summary": {
                "recommended_variant_id": architecture_overview.get("recommended_variant_id") if isinstance(architecture_overview, dict) else "",
                "best_next_development_step": architecture_overview.get("best_next_development_step") if isinstance(architecture_overview, dict) else "",
            },
            "handoff_pages": handoff_pages if isinstance(handoff_pages, list) else [],
            "narratives": narrative_rows if isinstance(narrative_rows, list) else [],
            "bundles": bundle_rows if isinstance(bundle_rows, list) else [],
            "checklists": checklist_rows if isinstance(checklist_rows, list) else [],
            "portfolio_reports": report_rows if isinstance(report_rows, list) else [],
        }
        evidence["artifact_counts"] = {
            "handoff_pages": len(evidence["handoff_pages"]),
            "narratives": len(evidence["narratives"]),
            "bundles": len(evidence["bundles"]),
            "checklists": len(evidence["checklists"]),
            "portfolio_reports": len(evidence["portfolio_reports"]),
        }
        return evidence

    def gallery_readiness(self, evidence: dict) -> str:
        readiness = evidence.get("readiness_summary", {})
        api_contract = evidence.get("api_contract_summary", {})
        validation = evidence.get("validation_summary", {})
        latest_handoff = (evidence.get("handoff_pages") or [{}])[0]
        if (
            readiness.get("failed_gate_count", 1) == 0
            and readiness.get("warning_gate_count", 1) == 0
            and api_contract.get("passed") is True
            and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints
            and validation.get("passed") is True
            and latest_handoff.get("handoff_readiness") == "ready_for_portfolio_handoff"
            and len(evidence.get("portfolio_reports", [])) > 0
        ):
            return "ready_for_portfolio_gallery"
        return "ready_with_review_warnings"

    def list_galleries(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.galleries_dir.exists():
            return rows
        for path in sorted(self.galleries_dir.glob("portfolio_evidence_gallery_*/portfolio_evidence_gallery_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            rows.append({
                "gallery_id": payload.get("gallery_id"),
                "created_at": payload.get("created_at"),
                "app_version": payload.get("app_version"),
                "gallery_readiness": payload.get("gallery_readiness"),
                "artifact_counts": payload.get("artifact_counts", {}),
                "html_file": payload.get("files", {}).get("html"),
                "json_file": str(path),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, gallery_id: str) -> dict:
        token = safe_token(gallery_id, "missing")
        path = self.galleries_dir / token / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "portfolio_evidence_gallery_not_found", "gallery_id": gallery_id, "source_gis_modified": False}
        return payload

    def output_file(self, gallery_id: str, output_id: str = "portfolio_evidence_gallery") -> dict:
        detail = self.detail(gallery_id)
        if detail.get("error"):
            return detail
        if output_id not in {"portfolio_evidence_gallery", "html"}:
            return {"ok": False, "error": "portfolio_evidence_gallery_output_not_found", "gallery_id": gallery_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists():
            return {"ok": False, "error": "portfolio_evidence_gallery_output_not_found", "gallery_id": gallery_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False}

    def gallery_html(self, gallery: dict) -> str:
        def esc(value: object) -> str:
            return html.escape(str(value if value is not None else ""))
        evidence = gallery.get("evidence", {})
        counts = gallery.get("artifact_counts", {})
        summary = gallery.get("readiness_summary", {})
        metrics = [
            ("Handoff pages", counts.get("handoff_pages")),
            ("Narratives", counts.get("narratives")),
            ("Bundles", counts.get("bundles")),
            ("Reports", counts.get("portfolio_reports")),
            ("API endpoints", evidence.get("api_contract_summary", {}).get("checked_endpoints")),
            ("Release gates", summary.get("gate_count")),
        ]
        metric_html = "\n".join(f"<div class=\"metric\"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>" for label, value in metrics)
        def cards(title: str, rows: list[dict], id_key: str, extra_key: str) -> str:
            items = []
            for row in rows[:8]:
                link = row.get("html_file") or row.get("markdown_file") or row.get("json_file") or row.get("download_url") or ""
                items.append(
                    f"<article class=\"card\"><h3>{esc(row.get(id_key) or row.get('report_id') or row.get('bundle_id') or 'artifact')}</h3>"
                    f"<p>{esc(row.get(extra_key) or row.get('readiness_level') or row.get('report_type') or row.get('created_at') or '')}</p>"
                    f"<small>{esc(link)}</small></article>"
                )
            if not items:
                items.append("<p class=\"empty\">No artifacts indexed yet.</p>")
            return f"<section class=\"band\"><div class=\"inner\"><h2>{esc(title)}</h2><div class=\"grid\">{''.join(items)}</div></div></section>"
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GeoReview Studio Portfolio Evidence Gallery</title>
    <style>
      :root {{ color-scheme: light; --ink:#17202a; --muted:#52616f; --line:#d7dee8; --panel:#ffffff; --soft:#eef5f1; --accent:#176b5b; --warn:#8a5a00; }}
      * {{ box-sizing: border-box; }}
      body {{ margin:0; font-family:Arial, Helvetica, sans-serif; color:var(--ink); background:#f7f9fb; line-height:1.5; }}
      header {{ background:#16362f; color:#fff; padding:44px 28px 36px; }}
      .inner {{ width:min(1120px, calc(100% - 40px)); margin:0 auto; }}
      h1 {{ margin:0 0 12px; font-size:42px; line-height:1.08; letter-spacing:0; }}
      h2 {{ margin:0 0 14px; font-size:24px; letter-spacing:0; }}
      p {{ margin:0 0 14px; }}
      .subtitle {{ max-width:860px; color:#dbe9e4; font-size:18px; }}
      .status-row {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:22px; }}
      .pill {{ border:1px solid rgba(255,255,255,.35); padding:7px 10px; font-size:13px; border-radius:6px; }}
      .metrics,.grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:12px; }}
      .metrics {{ margin:24px auto; }}
      .metric,.card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; min-height:92px; }}
      .metric span,.card small {{ display:block; color:var(--muted); font-size:13px; overflow-wrap:anywhere; }}
      .metric strong {{ display:block; font-size:24px; }}
      .card h3 {{ margin:0 0 8px; font-size:15px; overflow-wrap:anywhere; }}
      .band {{ padding:26px 0; border-top:1px solid var(--line); }}
      .band:nth-of-type(even) {{ background:var(--soft); }}
      .claim {{ background:#fff7e6; border-top:1px solid #eed7a3; border-bottom:1px solid #eed7a3; padding:24px 0; }}
      .claim strong {{ color:var(--warn); }}
      .empty {{ color:var(--muted); }}
      footer {{ padding:28px; color:var(--muted); font-size:13px; }}
      @media (max-width:680px) {{ h1 {{ font-size:32px; }} header {{ padding:34px 20px 28px; }} .inner {{ width:min(100% - 28px, 1120px); }} }}
    </style>
  </head>
  <body>
    <header>
      <div class="inner">
        <h1>GeoReview Studio Evidence Gallery</h1>
        <p class="subtitle">One local reviewer index for handoff pages, narratives, bundles, profile reports and release evidence.</p>
        <div class="status-row">
          <span class="pill">App {esc(gallery.get('app_version'))}</span>
          <span class="pill">{esc(gallery.get('gallery_readiness'))}</span>
          <span class="pill">Kfar Saba pilot</span>
          <span class="pill">Source GIS read-only</span>
        </div>
      </div>
    </header>
    <main>
      <div class="inner metrics">{metric_html}</div>
      {cards("Handoff Pages", evidence.get("handoff_pages", []), "page_id", "handoff_readiness")}
      {cards("Narratives", evidence.get("narratives", []), "narrative_id", "narrative_readiness")}
      {cards("Evidence Bundles", evidence.get("bundles", []), "bundle_id", "readiness_level")}
      {cards("Portfolio Reports", evidence.get("portfolio_reports", []), "report_id", "report_type")}
      <section class="claim">
        <div class="inner">
          <h2>Claim Boundary</h2>
          <p><strong>Approved wording:</strong> {esc(self.review_wording)}</p>
          <p>This gallery indexes evidence for infrastructure review prioritization and data-quality review only. It does not label a location and does not predict crashes.</p>
        </div>
      </section>
    </main>
    <footer>
      <div class="inner">
        Gallery: {esc(gallery.get('gallery_id'))}<br />
        Source GIS modified: false. Config mutated: false.
      </div>
    </footer>
  </body>
</html>
"""
