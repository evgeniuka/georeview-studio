# Accepted Contract Application Plan

v038 adds a guarded planning layer for approved profile promotion proposals.

## Purpose

An approved proposal is still not a config change. The application-plan layer creates evidence for a later explicit implementation task:

- chooses an approved promotion decision;
- compares existing profile mapper contract vs proposed contract;
- writes a JSON application plan;
- writes a config patch preview;
- writes a manual implementation checklist.

## API

- `GET /api/profile-promotion/application-candidates`
- `POST /api/profile-promotion/application-plan`
- `GET /api/profile-promotion/application-plans`
- `GET /api/profile-promotion/application-plans/{plan_id}`

## Boundary

This is still planning-only.

- Source GIS files remain read-only.
- `profile_mapper_contracts_v001.json` is not modified automatically.
- Missing OSM tags remain data-quality flags.
- No crash prediction is introduced.
- This location has infrastructure risk indicators and should be reviewed on-site.
