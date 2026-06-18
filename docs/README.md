# Documentation index

This folder has two kinds of docs. **If you are reviewing the project, read the
"Product & methodology" set first** — that is the actual GIS work. Everything under
"Internal tooling layer" documents how the project packages and reviews *itself*
and is supporting scaffolding, not product features.

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
[postgis_backend.md](postgis_backend.md) (planning-only) ·
[universal_gis_analytics_architecture.md](universal_gis_analytics_architecture.md) (direction)

## Internal tooling layer (packaging / QA / publication — not product features)

These document the machinery that turns finished analysis into shareable evidence
(bundles, handoffs, screenshots, release-readiness gates, reviewer-audit indexes and
the GitHub-publication pipeline). They exist so the project can package and quality-check
itself reproducibly; a recruiter does not need to read them to understand the product.

Representative entries: `release_readiness_dashboard.md`, `portfolio_evidence_bundle.md`,
`bundle_review_checklist.md`, `portfolio_handoff_page.md`, `reproducibility_audit_packet.md`,
`reviewer_audit_index.md`, `github_publication_bundle.md`, `repository_*` reviews,
`visual_evidence_*` and `visual_qa_*`, `demo_*`, `recruiter_demo_brief.md`,
`public_*_package.md`, `profile_promotion_wizard.md` and the related promotion/contract-diff docs.
