# Profile Dashboard Export Bundle

v025 adds a compact Markdown/JSON bundle over the normalized profile dashboard.

The bundle summarizes the three implemented profiles:

- `safe_access_pedestrian_review`
- `transit_stop_walk_access`
- `park_playground_access`

It links the generated profile comparison report and includes small result samples.

## API

- `POST /api/export-bundles/profile-dashboard`
- `GET /api/export-bundles`
- `GET /api/export-bundles/{bundle_id}`
- `GET /api/export-bundles/{bundle_id}/download`

## Claim Boundary

The bundle is infrastructure review evidence only. It is not a crash prediction model.

Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.
