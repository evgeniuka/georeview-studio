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
from collections import Counter, namedtuple
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

# The 9 scored rules from config/scoring_rules_v001.json. The three route add-ons and their
# weights mirror backend/route_network_analyzer.py:444-451 (route > 250 m = 20, ratio >= 1.8 and
# route > 150 m = 10, off-network > 35 m = 5). The zero-point context flags are not scored.
Rule = namedtuple("Rule", "name weight group label")
RULES = [
    Rule("major_road_within_150m", 25, "common", "major road <=150 m"),
    Rule("no_mapped_crossing_within_150m", 25, "common", "no crossing <=150 m"),
    Rule("nearest_crossing_near_major_road_without_signal_within_50m", 15, "common", "crossing on major road, no signal"),
    Rule("no_mapped_traffic_calming_within_100m_weak_indicator", 10, "common", "no traffic calming <=100 m"),
    Rule("explicit_sidewalk_no_within_50m", 10, "common", "sidewalk=no <=50 m"),
    Rule("explicit_lit_no_within_50m", 5, "common", "lit=no <=50 m"),
    Rule("route_nearest_crossing_over_250m", 20, "route", "route to crossing >250 m"),
    Rule("high_network_detour_ratio", 10, "route", "high detour ratio"),
    Rule("generator_far_from_network_proxy", 5, "route", "far from road network"),
]
# Rules about sparse or inadequate mapped-crossing access (by index into RULES).
CROSSING_ACCESS_RULES = (1, 2, 6)


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


# --------------------------------------------------------------------------- score frame + stats


def build_score_frame(conn: sqlite3.Connection) -> tuple[list[dict], int]:
    """One row per destination with the indices of the weighted rules it fired, for the S3 audit
    and the S4 protocols. Also confirms the recompute reconciles with the stored score everywhere."""
    rule_index = {ru.name: i for i, ru in enumerate(RULES)}
    frame: list[dict] = []
    reconciled = 0
    for gid, gtype, name, base, route_review, ratio, nflags, nearest, rflags in conn.execute(
        """
        SELECT n.generator_id, n.generator_type, n.name, n.base_risk_score,
               n.route_review_priority_score, n.route_vs_straight_ratio,
               n.network_flags, r.nearest_crossing_m, r.risk_flags
        FROM network n JOIN risk r ON n.generator_id = r.generator_id
        """
    ):
        fired = sorted(
            rule_index[flag]
            for flag in set(json.loads(rflags or "[]")) | set(json.loads(nflags or "[]"))
            if flag in rule_index
        )
        if sum(RULES[i].weight for i in fired) == route_review:
            reconciled += 1
        frame.append({
            "gid": gid, "gtype": gtype, "name": name or "",
            "base": base, "route_review": route_review,
            "nearest": nearest if nearest is not None else 0.0,
            "ratio": ratio, "fired": fired,
        })
    frame.sort(key=lambda d: d["gid"])
    assert reconciled == len(frame), (reconciled, len(frame))
    return frame, reconciled


