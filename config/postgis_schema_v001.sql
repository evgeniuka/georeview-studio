-- GeoReview Studio PostGIS schema v001
-- Planning schema only. No database connection is made by the local app.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS georeview;

CREATE TABLE IF NOT EXISTS georeview.source_datasets (
  dataset_id text PRIMARY KEY,
  file_name text NOT NULL,
  source_path text NOT NULL,
  extension text NOT NULL,
  size_mb numeric,
  modified_utc timestamptz,
  readiness_level text,
  source_gis_modified boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS georeview.dataset_layers (
  dataset_id text REFERENCES georeview.source_datasets(dataset_id),
  layer_name text NOT NULL,
  geometry_type text,
  crs text,
  feature_count bigint,
  useful_columns jsonb NOT NULL DEFAULT '[]'::jsonb,
  PRIMARY KEY (dataset_id, layer_name)
);

CREATE TABLE IF NOT EXISTS georeview.pilot_areas (
  pilot_osm_id text PRIMARY KEY,
  name text,
  source_dataset_id text,
  boundary geometry(MultiPolygon, 4326),
  boundary_itm geometry(MultiPolygon, 2039),
  boundary_source text NOT NULL DEFAULT 'OSM/Geofabrik place polygon'
);

CREATE TABLE IF NOT EXISTS georeview.pedestrian_generators (
  generator_id text PRIMARY KEY,
  osm_id text,
  generator_type text NOT NULL,
  name text,
  source_layer text,
  pilot_osm_id text REFERENCES georeview.pilot_areas(pilot_osm_id),
  geom geometry(Point, 2039) NOT NULL,
  lon double precision,
  lat double precision,
  data_quality_flags jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS georeview.crossings (
  crossing_id text PRIMARY KEY,
  osm_id text,
  crossing_type text,
  has_signal_nearby boolean,
  tactile_paving text,
  kerb text,
  crossing_island text,
  geom geometry(Point, 2039) NOT NULL
);

CREATE TABLE IF NOT EXISTS georeview.road_segments (
  road_id text PRIMARY KEY,
  osm_id text,
  highway_class text NOT NULL,
  name text,
  maxspeed text,
  oneway text,
  sidewalk text,
  lit text,
  geom geometry(LineString, 2039) NOT NULL
);

CREATE TABLE IF NOT EXISTS georeview.transit_stops (
  transit_stop_id text PRIMARY KEY,
  osm_id text,
  name text,
  geom geometry(Point, 2039) NOT NULL,
  lon double precision,
  lat double precision
);

CREATE TABLE IF NOT EXISTS georeview.public_spaces (
  public_space_id text PRIMARY KEY,
  osm_id text,
  place_type text NOT NULL,
  name text,
  source_layer text,
  geom geometry(Point, 2039) NOT NULL,
  lon double precision,
  lat double precision
);

CREATE TABLE IF NOT EXISTS georeview.analysis_runs (
  run_id text PRIMARY KEY,
  run_type text NOT NULL,
  status text NOT NULL,
  active_workspace_id text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  source_gis_modified boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS georeview.profile_results (
  profile_id text NOT NULL,
  workspace_id text NOT NULL,
  result_id text NOT NULL,
  entity_type text,
  name text,
  primary_score integer NOT NULL,
  secondary_score integer,
  score_label text,
  nearest_crossing_m numeric,
  route_nearest_crossing_m numeric,
  nearest_major_road_m numeric,
  flags jsonb NOT NULL DEFAULT '[]'::jsonb,
  data_quality_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_wording text NOT NULL,
  geom geometry(Point, 2039),
  lon double precision,
  lat double precision,
  source_table text,
  source_gis_modified boolean NOT NULL DEFAULT false,
  PRIMARY KEY (profile_id, workspace_id, result_id)
);

CREATE TABLE IF NOT EXISTS georeview.scoring_rules (
  scoring_rules_version text NOT NULL,
  profile_id text NOT NULL,
  rule_id text NOT NULL,
  rule_group text NOT NULL,
  points integer NOT NULL,
  condition jsonb NOT NULL,
  evidence text,
  PRIMARY KEY (scoring_rules_version, profile_id, rule_id)
);

CREATE INDEX IF NOT EXISTS idx_pilot_areas_boundary_itm ON georeview.pilot_areas USING gist (boundary_itm);
CREATE INDEX IF NOT EXISTS idx_generators_geom ON georeview.pedestrian_generators USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_crossings_geom ON georeview.crossings USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_roads_geom ON georeview.road_segments USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_transit_geom ON georeview.transit_stops USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_public_spaces_geom ON georeview.public_spaces USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_profile_results_geom ON georeview.profile_results USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_profile_results_profile_score ON georeview.profile_results (profile_id, primary_score DESC);
CREATE INDEX IF NOT EXISTS idx_profile_results_flags ON georeview.profile_results USING gin (flags);
CREATE INDEX IF NOT EXISTS idx_profile_results_quality ON georeview.profile_results USING gin (data_quality_flags);
