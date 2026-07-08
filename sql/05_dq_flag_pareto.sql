-- 05_dq_flag_pareto.sql
-- Data-quality flag pareto: how many distinct destinations carry each evidence-gap flag. The two
-- data_quality_flags bridge tables are UNION-ed (not UNION ALL) so a flag present on both the risk
-- and network side counts a destination once. These are evidence gaps, not confirmed absences.
WITH dq AS (
    SELECT generator_id, flag FROM network__data_quality_flags
    UNION
    SELECT generator_id, flag FROM risk__data_quality_flags
)
SELECT flag, COUNT(DISTINCT generator_id) AS destinations
FROM dq
GROUP BY flag
ORDER BY destinations DESC, flag;
