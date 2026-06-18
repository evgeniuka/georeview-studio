# Controlled Execution Queue

GeoReview Studio v032 adds a controlled local execution queue.

## Purpose

The queue converts validated profile contract dry-runs into allowlisted local runner actions. It writes small job records under `analysis_output/georeview_studio_execution_queue`.

## Gates

- A contract dry-run must return `can_execute_now=true`.
- The profile must be allowlisted.
- The adapter status must be executable.
- Source GIS files remain read-only.
- Runner outputs stay under `analysis_output`.

## API

- `GET /api/execution-queue`
- `POST /api/execution-queue/enqueue`
- `GET /api/execution-queue/jobs`
- `GET /api/execution-queue/jobs/{job_id}`

## Claim Boundary

The queue executes local analysis profiles and stores evidence. It does not predict crashes, prove real-world safety conditions, read credentials, deploy anything, or modify source GIS files.
