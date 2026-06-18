# Profile Result Contract

v024 introduces one normalized dashboard contract for implemented profile outputs.

The goal is simple: the frontend should not need a separate result table for every GIS profile.

## Endpoint Shape

- `GET /api/profile-dashboard`
- `GET /api/profile-dashboard/profiles`
- `GET /api/profile-dashboard/{profile_id}/summary`
- `GET /api/profile-dashboard/{profile_id}/results?limit=50&min_score=0&only_flags=false`

Implemented profile IDs:

- `safe_access_pedestrian_review`
- `transit_stop_walk_access`
- `park_playground_access`

## Normalized Row Fields

- `profile_id`
- `workspace_id`
- `result_id`
- `osm_id`
- `entity_type`
- `name`
- `primary_score`
- `secondary_score`
- `score_label`
- `nearest_crossing_m`
- `route_nearest_crossing_m`
- `nearest_major_road_m`
- `flags`
- `data_quality_flags`
- `review_wording`
- `lon`
- `lat`
- `source_table`
- `source_gis_modified`

## Interpretation Rule

`primary_score` is profile-specific but rendered through one UI contract:

- Safe Access: `route_review_priority_score`
- Transit Access: `transit_review_priority_score`
- Park/Playground Access: `public_space_review_priority_score`

The row wording stays:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```

Missing OSM tags remain data-quality evidence, not automatic risk.

## v026 Scoring Rules

- `config/scoring_rules_v001.json`
- `GET /api/scoring-rules`
- `GET /api/scoring-rules/{profile_id}`
- `GET /api/scoring-rules/{profile_id}/audit`
- `POST /api/scoring-rules/{profile_id}/audit`

The score audit recalculates expected profile scores from versioned rules and normalized result flags. Missing OSM tags remain data-quality flags, not score points by default.
