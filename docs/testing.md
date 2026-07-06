# Testing

Two stdlib-only suites gate the app; both run without installing any packages.

## Validation

```powershell
.\scripts\validate.ps1        # runs: python -B tests\validate_app.py
```

`tests/validate_app.py` boots the app in-process and checks:

- the tight post-Cut-A surface exists — the required backend modules and the required files (`README.md`, `project_manifest.json`, `config/scoring_rules_v001.json`, and the `frontend/static` trio);
- the forbidden-term / approved-wording scan is clean (it delegates to `scripts/check_forbidden_terms.py`);
- the core endpoints answer: `/api/health` (app version `v083`), project manifest, scoring rules, OSM tag quality, pilot areas, profile dashboard (at least three implemented profiles), and the default workspace summary / candidates / map-features;
- the product-mode gate hides archived tooling (`/api/release-readiness` returns 404) while still serving the product core;
- the review-worklist export produces both CSV and GeoJSON with the approved review wording stamped per row.

## API Contract Tests

```powershell
.\scripts\test_api_contract.ps1   # runs: python -B tests\test_api_contract.py
```

Starts the local handler on a temporary port and verifies the current live surface — **183 endpoints** — including:

- health and project-manifest;
- source onboarding status / refresh / list / detail;
- Analysis Profiles list / detail / readiness / plan, and the Transit Stop Walk Access and Park And Playground Access profile runners plus their workspace results;
- Create Analysis plan / start; Analysis Runs list / detail / outputs / download / rerun;
- Portfolio Reports list / detail / download / generate / profile-workspace / profile-comparison / compare;
- pilot metadata / search / detail, selected-pilot preflight, and job start / detail / history;
- dashboard summary / candidates / route-aware network-access, and the candidates CSV/GeoJSON worklist export;
- scoring rules and the score audit (`GET` and `POST /api/scoring-rules/{profile_id}` and `/audit`) — the audit recomputes expected scores from the versioned rules and normalized flags, keeping missing OSM tags as data-quality flags, not points;
- local intake (`/api/local-intake`, sources, preview, plan) and export bundles (`/api/export-bundles` create / list / detail / download);
- the planning-only PostGIS option (`/api/postgis-backend` status / schema / migration-plan / plans / detail);
- the source-import → handoff → handoff-execution governance workflow, and the profile mapper / promotion / template-authoring / contract-execution / execution-queue / dataset-package endpoints;
- review-decision persistence for the dashboard workspaces;
- error statuses: a missing workspace and a missing dataset return `404`, and a malformed request returns `400` (`bad_request`).

All generated files are metadata / report artifacts under `analysis_output`; source GIS files remain read-only.

## Evolution

Earlier revisions (v042–v062) added a large internal publication / QA / release-readiness tooling layer, each with its own validation and contract section here. The **Cut A** subtraction (2026-06) removed those modules, and their test sections went with them; the contract suite dropped from 362 to the current 183 endpoints as a result. The full pre-cut tree and its tests are preserved on the `archive/full-app-2026-06-25` branch.
