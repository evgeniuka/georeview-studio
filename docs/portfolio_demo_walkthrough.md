# Guided Portfolio Demo Walkthrough

v043 adds a guided demo layer for presenting GeoReview Studio as a serious portfolio project.

The feature does not run a new GIS analysis. It reads existing evidence from:

- product architecture;
- source onboarding;
- profile dashboard;
- scoring rules;
- profile promotion lifecycle;
- release readiness;
- portfolio reports and export bundles.

## API

- `GET /api/portfolio-demo`
- `GET /api/portfolio-demo/steps`
- `POST /api/portfolio-demo/snapshot`
- `GET /api/portfolio-demo/snapshots`
- `GET /api/portfolio-demo/snapshots/{snapshot_id}`

Snapshots are small JSON and Markdown artifacts written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_portfolio_demo
```

## Demo Story

The default walkthrough is intended for an 8-minute local portfolio demo:

1. Position the product.
2. Show inspected local data.
3. Walk through Safe Access Kfar Saba.
4. Show reusable profile expansion.
5. Explain engineering quality gates.
6. Show exportable outputs.
7. Close with the next roadmap step.

## Claim Boundary

The demo presents mapped infrastructure indicators and data-quality evidence for field-review prioritization. It does not make crash-prediction claims and does not treat missing OSM tags as proof of real-world absence.
