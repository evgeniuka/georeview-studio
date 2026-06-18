# Comparison Map Exports

v050 adds portable side-by-side map exports for the multi-pilot Safe Access workflow.

## Purpose

The feature renders Kfar Saba and Raanana route-aware workspaces into visual evidence that can be opened locally or included in a portfolio walkthrough.

It reads only generated workspace tables:

- `network_access_results.csv`
- `crossings.csv`
- `road_segments.csv`
- `workspace_summary.json`

Source GIS files are not modified.

## API

- `GET /api/comparison-map-exports`
- `POST /api/comparison-map-exports/create`
- `GET /api/comparison-map-exports/exports`
- `GET /api/comparison-map-exports/exports/{export_id}`
- `GET /api/comparison-map-exports/exports/{export_id}/download`

## Outputs

Generated exports are written under:

`D:\cloude_work\georeview-studio\analysis_output\georeview_studio_comparison_map_exports`

Each export contains:

- JSON metadata;
- standalone HTML report;
- one SVG map per pilot;
- `top_review_candidates.csv` for the mapped candidate sample.

## Claim Boundary

The maps show mapped infrastructure review indicators and data-quality context only. They do not label a location and do not predict crashes.

Approved wording:

`This location has infrastructure risk indicators and should be reviewed on-site.`
