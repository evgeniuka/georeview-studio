# Public Portfolio Interview Package

v072 adds a public portfolio package over the already validated recruiter demo brief.

The package creates:

- `public_portfolio_readme.md`
- `interview_walkthrough.md`
- `public_portfolio_interview_package.html`
- `public_portfolio_interview_package_manifest.json`

The purpose is to answer the product and interview questions directly: what value the app gives, what architecture exists, what analytics are supported, what the claim boundaries are, and how the project can grow.

The package does not modify source GIS data. It reads the generated recruiter brief, validation summary, API contract summary and project manifest, then writes small reviewer artifacts under `analysis_output/georeview_studio_public_portfolio_packages`.

## API

- `GET /api/public-portfolio-package`
- `POST /api/public-portfolio-package/create`
- `GET /api/public-portfolio-package/packages`
- `GET /api/public-portfolio-package/packages/{package_id}`
- `GET /api/public-portfolio-package/packages/{package_id}/download`

## Claim Boundary

Approved wording:

`This location has infrastructure risk indicators and should be reviewed on-site.`

Missing OSM tags remain data-quality flags. The package frames the product as infrastructure review prioritization, not crash prediction.
