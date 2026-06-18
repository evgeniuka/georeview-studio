# Release Checklist

- [x] Source GIS files are read-only.
- [x] Generated artifacts are contained under `analysis_output`.
- [x] Source onboarding scan excludes `analysis_output`.
- [x] Analysis Profiles expose runnable and planned GIS analytics profiles.
- [x] Transit Stop Walk Access profile runner creates a profile workspace.
- [x] Park And Playground Access profile runner creates a profile workspace.
- [x] Create Analysis workflow can plan and start a selected Safe Access analysis.
- [x] Analysis Runs can list, open, expose outputs, and rerun analyses.
- [x] Portfolio Reports can generate, list, download, and compare run evidence.
- [x] Portfolio Reports can generate Markdown/JSON evidence from the Transit profile workspace.
- [x] Portfolio Reports can generate Markdown/JSON evidence from the Park profile workspace.
- [x] Portfolio Reports can generate a comparison report across implemented profiles.
- [x] Default workspace is `safe_access_kfar_saba_route_aware_v001`.
- [x] Pilot-area catalog is generated from read-only source ZIP.
- [x] Selected-pilot preflight checks are available before background jobs.
- [x] Background selected-pilot job history is generated under `analysis_output`.
- [x] Route-aware network proxy workspace is generated.
- [x] Validation script passes.
- [x] API contract tests pass.
- [x] Static UI files are served.
- [x] Portfolio artifacts are generated.
- [x] Approved review wording is present.
- [x] Absolute safety-claim wording scan is clean.
- [x] Missing OSM tags are described as data-quality gaps.

## Known Limitations

- Route-aware distance is an OSM road-network proxy, not verified pedestrian navigation.
- The app is local-first and single-user.
- The current pilot boundary is OSM/Geofabrik-based, not an official municipal boundary.

- [x] Product Architecture endpoints return current evidence, top options, pipeline, and roadmap.

- [x] Profile Dashboard endpoints return normalized rows for all implemented profiles.


## v049 Multi-Pilot Comparison

- [x] Kfar Saba route-aware workspace is available.
- [x] Raanana route-aware workspace is available.
- [x] Comparison API, UI and docs are packaged.
- [x] Source GIS files remain read-only.


## v050 Comparison Map Exports

- [x] Kfar Saba route-aware workspace has map input tables.
- [x] Raanana route-aware workspace has map input tables.
- [x] SVG, HTML and CSV map export artifacts are generated under analysis_output.
- [x] Source GIS files remain read-only.


## v053 Source Import Guardrails

- [x] Source import guardrails backend/API added.
- [x] UI panel and docs packaged.
- [x] Review packet and approval decision are metadata-only.
- [x] Source GIS files remain read-only.

## Source Handoff Added In v053

v053 adds approved source handoff: an approved source import request can now create a mapper plan, contract dry-run and planned execution queue job while keeping source GIS files read-only.

## Source Handoff Execution Added In v053

v053 adds controlled handoff execution: an approved source handoff can now be executed explicitly through the controlled queue, then compared against generated workspace outputs while keeping source GIS files read-only.

## Execution Evidence Package Added In v054

- `backend/execution_evidence_package.py`;
- `docs/execution_evidence_package.md`;
- `GET /api/execution-evidence-package`;
- `GET /api/execution-evidence-package/candidates`;
- `POST /api/execution-evidence-package/create`;
- `GET /api/execution-evidence-package/packages`;
- `GET /api/execution-evidence-package/packages/{package_id}`;
- `GET /api/execution-evidence-package/packages/{package_id}/download`;
- UI `Execution Evidence Package` panel with package creation and download controls.

The package indexes verified handoff execution lineage, controlled queue evidence, generated workspace outputs, comparison checks, validation evidence and claim boundaries. It writes only small JSON/Markdown artifacts under `analysis_output` and does not copy or mutate source GIS files.

## Execution Result Diff Added In v055

- `backend/execution_result_diff.py`;
- `docs/execution_result_diff.md`;
- `GET /api/execution-result-diff`;
- `GET /api/execution-result-diff/candidates`;
- `POST /api/execution-result-diff/create`;
- `GET /api/execution-result-diff/diffs`;
- `GET /api/execution-result-diff/diffs/{diff_id}`;
- `GET /api/execution-result-diff/diffs/{diff_id}/download`;
- UI `Execution Result Diff` panel with diff creation and download controls.

The diff layer compares reviewer-ready execution evidence packages by lineage, workspace output rows, output sets, quality checks and release/API evidence. It writes only small JSON/Markdown artifacts under `analysis_output` and does not copy or mutate source GIS files.

## v056–v059 (Execution Diff Gallery, Diff Detail, Reproducibility Audit Packet, Reviewer Audit Index)

- [x] Implemented and exercised by the current validation and API-contract suites (84 gates / 362 endpoints).
- [x] Source GIS files remain read-only.

(The earlier per-version endpoint counts — 234 / 241 / 247 / 252 — are obsolete and were removed; the current suite checks 362 endpoints.)

## v060 Portfolio Export Launcher Checks

- Adds `backend/portfolio_export_launcher.py`.
- Adds `docs/portfolio_export_launcher.md`.
- Adds `/api/portfolio-export-launcher` status, create, list, detail and download routes.
- Adds a dashboard panel that creates a start-here reviewer launcher over audit indexes, audit packets and portfolio evidence.
- Keeps source GIS files read-only and writes only small launcher evidence under `analysis_output`.

## v061 Portable Release Package Checks

- Adds `backend/portable_release_package.py`.
- Adds `docs/portable_release_package.md`.
- Adds `/api/portable-release-package` status, create, list, detail and ZIP download routes.
- Adds a dashboard panel that creates a small reviewer-ready ZIP from launcher and evidence artifacts.
- Excludes source GIS files and writes generated packages only under `analysis_output`.

## v062 Demo Script Pack Checks

- Adds `backend/demo_script_pack.py`.
- Adds `docs/demo_script_pack.md`.
- Adds `/api/demo-script-pack` status, create, list, detail and Markdown download routes.
- Adds a dashboard panel that creates a repeatable walkthrough script, screenshot smoke plan and contact sheet.
- Keeps source GIS files read-only and writes only generated demo evidence under `analysis_output`.
