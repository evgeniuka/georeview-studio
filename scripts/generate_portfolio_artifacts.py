from __future__ import annotations

import csv
import html
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def infer_maps_root(project_dir: Path) -> Path:
    for parent in project_dir.parents:
        if parent.name == "analysis_output":
            return parent.parent
    return project_dir.parent


MAPS_ROOT = infer_maps_root(PROJECT_DIR)
WORKSPACE_ID = "safe_access_kfar_saba_route_aware_v001"
WORKSPACE_DIR = MAPS_ROOT / "analysis_output" / "georeview_studio_workspaces" / WORKSPACE_ID
TABLES_DIR = WORKSPACE_DIR / "tables"
REPORTS_DIR = WORKSPACE_DIR / "reports"
PORTFOLIO_DIR = PROJECT_DIR / "portfolio"
ASSETS_DIR = PORTFOLIO_DIR / "assets"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_float(value: object, default: float = 0.0) -> float:
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


def parse_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def write_csv(path: Path, rows: list[dict], headers: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def project_point(row: dict, bounds: dict, width: int, height: int) -> tuple[float, float]:
    pad = 28
    lon = parse_float(row.get("lon"))
    lat = parse_float(row.get("lat"))
    span_x = bounds["max_lon"] - bounds["min_lon"] or 1
    span_y = bounds["max_lat"] - bounds["min_lat"] or 1
    x = pad + ((lon - bounds["min_lon"]) / span_x) * (width - pad * 2)
    y = height - pad - ((lat - bounds["min_lat"]) / span_y) * (height - pad * 2)
    return x, y


def build_svg_map(risk_rows: list[dict], crossing_rows: list[dict]) -> str:
    width = 980
    height = 620
    points = [
        row for row in risk_rows + crossing_rows
        if row.get("lon") not in ("", None) and row.get("lat") not in ("", None)
    ]
    bounds = {
        "min_lon": min(parse_float(row.get("lon")) for row in points),
        "max_lon": max(parse_float(row.get("lon")) for row in points),
        "min_lat": min(parse_float(row.get("lat")) for row in points),
        "max_lat": max(parse_float(row.get("lat")) for row in points),
    }
    # Crossings = green SQUARES (shape encoding, matches the app marker language).
    crossing_marks = []
    for row in crossing_rows:
        x, y = project_point(row, bounds, width, height)
        side = 5.0
        crossing_marks.append(
            f'<rect x="{x - side / 2:.1f}" y="{y - side / 2:.1f}" width="{side:.1f}" height="{side:.1f}" '
            f'fill="#059669" stroke="#ffffff" stroke-width="1" opacity="0.8" />'
        )
    # Top candidates (score>=70) = red circles; other generators = blue diamonds
    # (shape encoding, matches the app marker language so category is not colour-only).
    generator_circles = []
    for row in risk_rows:
        x, y = project_point(row, bounds, width, height)
        score = parse_int(row.get("route_review_priority_score") or row.get("risk_score") or row.get("base_risk_score"))
        radius = max(3.0, min(8.5, score / 10))
        if score >= 70:
            generator_circles.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="#e11d48" '
                f'stroke="#ffffff" stroke-width="1" opacity="0.95" />'
            )
        else:
            s = radius
            pts = f"{x:.1f},{y - s:.1f} {x + s:.1f},{y:.1f} {x:.1f},{y + s:.1f} {x - s:.1f},{y:.1f}"
            generator_circles.append(
                f'<polygon points="{pts}" fill="#2563eb" stroke="#ffffff" stroke-width="1" opacity="0.5" />'
            )
    font = 'system-ui, -apple-system, "Segoe UI", Roboto, Inter, sans-serif'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Kfar Saba Safe Access static map preview. Red circles mark top review candidates (score 70 and above); blue diamonds mark pedestrian generators; green squares mark mapped crossings. Larger markers indicate higher review-priority scores.">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" fill="none" stroke="#e2e8f0" rx="12"/>
  <g>{''.join(crossing_marks)}</g>
  <g>{''.join(generator_circles)}</g>
  <text x="28" y="42" font-family='{font}' font-size="22" font-weight="650" fill="#0f172a" letter-spacing="-0.3">Kfar Saba Safe Access Route-Aware Review Candidates</text>
  <text x="28" y="66" font-family='{font}' font-size="13" fill="#64748b">Blue diamonds = pedestrian generators; red circles = top review candidates (score 70+).</text>
  <text x="28" y="84" font-family='{font}' font-size="13" fill="#64748b">Green squares = mapped crossings. Larger circles indicate higher review-priority scores.</text>
