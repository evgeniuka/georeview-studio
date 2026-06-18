# Portfolio Guide

## One-Sentence Description

GeoReview Studio is a local GIS analytics workbench that converts OSM/Geofabrik data into field-review candidate tables with straight-line and route-aware proxy metrics for pedestrian access infrastructure.

## What To Show

- `portfolio/index.html`: static case-study report.
- `portfolio/assets/kfar_saba_static_map.svg`: visual map preview.
- `portfolio/sample_review_candidates_top20.csv`: exportable review-candidate sample.
- `portfolio/case_study.md`: written project summary.
- `portfolio/portfolio_pitch.md`: short project pitch.
- `analysis_output/georeview_studio_portfolio_reports/*.md`: generated run evidence and run-comparison reports.
- `analysis_output/georeview_studio_portfolio_reports/profile_*.md`: generated profile-workspace evidence reports, starting with Transit Stop Walk Access.
- `analysis_output/georeview_studio_portfolio_reports/profile_compare_*.md`: generated comparison reports across implemented profiles.

## Strong Technical Signals

- real GIS source data;
- reproducible audit outputs;
- canonical data model;
- pilot-area catalog from Geofabrik place polygons;
- background job history for longer selected-pilot builds;
- OSM PBF tag enrichment;
- route-aware road-network proxy analysis;
- generated Markdown/JSON reports from completed analysis runs;
- generated Markdown/JSON reports from profile workspaces;
- generated Markdown/JSON comparison reports across implemented profiles;
- analysis profile registry showing how the product generalizes beyond Safe Access;
- second implemented profile: Transit Stop Walk Access;
- third implemented profile: Park And Playground Access;
- run comparison for reproducibility checks;
- workspace registry;
- dynamic dashboard endpoints;
- local validation script;
- clear separation between infrastructure indicators and data-quality gaps.

## Honest Limitation

The current route-aware analysis is still a mapped OSM road-network proxy. It is useful for prioritization, but it is not verified pedestrian navigation and still needs field review.

Pilot areas are OSM/Geofabrik polygons and should be replaced with official municipal boundaries when the project moves beyond portfolio MVP.

## v023 Portfolio Story

The portfolio story is now broader than a single city analysis: GeoReview Studio is a reusable GIS review workbench, with Safe Access Israel as the first polished profile and Transit/Park profiles proving reuse.

## v024 Portfolio Story

The app now demonstrates a reusable profile result dashboard: one UI table can inspect Safe Access, Transit Access, and Park/Playground Access outputs.

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
