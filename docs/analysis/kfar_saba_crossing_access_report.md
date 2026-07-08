# Kfar Saba crossing-access — analysis report

Recomputed from the committed pilot workspace (`safe_access_kfar_saba_route_aware_v001`) by a single standard-library Python script, `scripts/generate_analysis_report.py`. Every figure is generated, not hand-drawn. Wording follows the policy in [`../scope.md`](../scope.md).

## S0 — Executive summary

**Headline numbers**

- 391 pedestrian destinations measured against 342 mapped pedestrian crossings, over 2603 road segments.
- 155 of 342 crossings (45.3 %) carry a `traffic_signals` tag; the rest are marked, uncontrolled or generic.
- Priority scores span 25–110; every destination carries at least one indicator, so the ranking separates degree of concern, not presence.

**Claim boundaries**

- The median route distance to the nearest mapped crossing is **218.6 m** (a direct recompute from the committed tables, which round distances to 0.1 m, gives 218.7 m).
- **169 of 391 destinations** are beyond 250 m from the nearest mapped crossing by route.
- The priority score is transparent but **UNCALIBRATED** — it is never checked against real outcome data, so it says where to look first, not where conditions are worst. The approved and restricted wording is defined in [`../scope.md`](../scope.md).

> This location has infrastructure risk indicators and should be reviewed on-site.

## S1 — Study area and data inventory

| Layer | Count |
|---|---:|
| Pedestrian destinations | 391 |
| Mapped pedestrian crossings | 342 |
| Road segments | 2603 |
| Road-network graph nodes | 9828 |
| Road-network graph edges | 11366 |
| Road segments included in the network proxy | 2514 |
| Road segments excluded (motorway/trunk/track/unknown) | 89 |

**Crossing type mix** — distance is measured to the nearest *mapped* crossing, not a signal-controlled one:

| Crossing type | Count |
|---|---:|
| `traffic_signals` | 155 |
| `uncontrolled` | 123 |
| `marked` | 35 |
| `pedestrian_crossing` | 29 |

**Destination type mix:**

| Destination type | Count |
|---|---:|
| `bus_stop` | 180 |
| `park` | 103 |
| `playground` | 39 |
| `kindergarten` | 37 |
| `school` | 28 |
| `community_centre` | 2 |
| `childcare` | 1 |
| `recreation_ground` | 1 |

*Reconciliation:* all counts above are computed in SQL from the committed workspace tables and match the workspace `network_analysis_summary.json` exactly. The distance percentiles in S2 are quoted from that summary (full precision) and reproduce from the tables within 0.1 m, since the tables round distances to 0.1 m.

## S2 — Distance to the nearest mapped crossing

Each destination is measured to the nearest mapped crossing two ways: straight-line and along the OSM road-network proxy graph. The median route distance is **218.6 m** (p90 627.2 m); **169 of 391** destinations (43 %) are beyond 250 m by route and 244 are beyond 150 m. 390 destinations reach a crossing across the proxy graph; 1 does not (gen_0152) and is reported as a data-quality gap, not a finding. The median route-to-straight detour ratio is 1.26.

![Route-distance bands by destination type](figures/f1_route_bands_by_type.svg)

*Figure 1. Route distance to the nearest mapped crossing, banded and stacked per destination type. Bands are upper-inclusive, so the two longest bands together equal the 250 m count above.*

![Straight-line versus route distance](figures/f2_straight_vs_route.svg)

*Figure 2. Straight-line versus route distance for every reachable destination; the dashed line is route = straight. Points above it (the majority) travel further along the network than the crow-flies distance implies.*

### Reproducing the ranking

The live dashboard candidates endpoint orders destinations by `(-route_review_priority_score, -risk_score, -nearest_crossing_m)`. That key leaves ties unresolved, and the app falls back on Python's stable sort, which is not reproducible from the tables alone. This report appends `generator_id` ascending as a final deterministic tie-break; the top five under that order are:

| # | Type | Name | Straight (m) | Route (m) | Score |
|--:|---|---|--:|--:|--:|
| 1 | school | רחל המשוררת | 170.8 | 430.6 | 110 |
| 2 | park | — | 226.7 | 472.5 | 105 |
| 3 | school | חטיבת שרת | 339.7 | 477.0 | 100 |
| 4 | school | חטיבת שז"ר | 270.6 | 334.0 | 100 |
| 5 | school | חטיבת הביניים ע"ש יורם טהרלב | 254.5 | 409.2 | 100 |

