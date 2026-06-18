# Operations

## Start The App

```powershell
.\scripts\run_app.ps1
```

The app listens on:

```text
http://127.0.0.1:8847
```

## Run Validation

```powershell
.\scripts\validate.ps1
```

## Run API Contract Tests

```powershell
.\scripts\test_api_contract.ps1
```

The validator checks:

- packaged folder structure;
- backend imports;
- source audit files;
- source onboarding refresh and cache;
- Analysis Profiles readiness and plan adapter;
- Profile Runners and Transit/Park profile workspace generation;
- Create Analysis plan/start workflow;
- Analysis Runs list/detail/output/rerun workflow;
- Portfolio Reports generate/detail/download/compare workflow, including Transit/Park profile reports and profile comparison reports;
- existing generated workspaces;
- pilot-area catalog generation;
- selected-pilot preflight checks;
- background selected-pilot job history;
- PBF-enriched workspace evidence;
- route-aware network proxy workspace evidence;
- dynamic dashboard API logic;
- approved wording;
- absence of absolute safety-claim wording in app files.
- portfolio report artifacts.

## Generate Portfolio Artifacts

```powershell
.\scripts\generate_portfolio_artifacts.ps1
```

Outputs are written under:

```text
portfolio/
```

## Source Data Rule

Source GIS files in `D:\cloude_work\georeview-studio` are treated as read-only.

Generated artifacts go under:

```text
D:\cloude_work\georeview-studio\analysis_output
```

## Source Onboarding

Refresh the local source scan from the UI or via:

```text
POST /api/source-onboarding/refresh
```

The scanner excludes `analysis_output`, profiles supported source files, and writes:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_source_onboarding
```

## Create Analysis

The preferred user path is:

```text
source scan -> source selection -> pilot selection -> analysis plan -> background job -> dashboard workspace
```

The UI exposes this as the `Create Analysis` panel. The same flow is available through:

```text
POST /api/analysis-workflow/plan
POST /api/analysis-workflow/start
```

## Analysis Profiles

Use profiles to inspect which analytics are possible for the current source and pilot selection:

```text
GET /api/analysis-profiles
GET /api/analysis-profiles/{profile_id}
GET /api/analysis-profiles/{profile_id}/readiness
POST /api/analysis-profiles/{profile_id}/plan
```

The implemented runnable profile is:

```text
safe_access_pedestrian_review
```

## Profile Runners

Run the Transit Stop Walk Access profile:

```text
POST /api/profile-runners/transit_stop_walk_access/run
```

Run the Park And Playground Access profile:

```text
POST /api/profile-runners/park_playground_access/run
```

Inspect outputs:

```text
GET /api/profile-workspaces
GET /api/profile-workspaces/transit_stop_walk_access_kfar_saba_v001/summary
GET /api/profile-workspaces/transit_stop_walk_access_kfar_saba_v001/results
GET /api/profile-workspaces/park_playground_access_kfar_saba_v001/summary
GET /api/profile-workspaces/park_playground_access_kfar_saba_v001/results
```

## Analysis Runs

Use Analysis Runs to inspect previous analyses, open the active dashboard workspace, download CSV/JSON outputs, or rerun the same inputs:

```text
GET /api/analysis-runs
GET /api/analysis-runs/{run_id}
POST /api/analysis-runs/{run_id}/rerun
```

## Portfolio Reports

Use Portfolio Reports to generate a small Markdown/JSON evidence package from a completed analysis run, a profile workspace, or compare multiple runs:

```text
POST /api/portfolio-reports/from-run
POST /api/portfolio-reports/from-profile-workspace
POST /api/portfolio-reports/profile-comparison
POST /api/portfolio-reports/compare
GET /api/portfolio-reports
GET /api/portfolio-reports/{report_id}/download
```

For the Transit profile report, send:

```json
{
  "workspace_id": "transit_stop_walk_access_kfar_saba_v001"
}
```

For the Park profile report, send:

```json
{
  "workspace_id": "park_playground_access_kfar_saba_v001"
}
```

For the default implemented-profile comparison, send:

```json
{}
```

to:

```text
POST /api/portfolio-reports/profile-comparison
```

Reports are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_portfolio_reports
```

## Route-Aware Workspace

The default workspace is:

```text
safe_access_kfar_saba_route_aware_v001
```

It is derived from `safe_access_kfar_saba_pbf_enriched_v001` and adds `network_access_results.csv`.

## Pilot-Area Catalog

The app generates:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_pilot_catalog\pilot_areas.csv
```

This is a small derived catalog from the Geofabrik places polygon layer. Source GIS files remain read-only.

## Job History

Selected-pilot background jobs are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_runs
```

Each job has a JSON record with status, timestamps, payload, logs, result, and read-only source-data evidence.

## Preflight

Before building a selected pilot, the UI calls:

```text
GET /api/preflight/safe-access-pilot
```

The response checks required source layers, raw PBF availability, expected workspace ids, whether the active workspace already exists, and a runtime class. This gives the user a short readiness report before starting a background job.

## Main Limitation

Route-aware distance is an OSM road-network proxy. It is stronger than straight-line distance for review prioritization, but it is not verified pedestrian routing and does not prove real-world access conditions.

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
