-- State priority is based on sample size and actual late-order merchandise value.
SELECT customer_state, COUNT(*) FILTER(WHERE is_late IS NOT NULL) AS assessed,
       COUNT(*) FILTER(WHERE is_late=1) AS late_orders,
       ROUND(AVG(is_late::numeric),4) AS late_rate,
       ROUND(SUM(gmv) FILTER(WHERE is_late=1),2) AS late_gmv_brl
FROM analytics.fact_orders
GROUP BY 1 HAVING COUNT(*) FILTER(WHERE is_late IS NOT NULL)>=150
ORDER BY late_gmv_brl DESC NULLS LAST;
