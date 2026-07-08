-- 03_distance_buckets.sql
-- Route-distance distribution with a running (cumulative) count, via a CTE plus a window SUM.
-- Buckets are upper-inclusive; the unreachable destination is its own bucket (data-quality gap).
WITH bucketed AS (
    SELECT
        CASE
            WHEN route_nearest_crossing_m IS NULL       THEN 4
            WHEN route_nearest_crossing_m <= 100        THEN 0
            WHEN route_nearest_crossing_m <= 250        THEN 1
            WHEN route_nearest_crossing_m <= 500        THEN 2
            ELSE 3
        END AS ord,
        CASE
            WHEN route_nearest_crossing_m IS NULL       THEN 'unreachable'
            WHEN route_nearest_crossing_m <= 100        THEN '0-100 m'
            WHEN route_nearest_crossing_m <= 250        THEN '100-250 m'
            WHEN route_nearest_crossing_m <= 500        THEN '250-500 m'
            ELSE '500+ m'
        END AS bucket
    FROM network
),
per_bucket AS (
    SELECT ord, bucket, COUNT(*) AS destinations
    FROM bucketed
    GROUP BY ord, bucket
)
SELECT
    bucket,
    destinations,
    SUM(destinations) OVER (ORDER BY ord ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative
FROM per_bucket
ORDER BY ord;
