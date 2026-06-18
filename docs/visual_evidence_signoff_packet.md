# Visual Evidence Sign-Off Packet

v069 adds a final local sign-off packet over generated visual evidence annotations.

Purpose:

- read ready Visual Evidence Review Annotation artifacts;
- summarize annotation targets, attention-required rows and accepted/no-action rows;
- attach validation and API contract evidence;
- create a reviewer checklist for local portfolio sharing;
- write JSON, Markdown and HTML under `analysis_output`.

API:

- `GET /api/visual-evidence-signoff-packet`
- `POST /api/visual-evidence-signoff-packet/create`
- `GET /api/visual-evidence-signoff-packet/packets`
- `GET /api/visual-evidence-signoff-packet/packets/{packet_id}`
- `GET /api/visual-evidence-signoff-packet/packets/{packet_id}/download`

Claim boundary:

`This location has infrastructure risk indicators and should be reviewed on-site.`

The sign-off packet is local portfolio QA evidence. It is not field verification, crash prediction, or an absolute site-condition claim. Source GIS files remain read-only.
