# Release Readiness Dashboard

v042 adds a local dashboard that summarizes whether the current GeoReview Studio build is ready for a portfolio or demo review.

It is a release-evidence layer, not a new GIS analysis profile. It reads existing app state and reports gates for:

- project manifest and local URL;
- product architecture roadmap;
- source GIS read-only policy;
- approved infrastructure review wording;
- profile dashboard outputs;
- scoring-rule audit evidence;
- source onboarding evidence;
- profile mapper and contract execution readiness;
- template authoring, authored runner, controlled queue and dataset packages;
- promotion lifecycle evidence through regression preview;
- validation and API contract summaries;
- packaged UI and documentation.

## API

- `GET /api/release-readiness`
- `GET /api/release-readiness/gates`
- `POST /api/release-readiness/snapshot`
- `GET /api/release-readiness/snapshots`
- `GET /api/release-readiness/snapshots/{snapshot_id}`

Snapshots are small JSON and Markdown artifacts written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_release_readiness
```

The dashboard does not modify source GIS files and does not apply profile mapper config changes.

## Readiness Levels

- `ready_for_local_portfolio_demo`: all gates passed.
- `ready_with_verification_warnings`: no failed gates, but validation or API contract evidence may need a fresh run.
- `not_ready_for_release`: at least one required gate failed.

## Claim Boundary

This feature checks release evidence for infrastructure risk indicator workflows. It does not make crash prediction claims and does not convert missing OSM tags into real-world absence claims.
