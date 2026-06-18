# Demo Script Pack

`Demo Script Pack` is the v062 repeatable portfolio walkthrough layer.

It creates:

- `demo_script.md` with an 8-minute walkthrough;
- `screenshot_smoke_plan.md` with screenshot/API smoke targets;
- `screenshot_contact_sheet.html` for a compact visual checklist;
- `demo_script_pack_manifest.json` with package lineage and claim boundaries.

## API

- `GET /api/demo-script-pack`
- `POST /api/demo-script-pack/create`
- `GET /api/demo-script-pack/packs`
- `GET /api/demo-script-pack/packs/{pack_id}`
- `GET /api/demo-script-pack/packs/{pack_id}/download`

## Output

Generated packs are written under:

```text
analysis_output/georeview_studio_demo_script_packs
```

The pack is evidence-only. It does not mutate source GIS files and does not include source GIS data.

## Claim Boundary

The walkthrough explains infrastructure risk indicators and field-review prioritization. It is not a crash prediction demo and it does not claim real-world outcomes.
