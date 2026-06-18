# Authored Dashboard Contract

v035 promotes authored profile audit outputs into the shared `profile_dashboard_contract_v001` surface.

## What Changed

- Authored audit workspaces are discovered from `analysis_output/georeview_studio_workspaces`.
- The latest workspace for each authored `profile_id` appears in `GET /api/profile-dashboard`.
- `GET /api/profile-dashboard/{profile_id}/summary` works for authored profiles.
- `GET /api/profile-dashboard/{profile_id}/results` returns normalized rows with `primary_score`, `flags`, `data_quality_flags`, `review_wording`, and `source_evidence`.
- Portfolio profile reports and dashboard export bundles can include authored audit profiles.

## Boundary

This does not convert a draft into a domain-specific scoring model. It exposes audit evidence in the same dashboard contract so the profile can be reviewed, exported, and compared before a dedicated runner is built.

- Source GIS files remain read-only.
- Missing OSM tags remain data-quality flags.
- No crash prediction is introduced.
- This location has infrastructure risk indicators and should be reviewed on-site.
