# Repository Export Checklist

`v081` prepares the final local package before manual GitHub sharing. It consumes a ready public repository polish package and creates:

- final repository export checklist;
- screenshot capture pass with repository-relative `docs/screenshots/` paths;
- public repository tree plan;
- README final review notes;
- downloadable ZIP and manifest.

The builder does not publish, deploy, move, rename, delete, or modify source GIS files. It is a local evidence package for manual review.

## API

- `GET /api/repository-export-checklist`
- `POST /api/repository-export-checklist/create`
- `GET /api/repository-export-checklist/checklists`
- `GET /api/repository-export-checklist/checklists/{checklist_id}`
- `GET /api/repository-export-checklist/checklists/{checklist_id}/download`

## Evidence Rules

- Source GIS extracts stay outside the public package.
- Missing OSM tags remain data-quality flags, not automatic risk.
- The approved row wording remains: `This location has infrastructure risk indicators and should be reviewed on-site.`
- Screenshots use repository-relative paths under `docs/screenshots/`.
