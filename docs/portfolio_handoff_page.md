# Portfolio Handoff Page

v047 renders a ready portfolio narrative into a compact standalone local HTML page.

The page includes:

- project positioning;
- release and evidence metrics;
- narrative sections;
- approved claim boundary;
- reviewer talk track;
- source/config read-only evidence.

Generated handoff pages are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_portfolio_handoff_pages
```

## API

- `GET /api/portfolio-handoff-page`
- `POST /api/portfolio-handoff-page/create`
- `GET /api/portfolio-handoff-page/pages`
- `GET /api/portfolio-handoff-page/pages/{page_id}`
- `GET /api/portfolio-handoff-page/pages/{page_id}/download`

The handoff page reads generated narrative evidence and writes only JSON/HTML artifacts under `analysis_output`. It does not inspect or modify source GIS files and does not mutate profile mapper config.
