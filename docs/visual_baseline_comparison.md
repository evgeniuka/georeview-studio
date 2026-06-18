# Visual Baseline Comparison Manifest

v064 adds a generated comparison manifest for Visual QA Snapshot Ledgers.

The feature compares a baseline ledger and a latest ledger, then writes:

- a JSON comparison manifest;
- a Markdown reviewer summary;
- target-level added / removed / changed / unchanged rows;
- review recommendations for screenshot capture and portfolio walkthrough QA.

The comparison uses generated Visual QA ledger metadata only. It does not inspect, copy, modify, move, rename or overwrite source GIS files.

## API

- `GET /api/visual-baseline-comparison`
- `POST /api/visual-baseline-comparison/create`
- `GET /api/visual-baseline-comparison/comparisons`
- `GET /api/visual-baseline-comparison/comparisons/{comparison_id}`
- `GET /api/visual-baseline-comparison/comparisons/{comparison_id}/download`

## Output

Generated comparisons are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_visual_baseline_comparisons
```

## Claim Boundary

Approved review wording remains:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```

This feature compares demo/reviewer metadata only. It is not field verification, not crash prediction, and not an absolute site condition claim.
