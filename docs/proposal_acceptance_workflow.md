# Proposal Acceptance Workflow

v037 adds a manual decision ledger for profile promotion proposals.

## Purpose

Promotion proposals from v036 are useful, but they still need a clear review step before any profile contract config changes. v037 adds that governance layer:

- review queue for promotion proposals;
- approve/reject decisions;
- decision artifacts stored beside each proposal;
- explicit `mutates_config=false` evidence.

## API

- `GET /api/profile-promotion/review-queue`
- `GET /api/profile-promotion/decisions`
- `GET /api/profile-promotion/proposals/{proposal_id}/decision`
- `POST /api/profile-promotion/proposals/{proposal_id}/decision`

## Boundary

Approval here is not an automatic config update. It is evidence that a proposal was reviewed and can be used in a later, explicit implementation task.

- Source GIS files remain read-only.
- `profile_mapper_contracts_v001.json` is not modified automatically.
- Missing OSM tags remain data-quality flags.
- No crash prediction is introduced.
- This location has infrastructure risk indicators and should be reviewed on-site.
