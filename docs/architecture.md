# Architecture

GeoReview Studio is a local-first web workbench.

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
- `backend/review_decisions.py`: per-candidate reviewer decisions (status / note / assignee) in a local SQLite store.
- `backend/postgis_backend.py`: planning-only PostGIS migration option (target schema + migration plan; opens no database connection).
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

This is not yet a production FastAPI/PostGIS app. It is a local portfolio-grade prototype with a clean path toward that architecture. A planning-only PostGIS option ships today — `backend/postgis_backend.py` with `config/postgis_schema_v001.sql` and the `/api/postgis-backend` endpoints (status, schema, migration-plan, plans, plan detail) — which produces a target schema and migration plan without opening a database connection, reading credentials, or modifying source GIS files.

## Evolution

Between v023 and v062 the app accreted a large internal publication / QA / release-readiness tooling layer — product-architecture, release-readiness, portfolio evidence bundles and narratives, execution-diff and visual-evidence audit chains, export launchers and demo packs — each documented as its own version section here. The **Cut A** subtraction (2026-06) removed ~38 of those self-referential modules to keep the analysis product reviewable; the full pre-cut tree is preserved on the `archive/full-app-2026-06-25` branch. The source-import → handoff governance workflow, the profile mapper/promotion pipeline, and the PostGIS planning option survived the cut and remain live, while the Main Components list above stays focused on the analysis core.
