# Architecture

GeoReview Studio v024 is a local-first web workbench.

## Runtime

- Backend: Python standard library HTTP server.
- Analysis runs runtime: Python standard library read model over durable job records and workspace manifests.
- Analysis profile runtime: Python standard library capability registry over source onboarding, pilot catalog, and preflight evidence.
- Profile runner runtime: Python standard library profile adapters over generated workspace CSV outputs.
- Portfolio report runtime: Python standard library report builder over analysis runs, profile workspace manifests, and workspace outputs.
- Analysis workflow runtime: Python standard library orchestration over onboarding, preflight, jobs, and dashboard workspaces.
- Source onboarding runtime: Python standard library file scan plus ZIP/DBF/SHP/GPKG/GeoJSON metadata readers.
- Preflight runtime: Python standard library metadata checks before selected-pilot jobs.
- Job runtime: Python standard library background threads with JSON run records.
- Pilot catalog runtime: Python standard library DBF/SHP header reader for Geofabrik place polygons.
- GIS mapper runtime: QGIS Python for `geopandas`, `pyogrio`, `shapely`, and GDAL.
- Route-aware runtime: Python standard library graph analysis over generated CSV/WKT road geometry.
- Frontend: static HTML, CSS, and JavaScript.
- Storage: generated CSV/JSON/Markdown files under `analysis_output`.

## Main Components

- `backend/app.py`: local API server and static file server.
- `backend/analysis_profiles.py`: generic profile registry, readiness checks, runner status, and profile plan adapter.
- `backend/transit_access_analyzer.py`: Transit Stop Walk Access profile runner from route-aware Safe Access workspace outputs.
- `backend/park_playground_access_analyzer.py`: Park And Playground Access profile runner from route-aware Safe Access workspace outputs.
- `backend/analysis_runs.py`: product-level analysis run registry, output links, and rerun payloads.
- `backend/portfolio_report_builder.py`: Markdown/JSON report generation from inspected run evidence, profile workspaces, profile comparison, and run comparison.
- `backend/analysis_workflow.py`: Create Analysis orchestration and readiness plan.
- `backend/source_onboarding.py`: read-only local GIS source scan, lightweight profiles, readiness, and blockers.
- `backend/preflight.py`: selected-pilot readiness checks from catalog metadata and workspace manifests.
- `backend/run_job_manager.py`: background jobs and durable run history.
- `backend/pilot_area_catalog.py`: pilot-area catalog from Geofabrik place polygons.
- `backend/workspace_runner.py`: workspace registry and runner orchestration.
- `backend/generic_safe_access_mapper.py`: Geofabrik ZIP plus OSM PBF mapper.
- `backend/route_network_analyzer.py`: OSM road-network proxy shortest-path analysis.
- `frontend/static/`: dashboard UI.
- `tests/validate_app.py`: validation gate for local artifacts and API logic.

## Data Flow

1. Local source inventory is read from audit CSVs.
2. Source onboarding can refresh a read-only scan of `maps`, excluding `analysis_output`, and cache lightweight source profiles.
3. The pilot catalog reads `gis_osm_places_a_free_1` read-only and caches selectable AOIs.
4. Preflight checks the selected dataset, required layers, PBF availability, workspace ids, and existing workspace state.
5. Analysis Profiles evaluates which product profiles can be planned or run for the selected source and pilot.
6. Profile Runners can execute implemented profiles, currently Safe Access, Transit Stop Walk Access, and Park And Playground Access.
7. Create Analysis combines source readiness, pilot metadata, preflight, and job payload into one plan.
8. The selected analysis job API creates a durable run record and executes the mapper in a background thread.
9. The mapper reads source GIS files read-only.
10. Generated canonical tables are written into a workspace folder.
11. The route analyzer derives `network_access_results.csv` from the PBF-enriched workspace.
12. The transit analyzer derives bus-stop review outputs from the route-aware workspace.
13. The park/playground analyzer derives public-space review outputs from the route-aware workspace.
14. Analysis Runs derives product-visible run history and output links from durable job records and workspace manifests.
15. Portfolio Reports converts selected runs and profile workspaces into compact Markdown/JSON evidence packages, profile comparisons, and run comparisons.
16. The dashboard API reads selected workspace tables and run-history records.
17. The frontend renders metrics, map points, filters, candidate tables, source onboarding, analysis profiles, profile runners, analysis plan, analysis runs, portfolio reports, preflight status, and job status.

## Current Boundary

This is not yet a production FastAPI/PostGIS app. It is a local portfolio-grade prototype with a clean path toward that architecture.

## Product Architecture Layer

v023 adds `backend/product_architecture.py` and the `/api/product-architecture` endpoints. This layer turns the existing Safe Access, Transit and Park profile work into a clear Universal GIS Review Studio architecture with current evidence, pipeline stages, top product options, intake strategy and roadmap.

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


## Release Readiness Layer

v042 adds `backend/release_readiness.py` and `/api/release-readiness` endpoints. This layer does not run a new GIS analysis. It aggregates existing evidence into gates that are useful before a local portfolio demo: manifest version, roadmap, source read-only policy, approved wording, profile outputs, scoring audit, profile contracts, promotion lifecycle, validation and API contract summaries.


## Guided Portfolio Demo Layer