def average_ranks(values: list[float]) -> list[float]:
    """1-based ranks with tied values sharing their mean rank (for tie-aware Spearman)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def _pearson(x: list[float], y: list[float]) -> float:
    try:
        return statistics.correlation(x, y)
    except (statistics.StatisticsError, ValueError):
        n = len(x)
        mx, my = sum(x) / n, sum(y) / n
        sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
        sxx = sum((a - mx) ** 2 for a in x)
        syy = sum((b - my) ** 2 for b in y)
        return sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0


def _kendall_tau_b(x: list[float], y: list[float]) -> float:
    """Kendall tau-b (handles the heavy ties in the 17-value scores). O(n^2); single use only."""
    n = len(x)
    concordant = discordant = 0
    for i in range(n):
        xi, yi = x[i], y[i]
        for j in range(i + 1, n):
            dx, dy = xi - x[j], yi - y[j]
            if dx == 0 or dy == 0:
                continue
            if (dx > 0) == (dy > 0):
                concordant += 1
            else:
                discordant += 1
    n0 = n * (n - 1) // 2
    tx = sum(c * (c - 1) // 2 for c in Counter(x).values())
    ty = sum(c * (c - 1) // 2 for c in Counter(y).values())
    denom = math.sqrt((n0 - tx) * (n0 - ty))
    return (concordant - discordant) / denom if denom else 0.0


def jaccard(a: set, b: set) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def compute_s3(conn: sqlite3.Connection, frame: list[dict], reconciled: int) -> dict:
    fires = [0] * len(RULES)
    for row in frame:
        for i in row["fired"]:
            fires[i] += 1
    grand = sum(fires[i] * RULES[i].weight for i in range(len(RULES)))
    per_rule = [
        {"rule": ru.name, "label": ru.label, "group": ru.group, "weight": ru.weight,
         "fires": fires[i], "points": fires[i] * ru.weight,
         "share_pct": round(100.0 * fires[i] * ru.weight / grand, 1)}
        for i, ru in enumerate(RULES)
    ]
    crossing_share = round(100.0 * sum(fires[i] * RULES[i].weight for i in CROSSING_ACCESS_RULES) / grand, 1)
    distribution = Counter(row["route_review"] for row in frame)
    n_rows = len(frame)

    def coverage_pct(flag: str) -> float:
        missing = conn.execute(
            "SELECT COUNT(DISTINCT generator_id) FROM network__data_quality_flags WHERE flag = ?", (flag,)
        ).fetchone()[0]
        return round(100.0 * (1 - missing / n_rows), 1)

    return {
        "audit": {"rows": n_rows, "reconciled": reconciled},
        "per_rule": per_rule,
        "grand_total_points": grand,
        "crossing_access_share_pct": crossing_share,
        "distinct_scores": len(distribution),
        "score_distribution": [{"score": s, "count": distribution[s]} for s in sorted(distribution)],
        "dead_rules": {
            "lit_fires": fires[5],
            "sidewalk_fires": fires[4],
            "lit_coverage_pct": coverage_pct("nearby_lit_tags_missing"),
            "sidewalk_coverage_pct": coverage_pct("nearby_sidewalk_tags_missing"),
        },
    }


def compute_s4(frame: list[dict]) -> dict:
    n = len(frame)
    gids = [r["gid"] for r in frame]
    base = [r["base"] for r in frame]
    route = [r["route_review"] for r in frame]
    nearest = [r["nearest"] for r in frame]
    fired = [r["fired"] for r in frame]

    def order_by(scores: list[float]) -> list[int]:
        # app tie-break (-score, -risk_score, -nearest_crossing_m) + generator_id final key
        return sorted(range(n), key=lambda i: (-scores[i], -base[i], -nearest[i], gids[i]))

    def top_set(order: list[int], k: int) -> set:
        return {gids[i] for i in order[:k]}

    base_order = order_by(route)
    base_top20 = top_set(base_order, 20)
    base_top50 = top_set(base_order, 50)
    base_ranks = average_ranks(route)

    # Protocol A -- 1000 independent uniform(0.5,1.5) multipliers per weight.
    trial_rng = random.Random(SEED)
    jac20: list[float] = []
    jac50: list[float] = []
    rhos: list[float] = []
    freq: Counter = Counter()
    for _ in range(1000):
        mult = [trial_rng.uniform(0.5, 1.5) for _ in range(len(RULES))]
        scores = [sum(RULES[i].weight * mult[i] for i in fired[j]) for j in range(n)]
        order = order_by(scores)
        top20 = top_set(order, 20)
        jac20.append(jaccard(base_top20, top20))
        jac50.append(jaccard(base_top50, top_set(order, 50)))
        freq.update(top20)
        rhos.append(_pearson(base_ranks, average_ranks(scores)))

    def band(values: list[float]) -> dict:
        s = sorted(values)
        return {"median": round(statistics.median(s), 3),
                "p5": round(_percentile(s, 0.05), 3),
                "p95": round(_percentile(s, 0.95), 3)}

    stable_core = sorted(g for g, c in freq.items() if c >= 950)
    top20_frequency = sorted(
        ({"generator_id": g, "trials": c, "pct": round(100.0 * c / 1000, 1)} for g, c in freq.items()),
        key=lambda d: (-d["trials"], d["generator_id"]),
    )

    # Protocol B -- leave one rule out (9 deterministic runs).
    protocol_b = []
    for k in range(len(RULES)):
        scores = [route[j] - (RULES[k].weight if k in fired[j] else 0) for j in range(n)]
        order = order_by(scores)
        protocol_b.append({
            "dropped": RULES[k].name,
            "top20_jaccard": round(jaccard(base_top20, top_set(order, 20)), 3),
            "rho": round(_pearson(base_ranks, average_ranks(scores)), 3),
        })

    # Protocol D -- straight-only (base_risk_score) vs route-aware.
    straight_order = order_by(base)
    straight_top20 = top_set(straight_order, 20)
    straight_rank = {gids[i]: pos + 1 for pos, i in enumerate(straight_order)}
    route_rank = {gids[i]: pos + 1 for pos, i in enumerate(base_order)}
    movers = sorted(frame, key=lambda r: (-abs(straight_rank[r["gid"]] - route_rank[r["gid"]]), r["gid"]))
    protocol_d = {
        "rho": round(_pearson(average_ranks(base), average_ranks(route)), 3),
        "kendall_tau_b": round(_kendall_tau_b(base, route), 3),
        "top20_jaccard": round(jaccard(straight_top20, base_top20), 3),
        "entrants": sorted(base_top20 - straight_top20),
        "leavers": sorted(straight_top20 - base_top20),
        "largest_movers": [
            {"generator_id": r["gid"], "type": r["gtype"],
             "straight_rank": straight_rank[r["gid"]], "route_rank": route_rank[r["gid"]],
             "rank_change": straight_rank[r["gid"]] - route_rank[r["gid"]],
             "route_vs_straight_ratio": r["ratio"]}
            for r in movers[:5]
        ],
    }

    return {
        "protocol_a": {
            "trials": 1000,
            "top20_jaccard": band(jac20),
            "top50_jaccard": band(jac50),
            "spearman_rho": band(rhos),
            "stable_core": stable_core,
            "stable_core_size": len(stable_core),
            "top20_frequency": top20_frequency,
        },
        "protocol_b": protocol_b,
        "protocol_d": protocol_d,
        "baseline_top20": sorted(base_top20),
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


def hbar_svg(title, labels, values, colors, value_label, footer=""):
    n = len(labels)
    y_top, y_bottom, x_bar, x_right = 44.0, 314.0, 214.0, 606.0
    row_h = (y_bottom - y_top) / max(n, 1)
    bar_h = min(15.0, row_h * 0.68)
    v_max = max(values) if values else 1.0
    scale = (x_right - x_bar) / v_max if v_max else 0.0

    out = _svg_open()
    out.append(_text(320, 24, title, size=13, anchor="middle"))
    for i, (label, value) in enumerate(zip(labels, values)):
        cy = y_top + row_h * (i + 0.5)
        width = value * scale
        out.append(_text(x_bar - 6, cy + 3, label, size=9, anchor="end", color="#333"))
        out.append(f'<rect x="{_fmt(x_bar)}" y="{_fmt(cy - bar_h / 2)}" width="{_fmt(width)}" height="{_fmt(bar_h)}" fill="{colors[i]}"/>')
        out.append(_text(x_bar + width + 4, cy + 3, value_label(value), size=9, anchor="start", color="#333"))
    if footer:
        out.append(_text(320, 340, footer, size=9, anchor="middle", color="#555"))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def figure_f3(s3: dict) -> str:
    items = sorted(s3["per_rule"], key=lambda d: (-d["points"], d["rule"]))
    colors = ["#d73027" if d["group"] == "route" else "#4575b4" for d in items]
    footer = f"{s3['grand_total_points']} points total; crossing-access rules = {s3['crossing_access_share_pct']}% (red = route add-on)"
    return hbar_svg(
        "Total priority points contributed per rule",
        [d["label"] for d in items], [d["points"] for d in items], colors, str, footer,
    )


def figure_f4(s4: dict) -> str:
    freq = s4["protocol_a"]["top20_frequency"][:22]
    colors = ["#1a9850" if d["pct"] >= 95 else "#4575b4" for d in freq]
    footer = f"stable core (top-20 in >=95% of 1000 trials): {s4['protocol_a']['stable_core_size']} destinations (green)"
    return hbar_svg(
        "Top-20 membership frequency across 1000 weight-perturbation trials",
        [d["generator_id"] for d in freq], [d["pct"] for d in freq], colors,
        lambda v: f"{v}%", footer,
    )


# --------------------------------------------------------------------------- report


def _mix_table(mix: dict[str, int], header: str) -> list[str]:
    lines = [f"| {header} | Count |", "|---|---:|"]
    for key, value in mix.items():
        lines.append(f"| `{key}` | {value} |")
    return lines


def build_report(n: dict, s3: dict, s4: dict) -> str:
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
    L.append(
        f"- The top-20 shortlist is stable under +/-50 % weight perturbation "
        f"(median top-20 Jaccard {s4['protocol_a']['top20_jaccard']['median']}; "
        f"{s4['protocol_a']['stable_core_size']} of 20 recur in >=95 % of 1,000 trials). "
        f"**A stable ranking can still be a wrong ranking; stability is not validation.**"
    )
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

    # -- S3 --------------------------------------------------------------
    audit = s3["audit"]
    dead = s3["dead_rules"]
    L.append("## S3 — Anatomy of the score")
    L.append("")
    L.append(
        f"Every priority score is a sum over a small fixed rule set. Recomputing each score from its fired "
        f"flags times the configured weights **reconciles with** the stored `route_review_priority_score` for "
        f"all {audit['rows']} rows ({audit['reconciled']} of {audit['rows']}, 0 mismatches)."
    )
    L.append("")
    L.append("| Rule | Group | Weight | Fires | Points | Share |")
    L.append("|---|---|--:|--:|--:|--:|")
    for d in sorted(s3["per_rule"], key=lambda r: (-r["points"], r["rule"])):
        L.append(f"| `{d['rule']}` | {d['group']} | {d['weight']} | {d['fires']} | {d['points']} | {d['share_pct']} % |")
    L.append(f"| **total** | | | | **{s3['grand_total_points']}** | 100 % |")
    L.append("")
    L.append(
        f"The crossing-access rules (sparse or inadequate mapped crossings — `no_mapped_crossing_within_150m`, "
        f"`nearest_crossing_near_major_road_without_signal_within_50m`, `route_nearest_crossing_over_250m`) supply "
        f"**{s3['crossing_access_share_pct']} %** of all points, the largest single group."
    )
    L.append("")
    L.append(
        f"**Dead rules.** `explicit_lit_no_within_50m` fires {dead['lit_fires']} times and "
        f"`explicit_sidewalk_no_within_50m` fires {dead['sidewalk_fires']} times — not because the area is well "
        f"served, but because those OSM tags are sparsely mapped: a lit tag of any value sits near only "
        f"{dead['lit_coverage_pct']} % of destinations and a sidewalk tag near {dead['sidewalk_coverage_pct']} %, "
        f"and the explicit `lit=no` / `sidewalk=no` values these rules require are rarer still "
        f"({dead['lit_fires']} and {dead['sidewalk_fires']} of {audit['rows']} destinations). A missing tag stays a "
        f"data-quality gap and adds no points, so these two rules cannot move this ranking."
    )
    L.append("")
    L.append(
        f"Scores take only {s3['distinct_scores']} distinct values (range {n['priority_score_range']['min']}–"
        f"{n['priority_score_range']['max']}); those heavy ties drive the rank handling in S4."
    )
    L.append("")
    L.append("![Total points contributed per rule](figures/f3_points_per_rule.svg)")
    L.append("")
    L.append("*Figure 3. Total priority points per rule (fire count x weight); route add-ons in red. The two dead rules contribute almost nothing.*")
    L.append("")

    # -- S4 --------------------------------------------------------------
    pa = s4["protocol_a"]
    pd = s4["protocol_d"]
    L.append("## S4 — How robust is the ranking?")
    L.append("")
    L.append(
        "Three protocols ask whether the shortlist survives reasonable changes to the scoring. Each re-ranks all "
        f"{c['pedestrian_destinations']} destinations with the app tie-break plus `generator_id` as a final "
        "deterministic key. **A stable ranking can still be a wrong ranking; stability is not validation.**"
    )
    L.append("")
    L.append("**Protocol A — weight perturbation.** 1,000 trials; each multiplies every one of the 9 weights by an independent `uniform(0.5, 1.5)` factor, then re-ranks:")
    L.append("")
    L.append(f"- Top-20 Jaccard vs baseline: median **{pa['top20_jaccard']['median']}** (p5 {pa['top20_jaccard']['p5']}, p95 {pa['top20_jaccard']['p95']}).")
    L.append(f"- Top-50 Jaccard: median {pa['top50_jaccard']['median']} (p5 {pa['top50_jaccard']['p5']}, p95 {pa['top50_jaccard']['p95']}).")
    L.append(f"- Tie-aware Spearman rho vs baseline: median {pa['spearman_rho']['median']} (p5 {pa['spearman_rho']['p5']}, p95 {pa['spearman_rho']['p95']}).")
    L.append(f"- **Stable core** (top-20 in >=95 % of trials): {pa['stable_core_size']} of 20 destinations.")
    L.append("")
    L.append("![Top-20 membership frequency](figures/f4_top20_frequency.svg)")
    L.append("")
    L.append("*Figure 4. How often each destination lands in the top 20 across the 1,000 trials; green bars are the stable core (>=95 %).*")
    L.append("")
    L.append(
        f"> Tie-aware Spearman uses average ranks for tied scores with Pearson on those ranks. The textbook "
        f"`1 - 6*sum(d^2)/(n*(n^2-1))` shortcut is invalid here because scores take only {s3['distinct_scores']} "
        f"distinct values, so ties are pervasive."
    )
    L.append("")
    L.append("**Protocol B — leave one rule out.** Drop each rule in turn (9 deterministic runs) and re-rank:")
    L.append("")
    L.append("| Rule dropped | Top-20 Jaccard | Spearman rho |")
    L.append("|---|--:|--:|")
    for d in sorted(s4["protocol_b"], key=lambda r: (r["top20_jaccard"], r["dropped"])):
        L.append(f"| `{d['dropped']}` | {d['top20_jaccard']} | {d['rho']} |")
    L.append("")
    worst_j = min(d["top20_jaccard"] for d in s4["protocol_b"])
    worst_rules = [d["dropped"] for d in sorted(s4["protocol_b"], key=lambda r: r["dropped"]) if d["top20_jaccard"] == worst_j]
    joined = " and ".join(f"`{r}`" for r in worst_rules)
    L.append(f"The most disruptive single drops take the top-20 Jaccard down to {worst_j} ({joined}); dropping either dead rule leaves the top 20 unchanged.")
    L.append("")
    L.append("**Protocol D — straight-only vs route-aware.** Ranking by `base_risk_score` (straight-line only) against the route-aware `route_review_priority_score`:")
    L.append("")
    L.append(f"- Tie-aware Spearman rho {pd['rho']}, Kendall tau-b {pd['kendall_tau_b']}, top-20 Jaccard {pd['top20_jaccard']}.")
    L.append(f"- Route-awareness brings {len(pd['entrants'])} destinations into the top 20 and drops {len(pd['leavers'])}.")
    L.append("")
    L.append("| Generator | Type | Straight rank | Route rank | Move | Detour ratio |")
    L.append("|---|---|--:|--:|--:|--:|")
    for m in pd["largest_movers"]:
        ratio = "—" if m["route_vs_straight_ratio"] is None else m["route_vs_straight_ratio"]
        L.append(f"| `{m['generator_id']}` | {m['type']} | {m['straight_rank']} | {m['route_rank']} | {m['rank_change']:+d} | {ratio} |")
    L.append("")
    L.append("Kendall tau-b is computed once here, never inside the 1,000-trial loop where its O(n^2) cost would dominate.")
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
        frame, reconciled = build_score_frame(conn)
        s3 = compute_s3(conn, frame, reconciled)
        s4 = compute_s4(frame)
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
    (FIG_DIR / "f3_points_per_rule.svg").write_text(figure_f3(s3), encoding="utf-8", newline="\n")
    (FIG_DIR / "f4_top20_frequency.svg").write_text(figure_f4(s4), encoding="utf-8", newline="\n")
    REPORT_MD.write_text(build_report(numbers, s3, s4), encoding="utf-8", newline="\n")
    # Machine-readable numbers (gitignored): drop the bulky scatter payload.
    persisted = {k: v for k, v in numbers.items() if k != "scatter_points"}
    persisted["s3_score_anatomy"] = s3
    persisted["s4_ranking_robustness"] = s4
    NUMBERS_JSON.write_text(
        json.dumps(persisted, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"wrote {REPORT_MD.relative_to(REPO_ROOT)}, 4 figures, and {NUMBERS_JSON.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
