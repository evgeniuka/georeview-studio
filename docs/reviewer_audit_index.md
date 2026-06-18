# Reviewer Audit Index

v059 adds a reviewer-facing audit index.

The index collects:

- reproducibility audit packets;
- portfolio handoff pages;
- portfolio evidence galleries;
- portfolio narrative exports;
- release readiness snapshots;
- validation and API contract status.

## Purpose

The purpose is reviewer navigation. Instead of asking a reviewer to browse multiple folders, the app can produce one Markdown/JSON/HTML index that points to the strongest generated evidence.

## Claim Boundary

The index is portfolio and engineering evidence for infrastructure risk indicator review. It is not a crash prediction artifact and does not claim real-world safety outcomes.

Approved wording:

`This location has infrastructure risk indicators and should be reviewed on-site.`

## API

- `GET /api/reviewer-audit-index`
- `POST /api/reviewer-audit-index/create`
- `GET /api/reviewer-audit-index/indexes`
- `GET /api/reviewer-audit-index/indexes/{index_id}`
- `GET /api/reviewer-audit-index/indexes/{index_id}/download`

## Outputs

Output folder:

`analysis_output/georeview_studio_reviewer_audit_indexes`

Each index contains:

- JSON manifest;
- Markdown reviewer index;
- HTML reviewer index;
- links to generated evidence artifacts.