v043 adds `backend/portfolio_demo.py` and `/api/portfolio-demo` endpoints. This layer does not perform a new GIS analysis. It organizes existing evidence into an ordered local demo narrative: product positioning, data intake evidence, Safe Access review outputs, reusable profile expansion, quality gates, reports and roadmap.


## Shareable Portfolio Evidence Bundle Layer

v044 adds `backend/portfolio_evidence_bundle.py` and `/api/portfolio-evidence-bundle` endpoints. This layer packages generated evidence artifacts into a small review folder: readiness snapshot, guided demo snapshot, validation/API summaries, case study, pitch, sample CSV, static map and report references.


## Bundle Review Checklist

v045 adds `backend/bundle_review_checklist.py` and `/api/bundle-review-checklist` endpoints. This layer reviews the generated portfolio evidence bundle for current release metadata, validation/API evidence, copied artifact integrity, claim boundary and read-only guarantees before sharing the project as a portfolio artifact.


## Portfolio Narrative Export

v046 adds `backend/portfolio_narrative_export.py` and `/api/portfolio-narrative-export` endpoints. This layer converts a checked evidence bundle into a concise reviewer-facing narrative with positioning, data evidence, analytics, engineering quality, claim boundary, talk track and handoff guidance.


## Portfolio Handoff Page

v047 adds `backend/portfolio_handoff_page.py` and `/api/portfolio-handoff-page` endpoints. This layer renders a ready narrative export as a standalone local HTML page for portfolio review, while preserving source GIS read-only and config non-mutation guarantees.

## Portfolio Evidence Gallery

v048 adds `backend/portfolio_evidence_gallery.py` and `/api/portfolio-evidence-gallery` endpoints. This layer indexes generated handoff pages, narratives, bundles, checklists and portfolio reports into one standalone local HTML gallery while preserving source GIS read-only and config non-mutation guarantees.


v049 adds `backend/multi_pilot_comparison.py` and `/api/multi-pilot-comparison` endpoints. This layer compares Kfar Saba and Raanana route-aware Safe Access workspaces through the same canonical evidence contract while preserving source GIS read-only guarantees.


v050 adds `backend/comparison_map_exports.py` and `/api/comparison-map-exports` endpoints. This layer renders route-aware pilot comparison workspaces into portable SVG, HTML and CSV map evidence while preserving source GIS read-only guarantees.


## v051 Source Import Guardrails

`v051` adds a metadata-only manual approval gate between local intake and any future source handoff. It creates review packets and decision records under `analysis_output` without mutating source GIS files or config.

## v052 Source Handoff

Approved source handoff connects manual source-import approval to profile mapper plans, contract dry-runs and planned queue jobs without running analytics or modifying source GIS files.

## v053 Source Handoff Execution

Controlled handoff execution adds an explicit acknowledgement gate, runs an approved handoff through the controlled queue, and compares generated workspace tables with mapper-plan evidence.
## v054 Execution Evidence Package

The v054 layer packages a verified source handoff execution into reviewer-ready JSON and Markdown evidence. It links approved source review, controlled queue execution, generated workspace outputs, handoff comparison checks, validation summaries and claim boundaries without mutating source GIS files.
## v055 Execution Result Diff

The v055 layer compares reviewer-ready execution evidence packages. It supports repeat-run reproducibility checks and cross-profile/cross-pilot review prompts by diffing lineage, generated workspace table rows, output sets, quality checks and release evidence.

## v056 Execution Diff Gallery

The architecture now includes `execution_diff_gallery`, a non-mutating reviewer layer that indexes execution result diff artifacts by classification, readiness, scope and review priority.

## v057 Execution Diff Detail

The architecture now includes `execution_diff_detail`, a non-mutating drilldown layer that selects baseline diffs and exposes table/output/quality evidence for reproducibility review.

## v058 Reproducibility Audit Packet

The architecture now includes `reproducibility_audit_packet`, a non-mutating evidence layer that copies small generated diff/detail/gallery artifacts plus release summaries into one packet folder for reviewer inspection.

## v059 Reviewer Audit Index

The architecture now includes `reviewer_audit_index`, a non-mutating navigation layer over ready audit packets and portfolio evidence links.

## v060 Portfolio Export Launcher

- Adds `backend/portfolio_export_launcher.py`.
- Adds `docs/portfolio_export_launcher.md`.
- Adds `/api/portfolio-export-launcher` status, create, list, detail and download routes.
- Adds a dashboard panel that creates a start-here reviewer launcher over audit indexes, audit packets and portfolio evidence.
- Keeps source GIS files read-only and writes only small launcher evidence under `analysis_output`.

## v061 Portable Release Package

- Adds `backend/portable_release_package.py`.
- Adds `docs/portable_release_package.md`.
- Adds `/api/portable-release-package` status, create, list, detail and ZIP download routes.
- Adds a dashboard panel that creates a small reviewer-ready ZIP from launcher and evidence artifacts.
- Excludes source GIS files and writes generated packages only under `analysis_output`.

## v062 Demo Script Pack

- Adds `backend/demo_script_pack.py`.
- Adds `docs/demo_script_pack.md`.
- Adds `/api/demo-script-pack` status, create, list, detail and Markdown download routes.
- Adds a dashboard panel that creates a repeatable walkthrough script, screenshot smoke plan and contact sheet.
- Keeps source GIS files read-only and writes only generated demo evidence under `analysis_output`.
