# Portable Release Package

`Portable Release Package` is the v061 packaging layer for GeoReview Studio.

It creates a small ZIP package for local reviewer demos. The ZIP includes:

- package manifest;
- package README;
- current project, validation and API contract summaries;
- portfolio export launcher evidence;
- reviewer audit index evidence;
- reproducibility audit packet evidence;
- selected handoff/gallery/narrative/readiness files when they are small enough.

## API

- `GET /api/portable-release-package`
- `POST /api/portable-release-package/create`
- `GET /api/portable-release-package/packages`
- `GET /api/portable-release-package/packages/{package_id}`
- `GET /api/portable-release-package/packages/{package_id}/download`

## Output

Generated packages are written under:

```text
analysis_output/georeview_studio_portable_release_packages
```

The ZIP excludes source GIS data. It writes only small generated reviewer artifacts and summary files.

## Claim Boundary

The package is a reviewer/demo artifact for infrastructure risk indicators and field-review prioritization. It is not a crash prediction artifact and it does not claim real-world outcomes.
