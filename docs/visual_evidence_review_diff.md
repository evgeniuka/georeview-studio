# Visual Evidence Review Diff

v067 adds a local reviewer diff over completed Visual Evidence Capture artifacts.

The feature compares two ready screenshot capture sets and produces:

- JSON manifest with screenshot hashes, byte-size deltas and metadata changes.
- Markdown review summary.
- Standalone HTML side-by-side screenshot review page.

API endpoints:

- `GET /api/visual-evidence-review-diff`
- `POST /api/visual-evidence-review-diff/create`
- `GET /api/visual-evidence-review-diff/diffs`
- `GET /api/visual-evidence-review-diff/diffs/{diff_id}`
- `GET /api/visual-evidence-review-diff/diffs/{diff_id}/download`

Claim boundary:

- This compares generated local screenshots only.
- It is not field verification, crash prediction, or an absolute site condition claim.
- Source GIS files remain read-only.
