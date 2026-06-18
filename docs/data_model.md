# Data Model

The app uses canonical Safe Access tables.

## source_onboarding_catalog

Derived JSON/CSV cache under `analysis_output/georeview_studio_source_onboarding`.

Key fields:

- `dataset_id`
- `file_name`
- `path`
- `extension`
- `size_mb`
- `modified_utc`
- `likely_role`
- `profile_status`
- `layers`
- `readiness`
- `source_gis_modified`

This catalog is a lightweight onboarding profile. It reads source files read-only and does not replace the deeper GIS audit.

## pilot_areas

Derived catalog from `gis_osm_places_a_free_1` inside the Geofabrik Shapefile ZIP.

Key fields:

- `osm_id`
- `name`
- `fclass`
- `population`
- `bbox_min_lon`
- `bbox_min_lat`
- `bbox_max_lon`
- `bbox_max_lat`
- `pbf_enriched_workspace_id`
- `route_aware_workspace_id`

These polygons are useful for pilot selection. They are OSM/Geofabrik place polygons, not official municipal boundaries.

## preflight_result

JSON response from `GET /api/preflight/safe-access-pilot` or `POST /api/preflight/safe-access-pilot`.

Key fields:

- `pilot`
- `dataset`
- `required_layers`
- `pbf_enrichment`
- `workspaces`
- `estimate`
- `warnings`
- `claim_boundaries`
- `can_start_job`
- `source_gis_modified`

This model is a readiness report. It is generated from catalog metadata and workspace manifests, not from a new GIS analysis run.

## analysis_workflow_plan

JSON response from `GET /api/analysis-workflow/plan` or `POST /api/analysis-workflow/plan`.

Key fields:

- `workflow_version`
- `template_id`
- `dataset_id`
- `pilot_osm_id`
- `source`
- `pilot`
- `preflight`
- `steps`
- `job_payload`
- `can_start_job`
- `active_workspace_id`
- `source_gis_modified`

This model is the user-facing bridge between data onboarding and an executable workspace build.

## analysis_profile

Product-level profile metadata from `backend/analysis_profiles.py`.

Key fields:

- `profile_id`
- `legacy_template_id`
- `name`
- `domain`
- `status`
- `runner_status`
- `description`
- `input_needs`
- `outputs`
- `readiness_level`
- `can_plan`
- `can_run`
- `blockers`

Profiles separate the product roadmap from implemented runners. A profile can be visible and useful for readiness analysis even before its full calculation runner exists.

## analysis_profile_readiness

Readiness evidence for a profile against a selected source and optional pilot area.

Key fields:

- `profile_id`
- `dataset_id`
- `readiness_level`
- `can_plan`
- `can_run`
- `implemented_runner`
- `blockers`
- `evidence`
- `recommended_next_action`
- `source_gis_modified`

The `evidence` object includes source readiness, layer count, capability flags, and Safe Access preflight evidence where relevant.

## profile_workspace

Profile-specific generated workspace under `analysis_output/georeview_studio_workspaces`.

Key fields:

- `workspace_id`
- `profile_id`
- `profile_workspace`
- `base_workspace_id`
- `created_at_utc`
- `analyzer`
- `tables`
- `reports`
- `source_gis_modified`

Implemented profile workspaces include `transit_stop_walk_access_kfar_saba_v001` and `park_playground_access_kfar_saba_v001`.

## transit_stop_access_results

Profile table for bus-stop walk-access review.

Key fields:

- `transit_stop_id`
- `osm_id`
- `name`
- `nearest_crossing_id`
- `nearest_crossing_m`
- `crossing_within_150m`
- `route_nearest_crossing_id`
- `route_nearest_crossing_m`
- `route_vs_straight_ratio`
- `nearest_major_road_class`
- `nearest_major_road_m`
- `major_road_within_150m`
- `signals_within_50m`
- `traffic_calming_within_100m`
- `base_risk_score`
- `transit_review_priority_score`
- `transit_access_flags`
- `data_quality_flags`
- `review_wording`

The table is derived from Safe Access outputs. It is a profile-specific review-priority table, not a claim about real-world access conditions.

## park_playground_access_results

Profile table for public-space access review.

Key fields:

- `public_space_id`
- `osm_id`
- `place_type`
- `name`
- `nearest_crossing_id`
- `nearest_crossing_m`
- `crossing_within_100m`
- `crossing_within_150m`
- `route_nearest_crossing_id`
- `route_nearest_crossing_m`
- `route_vs_straight_ratio`
- `nearest_major_road_class`
- `nearest_major_road_m`
- `major_road_within_150m`
- `signals_within_50m`
- `traffic_calming_within_100m`
- `base_risk_score`
- `public_space_review_priority_score`
- `public_space_access_flags`
- `data_quality_flags`
- `review_wording`

The table is derived from Safe Access outputs for parks, playgrounds, community centres, and recreation grounds. Mapped public-space geometry may be a point, polygon centroid, or representative feature, so results are field-review indicators only.

## analysis_run

