-- Attribution: one delivery outcome per (order, seller), even for multi-item
-- orders. On multi-seller orders, each participating seller receives the shared
-- order-level outcome; this does not establish which seller caused a delay.
WITH seller_orders AS (
    SELECT DISTINCT order_id, seller_id
    FROM analytics.clean_items
), daily AS (
    SELECT si.seller_id, f.delivered_at::date AS delivery_day,
           COUNT(*) AS deliveries, SUM(f.is_late) AS late_deliveries
    FROM seller_orders si
    JOIN analytics.fact_orders f USING (order_id)
    WHERE f.delivered_at IS NOT NULL AND f.is_late IS NOT NULL
    GROUP BY si.seller_id, f.delivered_at::date
)
SELECT seller_id, delivery_day, deliveries,
       SUM(deliveries) OVER w AS deliveries_30d,
       SUM(late_deliveries) OVER w AS late_deliveries_30d,
       ROUND(SUM(late_deliveries) OVER w * 1.0 /
             NULLIF(SUM(deliveries) OVER w, 0), 4) AS late_rate_30d
FROM daily
WINDOW w AS (
    PARTITION BY seller_id ORDER BY delivery_day::timestamp
    RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW
);
