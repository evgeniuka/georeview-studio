# Testing

## Validation

```powershell
.\scripts\validate.ps1
```

Checks packaged files, source audit outputs, workspaces, portfolio artifacts, and approved wording.

For v024 it also checks Profile Dashboard API/docs, Product Architecture API/docs, and source onboarding refresh/cache, Analysis Profiles list/detail/readiness/plan adapter, Profile Runners, Transit Stop Walk Access profile output, Park And Playground Access profile output, Transit and Park profile portfolio report generation/detail/download, profile comparison report generation/detail/download, Create Analysis planning/start, Analysis Runs list/detail/output/rerun, Portfolio Reports generation/detail/download/compare, the pilot-area catalog, Kfar Saba pilot search, selected-pilot preflight, selected-pilot runner, background job creation/polling/history, route-aware workspace, network graph size, reachable generator count, route-aware candidate enrichment, and the `network-access` API.

## API Contract Tests

```powershell
.\scripts\test_api_contract.ps1
```

Starts the local handler on a temporary port and verifies:

- health endpoint;
- project manifest endpoint;
- source onboarding status, refresh, list, and detail endpoints;
- Analysis Profiles list/detail/readiness/plan endpoints;
- Profile Runners and profile workspace endpoints for Transit and Park profiles;
- Create Analysis plan/start endpoints;
- Analysis Runs list/detail/outputs/download/rerun endpoints;
- Portfolio Reports list/detail/download/generate/profile-workspace/profile-comparison/compare endpoints;
- pilot metadata/search/detail endpoints;
- selected-pilot preflight endpoint;
- job start/detail/history endpoints;
- dashboard summary endpoint;
- candidates endpoint;
- route-aware network-access endpoint;
- missing workspace returns `404`;
- missing dataset returns `404`;
- invalid JSON returns `400`.
- selected-pilot workspace run endpoint.

## v024 Checks

Validation and API contract tests verify the normalized profile dashboard overview, profile summaries, result rows for all three implemented profiles, contract fields, and source read-only evidence.

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


## Release Readiness Dashboard

v042 validation checks the release readiness module, API, UI panel and snapshot artifact flow. API contract coverage includes the release overview, gates, snapshot creation, snapshot list and snapshot detail endpoints.


## Guided Portfolio Demo Walkthrough

v043 validation checks the portfolio demo module, API, UI panel and snapshot artifact flow. API contract coverage includes the demo overview, steps, snapshot creation, snapshot list and snapshot detail endpoints.


## Shareable Portfolio Evidence Bundle

v044 validation checks bundle status, bundle creation, generated evidence copies, detail lookup and Markdown download. API contract coverage includes status, create, list, detail and download endpoints.


## Bundle Review Checklist

v045 validation checks checklist status, checklist creation, generated JSON/Markdown reports, detail lookup and Markdown download. API contract coverage includes status, create, list, detail and download endpoints.


## Portfolio Narrative Export

v046 validation checks narrative status, narrative creation, generated JSON/Markdown reports, detail lookup and Markdown download. API contract coverage includes status, create, list, detail and download endpoints.


## Portfolio Handoff Page

v047 validation checks handoff status, page creation, generated JSON/HTML files, detail lookup and HTML download. API contract coverage includes status, create, list, detail and download endpoints.

## Portfolio Evidence Gallery Testing

v048 validation checks gallery status, page creation, generated JSON/HTML files, detail lookup and HTML download. API contract coverage includes status, create, list, detail and download endpoints.


v049 validation checks multi-pilot comparison status, page creation, generated JSON/Markdown/HTML files, detail lookup and HTML download. API contract coverage includes status, create, list, detail and download endpoints.


v050 validation checks comparison map export status, generated SVG/HTML/CSV files, detail lookup and HTML download. API contract coverage includes status, create, list, detail and download endpoints.


## v051 Checks

Validation and API contract tests cover source import guardrail status, preview, review-packet creation, detail/list/download, and approval-decision endpoints.

## v052 Source Handoff Checks

Validation creates an approved source import request, builds a source handoff, verifies mapper and dry-run ids, confirms the queue job is planned, and checks the Markdown handoff artifact.

## v053 Source Handoff Execution Checks

Validation rejects missing acknowledgement, executes one approved handoff, verifies a succeeded queue job, checks the generated workspace manifest, and downloads the Markdown execution report.
## v054 Execution Evidence Package Checks

Validation creates an execution evidence package from a verified source handoff execution, checks readiness, verifies Markdown output, detail/list/download resolvers, release gates and API contract coverage for six new endpoints.
## v055 Execution Result Diff Checks

Validation creates at least two execution evidence packages, generates an execution result diff, checks Markdown output, detail/list/download resolvers, release gates and API contract coverage for six new endpoints.

## v056 Execution Diff Gallery Tests

Validation and API contract tests cover status, item list, gallery creation, list/detail/download, release gates, docs and UI wiring.

## v057 Execution Diff Detail Tests

Validation and API contract tests cover status, baseline list, inspect, drilldown creation, list/detail/download, release gates, docs and UI wiring.

## v058 Reproducibility Audit Packet Tests

Validation and API contract tests now create a packet from a ready execution diff detail, resolve list/detail/download endpoints, and verify that release readiness includes packet gates.

## v059 Reviewer Audit Index Tests

Validation and API contract tests now create a reviewer audit index, resolve list/detail/download endpoints, and verify release readiness gates for the index.

## v060 Portfolio Export Launcher Tests

- Adds `backend/portfolio_export_launcher.py`.
- Adds `docs/portfolio_export_launcher.md`.
- Adds `/api/portfolio-export-launcher` status, create, list, detail and download routes.
- Adds a dashboard panel that creates a start-here reviewer launcher over audit indexes, audit packets and portfolio evidence.
- Keeps source GIS files read-only and writes only small launcher evidence under `analysis_output`.

## v061 Portable Release Package Tests

- Adds `backend/portable_release_package.py`.
- Adds `docs/portable_release_package.md`.
- Adds `/api/portable-release-package` status, create, list, detail and ZIP download routes.
- Adds a dashboard panel that creates a small reviewer-ready ZIP from launcher and evidence artifacts.
- Excludes source GIS files and writes generated packages only under `analysis_output`.

## v062 Demo Script Pack Tests

- Adds `backend/demo_script_pack.py`.
- Adds `docs/demo_script_pack.md`.
- Adds `/api/demo-script-pack` status, create, list, detail and Markdown download routes.
- Adds a dashboard panel that creates a repeatable walkthrough script, screenshot smoke plan and contact sheet.
- Keeps source GIS files read-only and writes only generated demo evidence under `analysis_output`.
