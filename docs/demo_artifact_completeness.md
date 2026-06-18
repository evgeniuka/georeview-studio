# Demo Artifact Completeness Validator

v065 adds a generated completeness check for the local portfolio demo artifacts.

The validator answers a practical release question:

```text
Are the generated demo, package, QA and comparison artifacts present and ready to review before sharing the project?
```

It validates generated files and metadata only. It does not inspect field conditions, does not predict crashes, and does not make absolute site condition claims.

## API

- `GET /api/demo-artifact-completeness`
- `POST /api/demo-artifact-completeness/create`
- `GET /api/demo-artifact-completeness/checks`
- `GET /api/demo-artifact-completeness/checks/{check_id}`
- `GET /api/demo-artifact-completeness/checks/{check_id}/download`

## Checked Artifact Groups

- release manifest and local validation summaries;
- portfolio HTML, static map and sample CSV;
- portfolio evidence bundle;
- bundle review checklist;
- portfolio narrative;
- portfolio handoff page;
- portfolio evidence gallery;
- portable release package;
- demo script pack;
- visual QA ledger;
- visual baseline comparison.

## Output

Generated checks are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_demo_artifact_completeness
```

Each check writes:

- `demo_artifact_completeness_manifest.json`;
- `demo_artifact_completeness_report.md`;
- `latest_demo_artifact_completeness.json`.

## Claim Boundary

Approved review wording remains:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```

The validator checks generated demo artifacts only. Source GIS files remain read-only.
