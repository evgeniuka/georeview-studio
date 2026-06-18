# Reproducibility Audit Packet

v058 adds a small reviewer-facing reproducibility audit packet.

The packet does not create new GIS data and does not edit source GIS files. It bundles existing generated evidence from:

- execution diff detail drilldowns;
- execution result diff reports;
- execution diff gallery reports;
- validation summary;
- API contract summary;
- project manifest.

## Purpose

The purpose is to make the portfolio demo easier to review. A reviewer can open one packet and see what was run, which generated outputs were compared, which tables changed, which checks passed and what claim boundaries apply.

## Claim Boundary

The packet supports infrastructure risk indicator review. It is not a crash prediction artifact and it does not prove real-world safety outcomes.

Approved wording stays:

`This location has infrastructure risk indicators and should be reviewed on-site.`

## API

- `GET /api/reproducibility-audit-packet`
- `GET /api/reproducibility-audit-packet/candidates`
- `POST /api/reproducibility-audit-packet/create`
- `GET /api/reproducibility-audit-packet/packets`
- `GET /api/reproducibility-audit-packet/packets/{packet_id}`
- `GET /api/reproducibility-audit-packet/packets/{packet_id}/download`

## Outputs

Output folder:

`analysis_output/georeview_studio_reproducibility_audit_packets`

Each packet contains:

- `packet_manifest.json`
- `packet_summary.md`
- selected diff/detail/gallery Markdown and JSON evidence where available;
- project validation and API summaries.

## Validation

Validation checks that:

- at least one ready candidate exists;
- packet creation returns `ready_for_reviewer`;
- packet manifest and Markdown are resolvable;
- source GIS modified flag remains false;
- generated docs, backend, API routes and UI panel are present.
