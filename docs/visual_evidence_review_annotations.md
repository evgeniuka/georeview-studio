# Visual Evidence Review Annotations

v068 adds a local reviewer annotation layer on top of Visual Evidence Review Diff artifacts.

Purpose:

- read ready visual evidence review diffs;
- create a generated annotation set for every changed or unchanged visual target;
- separate `needs_reviewer_attention` from `accepted_no_action`;
- write JSON, Markdown and HTML evidence under `analysis_output`;
- keep source GIS files read-only.

This is a QA and portfolio-evidence workflow. It reviews generated screenshots and target metadata. It is not field verification and it does not make absolute safety claims.

API:

- `GET /api/visual-evidence-review-annotations`
- `POST /api/visual-evidence-review-annotations/create`
- `GET /api/visual-evidence-review-annotations/annotations`
- `GET /api/visual-evidence-review-annotations/annotations/{annotation_id}`
- `GET /api/visual-evidence-review-annotations/annotations/{annotation_id}/download`

Readiness:

- `ready_for_visual_evidence_annotations` means at least one ready visual evidence review diff is available.
- `ready_for_visual_evidence_annotation_review` means an annotation artifact was created and can be reviewed before sharing a demo.

Claim boundary:

`This location has infrastructure risk indicators and should be reviewed on-site.`

Annotations are generated review notes over visual evidence artifacts. They do not modify source GIS data and do not prove real-world site conditions.
