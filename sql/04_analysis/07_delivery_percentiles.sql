-- Business question: how long does delivery take at the median and p90 by state?
SELECT customer_state, COUNT(*) AS delivered_orders,
       ROUND(PERCENTILE_CONT(.5) WITHIN GROUP (
           ORDER BY EXTRACT(EPOCH FROM(delivered_at - purchase_at))/86400)::numeric,2) AS median_days,
       ROUND(PERCENTILE_CONT(.9) WITHIN GROUP (
           ORDER BY EXTRACT(EPOCH FROM(delivered_at - purchase_at))/86400)::numeric,2) AS p90_days
FROM analytics.fact_orders
WHERE delivered_at IS NOT NULL GROUP BY customer_state ORDER BY p90_days DESC;
