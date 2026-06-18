# Profile Promotion Wizard

v036 adds a proposal-only promotion layer for authored profile audits.

## Purpose

The wizard turns a successful authored audit workspace into reviewable contract artifacts:

- `promotion_proposal.json`
- `profile_contract_proposal.json`
- `mapper_contract_patch_preview.json`
- `promotion_report.md`

These files are written under `analysis_output/georeview_studio_profile_promotions`.

## API

- `GET /api/profile-promotion`
- `GET /api/profile-promotion/candidates`
- `GET /api/profile-promotion/candidates/{workspace_id}`
- `POST /api/profile-promotion/propose`
- `GET /api/profile-promotion/proposals`
- `GET /api/profile-promotion/proposals/{proposal_id}`

## Boundary

This wizard does not modify `profile_mapper_contracts_v001.json`. It creates evidence for manual review before a profile contract is changed.

- Source GIS files remain read-only.
- Missing OSM tags remain data-quality flags.
- No crash prediction is introduced.
- This location has infrastructure risk indicators and should be reviewed on-site.
