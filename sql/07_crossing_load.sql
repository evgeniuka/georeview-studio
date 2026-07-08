-- 07_crossing_load.sql
-- Crossing load, via a reversed LEFT JOIN (crossings on the left). For each crossing type, how many
-- crossings exist and how many destinations depend on them as their nearest crossing by route. The
-- reversed join keeps crossing types that serve zero destinations, exposing unused mapped crossings.
SELECT
    c.crossing_type,
    COUNT(DISTINCT c.crossing_id)                                   AS crossings,
    COUNT(DISTINCT n.generator_id)                                  AS destinations_served,
    COUNT(DISTINCT CASE WHEN n.generator_id IS NOT NULL THEN c.crossing_id END) AS crossings_used
FROM crossings c
LEFT JOIN network n ON n.route_nearest_crossing_id = c.crossing_id
GROUP BY c.crossing_type
ORDER BY destinations_served DESC, c.crossing_type;
