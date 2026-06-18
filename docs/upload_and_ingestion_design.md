# Upload And Ingestion Design

The current app intentionally scans the local `maps` folder instead of accepting browser uploads.

That is the correct stage for this project because the source GIS policy is strict:

- do not modify source GIS data;
- write derived outputs only under `analysis_output`;
- keep metadata and reports reproducible;
- separate data-quality gaps from infrastructure indicators.

## Future Intake Flow

1. User selects a local file or folder.
2. App records only the path and runs a read-only profile.
3. App reports format, size, CRS, layer count and likely role.
4. App checks whether any analysis profile can run.
5. User starts a workspace build only after reviewing blockers.
6. App writes normalized outputs to a generated workspace folder.

## Supported Future Formats

- OSM PBF
- Geofabrik Shapefile ZIP
- GeoPackage
- Shapefile folder or ZIP
- GeoJSON

## Required Gates

- source path exists;
- file size is known;
- format is supported;
- CRS is known or transformable;
- required profile layers exist;
- output workspace id is generated;
- `source_gis_modified=false` is preserved in every result.

## v025 Local Intake And Export Bundle

- `GET /api/local-intake`
- `GET /api/local-intake/sources`
- `POST /api/local-intake/preview`
- `POST /api/local-intake/plan`
- `POST /api/export-bundles/profile-dashboard`
- `GET /api/export-bundles`
- `GET /api/export-bundles/{bundle_id}`
- `GET /api/export-bundles/{bundle_id}/download`

All generated files are metadata/report artifacts under `analysis_output`; source GIS files remain read-only.
