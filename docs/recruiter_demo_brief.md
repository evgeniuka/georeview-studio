# Recruiter-Facing Demo Brief

v071 adds a compact one-page portfolio brief over ready Final Reviewer Launch Checklist artifacts.

The brief is meant for a technical recruiter or reviewer who needs the project story quickly:

- what GeoReview Studio does;
- what data was inspected;
- what the Kfar Saba MVP proves as an engineering artifact;
- which claim boundaries must be respected;
- which validation, API and launch evidence can be opened during a demo.

The approved wording remains:

`This location has infrastructure risk indicators and should be reviewed on-site.`

## API

- `GET /api/recruiter-demo-brief`
- `POST /api/recruiter-demo-brief/create`
- `GET /api/recruiter-demo-brief/briefs`
- `GET /api/recruiter-demo-brief/briefs/{brief_id}`
- `GET /api/recruiter-demo-brief/briefs/{brief_id}/download`

## Outputs

Generated files are written under:

`D:\cloude_work\georeview-studio\analysis_output\georeview_studio_recruiter_demo_briefs`

Each brief contains:

- JSON manifest;
- Markdown one-page brief;
- HTML reviewer page.

Source GIS files remain read-only.
