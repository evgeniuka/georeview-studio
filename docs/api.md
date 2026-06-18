# API

## Health

- `GET /api/health`

## Manifest

- `GET /api/project-manifest`

## Product Architecture

- `GET /api/product-architecture`
- `GET /api/product-architecture/variants`
- `GET /api/product-architecture/roadmap`
- `POST /api/product-architecture/implementation-plan`

Product Architecture exposes the recommended portfolio direction, top project variants, current implementation evidence, reusable pipeline, canonical tables, intake strategy, roadmap, and validation gates. It does not write GIS outputs and reports `source_gis_modified=false`.

## Catalog

- `GET /api/catalog/sources`
- `GET /api/catalog/sources/{dataset_id}`

Missing dataset IDs return `404`.

## Source Onboarding

- `GET /api/source-onboarding`
- `GET /api/source-onboarding/sources`
- `GET /api/source-onboarding/sources/{dataset_id}`
- `POST /api/source-onboarding/refresh`

Source onboarding scans the local `maps` folder read-only, excludes `analysis_output`, profiles compatible GIS files, and writes a small derived JSON/CSV cache under `analysis_output/georeview_studio_source_onboarding`.

## Templates

- `GET /api/templates`
- `GET /api/templates/{template_id}/check?dataset_id={dataset_id}`

## Profile Dashboard

- `GET /api/profile-dashboard`
- `GET /api/profile-dashboard/profiles`
- `GET /api/profile-dashboard/{profile_id}/summary`
- `GET /api/profile-dashboard/{profile_id}/results?limit={n}&min_score={score}&only_flags=false`

Profile Dashboard normalizes implemented profile outputs into one result-row contract for Safe Access, Transit Access, and Park/Playground Access. It is the API used by the v024 profile selector UI.

## Analysis Profiles

- `GET /api/analysis-profiles?dataset_id={dataset_id}&pilot_osm_id={osm_id}&route_aware=true`
- `GET /api/analysis-profiles/{profile_id}`
- `GET /api/analysis-profiles/{profile_id}/readiness`
- `POST /api/analysis-profiles/{profile_id}/plan`

Analysis Profiles are the product-level registry for reusable GIS analytics. They expose profile metadata, input needs, output expectations, runner status, readiness, blockers, and source-data evidence. `safe_access_pedestrian_review` is the implemented profile. Other profiles are explicit roadmap profiles with readiness evidence but no runner yet.

## Profile Runners

- `GET /api/profile-runners`
- `POST /api/profile-runners/{profile_id}/run`
- `GET /api/profile-workspaces`
- `GET /api/profile-workspaces/{workspace_id}/summary`
- `GET /api/profile-workspaces/{workspace_id}/results`
- `GET /api/profile-workspaces/{workspace_id}/download/{output_id}`

Profile Runners execute implemented profile adapters. `transit_stop_walk_access` creates `transit_stop_access_results.csv`, `transit_stop_access_top20.csv`, and transit summary reports from the existing route-aware Safe Access workspace. `park_playground_access` creates `park_playground_access_results.csv`, `park_playground_access_top20.csv`, and public-space summary reports from the same route-aware workspace.

## Workspace Registry

- `GET /api/workspace-registry`
- `GET /api/workspace-registry/{workspace_id}`

Missing workspace IDs return `404`.

## Pilot Areas

- `GET /api/pilot-areas/metadata`
- `GET /api/pilot-areas?q={text}&limit={n}`
- `GET /api/pilot-areas/{osm_id}`

The pilot catalog is generated from the Geofabrik `gis_osm_places_a_free_1` polygon layer and cached as a small CSV under `analysis_output`.

## Preflight

- `GET /api/preflight/safe-access-pilot?pilot_osm_id={osm_id}&dataset_id={dataset_id}&route_aware=true`
- `POST /api/preflight/safe-access-pilot`

Preflight checks selected-pilot readiness before a long job starts. It reports required layer presence, PBF enrichment availability, derived workspace ids, existing workspace status, runtime class, warnings, and `can_start_job`. It uses metadata and workspace manifests only.

## Analysis Workflow

