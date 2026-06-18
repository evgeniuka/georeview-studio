# Execution Evidence Package

`Execution Evidence Package` is the v054 reviewer-facing packaging layer over verified source handoff executions.

It answers a simple reviewer question:

> Can the project prove the path from approved source review to generated GIS analytics outputs?

The package indexes:

- approved source handoff execution JSON and Markdown;
- controlled queue job evidence;
- generated workspace manifest and canonical tables;
- handoff expected-output comparison;
- validation and API contract summaries;
- claim boundaries and approved review wording.

It writes only small JSON and Markdown artifacts under:

```text
analysis_output/georeview_studio_execution_evidence_packages
```

It does not copy or mutate source GIS files.

## API

- `GET /api/execution-evidence-package`
- `GET /api/execution-evidence-package/candidates`
- `POST /api/execution-evidence-package/create`
- `GET /api/execution-evidence-package/packages`
- `GET /api/execution-evidence-package/packages/{package_id}`
- `GET /api/execution-evidence-package/packages/{package_id}/download`

## Readiness

A package is `ready_for_reviewer` when:

- the source handoff execution is `executed_and_verified`;
- the handoff-to-workspace comparison is `outputs_match_handoff_evidence`;
- canonical outputs are present;
- core execution, workspace and manifest artifacts exist;
- source GIS mutation is explicitly false;
- API contract evidence is recorded for the current endpoint count.

The approved wording remains:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```
