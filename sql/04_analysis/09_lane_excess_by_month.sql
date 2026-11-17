-- A same-state benchmark is a comparison, not an estimate of preventable delays.
WITH comparison AS (
    SELECT AVG(is_late::numeric) AS baseline_rate
    FROM analytics.fact_orders
    WHERE is_late IS NOT NULL
      AND distinct_sellers = 1
      AND seller_state = customer_state
), lane_month AS (
    SELECT seller_state, customer_state,
           DATE_TRUNC('month', purchase_at)::date AS purchase_month,
           COUNT(*) AS assessed_orders,
           SUM(is_late) AS late_orders,
           SUM(CASE WHEN is_late = 1 THEN gmv ELSE 0 END) AS late_gmv_brl
    FROM analytics.fact_orders
    WHERE is_late IS NOT NULL AND distinct_sellers = 1
      AND seller_state <> 'Unknown'
    GROUP BY 1, 2, 3
)
SELECT seller_state, customer_state, purchase_month,
       assessed_orders, late_orders, late_gmv_brl,
       ROUND(late_orders::numeric / assessed_orders, 4) AS late_rate,
       ROUND(assessed_orders * baseline_rate, 1) AS benchmark_late_orders,
       ROUND(late_orders - assessed_orders * baseline_rate, 1) AS excess_vs_benchmark
FROM lane_month CROSS JOIN comparison
WHERE assessed_orders >= 30
ORDER BY excess_vs_benchmark DESC, assessed_orders DESC;
