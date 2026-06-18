# Source Import Guardrails

`v051` adds an approval-gated, metadata-only source import review workflow.

The workflow is intentionally conservative:

- source GIS files remain read-only;
- generated evidence is written only under `analysis_output/georeview_studio_source_import_guardrails`;
- browser upload is not implemented;
- approval requires explicit acknowledgements;
- missing OSM tags remain data-quality evidence, not proof of real-world absence.

## API

- `GET /api/source-import-guardrails`
- `POST /api/source-import-guardrails/preview`
- `POST /api/source-import-guardrails/request`
- `GET /api/source-import-guardrails/requests`
- `GET /api/source-import-guardrails/requests/{request_id}`
- `GET /api/source-import-guardrails/requests/{request_id}/download`
- `POST /api/source-import-guardrails/requests/{request_id}/decision`

## Guardrails

- path must stay inside the configured maps root;
- `analysis_output` is excluded from source intake;
- format must be supported by the local profiler;
- metadata profile must be available;
- selected template compatibility must be reviewed;
- large files get a size-review warning;
- manual approval is required;
- source read-only policy is explicit;
- approved field-review wording is preserved.

## Approval Phrase

`approve metadata-only import`

Approval does not run domain analytics by itself. It only records that the source has passed metadata-only review and can be handed to mapper planning or controlled execution in a later step.
