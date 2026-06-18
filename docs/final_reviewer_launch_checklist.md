# Final Reviewer Launch Checklist

v070 adds a final local launch checklist over ready Visual Evidence Sign-Off Packet artifacts.

The feature is intentionally local and read-only with respect to source GIS data. It writes generated JSON, Markdown and HTML checklist artifacts under `analysis_output/georeview_studio_final_reviewer_launch_checklists`.

## Purpose

- turn a ready sign-off packet into a compact reviewer walkthrough checklist;
- list the exact local app URL, evidence downloads and talk-track boundaries;
- keep the approved infrastructure-risk wording visible;
- separate reviewer attention items from absolute safety claims.

## API

- `GET /api/final-reviewer-launch-checklist`
- `POST /api/final-reviewer-launch-checklist/create`
- `GET /api/final-reviewer-launch-checklist/checklists`
- `GET /api/final-reviewer-launch-checklist/checklists/{checklist_id}`
- `GET /api/final-reviewer-launch-checklist/checklists/{checklist_id}/download`

## Claim Boundary

The checklist is a portfolio/demo launch artifact. It does not verify field conditions, predict crashes or make absolute site-safety claims. The approved wording remains:

`This location has infrastructure risk indicators and should be reviewed on-site.`
