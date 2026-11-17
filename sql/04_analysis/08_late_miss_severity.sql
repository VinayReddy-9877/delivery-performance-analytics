-- Which state has the most serious late-order misses?
-- Use observed delivered dates only; a ten-day miss is not the same as a one-day miss.
WITH observed AS (
    SELECT customer_state, delivered_at::date - estimated_date AS miss_days,
           CASE WHEN is_late = 1 THEN 1 ELSE 0 END AS late_flag
    FROM analytics.fact_orders
    WHERE delivered_at IS NOT NULL AND estimated_date IS NOT NULL
)
SELECT customer_state,
       COUNT(*) AS assessed_orders,
       SUM(late_flag) AS late_orders,
       SUM(CASE WHEN miss_days BETWEEN 1 AND 3 THEN 1 ELSE 0 END) AS late_1_to_3_days,
       SUM(CASE WHEN miss_days BETWEEN 4 AND 9 THEN 1 ELSE 0 END) AS late_4_to_9_days,
       SUM(CASE WHEN miss_days >= 10 THEN 1 ELSE 0 END) AS late_10_plus_days,
       ROUND(AVG(late_flag::numeric), 4) AS late_rate,
       ROUND(SUM(CASE WHEN miss_days >= 10 THEN 1 ELSE 0 END)::numeric /
           NULLIF(SUM(late_flag), 0), 4) AS long_miss_share_of_late
FROM observed
GROUP BY customer_state
HAVING COUNT(*) >= 150
ORDER BY late_rate DESC;
