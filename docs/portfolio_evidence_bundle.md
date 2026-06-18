# Shareable Portfolio Evidence Bundle

v044 adds a small shareable evidence bundle for reviewing GeoReview Studio as a portfolio project.

The feature packages generated evidence, not source GIS data:

- project manifest;
- validation summary;
- API contract summary;
- release readiness snapshot;
- guided portfolio demo snapshot;
- portfolio case study;
- portfolio pitch;
- top-20 sample review candidate CSV;
- static SVG map;
- recent report references.

## API

- `GET /api/portfolio-evidence-bundle`
- `POST /api/portfolio-evidence-bundle/create`
- `GET /api/portfolio-evidence-bundle/bundles`
- `GET /api/portfolio-evidence-bundle/bundles/{bundle_id}`
- `GET /api/portfolio-evidence-bundle/bundles/{bundle_id}/download`

Bundles are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_portfolio_evidence_bundles
```

## Policy

The bundle does not copy or mutate source GIS files. It copies only small generated evidence artifacts from the app and `analysis_output`.
