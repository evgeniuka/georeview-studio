# Source Handoff

`Source Handoff` is the v052 bridge from a manually approved source import review packet to profile-mapper planning and controlled execution evidence.

It creates three linked artifacts:

- a `Profile Mapper Plan`;
- a `Contract Execution Dry Run`;
- a `Controlled Execution Queue Job` with `execute_now=false`.

The handoff does not run analytics by itself. It records that an approved local source can be mapped to a profile, dry-run against the runner adapter, and queued as a planned action for a later controlled execution step.

## API

- `GET /api/source-handoff`
- `GET /api/source-handoff/candidates`
- `POST /api/source-handoff/create`
- `GET /api/source-handoff/handoffs`
- `GET /api/source-handoff/handoffs/{handoff_id}`
- `GET /api/source-handoff/handoffs/{handoff_id}/download`

## Guardrails

- Only approved source import requests can be used.
- Source import requests with hard guardrail failures are rejected.
- The queue job is created with `execute_now=false`.
- Source GIS files are not edited, moved, renamed, overwritten, or copied by this workflow.
- Missing OSM tags remain data-quality gaps, not proof that infrastructure is absent.

Approved wording:

`This location has infrastructure risk indicators and should be reviewed on-site.`

## Portfolio Value

This feature shows the product is becoming a reusable GIS analytics platform, not only a one-off Kfar Saba notebook. A reviewer can see a controlled path from local source review to profile compatibility, dry-run execution evidence, queue planning, and later reproducible profile runs.
