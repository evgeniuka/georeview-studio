# PostGIS Backend Option v001

v027 adds a PostGIS-oriented planning layer for larger-region analysis.

This is not a live database connection. The local app does not read credentials, does not modify `.env`, and does not connect to Postgres.

## Artifacts

- `config/postgis_schema_v001.sql`
- `backend/postgis_backend.py`

## API

- `GET /api/postgis-backend`
- `GET /api/postgis-backend/schema`
- `GET /api/postgis-backend/migration-plan`
- `POST /api/postgis-backend/migration-plan`
- `GET /api/postgis-backend/plans`
- `GET /api/postgis-backend/{plan_id}`

## Purpose

PostGIS is the natural backend option when the project grows from one pilot city to larger regions. It provides spatial indexes, SQL joins, and better storage for repeated profile results.

Current status: schema and migration planning are ready. ETL loader and real database connection are intentionally not implemented yet.
