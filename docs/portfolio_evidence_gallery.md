# Portfolio Evidence Gallery

v048 indexes generated portfolio evidence into one standalone local HTML gallery.

The gallery does not read or mutate source GIS files. It reads existing generated artifacts from `analysis_output`, optionally creates a fresh handoff page through the existing handoff/narrative/bundle chain, and writes small JSON/HTML files under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_portfolio_evidence_galleries
```

## API

- `GET /api/portfolio-evidence-gallery`
- `POST /api/portfolio-evidence-gallery/create`
- `GET /api/portfolio-evidence-gallery/galleries`
- `GET /api/portfolio-evidence-gallery/galleries/{gallery_id}`
- `GET /api/portfolio-evidence-gallery/galleries/{gallery_id}/download`

## Indexed Evidence

- portfolio handoff pages;
- portfolio narratives;
- evidence bundles;
- bundle review checklists;
- portfolio reports;
- release readiness summary;
- validation and API contract summaries.

## Claim Boundary

The gallery is a portfolio evidence index for infrastructure review indicators and data-quality flags. It is not a crash prediction artifact and does not make absolute safety claims.
