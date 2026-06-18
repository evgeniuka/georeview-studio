# Project Rules

- Treat GeoReview Studio as a local-first GIS review workbench for infrastructure risk indicators and data-quality evidence.
- Do not describe outputs as crash prediction or as proof that a location is dangerous.
- Approved wording: `This location has infrastructure risk indicators and should be reviewed on-site.`
- Keep source GIS data read-only. Do not delete, rename, move, or overwrite original GIS inputs.
- Generated analysis artifacts belong under `analysis_output` or the release/workspace directories already documented by the project.
- Do not enable public hosting, deploy, billing, external database, or network-facing settings without explicit approval.
- Do not edit secrets, `.env`, auth/session/capability files, credentials, or local machine identity files.
- Keep `v083_2026-06-01` aligned with `project_manifest.json` and the parent `LATEST.txt`.
- Run or document validation scripts before claiming portfolio readiness.

## Files To Read First

1. `README.md`
2. `project_manifest.json`
3. `.codex/project-profile.md`
4. Parent `LATEST.txt`
5. `docs/` files relevant to the touched backend/frontend area

## Validation Focus

- App version remains `v083`.
- Local URL remains `http://127.0.0.1:8847`.
- Risk-indicator wording stays conservative.
- Validation and API contract summaries are not invented; if not run, say `not run`.
