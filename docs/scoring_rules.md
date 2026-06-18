# Scoring Rules v001

v026 makes scoring rules explicit and testable.

The canonical rules live in:

```text
config/scoring_rules_v001.json
```

The backend exposes:

- `GET /api/scoring-rules`
- `GET /api/scoring-rules/{profile_id}`
- `GET /api/scoring-rules/{profile_id}/audit`
- `POST /api/scoring-rules/{profile_id}/audit`

The audit recalculates expected score from normalized profile result flags and compares it with the actual profile score.

Current profiles:

- `safe_access_pedestrian_review`
- `transit_stop_walk_access`
- `park_playground_access`

Important policy:

- missing OSM tags are data-quality flags;
- missing tags do not add score by default;
- explicit negative tags such as `sidewalk=no` or `lit=no` may add points;
- the score is a field-review priority indicator, not a crash prediction.

## What the score actually measures (composition)

Read the score honestly: on the Kfar Saba pilot it is dominated by **major-road
proximity and the density of mapped pedestrian crossings**, not by sidewalk or
lighting condition. Measured on the 391-generator route-aware output:

- ~53% of all accumulated points come from "no mapped feature within distance"
  rules: `no_mapped_crossing_within_150m` (fires on 206/391 at 25 pts),
  `route_nearest_crossing_over_250m` (169/391 at 20 pts) and
  `no_mapped_traffic_calming_within_100m_weak_indicator` (385/391 at 10 pts —
  the source maps only ~11 traffic-calming features pilot-wide, so this flag is
  near-universal and is intentionally weighted low and labelled `weak_indicator`).
- The explicit negative-tag rules behave differently in this source: `sidewalk=no`
  fires on only 3/391 generators and `lit=no` on 0/391, because OSM coverage of
  those tags here is roughly 5–10% (the data-quality flags
  `nearby_sidewalk_tags_missing` and `nearby_lit_tags_missing` fire on ~90–95% of
  generators instead).

Consequence: for ~9 of 10 generators there is no sidewalk/lighting evidence in
either direction, so the score should be read as **"where mapped pedestrian-crossing
infrastructure is sparse near a generator"**, not as "where sidewalks or lighting
are poor". This is a deliberate, transparent limitation of the OSM/Geofabrik source,
not a defect of the scoring model — missing tags are kept out of the score by design.
