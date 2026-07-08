-- 06_signal_gap_major_roads.sql
-- Signal gap near major roads, via conditional aggregation. Of the destinations flagged within 150 m
-- of a mapped major road, how many also have a nearest mapped crossing with no signal evidence within
-- 50 m. "No signal evidence" is a data-quality gap (see docs/scope.md), not proof a signal is absent.
WITH flags AS (
    SELECT generator_id, flag FROM risk__risk_flags
)
SELECT
    SUM(CASE WHEN flag = 'major_road_within_150m' THEN 1 ELSE 0 END) AS near_major_road,
    SUM(CASE WHEN flag = 'nearest_crossing_near_major_road_without_signal_within_50m' THEN 1 ELSE 0 END)
        AS near_major_road_no_signal_evidence
FROM flags;
