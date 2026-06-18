# Authored Profile Runner

v034 adds a read-only runner for drafts created by the Template Authoring Wizard.

## Purpose

The runner closes the gap between a draft profile contract and a real domain-specific runner. It executes a draft as a tag and layer evidence audit using the inspected CSV evidence already present under `analysis_output`.

## API

- `GET /api/authored-profile-runner`
- `POST /api/authored-profile-runner/run`
- `GET /api/authored-profile-runner/workspaces`
- `POST /api/execution-queue/enqueue-authored-draft`
- `GET /api/profile-workspaces/{workspace_id}/summary`
- `GET /api/profile-workspaces/{workspace_id}/results`
- `GET /api/profile-workspaces/{workspace_id}/download/authored_profile_results`

## Output Workspace

Each run writes a small profile workspace under `analysis_output/georeview_studio_workspaces`:

- `tables/authored_profile_results.csv`
- `tables/authored_profile_source_evidence.csv`
- `tables/authored_profile_layer_requirements.csv`
- `reports/authored_profile_summary.json`
- `reports/authored_profile_report.md`
- `manifest.json`

## Boundaries

- Source GIS files are read-only.
- Profile mapper config is not modified automatically.
- Missing OSM tags are data-quality flags, not proof that infrastructure is absent.
- This is not crash prediction.
- This location has infrastructure risk indicators and should be reviewed on-site.
