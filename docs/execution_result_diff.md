# Execution Result Diff

`Execution Result Diff` is the v055 reproducibility layer for reviewer-ready execution evidence packages.

It compares two `Execution Evidence Package` artifacts and summarizes:

- lineage differences;
- profile, dataset, pilot and workspace scope;
- generated workspace table row counts;
- expected and actual output set differences;
- package quality-check differences;
- validation and API contract evidence;
- claim boundaries.

It writes only small JSON and Markdown artifacts under:

```text
analysis_output/georeview_studio_execution_result_diffs
```

It does not copy or mutate source GIS files.

## API

- `GET /api/execution-result-diff`
- `GET /api/execution-result-diff/candidates`
- `POST /api/execution-result-diff/create`
- `GET /api/execution-result-diff/diffs`
- `GET /api/execution-result-diff/diffs/{diff_id}`
- `GET /api/execution-result-diff/diffs/{diff_id}/download`

## Interpretation

`reproducible_match` means the compared package evidence is consistent across the checked table and output dimensions. It is not a real-world safety claim.

The approved wording remains:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```
