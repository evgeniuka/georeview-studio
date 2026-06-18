# GeoReview Studio v083

GeoReview Studio scans OpenStreetMap / Geofabrik data for a pilot area (Kfar Saba) and surfaces the pedestrian destinations — schools, kindergartens, parks, bus stops — that sit far from a mapped, signalised crossing, so a municipal or road-safety reviewer can **prioritise which locations to inspect on-site first**. It is a local-first, field-review prioritisation tool that flags locations for human review; it makes no crash-prediction or absolute-safety claims.

## Screenshots

![GeoReview Studio dashboard — Safe Access Kfar Saba review map, review queue and selected-candidate detail](screenshots/dashboard_desktop.png)

<sub>Dashboard-first review workspace (desktop, 1440×1320). The mobile layout is in [screenshots/dashboard_mobile.png](screenshots/dashboard_mobile.png).</sub>

## Who it's for

Municipal road-safety planners, pedestrian-access reviewers and GIS analysts who need to turn raw OSM data into a ranked, evidence-backed shortlist of locations worth a physical visit.

## What to look at

- **The product**: the dashboard (map + review queue + selected-candidate evidence), the Kfar Saba pilot results in [`portfolio/case_study.md`](portfolio/case_study.md), and the transparent, audited scoring in [`config/scoring_rules_v001.json`](config/scoring_rules_v001.json) + [`docs/scoring_rules.md`](docs/scoring_rules.md).
- **The GIS workflow** (~12 endpoints): source onboarding → selected-pilot preflight → run analysis profile → dashboard candidates → portfolio report.
- **Scope note**: the repository also carries an internal *tooling layer* (publication / handoff / QA / release-readiness endpoints and docs) used to package and review the project itself. That layer is supporting scaffolding, not the product — see [`docs/README.md`](docs/README.md) for a guided index that separates the two.

## Current Release

- App version: `v083`
- Project manifest: `v083_2026-06-01`
- Local URL: `http://127.0.0.1:8847`
- Focus: Figma-aligned dashboard polish

## v083 Focus

v083 applies the prepared Figma direction to the local dashboard. The first workflow now keeps the map, review queue, selected candidate detail and compact workflow sidebar visible as the primary product surface. Advanced evidence and publication operations remain available, but they stay behind an explicit toggle.

## Data Boundary

This project supports infrastructure risk indicator review. It does not make absolute safety conclusions about a place. Missing OSM tags are data-quality flags, not proof that infrastructure is absent.

Approved wording:

`This location has infrastructure risk indicators and should be reviewed on-site.`

## Run Locally

```powershell
cd <repo-or-release-root>
python -B backend\app.py
```

Open `http://127.0.0.1:8847` after the local server starts.

## Codex Navigation

- Project rules: `AGENTS.md`
- Project profile: `.codex/project-profile.md`
- Release manifest: `project_manifest.json`
- Backend entrypoint: `backend/app.py`
- Frontend assets: `frontend/static`
- Validation: `tests/validate_app.py`
- API contract tests: `tests/test_api_contract.py`
- Product and release docs: `docs/`

Before claiming portfolio readiness, verify actual validation outputs instead of relying on old chat state.
