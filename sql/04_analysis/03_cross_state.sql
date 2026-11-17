-- Multi-seller orders lack one unambiguous state of origin: exclude them.
SELECT CASE WHEN seller_state=customer_state THEN 'same_state' ELSE 'cross_state' END AS lane,
       COUNT(*) AS assessed, ROUND(AVG(is_late::numeric),4) AS late_rate
FROM analytics.fact_orders
WHERE is_late IS NOT NULL AND distinct_sellers=1 AND seller_state<>'Unknown'
GROUP BY 1 ORDER BY 1;