</svg>
'''


def build_html_report(summary: dict, top_rows: list[dict], svg_file: str) -> str:
    counts = summary["counts"]
    validation = summary["validation"]
    table_rows = []
    for row in top_rows[:10]:
        flags = ", ".join(parse_list(row.get("network_flags") or row.get("risk_flags", "[]"))[:3])
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(row.get('generator_id', ''))}</td>"
            f"<td>{html.escape(row.get('generator_type', ''))}</td>"
            f"<td>{html.escape(row.get('name', ''))}</td>"
            f"<td>{html.escape(str(row.get('straight_nearest_crossing_m') or row.get('nearest_crossing_m', '')))}</td>"
            f"<td>{html.escape(str(row.get('route_nearest_crossing_m', '')))}</td>"
            f"<td>{html.escape(str(row.get('route_vs_straight_ratio', '')))}</td>"
            f"<td>{html.escape(str(row.get('route_review_priority_score') or row.get('risk_score', '')))}</td>"
            f"<td>{html.escape(flags)}</td>"
            "</tr>"
        )
    metrics = [
        ("Pedestrian generators", counts.get("pedestrian_generators")),
        ("Crossings", counts.get("crossings")),
        ("Road segments", counts.get("road_segments")),
        ("Traffic signals", counts.get("traffic_signals")),
        ("Traffic calming", counts.get("traffic_calming_features")),
        ("PBF points read", validation.get("pbf_points")),
    ]
    route = summary.get("route_aware_analysis", {})
    if route:
        metrics.extend([
            ("Route median m", route.get("median_route_nearest_crossing_m")),
            ("Route >250 m", route.get("generators_route_over_250m")),
        ])
    metric_cards = "\n".join(
        f"<div class='metric'><span>{html.escape(str(label))}</span><b>{html.escape(str(value))}</b></div>"
        for label, value in metrics
    )
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GeoReview Studio Portfolio Report</title>
    <link rel="icon" href="data:," />
    <style>
      :root {{
        --bg: #f8fafc;
        --panel: #ffffff;
        --surface: #f1f5f9;
        --ink: #0f172a;
        --muted: #64748b;
        --muted-soft: #94a3b8;
        --line: #e2e8f0;
        --line-strong: #cbd5e1;
        --accent: #4f46e5;
        --accent-strong: #4338ca;
        --accent-soft: #eef2ff;
        --accent-soft-line: #c7d2fe;
        --accent-ink: #3730a3;
        --r-sm: 6px;
        --r-md: 8px;
        --r-lg: 12px;
        --shadow-1: 0 1px 2px rgba(15, 23, 42, 0.04);
        --shadow-2: 0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.04);
        --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, Inter, sans-serif;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font-family: var(--font-sans);
        font-size: 14px;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;
      }}
      .wrap {{ max-width: 1100px; margin: 0 auto; padding: 0 24px; }}
      header {{
        padding: 40px 0 28px;
        border-bottom: 1px solid var(--line);
        background: var(--panel);
      }}
      .eyebrow {{
        display: inline-block;
        margin-bottom: 8px;
        color: var(--accent-ink);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      h1 {{
        margin: 0 0 8px;
        font-size: 30px;
        font-weight: 650;
        letter-spacing: -0.02em;
        line-height: 1.12;
      }}
      h2 {{
        margin: 0 0 16px;
        font-size: 16px;
        font-weight: 650;
        letter-spacing: -0.005em;
      }}
      p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
      .subtitle {{ max-width: 760px; font-size: 15px; }}
      main {{ padding: 28px 0 56px; display: grid; gap: 20px; }}
      .metrics {{
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 12px;
      }}
      .metric {{
        display: grid;
        align-content: start;
        gap: 8px;
        padding: 16px;
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: var(--r-md);
        box-shadow: var(--shadow-1);
      }}
      .metric span {{ color: var(--muted); font-size: 12px; font-weight: 500; }}
      .metric b {{
        color: var(--ink);
        font-size: 30px;
        font-weight: 650;
        letter-spacing: -0.02em;
        line-height: 1;
        font-variant-numeric: tabular-nums;
      }}
      section {{
        padding: 24px;
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: var(--r-lg);
        box-shadow: var(--shadow-2);
      }}
      img {{
        width: 100%;
        max-height: 640px;
        object-fit: contain;
        border: 1px solid var(--line);
        border-radius: var(--r-md);
        background: var(--bg);
      }}
      table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
      th, td {{
        padding: 10px 12px;
        border-bottom: 1px solid var(--line);
        text-align: left;
        vertical-align: top;
        font-variant-numeric: tabular-nums;
      }}
      th {{
        background: var(--bg);
        color: var(--muted);
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        border-bottom: 1px solid var(--line-strong);
      }}
      tbody tr:last-child td {{ border-bottom: 0; }}
      .table-frame {{
        border: 1px solid var(--line);
        border-radius: var(--r-md);
        overflow: hidden;
      }}
      .review-callout {{
        display: flex;
        gap: 12px;
        align-items: flex-start;
        margin-top: 18px;
        padding: 14px 16px;
        border: 1px solid var(--accent-soft-line);
        border-radius: var(--r-md);
        background: var(--accent-soft);
      }}
      .review-callout span.dot {{
        flex: 0 0 auto;
        width: 8px;
        height: 8px;
        margin-top: 6px;
        border-radius: 50%;
        background: var(--accent);
      }}
      .review-callout p {{ color: var(--accent-ink); }}
      .note {{ font-size: 13px; color: var(--muted); }}
    </style>
  </head>
  <body>
    <header>
      <div class="wrap">
        <span class="eyebrow">Local GIS review workbench</span>
        <h1>GeoReview Studio: Safe Access Kfar Saba</h1>
        <p class="subtitle">Infrastructure risk indicator workflow built from OpenStreetMap / Geofabrik data with PBF tag enrichment and OSM road-network proxy distances.</p>
      </div>
    </header>
    <main class="wrap">
      <div class="metrics">{metric_cards}</div>
      <section>
        <h2>Static map preview</h2>
        <img src="{html.escape(svg_file)}" alt="Static map preview" />
      </section>
      <section>
        <h2>Top review candidates</h2>
        <div class="table-frame">
          <table>
            <thead><tr><th>ID</th><th>Type</th><th>Name</th><th>Straight m</th><th>Route m</th><th>Ratio</th><th>Route score</th><th>Flags</th></tr></thead>
            <tbody>{''.join(table_rows)}</tbody>
          </table>
        </div>
        <div class="review-callout">
          <span class="dot" aria-hidden="true"></span>
          <p>{REVIEW_WORDING}</p>
        </div>
      </section>
      <section>
        <h2>Data quality note</h2>
        <p>Missing OSM tags are tracked as data-quality flags, not proof that real-world infrastructure is absent.</p>
      </section>
    </main>
  </body>
</html>
'''


