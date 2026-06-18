# Portfolio Narrative Export

v046 turns a checked evidence bundle into a concise reviewer-facing portfolio narrative.

The export includes:

- project positioning;
- inspected data evidence;
- analytics and profile evidence;
- engineering quality evidence;
- approved claim boundary;
- reviewer walkthrough order;
- short talk track;
- JSON and Markdown outputs.

Generated narrative files are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_portfolio_narratives
```

## API

- `GET /api/portfolio-narrative-export`
- `POST /api/portfolio-narrative-export/create`
- `GET /api/portfolio-narrative-export/narratives`
- `GET /api/portfolio-narrative-export/narratives/{narrative_id}`
- `GET /api/portfolio-narrative-export/narratives/{narrative_id}/download`

The narrative export reads generated checklist and bundle evidence. It does not inspect or modify source GIS files and does not mutate profile mapper config.
