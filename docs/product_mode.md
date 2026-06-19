# Product mode vs full mode

GeoReview Studio ships two layers behind one server:

- the **GIS-review product** (~the endpoints a reviewer actually uses), and
- an internal **publication / QA tooling layer** (release-readiness dashboards,
  evidence bundles, repository-export packets, recruiter briefs, visual-QA
  ledgers, etc.) that exists to build and audit the project itself.

By default the server runs in **full mode** and serves both layers (this is also
what the two test suites exercise). To serve only the product surface — for a
slimmer, more auditable deployable — start it in **product mode**:

```powershell
$env:GEOREVIEW_MODE = "product"
python -B backend\app.py
```

In product mode every request outside the product surface returns `404`
(`served_in_product_mode()` in `backend/app.py`); the static frontend is always
served, and its internal-tooling panels (already hidden behind the
"Show advanced evidence operations" toggle) simply fail their data load
gracefully via the per-panel boot isolation.

## Product surface (served in both modes)

| Area | Endpoints (prefix) |
|---|---|
| Health / manifest | `/api/health`, `/api/project-manifest` |
| Sources / templates | `/api/catalog/sources`, `/api/templates` |
| Pilot areas | `/api/pilot-areas`, `/api/preflight` |
| Dashboard | `/api/dashboard-workspaces/*` (summary, candidates, map-features, network-access, validation, review-decisions) |
| Workspaces / runs | `/api/workspace-registry`, `/api/runs/*`, `/api/jobs`, `/api/analysis-runs` |
| Analysis | `/api/analysis-profiles`, `/api/profile-dashboard`, `/api/profile-workspaces`, `/api/scoring-rules`, `/api/osm-tag-quality` |
| Reports | `/api/portfolio-reports` |

Everything else under `/api/` is the internal tooling layer and is only served
in full mode.
