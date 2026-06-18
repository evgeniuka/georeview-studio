# Demo Review Playbook

GeoReview Studio v073 adds a final demo-review layer over the public portfolio package.

## Purpose

The playbook converts the public README and interview package into a practical portfolio walkthrough:

- demo agenda;
- final sharing checklist;
- likely reviewer questions;
- reviewer notes;
- claim-boundary reminders.

## Inputs

- A ready Public Portfolio Package.
- `validation_summary.json`.
- `api_contract_summary.json`.
- `project_manifest.json`.

## Outputs

- `demo_review_playbook_manifest.json`
- `demo_review_playbook.md`
- `final_sharing_checklist.md`
- `demo_review_playbook.html`
- `latest_demo_review_playbook.json`

## API

- `GET /api/demo-review-playbook`
- `POST /api/demo-review-playbook/create`
- `GET /api/demo-review-playbook/playbooks`
- `GET /api/demo-review-playbook/playbooks/{playbook_id}`
- `GET /api/demo-review-playbook/playbooks/{playbook_id}/download`

## Claim Boundary

`This location has infrastructure risk indicators and should be reviewed on-site.`

Missing OSM tags remain data-quality flags. They are not treated as proof of real-world infrastructure absence.
