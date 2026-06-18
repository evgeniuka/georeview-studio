# Profile Mapper SDK

GeoReview Studio v028 adds a planning layer for reusable analysis profile templates.

The mapper SDK is intentionally contract-first:

```text
source dataset evidence
  -> profile mapper contract
  -> compatibility check
  -> mapper plan
  -> existing or future profile runner
  -> normalized profile dashboard rows
```

## What It Solves

Before v028, new profiles were possible but still required reading the backend code to understand required layers, canonical outputs, and scoring links.

v028 makes those expectations explicit in:

```text
config/profile_mapper_contracts_v001.json
backend/profile_mapper.py
```

The current SDK does not execute arbitrary uploaded data. It validates contracts, checks local source compatibility, and writes small mapper plans under:

```text
D:\cloude_work\georeview-studio\analysis_output\georeview_studio_profile_mapper_plans
```

## Public API

- `GET /api/profile-mapper`
- `GET /api/profile-mapper/contracts`
- `GET /api/profile-mapper/contracts/{profile_id}`
- `GET /api/profile-mapper/compatibility`
- `GET /api/profile-mapper/plan`
- `POST /api/profile-mapper/plan`
- `GET /api/profile-mapper/plans`
- `GET /api/profile-mapper/plans/{plan_id}`

## Current Contracts

- `safe_access_pedestrian_review`
- `transit_stop_walk_access`
- `park_playground_access`
- `cycling_micromobility_access`
- `osm_tag_quality`
- `generic_layer_inventory`

The first three have implemented runners. The other three are explicit contracts for future work or read-only planning.

## Safety Boundary

The mapper SDK does not modify source GIS files, does not read credentials, and does not make crash-prediction or absolute safety claims.

Missing OSM tags remain data-quality evidence. They are not treated as proof that infrastructure is absent.
