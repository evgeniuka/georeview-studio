# Universal GIS Analytics Architecture

GeoReview Studio should evolve from one Safe Access pilot into a reusable local-first GIS analytics workbench.

## Product Position

The strongest portfolio direction is not a single Kfar Saba notebook. It is a repeatable GIS analysis platform:

- load local OSM/GIS sources;
- profile data quality and tag availability;
- normalize layers into analysis-ready tables;
- run a selected analysis profile;
- store every run as reproducible evidence;
- show dashboards and export reports.

Safe Access Israel remains the first analysis profile, not the whole product.

## Best Project Variants

1. **GeoReview Studio: Universal OSM/GIS Review Workbench**

   Best portfolio option. It shows backend design, data engineering, GIS analytics, frontend dashboards, reproducibility, and domain judgment.

2. **Safe Access Israel: Pedestrian Infrastructure Review**

   Best domain story. It is focused, understandable, and useful for explaining road safety engineering decisions.

3. **Open Mobility Evidence Lab**

   Broader civic-tech version. It can include transit access, cycling infrastructure, parks access, and pedestrian crossings.

The recommended path is to build option 1, with option 2 as the first polished profile.

## Target Architecture

```text
Local GIS files
  -> source onboarding
  -> layer/tag profiler
  -> normalized canonical model
  -> analysis profile runner
  -> workspace outputs
  -> analysis run registry
  -> dashboards
  -> portfolio reports
```

## Core Modules

- `source_onboarding`: finds supported files and profiles readiness.
- `profile_engine`: extracts layers, schemas, CRS, feature counts, and tag coverage.
- `normalizer`: maps source-specific layers into canonical tables.
- `analysis_profiles`: contains Safe Access, transit access, cycle access, and park access logic.
- `workspace_runner`: creates small reproducible workspace outputs.
- `run_registry`: tracks job status, inputs, outputs, and reruns.
- `dashboard_api`: serves metrics, map features, candidates, and quality flags.
- `report_builder`: generates Markdown/JSON evidence reports.

## Analysis Profiles

### Safe Access

Inputs:

- pedestrian generators;
- crossings;
- roads;
- traffic signals;
- traffic calming;
- sidewalk, lighting, and speed tags where available.

Outputs:

- review candidates;
- nearest crossing metrics;
- major-road proximity;
- route-aware proxy metrics;
- infrastructure review flags;
- data-quality flags.

### Transit Access

Inputs:

- bus stops;
- platforms;
- crossings;
- roads;
- shelters and benches where available.

Outputs:

- stops with weak mapped crossing access;
- stop amenities coverage;
- route-aware crossing distance.

### Cycling And Micromobility

Inputs:

- cycleways;
- bicycle tags;
- segregated paths;
- road classes;
- crossings and junctions.

Outputs:

- cycle infrastructure continuity indicators;
- mixed-traffic exposure indicators;
- tag coverage gaps.

### Park And Playground Access

Inputs:

- parks;
- playgrounds;
- schools and kindergartens;
- crossings;
- roads.

Outputs:

- access review candidates around public spaces;
- crossing proximity;
- major-road proximity.

## MVP v0.1

Keep the first serious MVP narrow:

- source onboarding;
- Kfar Saba Safe Access profile;
- analysis runs;
- route-aware proxy metrics;
- portfolio report builder;
- static local frontend dashboard.

This is enough to demonstrate end-to-end value without pretending the data proves real-world conditions.

## MVP v0.2

Add generalization:

- let the user choose another pilot polygon;
- generate a new workspace id from selected area and profile;
- expose profile templates in the UI;
- add run comparison;
- add report download.

## MVP v0.3

Add stronger platform capabilities:

- upload/import folder path flow;
- PostGIS option for larger regions;
- MapLibre frontend map;
- configurable scoring rules;
- PDF export or printable HTML report;
- per-profile validation gates.

## Internal Data Model

Use canonical tables:

- `source_datasets`
- `dataset_layers`
- `analysis_profiles`
- `pedestrian_generators`
- `crossings`
- `road_segments`
- `transit_stops`
- `safety_features`
- `risk_assessment_results`
- `network_access_results`
- `analysis_runs`
- `portfolio_reports`

Every row should keep source evidence fields such as `osm_id`, `source_layer`, `source_dataset_id`, and `data_quality_flags`.

## Claim Boundary

The platform should always separate:

- infrastructure review indicators;
- data-quality gaps;
- field-review recommendations.

Approved wording:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```

The product should not present OSM absence as real-world absence.

## Next Build Step

After v024, the best next version is a reviewed local intake wizard and profile selector export bundle:

- move profile definitions into versioned JSON if the list grows;
- add a profile selector that switches dashboard tables from Safe Access candidates to Transit or Park results;
- add profile-specific report sections for future non-transit profiles;
- add export bundles that include the comparison report plus each profile report.

## v023 Architecture Evidence

v023 promotes this plan into executable product evidence through `backend/product_architecture.py`, product architecture API endpoints, a UI panel, and validation/API contract checks. The next implementation target is a profile selector dashboard that reuses one result-table contract across implemented profiles.

## v027 PostGIS Backend Option

- `config/postgis_schema_v001.sql`
- `backend/postgis_backend.py`
- `GET /api/postgis-backend`
- `GET /api/postgis-backend/schema`
- `GET /api/postgis-backend/migration-plan`
- `POST /api/postgis-backend/migration-plan`
- `GET /api/postgis-backend/plans`
- `GET /api/postgis-backend/{plan_id}`

This is a planning layer only. It does not open a database connection, does not read credentials, and does not modify source GIS files.
