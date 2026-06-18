# Product Architecture

GeoReview Studio v083 frames the project as a universal local-first GIS review workbench.

The important product decision is that Safe Access Israel is the first implemented profile, not the entire product. The reusable platform is:

```text
local GIS sources
  -> source onboarding
  -> layer and tag profile
  -> canonical workspace
  -> analysis profile runner
  -> dashboard
  -> portfolio report
```

## Why This Is Stronger For Portfolio

The current data can already support three real review profiles in Kfar Saba:

- `safe_access_pedestrian_review`
- `transit_stop_walk_access`
- `park_playground_access`

That proves the product is not just one notebook. It is a repeatable architecture for infrastructure evidence review.

## Product Boundary

The app does not predict crashes and does not claim a location is objectively problematic. It reports mapped infrastructure indicators and data-quality evidence.

Approved row wording:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```

Missing OSM tags remain data-quality flags. They are not treated as proof that infrastructure is absent.

## Current Architecture Evidence

- read-only source onboarding for the local `maps` folder;
- pilot-area catalog from Geofabrik place polygons;
- Safe Access selected-pilot preflight;
- canonical Safe Access workspace outputs;
- route-aware proxy metrics;
- reusable analysis profile registry;
- implemented Transit and Park profile runners;
- profile comparison portfolio report;
- API contract tests over the public app surface.

## Current Limits

- browser upload is designed but not implemented;
- PostGIS is a later option, not required for Kfar Saba MVP;
- only three profile runners are implemented;
- profile result tables still have profile-specific schemas;
- OSM data quality varies by tag and area.

## v024 Profile Selector

v024 implements the recommended next step from v023: one normalized dashboard contract over Safe Access, Transit and Park profile results.

## v026 Scoring Rules

- `config/scoring_rules_v001.json`
- `GET /api/scoring-rules`
- `GET /api/scoring-rules/{profile_id}`
- `GET /api/scoring-rules/{profile_id}/audit`
- `POST /api/scoring-rules/{profile_id}/audit`

The score audit recalculates expected profile scores from versioned rules and normalized result flags. Missing OSM tags remain data-quality flags, not score points by default.

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

## v028 Profile Mapper SDK

- `config/profile_mapper_contracts_v001.json`
- `backend/profile_mapper.py`
- `GET /api/profile-mapper`
- `GET /api/profile-mapper/contracts`
- `GET /api/profile-mapper/contracts/{profile_id}`
- `GET /api/profile-mapper/compatibility`
- `GET /api/profile-mapper/plan`
- `POST /api/profile-mapper/plan`
- `GET /api/profile-mapper/plans`
- `GET /api/profile-mapper/plans/{plan_id}`

This release turns profile requirements into explicit contracts. The contract layer is planning-first: it checks whether a source can support a profile and creates a mapper plan without modifying source GIS files.

## v029 Contract Execution Dry Run

- `backend/contract_execution.py`
- `GET /api/contract-execution`
- `GET /api/contract-execution/adapters`
- `GET /api/contract-execution/dry-run`
- `POST /api/contract-execution/dry-run`
- `GET /api/contract-execution/dry-runs`
- `GET /api/contract-execution/dry-runs/{dry_run_id}`

This release binds validated profile mapper contracts to existing or planned backend runners in dry-run mode. It is execution evidence, not a database connection or source GIS mutation.
