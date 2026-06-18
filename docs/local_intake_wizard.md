# Local Intake Wizard

v025 adds a reviewed local intake workflow.

The app does not accept browser uploads. It previews a local file or folder under:

```text
D:\cloude_work\georeview-studio
```

It rejects paths outside the maps root and rejects generated `analysis_output` paths.

## API

- `GET /api/local-intake`
- `GET /api/local-intake/sources`
- `POST /api/local-intake/preview`
- `POST /api/local-intake/plan`

## Output

Plans are small JSON metadata files under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_local_intake
```

Source GIS files remain read-only.
