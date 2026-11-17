-- Do not calculate MoM growth across tiny or missing monthly cohorts.
WITH summary AS (
 SELECT DATE_TRUNC('month',purchase_at)::date AS month,
        COUNT(*) AS orders, SUM(gmv) AS merchandise_gmv,
        AVG(is_late::numeric) AS late_rate
 FROM analytics.fact_orders GROUP BY 1
), with_prior AS (
 SELECT *, LAG(orders) OVER (ORDER BY month) AS prior_orders,
           LAG(merchandise_gmv) OVER (ORDER BY month) AS prior_gmv,
           LAG(month) OVER (ORDER BY month) AS prior_month
 FROM summary
)
SELECT month, orders, merchandise_gmv, ROUND(late_rate,4) AS late_rate,
 CASE WHEN orders>=500 AND prior_orders>=500 AND prior_month=month-INTERVAL '1 month'
      THEN ROUND(100*(merchandise_gmv-prior_gmv)/NULLIF(prior_gmv,0),2) END AS mom_gmv_pct
FROM with_prior ORDER BY month;
