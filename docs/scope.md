# GeoReview Studio — Scope & Mission

## Mission (one line)

Pedestrian-access safety **prioritization**: from open OpenStreetMap / Geofabrik
data, find the pedestrian **destinations** that are poorly served by mapped
pedestrian crossings, and rank which ones a human should **inspect on-site first**.

## Subject vs yardstick (read this first — common confusion)

- **SUBJECT of the analysis = pedestrian "generators" / destinations:** schools,
  kindergartens, childcare, parks, playgrounds, bus stops, community centres —
  the places people (often children) walk to.
- **YARDSTICK = mapped (signalised) pedestrian crossings.** We measure how far
  each destination is from the nearest crossing — straight-line **and** route-aware
  along the road network — plus context flags (major road within 150 m, no mapped
  crossing within 150 m, near a major road without a signal, weak traffic calming).
- **OUTPUT = a ranked, explainable, trackable shortlist of destinations to review
  on-site**, with a per-candidate reviewer decision (status / note / assignee).

So this is **not** "an app about crossings". Crossings are the reference we measure
against; the product is *prioritising where pedestrian-crossing access looks
inadequate near the places people walk to.*

## What it is NOT

- NOT crash / accident prediction.
- NOT a crossing-inventory tool.
- NOT a validated verdict — the score is a **transparent but UNCALIBRATED**
  heuristic ("where mapped crossing access is sparse"), never checked against
  real outcome data. It tells you *where to look first*, not *where it is worst*.
- A missing OSM tag is a **data-quality flag**, never proof that infrastructure
  is absent.
- Approved wording only: **"This location has infrastructure risk indicators and
  should be reviewed on-site."** (Banned: "crash prediction", "definitely dangerous".)

## Profiles

Flagship profile: **safe-access** (destinations vs crossings). Also implemented:
**transit-stop walk access** and **park/playground access** — same pipeline, different
destination sets. So the specialisation is **"pedestrian access to destinations"**,
with crossings as the flagship lens.

## Product & engineering principles (agreed direction)

- **Local-first, single analyst by default.** No external DB / hosting / deploy
  without explicit approval.
- **Stdlib-only Python + vanilla JS. NO frameworks. Zero runtime dependencies.** Keep it.
- **Simple and clean: prefer SUBTRACTING code over adding.** The product core
  (~12 endpoints) must be cleanly separable from the internal publication/QA
  **tooling layer** (~50 endpoints; already opt-out via `GEOREVIEW_MODE=product`).
- **Simple is not unstructured** — a stdlib route table and an ES-module split of
  `app.js` are welcome; frameworks are not.
- **Honest framing always** (see "What it is NOT").
- Analysis CRS is **EPSG:2039 (Israeli grid)** → today the analysis is Israel-specific;
  other regions need a different projection, not just new data.
