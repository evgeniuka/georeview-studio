# Visual Evidence Capture

v066 adds automated browser screenshots for Visual QA ledger targets.

The feature uses a local headless Chrome or Edge executable to capture the demo screens listed in the latest Visual QA Snapshot Ledger. It writes PNG screenshots, a contact sheet, a JSON manifest and a Markdown summary under `analysis_output`.

## API

- `GET /api/visual-evidence-capture`
- `POST /api/visual-evidence-capture/create`
- `GET /api/visual-evidence-capture/captures`
- `GET /api/visual-evidence-capture/captures/{capture_id}`
- `GET /api/visual-evidence-capture/captures/{capture_id}/download`

## Output

Generated captures are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_visual_evidence_captures
```

Each capture writes:

- `visual_evidence_capture_manifest.json`;
- `visual_evidence_capture.md`;
- `visual_evidence_contact_sheet.html`;
- `screenshots/*.png`;
- `latest_visual_evidence_capture.json`.

## Runtime

The capture runtime looks for local Chrome or Edge executables and runs them in headless mode. The API accepts an optional `base_url` so tests can capture against a random local server port while the dashboard uses the default local app URL.

## Claim Boundary

Approved review wording remains:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```

Screenshots are demo evidence only. They are not field verification, crash prediction, or absolute site condition claims. Source GIS files remain read-only.
