-- Detect entrants AND exits by comparing contiguous calendar months' top 20.
-- Use allocated item revenue, not the whole multi-seller order GMV.
WITH revenue AS (
 SELECT DATE_TRUNC('month',o.purchase_at)::date AS month,
        i.seller_id, SUM(i.price) AS gmv
 FROM analytics.clean_items i JOIN analytics.fact_orders o USING(order_id)
 GROUP BY 1,2
), ranked AS (
 SELECT *, ROW_NUMBER() OVER(PARTITION BY month ORDER BY gmv DESC,seller_id) AS position
 FROM revenue
), top20 AS (
 SELECT month,seller_id,position,gmv FROM ranked WHERE position<=20
), changes AS (
 SELECT COALESCE(cur.month, prev.month+INTERVAL '1 month')::date AS month,
        COALESCE(cur.seller_id,prev.seller_id) AS seller_id,
        prev.position AS prior_position,cur.position AS current_position,
        CASE WHEN prev.seller_id IS NULL THEN 'ENTERED'
             WHEN cur.seller_id IS NULL THEN 'EXITED' ELSE 'STAYED' END AS movement
 FROM top20 cur FULL JOIN top20 prev
   ON cur.seller_id=prev.seller_id AND cur.month=prev.month+INTERVAL '1 month'
)
SELECT c.* FROM changes c JOIN (SELECT DISTINCT month FROM revenue) observed USING (month) WHERE movement<>'STAYED' ORDER BY month,movement,seller_id;
