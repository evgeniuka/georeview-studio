# GitHub-ready Publication Bundle

GeoReview Studio v074 adds a publication layer over the Demo Review Playbook.

## Purpose

The bundle prepares small, reviewer-facing files that can be moved into a public portfolio repository:

- public README export;
- portfolio case study;
- repository file manifest;
- publication checklist;
- standalone HTML overview;
- ZIP package without source GIS data.

## Inputs

- A ready Demo Review Playbook.
- `validation_summary.json`.
- `api_contract_summary.json`.
- `project_manifest.json`.

## Outputs

- `github_publication_bundle_manifest.json`
- `README_public.md`
- `PORTFOLIO_CASE_STUDY.md`
- `REPOSITORY_FILE_MANIFEST.md`
- `github_publication_bundle.html`
- `github_publication_bundle.zip`
- `latest_github_publication_bundle.json`

## API

- `GET /api/github-publication-bundle`
- `POST /api/github-publication-bundle/create`
- `GET /api/github-publication-bundle/bundles`
- `GET /api/github-publication-bundle/bundles/{bundle_id}`
- `GET /api/github-publication-bundle/bundles/{bundle_id}/download`

## Claim Boundary

`This location has infrastructure risk indicators and should be reviewed on-site.`

The ZIP excludes source GIS data. Missing OSM tags remain data-quality flags, not proof of real-world absence.