Derived read model over durable job records and workspace manifests.

Key fields:

- `run_id`
- `run_type`
- `status`
- `dataset_id`
- `pilot_osm_id`
- `pilot_name`
- `active_workspace_id`
- `output_count`
- `dashboard_links`
- `outputs`
- `logs`
- `source_gis_modified`

Outputs include CSV tables and JSON/CSV reports from the generated workspace, exposed through local download URLs.

## portfolio_report

Generated Markdown/JSON report under `analysis_output/georeview_studio_portfolio_reports`.

Key fields:

- `report_id`
- `report_type`
- `generated_at_utc`
- `run`
- `profile_id`
- `workspace_id`
- `base_workspace_id`
- `counts`
- `route_aware_metrics`
- `median_route_nearest_crossing_m`
- `top_flags`
- `validation`
- `outputs`
- `top_candidates`
- `top_transit_stops`
- `claim_boundaries`
- `source_gis_modified`

The report is an evidence package for a completed analysis run or a profile workspace. It is generated from existing run records, workspace manifests, summaries, and small CSV samples. It does not create large derived GIS files.

## portfolio_run_compare

Generated Markdown/JSON report comparing two or more completed analysis runs.

Key fields:

- `report_id`
- `report_type`
- `generated_at_utc`
- `runs`
- `errors`
- `claim_boundaries`
- `source_gis_modified`

Run comparison is a reproducibility and product QA artifact. It checks output consistency across runs, not real-world safety.

## portfolio_profile_comparison

Generated Markdown/JSON report comparing implemented profile workspaces on one base Safe Access workspace.

Key fields:

- `report_id`
- `report_type`
- `base_workspace_id`
- `base_profile`
- `profiles`
- `comparison_rows`
- `claim_boundaries`
- `source_gis_modified`

The default comparison covers `safe_access_pedestrian_review`, `transit_stop_walk_access`, and `park_playground_access`. It is a portfolio evidence artifact for reusable analytics coverage, not a ranking of real-world safety.

## job_records

Durable JSON records under `analysis_output/georeview_studio_runs`.

Key fields:

- `job_id`
- `job_type`
- `status`
- `created_at_utc`
- `started_at_utc`
- `finished_at_utc`
- `runtime_seconds`
- `payload`
- `logs`
- `result`
- `error`
- `source_gis_modified`

These records make long workspace builds auditable and recoverable from the local filesystem.

## pedestrian_generators

Point features representing schools, kindergartens, childcare, bus stops, parks, playgrounds, and related pedestrian generators.

Key fields:

- `generator_id`
- `osm_id`
- `generator_type`
- `name`
- `source_layer`
- `data_quality_flags`
- `geometry_wkt`
- `lon`
- `lat`

## crossings

Point features for mapped pedestrian crossings.

Key fields:

- `crossing_id`
- `osm_id`
- `crossing_type`
- `has_signal_nearby`
- `tactile_paving`
- `kerb`
- `crossing_island`
- `geometry_wkt`

## road_segments

Road features used for proximity and infrastructure tag checks.

Key fields:

- `road_id`
- `osm_id`
- `highway_class`
- `name`
- `maxspeed_effective`
- `oneway_effective`
- `sidewalk`
- `lit`
- `geometry_wkt`

## risk_assessment_results

Per-generator infrastructure indicator table.

Key fields:

- `nearest_crossing_m`
- `nearest_major_road_m`
- `crossing_within_150m`
- `major_road_within_150m`
- `signals_within_50m`
- `traffic_calming_within_100m`
- `risk_score`
- `risk_flags`
- `data_quality_flags`
- `review_wording`

Missing tags do not add risk points unless the tag explicitly indicates a negative condition, such as `sidewalk=no` or `lit=no`.

## network_access_results

Per-generator route-aware proxy table for `safe_access_kfar_saba_route_aware_v001`.

Key fields:

- `route_nearest_crossing_id`
- `route_nearest_crossing_m`
- `straight_distance_to_route_crossing_m`
- `route_vs_straight_ratio`
- `reachable_crossings`
- `generator_network_attach_m`
- `network_status`
- `network_flags`
- `route_review_priority_score`
- `data_quality_flags`
- `review_wording`

This table is derived from OSM road-segment geometry. It is a mapped-network review indicator, not verified walking navigation.

## Product Architecture Tables

v024 documents `source_datasets`, `dataset_layers`, normalized profile result tables, `analysis_runs`, and `portfolio_reports` as the minimum internal model for a reusable GIS review workbench.

## v027 PostGIS Backend Option

- `config/postgis_schema_v001.sql`
- `backend/postgis_backend.py`
- `GET /api/postgis-backend`
- `GET /api/postgis-backend/schema`
- `GET /api/postgis-backend/migration-plan`
- `POST /api/postgis-backend/migration-plan`
- `GET /api/postgis-backend/plans`
- `GET /api/postgis-backend/{plan_id}`

This is a planning layer only. It does not open a database connection, does not read credentials, and does not modify source GIS files.
