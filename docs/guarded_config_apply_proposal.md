# Guarded Config Apply Proposal

v040 adds a proposal-only layer for reviewing a potential profile mapper config change.

## Purpose

The workflow creates a proposed `profile_mapper_contracts_v001.json` preview under `analysis_output` after:

- a promotion proposal exists;
- a contract diff review exists;
- an application plan exists;
- the target config hash is recorded.

## API

- `GET /api/profile-promotion/apply-candidates`
- `POST /api/profile-promotion/config-apply-proposal`
- `GET /api/profile-promotion/config-apply-proposals`
- `GET /api/profile-promotion/config-apply-proposals/{apply_id}`

## Safety Boundary

This workflow does not modify `profile_mapper_contracts_v001.json`.

It writes only preview artifacts under `analysis_output/georeview_studio_profile_promotions`. Any real config change requires a separate explicit config-change task.

Source GIS files remain read-only.

Approved wording remains: This location has infrastructure risk indicators and should be reviewed on-site.
