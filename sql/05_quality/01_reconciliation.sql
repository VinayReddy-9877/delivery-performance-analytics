-- Expected: mismatch count = 0, overall delta = 0.00 and no duplicated order IDs.
SELECT COUNT(*) AS fact_orders,
       COUNT(*)-COUNT(DISTINCT order_id) AS duplicate_orders,
       COUNT(*) FILTER(WHERE ABS(gmv-item_gmv)>0.01) AS failed_item_reconciliations,
       ROUND(SUM(gmv-item_gmv),2) AS total_difference_brl
FROM analytics.fact_orders;
