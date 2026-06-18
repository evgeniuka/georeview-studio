# Template Authoring Wizard

GeoReview Studio v031 adds draft-only profile template authoring.

## Purpose

The wizard helps design new GIS review profiles before implementation. It creates small draft JSON and Markdown files under `analysis_output/georeview_studio_template_authoring`.

It does not modify:

- source GIS files;
- `profile_mapper_contracts_v001.json`;
- credentials;
- hosting or deployment settings.

## API

- `GET /api/template-authoring`
- `GET /api/template-authoring/options`
- `POST /api/template-authoring/draft`
- `GET /api/template-authoring/drafts`
- `GET /api/template-authoring/drafts/{draft_id}`

## Current Blueprints

- `cycling_micromobility_access`
- `school_zone_walk_access`
- `bus_stop_crossing_access`
- `generic_osm_tag_coverage`

## Claim Boundary

Drafts describe profile requirements, expected outputs, and data-quality warnings. They do not execute analysis, predict crashes, or prove real-world safety conditions.
