-- 04_score_integrity.sql
-- Score-decomposition integrity check. Recompute every destination's priority score from its fired
-- weighted rules (common risk flags UNION route-proxy flags, joined to rule_weights) and surface any
-- row whose recompute does not RECONCILE WITH the stored route_review_priority_score.
-- The report runs this and asserts the result set is empty (zero mismatching rows).
WITH fired AS (
    SELECT generator_id, flag FROM network__network_flags
    UNION ALL
    SELECT generator_id, flag FROM risk__risk_flags
),
recomputed AS (
    SELECT f.generator_id, COALESCE(SUM(w.weight), 0) AS score
    FROM fired f
    JOIN rule_weights w ON w.flag = f.flag
    GROUP BY f.generator_id
)
SELECT
    n.generator_id,
    n.route_review_priority_score AS stored,
    COALESCE(rc.score, 0)         AS recomputed
FROM network n
LEFT JOIN recomputed rc ON rc.generator_id = n.generator_id
WHERE n.route_review_priority_score <> COALESCE(rc.score, 0)
ORDER BY n.generator_id;
