from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PORTFOLIO_HANDOFF_PAGE_VERSION = "portfolio_handoff_page_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "portfolio_handoff") -> str:
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
        return {"error": "portfolio_handoff_probe_failed", "detail": repr(exc)}


class PortfolioHandoffPageBuilder:
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
        self.pages_dir = output_root / "georeview_studio_portfolio_handoff_pages"
        self.narratives_dir = output_root / "georeview_studio_portfolio_narratives"

    def status(self) -> dict:
        manifest = safe_call(self.manifest_reader, {})
        latest_narrative = self.latest_narrative()
        latest_page = self.list_pages(1)
        return {
            "ok": True,
            "portfolio_handoff_page_version": PORTFOLIO_HANDOFF_PAGE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "expected_api_endpoints": self.expected_api_endpoints,
            "page_count": len(self.list_pages(500)),
            "latest_narrative_id": latest_narrative.get("narrative_id") if latest_narrative else "",
            "latest_narrative_readiness": latest_narrative.get("narrative_readiness") if latest_narrative else "",
            "latest_page_id": latest_page[0].get("page_id") if latest_page else "",
            "default_action": "create_portfolio_handoff_page",
            "page_sections": ["hero", "metrics", "narrative", "talk_track", "claim_boundary", "handoff"],
            "output_dir": str(self.pages_dir),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_page(self, body: dict | None = None) -> dict:
        body = body or {}
        narrative = self.resolve_narrative(body)
        if not narrative:
            return {"ok": False, "error": "portfolio_narrative_not_found", "source_gis_modified": False, "mutates_config": False}
        readiness = self.page_readiness(narrative)
        stamp = utc_now()
        page_id = f"portfolio_handoff_page_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        page = {
            "ok": True,
            "page_id": page_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Local HTML portfolio handoff page."),
            "portfolio_handoff_page_version": PORTFOLIO_HANDOFF_PAGE_VERSION,
            "app_version": self.app_version,
            "narrative_id": narrative.get("narrative_id"),
            "narrative_readiness": narrative.get("narrative_readiness"),
            "handoff_readiness": readiness,
            "evidence_summary": narrative.get("evidence_summary", {}),
            "section_count": len(narrative.get("sections", [])),
            "talk_track_count": len(narrative.get("talk_track", [])),
            "approved_review_wording": self.review_wording,
            "claim_boundary": "Local handoff page presents infrastructure indicators, evidence and engineering work; it is not a crash prediction artifact.",
            "source_gis_modified": False,
            "mutates_config": False,
        }
        page_dir = self.pages_dir / page_id
        json_path = page_dir / f"{page_id}.json"
        html_path = page_dir / "index.html"
        latest_path = self.pages_dir / "latest_portfolio_handoff_page.json"
        page["files"] = {"json": str(json_path), "html": str(html_path), "latest": str(latest_path), "directory": str(page_dir)}
        write_json(json_path, page)
        write_json(latest_path, page)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(self.page_html(page, narrative), encoding="utf-8", newline="\n")
        return {"ok": True, "page": page, "source_gis_modified": False, "mutates_config": False}

    def resolve_narrative(self, body: dict) -> dict:
        narrative_id = str(body.get("narrative_id") or "")
        exporter = self.dependencies.get("portfolio_narrative_export")
        if narrative_id and exporter:
            detail = safe_call(lambda: exporter.detail(narrative_id), {})
            return detail if isinstance(detail, dict) and not detail.get("error") else {}
        if body.get("create_narrative", True) and exporter:
            result = safe_call(
                lambda: exporter.create_narrative({
                    "created_by": str(body.get("created_by") or "portfolio_handoff_page"),
                    "notes": "Handoff-created portfolio narrative.",
                    "create_checklist": body.get("create_checklist", True),
                    "create_bundle": body.get("create_bundle", True),
                    "reuse_latest": body.get("reuse_latest", True),
                }),
                {},
            )
            if isinstance(result, dict) and result.get("ok"):
                narrative = result.get("narrative", {})
                return narrative if isinstance(narrative, dict) else {}
        return self.latest_narrative()

    def latest_narrative(self) -> dict:
        latest = read_json(self.narratives_dir / "latest_portfolio_narrative.json")
        if latest:
            return latest
        exporter = self.dependencies.get("portfolio_narrative_export")
        if exporter:
            rows = safe_call(lambda: exporter.list_narratives(1), [])
            if isinstance(rows, list) and rows:
                detail = safe_call(lambda: exporter.detail(str(rows[0].get("narrative_id") or "")), {})
                return detail if isinstance(detail, dict) else {}
        return {}

    def page_readiness(self, narrative: dict) -> str:
        summary = narrative.get("evidence_summary", {})
        if (
            narrative.get("narrative_readiness") == "ready_for_reviewer"
            and summary.get("validation_passed") is True
            and summary.get("api_contract_passed") is True
            and int(summary.get("checked_endpoints") or 0) >= self.expected_api_endpoints
        ):
            return "ready_for_portfolio_handoff"
        return "ready_with_review_warnings"

    def list_pages(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.pages_dir.exists():
            return rows
        for path in sorted(self.pages_dir.glob("portfolio_handoff_page_*/portfolio_handoff_page_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            rows.append({
                "page_id": payload.get("page_id"),
                "created_at": payload.get("created_at"),
                "app_version": payload.get("app_version"),
                "narrative_id": payload.get("narrative_id"),
                "handoff_readiness": payload.get("handoff_readiness"),
                "html_file": payload.get("files", {}).get("html"),
                "json_file": str(path),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, page_id: str) -> dict:
        token = safe_token(page_id, "missing")
        path = self.pages_dir / token / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "portfolio_handoff_page_not_found", "page_id": page_id, "source_gis_modified": False}
        return payload

    def output_file(self, page_id: str, output_id: str = "portfolio_handoff_page") -> dict:
        detail = self.detail(page_id)
        if detail.get("error"):
            return detail
        if output_id not in {"portfolio_handoff_page", "html"}:
            return {"ok": False, "error": "portfolio_handoff_page_output_not_found", "page_id": page_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists():
            return {"ok": False, "error": "portfolio_handoff_page_output_not_found", "page_id": page_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False}

    def page_html(self, page: dict, narrative: dict) -> str:
        summary = narrative.get("evidence_summary", {})
        sections = narrative.get("sections", [])
        talk_track = narrative.get("talk_track", [])
        def esc(value: object) -> str:
            return html.escape(str(value if value is not None else ""))
        metrics = [
            ("Validation", summary.get("validation_passed")),
            ("API endpoints", summary.get("checked_endpoints")),
            ("Generators", summary.get("pedestrian_generators")),
            ("Crossings", summary.get("crossings")),
            ("Route rows", summary.get("route_aware_rows")),
            ("Profiles", summary.get("implemented_profiles")),
        ]
        metric_html = "\n".join(f"<div class=\"metric\"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>" for label, value in metrics)
        section_html = "\n".join(
            f"<section class=\"band\"><div class=\"inner\"><h2>{esc(section.get('title'))}</h2><p>{esc(section.get('body'))}</p></div></section>"
            for section in sections
        )
        talk_html = "\n".join(
            f"<li><strong>{esc(item.get('title'))}</strong><span>{esc(item.get('talking_point'))}</span></li>"
            for item in talk_track
        )
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GeoReview Studio Portfolio Handoff</title>
    <style>
      :root {{ color-scheme: light; --ink:#17202a; --muted:#52616f; --line:#d7dee8; --panel:#ffffff; --soft:#eef5f1; --accent:#176b5b; --warn:#8a5a00; }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: #f7f9fb; line-height: 1.5; }}
      header {{ background: #16362f; color: #fff; padding: 44px 28px 36px; }}
      .inner {{ width: min(1080px, calc(100% - 40px)); margin: 0 auto; }}
      h1 {{ margin: 0 0 12px; font-size: 42px; line-height: 1.08; letter-spacing: 0; }}
      h2 {{ margin: 0 0 12px; font-size: 24px; letter-spacing: 0; }}
      p {{ margin: 0 0 14px; }}
      .subtitle {{ max-width: 820px; color: #dbe9e4; font-size: 18px; }}
      .status-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
      .pill {{ border: 1px solid rgba(255,255,255,.35); padding: 7px 10px; font-size: 13px; border-radius: 6px; }}
      .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 24px auto; }}
      .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-height: 86px; }}
      .metric span {{ display: block; color: var(--muted); font-size: 13px; margin-bottom: 8px; }}
      .metric strong {{ display: block; font-size: 24px; }}
      .band {{ padding: 26px 0; border-top: 1px solid var(--line); }}
      .band:nth-of-type(even) {{ background: var(--soft); }}
      .claim {{ background: #fff7e6; border-top: 1px solid #eed7a3; border-bottom: 1px solid #eed7a3; padding: 24px 0; }}
      .claim strong {{ color: var(--warn); }}
      ol {{ padding-left: 22px; }}
      li {{ margin: 0 0 12px; }}
      li span {{ display: block; color: var(--muted); }}
      footer {{ padding: 28px; color: var(--muted); font-size: 13px; }}
      @media (max-width: 680px) {{ h1 {{ font-size: 32px; }} header {{ padding: 34px 20px 28px; }} .inner {{ width: min(100% - 28px, 1080px); }} }}
    </style>
  </head>
  <body>
    <header>
      <div class="inner">
        <h1>GeoReview Studio</h1>
        <p class="subtitle">A local-first GIS analytics portfolio project for infrastructure review indicators, OSM data-quality evidence, and reproducible pedestrian access analysis.</p>
        <div class="status-row">
          <span class="pill">App {esc(page.get('app_version'))}</span>
          <span class="pill">{esc(page.get('handoff_readiness'))}</span>
          <span class="pill">Kfar Saba pilot</span>
          <span class="pill">Source GIS read-only</span>
        </div>
      </div>
    </header>
    <main>
      <div class="inner metrics">{metric_html}</div>
      {section_html}
      <section class="claim">
        <div class="inner">
          <h2>Claim Boundary</h2>
          <p><strong>Approved wording:</strong> {esc(self.review_wording)}</p>
          <p>This page supports infrastructure review prioritization and data-quality evidence only. It does not label a location and does not predict crashes.</p>
        </div>
      </section>
      <section class="band">
        <div class="inner">
          <h2>Reviewer Talk Track</h2>
          <ol>{talk_html}</ol>
        </div>
      </section>
    </main>
    <footer>
      <div class="inner">
        Page: {esc(page.get('page_id'))}<br />
        Narrative: {esc(page.get('narrative_id'))}<br />
        Source GIS modified: false. Config mutated: false.
      </div>
    </footer>
  </body>
</html>
"""
