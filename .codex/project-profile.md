# Project Profile

## Identity

- Project: GeoReview Studio
- Canonical release root: `D:\cloude_work\georeview-studio\v083_2026-06-01`
- Version: `v083_2026-06-01`
- Domain: GIS infrastructure risk indicators for pedestrian access review
- Local URL: `http://127.0.0.1:8847`

## Stack

- Python backend
- Static frontend under `frontend/static`
- Local JSON/CSV/GIS artifacts
- Validation scripts under `tests/`

## Commands

```powershell
python -B backend\app.py
```

Project-specific validation commands should be taken from `README.md`, `project_manifest.json`, and `tests/`.

## Context Map

- Release manifest: `project_manifest.json`
- Backend entrypoint: `backend/app.py`
- Frontend assets: `frontend/static`
- Validation: `tests/validate_app.py`
- API contract tests: `tests/test_api_contract.py`
- Documentation: `docs/`
- Portfolio artifacts: `portfolio/`
- UI review screenshots: `ui_review/`

## Product Boundary

GeoReview Studio supports field-review prioritization. It must separate:

- infrastructure risk indicators
- OSM/data-quality flags
- unknown/missing data

Missing OSM tags are not proof that infrastructure is absent.

## Quality Gates

- Check `validation_summary.json` when present.
- Check `api_contract_summary.json` when present.
- Use screenshots for UI review when available.
- Run local browser QA only after the app is started locally.

## Goal-Mode Readiness

Suitable for read-only audit or narrow patch Goal runs. Not suitable for broad cleanup against the parent `maps` folder.
