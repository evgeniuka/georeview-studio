# OSM Tag Quality Runner

GeoReview Studio v030 adds a read-only `osm_tag_quality` profile runner.

## Inputs

- `analysis_output/osm_tag_counts.csv`
- `analysis_output/layer_summary.csv`

The runner does not read or modify source GIS files directly. It converts already inspected audit CSV evidence into a small profile workspace.

## Outputs

Default workspace:

`analysis_output/georeview_studio_workspaces/osm_tag_quality_kfar_saba_v001`

Generated files:

- `tables/tag_quality_summary.csv`
- `tables/tag_presence_summary.csv`
- `tables/source_scope_summary.csv`
- `reports/workspace_summary.json`
- `reports/tag_quality_report.md`
- `manifest.json`

## API

- `GET /api/osm-tag-quality`
- `GET /api/osm-tag-quality/summary`
- `GET /api/osm-tag-quality/results?limit=50`
- `POST /api/profile-runners/osm_tag_quality/run`
- `GET /api/profile-workspaces/{workspace_id}/summary`
- `GET /api/profile-workspaces/{workspace_id}/results`
- `GET /api/profile-workspaces/{workspace_id}/download/tag_quality_summary`

## Claim Boundary

This profile reports OSM tag coverage and source schema limitations. Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.
