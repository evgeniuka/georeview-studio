# Bundle Review Checklist

v045 adds a guided review gate for shareable portfolio evidence bundles.

The checklist evaluates whether a bundle is ready to hand to a reviewer:

- current app and project manifest version;
- release readiness snapshot status;
- validation summary status;
- API contract coverage;
- required copied evidence files;
- portfolio story artifacts;
- approved field-review wording;
- claim boundary;
- source GIS and profile config read-only guarantees;
- small shareable size budget.

Generated checklist files are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_bundle_review_checklists
```

## API

- `GET /api/bundle-review-checklist`
- `POST /api/bundle-review-checklist/create`
- `GET /api/bundle-review-checklist/checklists`
- `GET /api/bundle-review-checklist/checklists/{checklist_id}`
- `GET /api/bundle-review-checklist/checklists/{checklist_id}/download`

The checklist does not inspect or modify source GIS files. It reads generated evidence artifacts and writes only JSON/Markdown checklist reports under `analysis_output`.
