# GeoReview Studio v083

GeoReview Studio scans OpenStreetMap / Geofabrik data for a pilot area (Kfar Saba) and surfaces the pedestrian destinations — schools, kindergartens, parks, bus stops — that sit far from a mapped, signalised crossing, so a municipal or road-safety reviewer can **prioritise which locations to inspect on-site first**. It is a local-first, field-review prioritisation tool that flags locations for human review; it makes no crash-prediction or absolute-safety claims.

As a portfolio project, it demonstrates GIS data engineering, road-safety domain modelling, and pragmatic software engineering.

## Screenshots

![GeoReview Studio dashboard — Safe Access Kfar Saba review map, review queue and selected-candidate detail](screenshots/dashboard_desktop.png)

<sub>Dashboard-first review workspace (desktop, 1440×1320).</sub>

## Who it's for

Municipal road-safety planners, pedestrian-access reviewers and GIS analysts who need to turn raw OSM data into a ranked, evidence-backed shortlist of locations worth a physical visit.

## What to look at

- **The product**: the dashboard (map + review queue + selected-candidate evidence), the Kfar Saba pilot results in [`portfolio/case_study.md`](portfolio/case_study.md), and the transparent, audited scoring in [`config/scoring_rules_v001.json`](config/scoring_rules_v001.json) + [`docs/scoring_rules.md`](docs/scoring_rules.md).
- **The GIS workflow**: source onboarding → selected-pilot preflight → run analysis profile → dashboard candidates → **review-worklist export (CSV / GeoJSON)** → portfolio report.
- **Editorial note**: an earlier AI-assisted build had accreted ~50 self-referential "tooling" endpoints (publication / QA / release-readiness machinery that mostly packaged the project itself). I removed them to keep the product core honest and reviewable — the backend is now ~32 focused modules. The full pre-subtraction tree is preserved on the `archive/full-app-2026-06-25` branch.

## How to read the score (and what it is not)

The score is a **transparent but UNCALIBRATED** heuristic: it measures where mapped, signalised pedestrian-crossing access is *sparse* near a destination — it is **never checked against real crash or outcome data**. So it tells you **where to look first, not where it is worst**. It is a triage aid for on-site review, not a verdict.

- NOT crash / accident prediction. NOT a calibrated severity ranking.
- A missing OSM tag is a **data-quality flag**, never proof that infrastructure is absent.
- Analysis CRS is EPSG:2039 (Israeli grid): the pipeline generalises to other regions by reprojection, but the distance thresholds stay Israel/OSM-shaped until recalibrated.

Approved wording:

`This location has infrastructure risk indicators and should be reviewed on-site.`

## Current Release

App version `v083` · manifest `v083_2026-06-01` · local URL `http://127.0.0.1:8847`

## Run Locally

```powershell
cd <repo-or-release-root>
python -B backend\app.py
```

Open `http://127.0.0.1:8847` after the local server starts.

## Repository map

- Project rules: `AGENTS.md`
- Release manifest: `project_manifest.json`
- Backend entrypoint: `backend/app.py`
- Frontend assets: `frontend/static`
- Validation: `tests/validate_app.py`
- API contract tests: `tests/test_api_contract.py`
- Product and release docs: `docs/`

The `AGENTS.md` working rules and the editorial note above — recording the deliberate removal of ~50 self-referential tooling endpoints — are kept in the repository as visible evidence that this AI-assisted build was scoped and pruned under human control rather than left to accrete.
