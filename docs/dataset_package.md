# Dataset Evidence Packages

GeoReview Studio v033 adds reusable dataset evidence packages.

## Purpose

A package gathers the evidence needed to explain whether a selected local OSM/GIS dataset can support a profile:

- source onboarding readiness;
- local intake plan;
- template authoring draft;
- controlled execution queue job;
- Markdown package report.

## API

- `GET /api/dataset-packages`
- `POST /api/dataset-packages/create`
- `GET /api/dataset-packages/packages`
- `GET /api/dataset-packages/packages/{package_id}`
- `GET /api/dataset-packages/packages/{package_id}/download`

## Boundary

Packages are evidence artifacts. They do not modify source GIS files, deploy anything, predict crashes, or prove real-world conditions. Missing tags remain data-quality flags.
