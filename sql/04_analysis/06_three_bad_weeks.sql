-- Consecutive completed-delivery weeks by actual item sellers. Count each
-- (order, seller) only once; shared outcomes on multi-seller orders are noted.
WITH seller_orders AS (
    SELECT DISTINCT order_id, seller_id FROM analytics.clean_items
), weekly AS (
    SELECT si.seller_id, DATE_TRUNC('week', f.delivered_at)::date AS week,
           COUNT(*) AS deliveries, AVG(f.is_late::numeric) AS late_rate
    FROM seller_orders si
    JOIN analytics.fact_orders f USING (order_id)
    WHERE f.delivered_at IS NOT NULL AND f.is_late IS NOT NULL
    GROUP BY si.seller_id, DATE_TRUNC('week', f.delivered_at)::date
), bad_weeks AS (
    SELECT * FROM weekly
    WHERE deliveries >= 3 AND late_rate >= 0.15
), islands AS (
    SELECT *, week - (ROW_NUMBER() OVER (
        PARTITION BY seller_id ORDER BY week))::integer * 7 AS group_key
    FROM bad_weeks
)
SELECT seller_id, MIN(week) AS first_bad_week,
       MAX(week) AS last_bad_week, COUNT(*) AS consecutive_bad_weeks
FROM islands
GROUP BY seller_id, group_key
HAVING COUNT(*) >= 3
ORDER BY consecutive_bad_weeks DESC, seller_id;
