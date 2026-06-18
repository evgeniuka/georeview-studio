# Execution Diff Gallery

`Execution Diff Gallery` is a reviewer-facing index over generated execution result diff artifacts.

It does not inspect or modify source GIS files. It reads existing execution result diff JSON artifacts and writes small JSON/Markdown gallery snapshots under `analysis_output`.

## Purpose

- show how many execution diffs are available;
- separate `reproducible_match` evidence from diffs that need engineering review;
- expose classification, readiness and comparison-scope counts;
- create a compact Markdown artifact that can be shared in a portfolio review;
- preserve the approved field-review wording.

## API

- `GET /api/execution-diff-gallery`
- `GET /api/execution-diff-gallery/items`
- `POST /api/execution-diff-gallery/create`
- `GET /api/execution-diff-gallery/galleries`
- `GET /api/execution-diff-gallery/galleries/{gallery_id}`
- `GET /api/execution-diff-gallery/galleries/{gallery_id}/download`

## Claim Boundary

The gallery is reproducibility and data-engineering evidence. It does not predict crashes and does not prove real-world safety outcomes.

Approved wording remains:

> This location has infrastructure risk indicators and should be reviewed on-site.
