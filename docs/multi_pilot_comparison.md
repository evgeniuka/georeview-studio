# Multi-Pilot Comparison

v049 adds a reusable comparison layer for route-aware Safe Access pilot workspaces.

## Purpose

The feature compares Kfar Saba and Raanana with the same canonical workspace contract:

- `pedestrian_generators`
- `crossings`
- `road_segments`
- `risk_assessment_results`
- `network_access_results`

It is designed as portfolio evidence that GeoReview Studio is not hard-coded to one city.

## API

- `GET /api/multi-pilot-comparison`
- `POST /api/multi-pilot-comparison/create`
- `GET /api/multi-pilot-comparison/comparisons`
- `GET /api/multi-pilot-comparison/comparisons/{comparison_id}`
- `GET /api/multi-pilot-comparison/comparisons/{comparison_id}/download`

## Output

Generated comparisons are written under:

`D:\cloude_work\georeview-studio\analysis_output\georeview_studio_multi_pilot_comparisons`

Each comparison writes JSON, Markdown and standalone HTML. Source GIS files are not modified.

## Metrics

The comparison uses only inspected workspace evidence:

- generator, crossing, major road and traffic calming counts;
- route-aware nearest crossing distance metrics;
- rows over 250 m by mapped road-network proxy;
- normalized mapped crossing and calming evidence;
- top review candidates and OSM data-quality flags.

Missing OSM tags are not treated as proof that infrastructure is absent. They remain data-quality flags.

## Claim Boundary

This feature supports infrastructure review prioritization and data-quality review only. It does not label a location and does not predict crashes.

Approved wording:

`This location has infrastructure risk indicators and should be reviewed on-site.`