- `GET /api/analysis-workflow/plan?dataset_id={dataset_id}&pilot_osm_id={osm_id}&template_id=safe_access&route_aware=true`
- `POST /api/analysis-workflow/plan`
- `POST /api/analysis-workflow/start`

The workflow API combines source onboarding readiness, selected pilot metadata, Safe Access preflight, a job payload, and active dashboard workspace into one plan. `start` returns `202` with a background `job_id` when the plan can start.

## Analysis Runs

- `GET /api/analysis-runs?limit={n}`
- `GET /api/analysis-runs/{run_id}`
- `GET /api/analysis-runs/{run_id}/outputs`
- `GET /api/analysis-runs/{run_id}/outputs/{output_id}`
- `POST /api/analysis-runs/{run_id}/rerun`

Analysis Runs expose product-level history over durable job records: inputs, status, active workspace, dashboard links, downloadable CSV/JSON outputs, and rerun support.

## Portfolio Reports

- `GET /api/portfolio-reports?limit={n}`
- `GET /api/portfolio-reports/{report_id}`
- `GET /api/portfolio-reports/{report_id}/download`
- `POST /api/portfolio-reports/from-run`
- `POST /api/portfolio-reports/from-profile-workspace`
- `POST /api/portfolio-reports/profile-comparison`
- `POST /api/portfolio-reports/compare`

`from-run` accepts `{ "run_id": "..." }` and writes a compact Markdown/JSON report under `analysis_output/georeview_studio_portfolio_reports`. `from-profile-workspace` accepts workspace IDs such as `transit_stop_walk_access_kfar_saba_v001` or `park_playground_access_kfar_saba_v001` and writes profile-level evidence with `profile_id`, profile counts, top flags, outputs, and a top candidate sample. `compare` accepts `{ "run_ids": ["...", "..."] }` and writes a run comparison report. Reports are generated from run detail, profile workspace manifests, workspace summaries, output lists, and small CSV samples.

`profile-comparison` accepts optional `base_workspace_id` and `profile_workspace_ids`. With an empty body, it ensures the default Transit and Park profile workspaces exist and writes a comparison report for Safe Access, Transit Access, and Park And Playground Access.

## Jobs

- `POST /api/jobs/safe-access-pilot`
- `GET /api/jobs?limit={n}`
- `GET /api/jobs/{job_id}`

The job API returns immediately with a `job_id`, writes durable JSON status records under `analysis_output/georeview_studio_runs`, and supports polling for long selected-pilot builds.

## Dashboard Workspaces

- `GET /api/dashboard-workspaces`
- `GET /api/dashboard-workspaces/{workspace_id}/summary`
- `GET /api/dashboard-workspaces/{workspace_id}/candidates`
- `GET /api/dashboard-workspaces/{workspace_id}/network-access`
- `GET /api/dashboard-workspaces/{workspace_id}/map-features`
- `GET /api/dashboard-workspaces/{workspace_id}/validation`

`network-access` is available for workspaces that contain `network_access_results.csv`, especially `safe_access_kfar_saba_route_aware_v001`.

## Runs

- `POST /api/runs/safe-access-kfar-saba`
- `POST /api/runs/safe-access-generic`
- `POST /api/runs/route-aware-kfar-saba`
- `POST /api/runs/safe-access-pilot`

Invalid JSON bodies return `400`.

`route-aware-kfar-saba` creates or returns `safe_access_kfar_saba_route_aware_v001`. It does not modify source GIS files.

`safe-access-pilot` accepts `pilot_osm_id`, optional `workspace_id`, optional `route_workspace_id`, and `route_aware`. It reuses the generic mapper and then optionally creates route-aware network proxy outputs.

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

## Profile Mapper SDK

- `GET /api/profile-mapper` returns contract overview, validation summary, canonical result fields, and SDK status.
- `GET /api/profile-mapper/contracts` returns full profile mapper contracts.
- `GET /api/profile-mapper/contracts/{profile_id}` returns one contract.
- `GET /api/profile-mapper/compatibility` checks all contracts against the default local source.
- `GET /api/profile-mapper/plan` previews a mapper plan.
- `POST /api/profile-mapper/plan` writes a small JSON/Markdown mapper plan under `analysis_output`.
- `GET /api/profile-mapper/plans` lists generated mapper plans.
- `GET /api/profile-mapper/plans/{plan_id}` returns one mapper plan.

