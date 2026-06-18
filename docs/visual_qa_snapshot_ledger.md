# Visual QA Snapshot Ledger

v063 adds a lightweight visual QA ledger for portfolio walkthroughs.

The ledger turns a ready Demo Script Pack into:

- a JSON manifest;
- a Markdown visual QA checklist;
- a small HTML contact sheet;
- per-target capture/review status fields.

The feature is local-first and evidence-only. It does not capture screenshots automatically, does not modify source GIS files, and does not make field safety claims.

## API

- `GET /api/visual-qa-snapshot-ledger`
- `POST /api/visual-qa-snapshot-ledger/create`
- `GET /api/visual-qa-snapshot-ledger/ledgers`
- `GET /api/visual-qa-snapshot-ledger/ledgers/{ledger_id}`
- `GET /api/visual-qa-snapshot-ledger/ledgers/{ledger_id}/download`

## Output

Generated ledgers are written under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_visual_qa_ledgers
```

## Claim Boundary

Approved review wording remains:

```text
This location has infrastructure risk indicators and should be reviewed on-site.
```

Visual QA checks demo readability and generated artifact review flow. It is not a field survey, crash model, or proof of real-world infrastructure condition.
