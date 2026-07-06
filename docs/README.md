# Documentation index

This folder documents the GIS review workbench. **If you are reviewing the project,
read the "Product & methodology" set first** — that is the actual GIS work; the
section below it is deeper workflow dives.

## Product & methodology (start here)

| Doc | What it covers |
|---|---|
| [architecture.md](architecture.md) | System architecture: Python backend, static frontend, local artifact stores. |
| [product_architecture.md](product_architecture.md) | Product direction and the reusable-profile model (with honest current limits). |
| [data_model.md](data_model.md) | Canonical geospatial tables built from OSM/Geofabrik source. |
| [scoring_rules.md](scoring_rules.md) | Transparent, audited scoring — and what the score actually measures. |
| [osm_tag_quality.md](osm_tag_quality.md) | OSM tag coverage, missing-tag handling, risk vs data-quality separation. |
| [profile_result_contract.md](profile_result_contract.md) | Normalized result contract shared across analysis profiles. |
| [api.md](api.md) | Endpoint reference for the GIS workflow. |
| [testing.md](testing.md) | Validation suite and API-contract tests. |
| [operations.md](operations.md) | How to run and operate the local app. |

## The GIS analysis workflow (deeper dives)

[local_intake_wizard.md](local_intake_wizard.md) ·
[profile_mapper_sdk.md](profile_mapper_sdk.md) ·
[contract_execution.md](contract_execution.md) ·
[template_authoring.md](template_authoring.md) ·
[authored_profile_runner.md](authored_profile_runner.md) ·
[authored_dashboard_contract.md](authored_dashboard_contract.md) ·
[postgis_backend.md](postgis_backend.md) (planning-only) ·
[universal_gis_analytics_architecture.md](universal_gis_analytics_architecture.md) (direction)

Profile governance workflow (authoring → promotion → acceptance):
[profile_promotion_wizard.md](profile_promotion_wizard.md) ·
[proposal_acceptance_workflow.md](proposal_acceptance_workflow.md) ·
[accepted_contract_application_plan.md](accepted_contract_application_plan.md) ·
[profile_contract_diff_review.md](profile_contract_diff_review.md) ·
[profile_contract_regression_preview.md](profile_contract_regression_preview.md) ·
[guarded_config_apply_proposal.md](guarded_config_apply_proposal.md)

---

> **Note (2026-07):** ~37 self-referential "tooling" docs — packaging / QA / publication
> scaffolding that described how the project reviewed and shipped *itself* — were removed
> together with the backend modules they documented (see the top-level `README.md` editorial
> note on the cut). This index now covers product and workflow docs only.
