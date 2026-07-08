-- 02_evidence_coverage.sql
-- Evidence coverage (fill rate) for the attributes the priority score cannot see. "present" counts
-- a non-null tag value; a blank stays a data-quality gap, never treated as absent infrastructure.
-- Low coverage here is exactly why the score must not be read as a sidewalk/lighting assessment.
SELECT 'crossings' AS layer, 'tactile_paving' AS attribute,
       SUM(CASE WHEN tactile_paving   IS NOT NULL THEN 1 ELSE 0 END) AS present, COUNT(*) AS total FROM crossings
UNION ALL
SELECT 'crossings', 'kerb',
       SUM(CASE WHEN kerb             IS NOT NULL THEN 1 ELSE 0 END), COUNT(*) FROM crossings
UNION ALL
SELECT 'crossings', 'crossing_island',
       SUM(CASE WHEN crossing_island  IS NOT NULL THEN 1 ELSE 0 END), COUNT(*) FROM crossings
UNION ALL
SELECT 'roads', 'maxspeed_effective',
       SUM(CASE WHEN maxspeed_effective IS NOT NULL THEN 1 ELSE 0 END), COUNT(*) FROM road_segments
UNION ALL
SELECT 'roads', 'sidewalk',
       SUM(CASE WHEN sidewalk         IS NOT NULL THEN 1 ELSE 0 END), COUNT(*) FROM road_segments
UNION ALL
SELECT 'roads', 'lit',
       SUM(CASE WHEN lit              IS NOT NULL THEN 1 ELSE 0 END), COUNT(*) FROM road_segments;