def main() -> None:
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    summary = read_json(REPORTS_DIR / "workspace_summary.json")
    risk_rows = read_csv_rows(TABLES_DIR / "risk_assessment_results.csv")
    network_rows = read_csv_rows(TABLES_DIR / "network_access_results.csv")
    crossing_rows = read_csv_rows(TABLES_DIR / "crossings.csv")
    top_rows = sorted(
        network_rows,
        key=lambda row: (
            -parse_int(row.get("route_review_priority_score")),
            -parse_float(row.get("route_nearest_crossing_m")),
        ),
    )[:20]

    sample_headers = [
        "generator_id",
        "generator_type",
        "name",
        "straight_nearest_crossing_m",
        "route_nearest_crossing_m",
        "route_vs_straight_ratio",
        "base_risk_score",
        "route_review_priority_score",
        "network_flags",
        "data_quality_flags",
        "review_wording",
    ]
    write_csv(PORTFOLIO_DIR / "sample_review_candidates_top20.csv", top_rows, sample_headers)

    svg = build_svg_map(risk_rows, crossing_rows)
    (ASSETS_DIR / "kfar_saba_static_map.svg").write_text(svg, encoding="utf-8")
    html_report = build_html_report(summary, top_rows, "assets/kfar_saba_static_map.svg")
    (PORTFOLIO_DIR / "index.html").write_text(html_report, encoding="utf-8")

    case_study = f"""# GeoReview Studio Portfolio Case Study

## Project

GeoReview Studio is a local-first GIS analytics workbench for infrastructure review prioritization.

## Pilot

Safe Access Kfar Saba, using OpenStreetMap / Geofabrik source data.

## Result

- Pedestrian generators: {summary['counts']['pedestrian_generators']}
- Crossings: {summary['counts']['crossings']}
- Road segments: {summary['counts']['road_segments']}
- Traffic-calming features: {summary['counts']['traffic_calming_features']}
- Raw PBF enrichment: {summary['validation']['raw_pbf_enrichment_used']}
- Route-aware rows: {summary.get('route_aware_analysis', {}).get('rows')}
- Median route distance to mapped crossing: {summary.get('route_aware_analysis', {}).get('median_route_nearest_crossing_m')} m
- Generators over 250 m by route proxy: {summary.get('route_aware_analysis', {}).get('generators_route_over_250m')}

## Correct Interpretation

{REVIEW_WORDING}

Missing OSM tags are data-quality flags, not proof that infrastructure is absent.
"""
    (PORTFOLIO_DIR / "case_study.md").write_text(case_study, encoding="utf-8")

    pitch = """# Portfolio Pitch

GeoReview Studio demonstrates GIS data engineering, road safety domain modeling, and pragmatic software engineering.

The project ingests OSM/Geofabrik data, builds canonical geospatial analysis tables, enriches simplified geometry with raw OSM PBF tags, adds route-aware road-network proxy metrics, and presents review-priority dashboards for field inspection planning.

Strong portfolio signals:

- real local GIS data;
- reproducible data audit;
- canonical data model;
- PBF tag enrichment;
- workspace registry;
- workspace-aware dashboard;
- route-aware network proxy analysis;
- explicit separation between risk indicators and data-quality gaps;
- validated local app and generated report artifacts.
"""
    (PORTFOLIO_DIR / "portfolio_pitch.md").write_text(pitch, encoding="utf-8")

    manifest = {
        "generated": True,
        "workspace_id": WORKSPACE_ID,
        "portfolio_dir": "portfolio",
        "artifacts": [
            "index.html",
            "assets/kfar_saba_static_map.svg",
            "sample_review_candidates_top20.csv",
            "case_study.md",
            "portfolio_pitch.md",
        ],
        "counts": summary["counts"],
    }
    (PORTFOLIO_DIR / "portfolio_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

# Comparison map exports are available through the v050 dashboard and API artifacts.
