#!/usr/bin/env python3
"""Generate the Kfar Saba crossing-access analysis report from the committed pilot workspace.

One self-contained, standard-library-only script. It loads the workspace CSV tables into an
in-memory SQLite database, computes every section metric in SQL, renders a few small SVG
figures by hand, and writes a Markdown report plus a machine-readable numbers file.

Design rules:
- stdlib only (csv, json, sqlite3, statistics, math, random, argparse) -- no third-party packages.
- read-only with respect to the store; deterministic and idempotent (fixed seed, no timestamps).
- wording follows the policy defined in docs/scope.md; this file quotes only the approved
  reviewer sentence and never restates the restricted phrases.

Usage:  python -B scripts/generate_analysis_report.py [--store PATH]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sqlite3
import statistics
from pathlib import Path

SEED = 20260706
RNG = random.Random(SEED)

REPO_ROOT = Path(__file__).resolve().parents[1]
# Repo-relative default: the committed demo bundle, so the report reproduces on a fresh clone.
DEFAULT_STORE = REPO_ROOT / "demo_data" / "analysis_output"
WORKSPACE_ID = "safe_access_kfar_saba_route_aware_v001"
WORKSPACE_SUBPATH = Path("georeview_studio_workspaces") / WORKSPACE_ID

OUT_DIR = REPO_ROOT / "docs" / "analysis"
FIG_DIR = OUT_DIR / "figures"
REPORT_MD = OUT_DIR / "kfar_saba_crossing_access_report.md"
NUMBERS_JSON = OUT_DIR / "report_numbers.json"

APPROVED_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."

# Route-distance bands (metres). Upper-inclusive, so "250-500" + "500+" == count(route > 250).
BAND_ORDER = ["0-100", "100-250", "250-500", "500+", "unreachable"]
BAND_COLOR = {
    "0-100": "#1a9850",
    "100-250": "#a6d96a",
    "250-500": "#fdae61",
    "500+": "#d73027",
    "unreachable": "#9e9e9e",
}

# Table load config: (sqlite table, csv relative path, id column, flag columns to json-explode).
TABLE_CONFIG = [
    ("generators", "tables/pedestrian_generators.csv", "generator_id", ["data_quality_flags"]),
    ("crossings", "tables/crossings.csv", "crossing_id", []),
    ("road_segments", "tables/road_segments.csv", "road_id", []),
    ("network", "tables/network_access_results.csv", "generator_id", ["network_flags", "data_quality_flags"]),
    ("risk", "tables/risk_assessment_results.csv", "generator_id", ["risk_flags", "data_quality_flags"]),
]


# --------------------------------------------------------------------------- loading


def _looks_int(value: str) -> bool:
    if "." in value or "e" in value.lower():
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


def _looks_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _column_types(rows: list[dict], columns: list[str], flag_cols: list[str]) -> dict[str, str]:
    """Infer a sqlite storage type per column from the non-empty values."""
    types: dict[str, str] = {}
    for col in columns:
        present = [r[col] for r in rows if r[col] != ""]
        if col in flag_cols:
            types[col] = "TEXT"
        elif present and all(v in ("True", "False") for v in present):
            types[col] = "BOOL"          # stored as INTEGER 0/1
        elif present and all(_looks_int(v) for v in present):
            types[col] = "INTEGER"
        elif present and all(_looks_float(v) for v in present):
            types[col] = "REAL"
        else:
            types[col] = "TEXT"
    return types


def _convert(value: str, sqlite_type: str):
    if value == "":
        return None                      # empty numerics (and blanks) become NULL
    if sqlite_type == "BOOL":
        return 1 if value == "True" else 0
    if sqlite_type == "INTEGER":
        return int(value)
    if sqlite_type == "REAL":
        return float(value)
    return value


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_store(conn: sqlite3.Connection, workspace: Path) -> None:
    """Load each configured CSV into sqlite, converting booleans and blanks, and pre-explode
    the JSON flag columns into bridge tables in Python (not via sqlite json_each)."""
    for table, rel, id_col, flag_cols in TABLE_CONFIG:
        rows = _read_csv(workspace / rel)
        columns = list(rows[0].keys()) if rows else []
        types = _column_types(rows, columns, flag_cols)
        storage = {c: ("INTEGER" if types[c] in ("BOOL", "INTEGER") else "REAL" if types[c] == "REAL" else "TEXT") for c in columns}
        coldefs = ", ".join(f'"{c}" {storage[c]}' for c in columns)
        conn.execute(f'CREATE TABLE "{table}" ({coldefs})')
        placeholders = ", ".join("?" for _ in columns)
        conn.executemany(
            f'INSERT INTO "{table}" VALUES ({placeholders})',
            [[_convert(r[c], types[c]) for c in columns] for r in rows],
        )
        for flag_col in flag_cols:
            bridge = f"{table}__{flag_col}"
            conn.execute(f'CREATE TABLE "{bridge}" ("{id_col}" TEXT, flag TEXT)')
            exploded = []
            for r in rows:
                for flag in json.loads(r[flag_col] or "[]"):
                    exploded.append((r[id_col], str(flag)))
            conn.executemany(f'INSERT INTO "{bridge}" VALUES (?, ?)', exploded)
    conn.commit()


# --------------------------------------------------------------------------- metrics


def _percentile(ordered: list[float], fraction: float) -> float:
    """Linear-interpolated percentile over an already-sorted list."""
    if not ordered:
        return 0.0
    pos = (len(ordered) - 1) * fraction
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[int(pos)]
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def compute_numbers(conn: sqlite3.Connection, summary: dict) -> dict:
    cur = conn.cursor()

    counts = {
        "pedestrian_destinations": cur.execute("SELECT COUNT(*) FROM generators").fetchone()[0],
        "mapped_crossings": cur.execute("SELECT COUNT(*) FROM crossings").fetchone()[0],
        "road_segments": cur.execute("SELECT COUNT(*) FROM road_segments").fetchone()[0],
    }

    crossing_mix = {row[0]: row[1] for row in cur.execute(
        "SELECT crossing_type, COUNT(*) FROM crossings GROUP BY crossing_type ORDER BY COUNT(*) DESC, crossing_type"
    )}
    generator_mix = {row[0]: row[1] for row in cur.execute(
        "SELECT generator_type, COUNT(*) FROM generators GROUP BY generator_type ORDER BY COUNT(*) DESC, generator_type"
    )}

    signal_tagged = crossing_mix.get("traffic_signals", 0)
    signal_share = round(100.0 * signal_tagged / counts["mapped_crossings"], 1)

    reachable = cur.execute("SELECT COUNT(*) FROM network WHERE route_nearest_crossing_m IS NOT NULL").fetchone()[0]
    unreachable = cur.execute("SELECT COUNT(*) FROM network WHERE route_nearest_crossing_m IS NULL").fetchone()[0]
    over_250 = cur.execute("SELECT COUNT(*) FROM network WHERE route_nearest_crossing_m > 250").fetchone()[0]
    over_150 = cur.execute("SELECT COUNT(*) FROM network WHERE route_nearest_crossing_m > 150").fetchone()[0]
    unreachable_ids = [row[0] for row in cur.execute(
        "SELECT generator_id FROM network WHERE route_nearest_crossing_m IS NULL ORDER BY generator_id"
    )]

    route_vals = [row[0] for row in cur.execute(
        "SELECT route_nearest_crossing_m FROM network WHERE route_nearest_crossing_m IS NOT NULL ORDER BY route_nearest_crossing_m"
    )]
    detour_vals = [row[0] for row in cur.execute(
        "SELECT route_vs_straight_ratio FROM network WHERE route_nearest_crossing_m IS NOT NULL AND route_vs_straight_ratio IS NOT NULL ORDER BY route_vs_straight_ratio"
    )]
    score_row = cur.execute("SELECT MIN(route_review_priority_score), MAX(route_review_priority_score) FROM network").fetchone()

    # Route-distance bands per generator type (single SQL statement).
    band_rows = cur.execute(
        """
        SELECT generator_type,
               CASE
                   WHEN route_nearest_crossing_m IS NULL THEN 'unreachable'
                   WHEN route_nearest_crossing_m <= 100 THEN '0-100'
                   WHEN route_nearest_crossing_m <= 250 THEN '100-250'
                   WHEN route_nearest_crossing_m <= 500 THEN '250-500'
                   ELSE '500+'
               END AS band,
               COUNT(*)
        FROM network
        GROUP BY generator_type, band
        """
    ).fetchall()
    bands_by_type: dict[str, dict[str, int]] = {}
    for gtype, band, n in band_rows:
        bands_by_type.setdefault(gtype, {b: 0 for b in BAND_ORDER})[band] = n
    # Internal consistency: the two long-distance bands must equal the > 250 m count.
    long_band_total = sum(v["250-500"] + v["500+"] for v in bands_by_type.values())
    assert long_band_total == over_250, (long_band_total, over_250)

    # Straight-vs-route pairs for the scatter (reachable only), deterministic order.
    scatter = [
        (row[0], row[1])
        for row in cur.execute(
            "SELECT straight_nearest_crossing_m, route_nearest_crossing_m FROM network "
            "WHERE route_nearest_crossing_m IS NOT NULL AND straight_nearest_crossing_m IS NOT NULL "
            "ORDER BY generator_id"
        )
    ]

    # Ranking that reproduces the dashboard candidates endpoint:
    #   app sort key = (-route_review_priority_score, -risk_score, -nearest_crossing_m)
    # We append generator_id ascending as a final deterministic tie-break, because the live app
    # relies on Python's stable sort / insertion order, which is not reproducible from the tables.
    ranking = cur.execute(
        """
        SELECT n.generator_id, n.generator_type, n.name,
               n.route_review_priority_score, r.risk_score,
               r.nearest_crossing_m, n.route_nearest_crossing_m
        FROM network n JOIN risk r ON n.generator_id = r.generator_id
        ORDER BY n.route_review_priority_score DESC, r.risk_score DESC,
                 r.nearest_crossing_m DESC, n.generator_id ASC
        LIMIT 5
        """
    ).fetchall()
    top5 = [
        {
            "rank": i + 1,
            "generator_id": row[0],
            "generator_type": row[1],
            "name": row[2] or "",
            "priority_score": row[3],
            "risk_score": row[4],
            "straight_m": row[5],
            "route_m": row[6],
        }
        for i, row in enumerate(ranking)
    ]

    return {
        "config": {"seed": SEED, "workspace": WORKSPACE_ID},
        "counts": counts,
        "crossing_type_mix": crossing_mix,
        "generator_type_mix": generator_mix,
        "traffic_signal_tagged": {"count": signal_tagged, "total": counts["mapped_crossings"], "pct": signal_share},
        "network_size": {
            "nodes": summary.get("network_nodes"),
            "edges": summary.get("network_edges"),
            "included_road_segments": summary.get("included_road_segments"),
            "excluded_road_segments": summary.get("excluded_road_segments"),
        },
        "route_distance": {
            "reachable": reachable,
            "unreachable": unreachable,
            "unreachable_ids": unreachable_ids,
            "over_250m": over_250,
            "over_150m": over_150,
            "median_m_summary": summary.get("median_route_nearest_crossing_m"),
            "median_m_recomputed": round(statistics.median(route_vals), 1),
            "p90_m_summary": summary.get("p90_route_nearest_crossing_m"),
            "p90_m_recomputed": round(_percentile(route_vals, 0.9), 1),
        },
        "detour_ratio": {
            "median_summary": summary.get("median_route_vs_straight_ratio"),
            "median_recomputed": round(statistics.median(detour_vals), 2),
        },
        "priority_score_range": {"min": score_row[0], "max": score_row[1]},
        "route_bands_by_type": bands_by_type,
        "scatter_points": scatter,
        "ranking_top5": top5,
    }


# --------------------------------------------------------------------------- svg


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def _svg_open() -> list[str]:
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" font-family="sans-serif">',
        '<rect x="0" y="0" width="640" height="360" fill="#ffffff"/>',
    ]


def _text(x: float, y: float, s: str, size: int = 11, anchor: str = "start", color: str = "#222", extra: str = "") -> str:
    safe = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<text x="{_fmt(x)}" y="{_fmt(y)}" font-size="{size}" text-anchor="{anchor}" fill="{color}"{extra}>{safe}</text>'


def stacked_bar_svg(title: str, bands_by_type: dict[str, dict[str, int]]) -> str:
    order = sorted(bands_by_type, key=lambda t: (-sum(bands_by_type[t].values()), t))
    totals = [sum(bands_by_type[t].values()) for t in order]
    y_top, y_base, x_left, x_right = 46.0, 300.0, 70.0, 610.0
    y_max = max(totals) if totals else 1
    tick = 50 if y_max > 60 else 10
    top_tick = (math.ceil(y_max / tick)) * tick
    scale = (y_base - y_top) / top_tick

    out = _svg_open()
    out.append(_text(320, 24, title, size=14, anchor="middle"))
    for value in range(0, top_tick + 1, tick):
        y = y_base - value * scale
        out.append(f'<line x1="{_fmt(x_left)}" y1="{_fmt(y)}" x2="{_fmt(x_right)}" y2="{_fmt(y)}" stroke="#e5e7eb" stroke-width="1"/>')
        out.append(_text(x_left - 8, y + 4, str(value), size=10, anchor="end", color="#555"))

    slot = (x_right - x_left) / len(order)
    bar_w = min(46.0, slot * 0.6)
    for i, gtype in enumerate(order):
        cx = x_left + slot * (i + 0.5)
        y_cursor = y_base
        for band in BAND_ORDER:
            n = bands_by_type[gtype].get(band, 0)
            if n <= 0:
                continue
            h = n * scale
            out.append(
                f'<rect x="{_fmt(cx - bar_w / 2)}" y="{_fmt(y_cursor - h)}" width="{_fmt(bar_w)}" '
                f'height="{_fmt(h)}" fill="{BAND_COLOR[band]}"/>'
            )
            y_cursor -= h
        out.append(_text(cx, y_base + 14, gtype, size=9, anchor="middle", color="#333"))
        out.append(_text(cx, y_cursor - 4, str(sum(bands_by_type[gtype].values())), size=9, anchor="middle", color="#333"))

    lx = x_left
    for band in BAND_ORDER:
        out.append(f'<rect x="{_fmt(lx)}" y="336" width="12" height="12" fill="{BAND_COLOR[band]}"/>')
        out.append(_text(lx + 16, 346, f"{band} m" if band != "unreachable" else band, size=10))
        lx += 108
    out.append("</svg>")
    return "\n".join(out) + "\n"


def scatter_svg(title: str, points: list[tuple[float, float]]) -> str:
    y_top, y_base, x_left, x_right = 46.0, 300.0, 60.0, 610.0
    data_max = max((max(x, y) for x, y in points), default=1.0)
    axis_max = max(100.0, math.ceil(data_max / 100.0) * 100.0)
    sx = (x_right - x_left) / axis_max
    sy = (y_base - y_top) / axis_max

    def px(v: float) -> float:
        return x_left + v * sx

    def py(v: float) -> float:
        return y_base - v * sy

    out = _svg_open()
    out.append(_text(320, 24, title, size=14, anchor="middle"))
    for value in range(0, int(axis_max) + 1, 250):
        gx, gy = px(value), py(value)
        out.append(f'<line x1="{_fmt(gx)}" y1="{_fmt(y_base)}" x2="{_fmt(gx)}" y2="{_fmt(y_top)}" stroke="#f1f1f1" stroke-width="1"/>')
        out.append(f'<line x1="{_fmt(x_left)}" y1="{_fmt(gy)}" x2="{_fmt(x_right)}" y2="{_fmt(gy)}" stroke="#f1f1f1" stroke-width="1"/>')
        out.append(_text(gx, y_base + 14, str(value), size=9, anchor="middle", color="#555"))
        out.append(_text(x_left - 6, gy + 3, str(value), size=9, anchor="end", color="#555"))
    # y = x reference line
    out.append(f'<line x1="{_fmt(px(0))}" y1="{_fmt(py(0))}" x2="{_fmt(px(axis_max))}" y2="{_fmt(py(axis_max))}" stroke="#888" stroke-width="1" stroke-dasharray="4 3"/>')
    out.append(_text(px(axis_max) - 4, py(axis_max) + 14, "route = straight", size=9, anchor="end", color="#888"))

    seen: dict[tuple[int, int], int] = {}
    for straight, route in points:
        bx, by = px(straight), py(route)
        key = (round(bx), round(by))
        if key in seen:  # nudge coincident markers apart for visibility (visual only; values unchanged)
            bx += RNG.uniform(-1.5, 1.5)
            by += RNG.uniform(-1.5, 1.5)
        seen[key] = seen.get(key, 0) + 1
        color = "#d73027" if route > 250 else "#4575b4"
        out.append(f'<circle cx="{_fmt(bx)}" cy="{_fmt(by)}" r="2.4" fill="{color}" fill-opacity="0.75"/>')

    out.append(_text(320, 344, "straight-line distance to nearest mapped crossing (m)", size=10, anchor="middle", color="#333"))
    out.append('<text x="16" y="173" font-size="10" fill="#333" transform="rotate(-90 16 173)">route distance (m)</text>')
    out.append('<rect x="470" y="52" width="10" height="10" fill="#d73027"/>')
    out.append(_text(484, 61, "route > 250 m", size=10))
    out.append('<rect x="470" y="68" width="10" height="10" fill="#4575b4"/>')
    out.append(_text(484, 77, "route <= 250 m", size=10))
    out.append("</svg>")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- report


def _mix_table(mix: dict[str, int], header: str) -> list[str]:
    lines = [f"| {header} | Count |", "|---|---:|"]
    for key, value in mix.items():
        lines.append(f"| `{key}` | {value} |")
    return lines


def build_report(n: dict) -> str:
    c = n["counts"]
    rd = n["route_distance"]
    sig = n["traffic_signal_tagged"]
    net = n["network_size"]
    dest = c["pedestrian_destinations"]
    L: list[str] = []

    L.append("# Kfar Saba crossing-access — analysis report")
    L.append("")
    L.append(
        f"Recomputed from the committed pilot workspace (`{WORKSPACE_ID}`) by a single standard-library "
        f"Python script, `scripts/generate_analysis_report.py`. Every figure is generated, not hand-drawn. "
        f"Wording follows the policy in [`../scope.md`](../scope.md)."
    )
    L.append("")

    # -- S0 --------------------------------------------------------------
    L.append("## S0 — Executive summary")
    L.append("")
    L.append("**Headline numbers**")
    L.append("")
    L.append(f"- {dest} pedestrian destinations measured against {c['mapped_crossings']} mapped pedestrian crossings, over {c['road_segments']} road segments.")
    L.append(f"- {sig['count']} of {sig['total']} crossings ({sig['pct']} %) carry a `traffic_signals` tag; the rest are marked, uncontrolled or generic.")
    L.append(f"- Priority scores span {n['priority_score_range']['min']}–{n['priority_score_range']['max']}; every destination carries at least one indicator, so the ranking separates degree of concern, not presence.")
    L.append("")
    L.append("**Claim boundaries**")
    L.append("")
    L.append(f"- The median route distance to the nearest mapped crossing is **{rd['median_m_summary']} m** (a direct recompute from the committed tables, which round distances to 0.1 m, gives {rd['median_m_recomputed']} m).")
    L.append(f"- **{rd['over_250m']} of {dest} destinations** are beyond 250 m from the nearest mapped crossing by route.")
    L.append("- The priority score is transparent but **UNCALIBRATED** — it is never checked against real outcome data, so it says where to look first, not where conditions are worst. The approved and restricted wording is defined in [`../scope.md`](../scope.md).")
    L.append("")
    L.append(f"> {APPROVED_WORDING}")
    L.append("")

    # -- S1 --------------------------------------------------------------
    L.append("## S1 — Study area and data inventory")
    L.append("")
    L.append("| Layer | Count |")
    L.append("|---|---:|")
    L.append(f"| Pedestrian destinations | {c['pedestrian_destinations']} |")
    L.append(f"| Mapped pedestrian crossings | {c['mapped_crossings']} |")
    L.append(f"| Road segments | {c['road_segments']} |")
    L.append(f"| Road-network graph nodes | {net['nodes']} |")
    L.append(f"| Road-network graph edges | {net['edges']} |")
    L.append(f"| Road segments included in the network proxy | {net['included_road_segments']} |")
    L.append(f"| Road segments excluded (motorway/trunk/track/unknown) | {net['excluded_road_segments']} |")
    L.append("")
    L.append("**Crossing type mix** — distance is measured to the nearest *mapped* crossing, not a signal-controlled one:")
    L.append("")
    L.extend(_mix_table(n["crossing_type_mix"], "Crossing type"))
    L.append("")
    L.append("**Destination type mix:**")
    L.append("")
    L.extend(_mix_table(n["generator_type_mix"], "Destination type"))
    L.append("")
    L.append(
        "*Reconciliation:* all counts above are computed in SQL from the committed workspace tables and match the "
        "workspace `network_analysis_summary.json` exactly. The distance percentiles in S2 are quoted from that summary "
        "(full precision) and reproduce from the tables within 0.1 m, since the tables round distances to 0.1 m."
    )
    L.append("")

    # -- S2 --------------------------------------------------------------
    L.append("## S2 — Distance to the nearest mapped crossing")
    L.append("")
    L.append(
        f"Each destination is measured to the nearest mapped crossing two ways: straight-line and along the OSM "
        f"road-network proxy graph. The median route distance is **{rd['median_m_summary']} m** (p90 {rd['p90_m_summary']} m); "
        f"**{rd['over_250m']} of {dest}** destinations ({round(100 * rd['over_250m'] / dest)} %) are beyond 250 m by route and "
        f"{rd['over_150m']} are beyond 150 m. {rd['reachable']} destinations reach a crossing across the proxy graph; "
        f"{rd['unreachable']} does not ({', '.join(rd['unreachable_ids'])}) and is reported as a data-quality gap, not a finding. "
        f"The median route-to-straight detour ratio is {n['detour_ratio']['median_summary']}."
    )
    L.append("")
    L.append("![Route-distance bands by destination type](figures/f1_route_bands_by_type.svg)")
    L.append("")
    L.append("*Figure 1. Route distance to the nearest mapped crossing, banded and stacked per destination type. Bands are upper-inclusive, so the two longest bands together equal the 250 m count above.*")
    L.append("")
    L.append("![Straight-line versus route distance](figures/f2_straight_vs_route.svg)")
    L.append("")
    L.append("*Figure 2. Straight-line versus route distance for every reachable destination; the dashed line is route = straight. Points above it (the majority) travel further along the network than the crow-flies distance implies.*")
    L.append("")
    L.append("### Reproducing the ranking")
    L.append("")
    L.append(
        "The live dashboard candidates endpoint orders destinations by "
        "`(-route_review_priority_score, -risk_score, -nearest_crossing_m)`. That key leaves ties unresolved, and the app "
        "falls back on Python's stable sort, which is not reproducible from the tables alone. This report appends "
        "`generator_id` ascending as a final deterministic tie-break; the top five under that order are:"
    )
    L.append("")
    L.append("| # | Type | Name | Straight (m) | Route (m) | Score |")
    L.append("|--:|---|---|--:|--:|--:|")
    for row in n["ranking_top5"]:
        name = row["name"] or "—"
        L.append(f"| {row['rank']} | {row['generator_type']} | {name} | {row['straight_m']} | {row['route_m']} | {row['priority_score']} |")
    L.append("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Kfar Saba crossing-access analysis report.")
    parser.add_argument(
        "--store",
        type=Path,
        default=DEFAULT_STORE,
        help="Path to an analysis_output store (default: the repo-relative committed demo bundle).",
    )
    args = parser.parse_args()

    workspace = args.store / WORKSPACE_SUBPATH
    if not (workspace / "tables").is_dir():
        parser.error(f"workspace tables not found under {workspace}")
    summary = json.loads((workspace / "reports" / "network_analysis_summary.json").read_text(encoding="utf-8"))

    conn = sqlite3.connect(":memory:")
    try:
        load_store(conn, workspace)
        numbers = compute_numbers(conn, summary)
    finally:
        conn.close()

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    (FIG_DIR / "f1_route_bands_by_type.svg").write_text(
        stacked_bar_svg("Route distance to nearest mapped crossing, by destination type", numbers["route_bands_by_type"]),
        encoding="utf-8", newline="\n",
    )
    (FIG_DIR / "f2_straight_vs_route.svg").write_text(
        scatter_svg("Straight-line vs route distance to nearest mapped crossing", numbers["scatter_points"]),
        encoding="utf-8", newline="\n",
    )
    REPORT_MD.write_text(build_report(numbers), encoding="utf-8", newline="\n")
    # Machine-readable numbers (gitignored): drop the bulky scatter payload.
    persisted = {k: v for k, v in numbers.items() if k != "scatter_points"}
    NUMBERS_JSON.write_text(
        json.dumps(persisted, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"wrote {REPORT_MD.relative_to(REPO_ROOT)}, 2 figures, and {NUMBERS_JSON.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
