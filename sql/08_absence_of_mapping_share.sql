-- 08_absence_of_mapping_share.sql
-- What the score does NOT say. Split total priority points by rule kind: rules that fire on the
-- ABSENCE of a mapped feature (no mapped crossing, no mapped traffic calming, no mapped signal at the
-- nearest crossing) versus rules that fire on a mapped condition. A large absence share means the
-- score is driven by what is not on the map; a missing tag is a data-quality gap, per docs/scope.md.
WITH fired AS (
    SELECT generator_id, flag FROM network__network_flags
    UNION ALL
    SELECT generator_id, flag FROM risk__risk_flags
),
by_kind AS (
    SELECT w.kind, SUM(w.weight) AS points
    FROM fired f
    JOIN rule_weights w ON w.flag = f.flag
    GROUP BY w.kind
)
SELECT
    kind,
    points,
    ROUND(100.0 * points / (SELECT SUM(points) FROM by_kind), 1) AS share_pct
FROM by_kind
ORDER BY points DESC;
