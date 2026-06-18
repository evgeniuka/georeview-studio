# Execution Diff Detail

`Execution Diff Detail` adds a baseline selector and drilldown layer above execution result diffs and the execution diff gallery.

It reads existing diff artifacts, ranks baseline candidates, inspects table/output/quality-check evidence, and writes small JSON/Markdown drilldown artifacts under `analysis_output`.

## Purpose

- choose a reproducibility baseline diff;
- inspect table row deltas and output-set deltas;
- expose quality-check and validation evidence;
- generate reviewer-ready drilldown artifacts;
- keep source GIS data read-only.

## API

- `GET /api/execution-diff-detail`
- `GET /api/execution-diff-detail/baselines`
- `GET /api/execution-diff-detail/inspect`
- `POST /api/execution-diff-detail/create`
- `GET /api/execution-diff-detail/drilldowns`
- `GET /api/execution-diff-detail/drilldowns/{detail_id}`
- `GET /api/execution-diff-detail/drilldowns/{detail_id}/download`

## Claim Boundary

The drilldown is reproducibility and data-engineering evidence. It does not predict crashes and does not prove real-world safety outcomes.

Approved wording remains:

> This location has infrastructure risk indicators and should be reviewed on-site.
