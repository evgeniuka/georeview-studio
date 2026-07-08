-- 01_top20_worklist.sql
-- The field worklist: top 20 destinations to review on-site first, in the exact order the
-- live dashboard candidates endpoint uses, joined to any recorded reviewer decision.
--
-- Ranking key mirrors the app: (-route_review_priority_score, -risk_score, -nearest_crossing_m),
-- with generator_id appended as a final deterministic tie-break. The LEFT JOIN keeps every
-- candidate even when no decision has been recorded yet (the bundled demo has none).
SELECT
    n.generator_id,
    n.generator_type,
    n.name,
    r.nearest_crossing_m        AS straight_m,
    n.route_nearest_crossing_m  AS route_m,
    n.route_vs_straight_ratio   AS detour_ratio,
    n.route_review_priority_score AS score,
    COALESCE(d.status, 'unreviewed') AS review_status,
    d.assignee,
    n.review_wording
FROM network n
JOIN risk r ON r.generator_id = n.generator_id
LEFT JOIN decisions d ON d.generator_id = n.generator_id
ORDER BY
    n.route_review_priority_score DESC,
    r.risk_score DESC,
    r.nearest_crossing_m DESC,
    n.generator_id ASC
LIMIT 20;
