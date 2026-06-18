# Implementation Plan

## v023 Current Release

Purpose: make the universal product architecture explicit in code, API, UI, docs and tests.

Deliverables:

- `backend/product_architecture.py`
- `GET /api/product-architecture`
- `GET /api/product-architecture/variants`
- `GET /api/product-architecture/roadmap`
- `POST /api/product-architecture/implementation-plan`
- Product Architecture UI panel
- architecture docs and validation checks

## v024 Recommended Build

Build a profile selector dashboard.

Milestones:

1. Define one result-row contract across implemented profiles.
2. Add a profile selector UI.
3. Render Safe Access, Transit and Park profile result rows in the same table component.
4. Add profile-specific metrics without duplicating dashboard code.
5. Add export bundle metadata linking the three profile reports and the comparison report.

Validation:

- API contract tests cover all profile result endpoints.
- The browser smoke test confirms non-empty result tables for all implemented profiles.
- Wording scan finds no absolute safety claims.
- Source GIS files remain read-only.

## v025 Recommended Build

Add a local intake wizard.

Milestones:

1. Let the user choose a local folder path or registered source id.
2. Profile files before any run starts.
3. Show format, CRS, layers, counts and profile readiness.
4. Write only derived metadata under `analysis_output`.
5. Require explicit confirmation before generating a workspace.

## v026 Recommended Build

Move scoring rules into versioned JSON per profile.

## v027 Recommended Build

Add a PostGIS option for larger regions while keeping CSV/GeoPackage outputs for portfolio demonstration.

## v024 Completed Step

The profile selector dashboard is implemented through `backend/profile_dashboard.py`, the `/api/profile-dashboard` endpoints, and the Universal Profile Results UI panel.

## v025 Local Intake And Export Bundle

- `GET /api/local-intake`
- `GET /api/local-intake/sources`
- `POST /api/local-intake/preview`
- `POST /api/local-intake/plan`
- `POST /api/export-bundles/profile-dashboard`
- `GET /api/export-bundles`
- `GET /api/export-bundles/{bundle_id}`
- `GET /api/export-bundles/{bundle_id}/download`

All generated files are metadata/report artifacts under `analysis_output`; source GIS files remain read-only.

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
