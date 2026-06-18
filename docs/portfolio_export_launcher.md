# Portfolio Export Launcher

`Portfolio Export Launcher` is the v060 start-here layer for local portfolio review.

It creates one small JSON/Markdown/HTML artifact that links the best reviewer-facing evidence already produced by the app:

- reviewer audit indexes;
- reproducibility audit packets;
- portfolio handoff pages;
- evidence galleries;
- portfolio narratives;
- release readiness snapshots.

## API

- `GET /api/portfolio-export-launcher`
- `POST /api/portfolio-export-launcher/create`
- `GET /api/portfolio-export-launcher/launchers`
- `GET /api/portfolio-export-launcher/launchers/{launcher_id}`
- `GET /api/portfolio-export-launcher/launchers/{launcher_id}/download`

## Output

Generated launcher files are written under:

```text
analysis_output/georeview_studio_portfolio_export_launchers
```

The launcher writes only small review artifacts. It does not mutate source GIS files and it does not change mapper config.

## Claim Boundary

The launcher is a navigation and evidence artifact for infrastructure risk indicators and field-review prioritization. It is not a crash prediction model and it does not claim real-world outcomes.
