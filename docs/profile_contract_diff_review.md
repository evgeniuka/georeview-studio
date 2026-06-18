# Profile Contract Diff Review

v039 adds a review artifact between profile promotion proposals and any later config-change task.

## Purpose

The diff review compares the current `profile_mapper_contracts_v001.json` contract with the promoted contract proposal. It separates:

- added fields;
- removed fields;
- changed fields;
- unchanged fields;
- priority fields that deserve manual review.

## API

- `GET /api/profile-promotion/diff-candidates`
- `POST /api/profile-promotion/contract-diff`
- `GET /api/profile-promotion/contract-diffs`
- `GET /api/profile-promotion/contract-diffs/{diff_id}`

## Output Policy

Generated files are written under `analysis_output/georeview_studio_profile_promotions`.

The workflow does not modify source GIS files and does not modify `profile_mapper_contracts_v001.json`. A separate explicit task is still required for any config change.

## Review Use

Use the diff before approving implementation work:

1. Confirm the operation is `append_contract` or `replace_contract`.
2. Review `required_layers`, `required_tags`, `output_schema`, `claim_boundaries`, `missing_data_policy`, and `implementation_entrypoint`.
3. Confirm missing OSM tags remain data-quality flags.
4. Keep the approved wording: This location has infrastructure risk indicators and should be reviewed on-site.