## Contract Execution

- `GET /api/contract-execution` returns execution adapter status and policy.
- `GET /api/contract-execution/adapters` returns the adapter matrix.
- `GET /api/contract-execution/dry-run` previews dry-run execution for a profile contract.
- `POST /api/contract-execution/dry-run` writes a small dry-run evidence package under `analysis_output`.
- `GET /api/contract-execution/dry-runs` lists generated dry runs.
- `GET /api/contract-execution/dry-runs/{dry_run_id}` returns one dry run.


## Release Readiness

- `GET /api/release-readiness`
- `GET /api/release-readiness/gates`
- `POST /api/release-readiness/snapshot`
- `GET /api/release-readiness/snapshots`
- `GET /api/release-readiness/snapshots/{snapshot_id}`

Release Readiness summarizes local demo gates across manifest, roadmap, source read-only evidence, approved wording, profile outputs, scoring audit, mapper contracts, promotion lifecycle, validation and API contract evidence. Snapshot endpoints write small JSON/Markdown artifacts under `analysis_output`.


## Portfolio Demo

- `GET /api/portfolio-demo`
- `GET /api/portfolio-demo/steps`
- `POST /api/portfolio-demo/snapshot`
- `GET /api/portfolio-demo/snapshots`
- `GET /api/portfolio-demo/snapshots/{snapshot_id}`

Portfolio Demo returns an ordered walkthrough for presenting product positioning, inspected data, Safe Access outputs, reusable profile expansion, quality gates, exportable reports and next roadmap steps. Snapshot endpoints write small JSON/Markdown artifacts under `analysis_output`.


## Portfolio Evidence Bundle

- `GET /api/portfolio-evidence-bundle`
- `POST /api/portfolio-evidence-bundle/create`
- `GET /api/portfolio-evidence-bundle/bundles`
- `GET /api/portfolio-evidence-bundle/bundles/{bundle_id}`
- `GET /api/portfolio-evidence-bundle/bundles/{bundle_id}/download`

Portfolio Evidence Bundle creates a small generated review folder with JSON/Markdown manifest and copied generated evidence files. It does not copy source GIS data.


## Bundle Review Checklist

- `GET /api/bundle-review-checklist`
- `POST /api/bundle-review-checklist/create`
- `GET /api/bundle-review-checklist/checklists`
- `GET /api/bundle-review-checklist/checklists/{checklist_id}`
- `GET /api/bundle-review-checklist/checklists/{checklist_id}/download`

Bundle Review Checklist evaluates a generated evidence bundle and returns pass/warning/failed checks plus remediation actions. It writes small JSON/Markdown checklist reports under `analysis_output`.


## Portfolio Narrative Export

- `GET /api/portfolio-narrative-export`
- `POST /api/portfolio-narrative-export/create`
- `GET /api/portfolio-narrative-export/narratives`
- `GET /api/portfolio-narrative-export/narratives/{narrative_id}`
- `GET /api/portfolio-narrative-export/narratives/{narrative_id}/download`

Portfolio Narrative Export creates a concise reviewer-facing case-study package from the latest checked evidence bundle. It writes small JSON/Markdown narrative reports under `analysis_output`.


## Portfolio Handoff Page

- `GET /api/portfolio-handoff-page`
- `POST /api/portfolio-handoff-page/create`
- `GET /api/portfolio-handoff-page/pages`
- `GET /api/portfolio-handoff-page/pages/{page_id}`
- `GET /api/portfolio-handoff-page/pages/{page_id}/download`

Portfolio Handoff Page renders the latest ready narrative export as a standalone local HTML page and writes JSON/HTML artifacts under `analysis_output`.

## Portfolio Evidence Gallery

- `GET /api/portfolio-evidence-gallery`
- `POST /api/portfolio-evidence-gallery/create`
- `GET /api/portfolio-evidence-gallery/galleries`
- `GET /api/portfolio-evidence-gallery/galleries/{gallery_id}`
- `GET /api/portfolio-evidence-gallery/galleries/{gallery_id}/download`
