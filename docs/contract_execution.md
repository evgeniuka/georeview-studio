# Contract Execution Dry Run

GeoReview Studio v029 adds a dry-run execution adapter over the profile mapper contracts.

The purpose is to answer a practical engineering question:

```text
Given this source dataset and profile contract,
which backend runner would execute,
which workspace would be targeted,
what would be written,
and what blocks execution?
```

This is still local-first and read-only for source GIS files. The dry run writes only small JSON/Markdown evidence files under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_contract_execution_dry_runs
```

## Public API

- `GET /api/contract-execution`
- `GET /api/contract-execution/adapters`
- `GET /api/contract-execution/dry-run`
- `POST /api/contract-execution/dry-run`
- `GET /api/contract-execution/dry-runs`
- `GET /api/contract-execution/dry-runs/{dry_run_id}`

## Current Adapter Matrix

- `safe_access_pedestrian_review` -> `WorkspaceRunner.ensure_workspace`
- `transit_stop_walk_access` -> `TransitAccessAnalyzer.ensure_workspace`
- `park_playground_access` -> `ParkPlaygroundAccessAnalyzer.ensure_workspace`
- `cycling_micromobility_access` -> planned runner
- `osm_tag_quality` -> planning-ready audit profile
- `generic_layer_inventory` -> planning-ready inventory profile

## Boundary

This layer does not start public hosting, does not read credentials, does not modify source GIS files, and does not change the claim boundary of the project.
