-- Item-grain allocation: multi-seller merchandise is NOT credited to one seller.
DROP TABLE IF EXISTS analytics.seller_scorecard;
CREATE TABLE analytics.seller_scorecard AS
SELECT i.seller_id, COUNT(DISTINCT i.order_id) AS orders,
       COUNT(*) AS items, SUM(i.price) AS merchandise_gmv,
       COUNT(*) FILTER (WHERE o.is_late=1) AS late_items,
       AVG(o.is_late::numeric) AS late_item_rate
FROM analytics.clean_items i
JOIN analytics.fact_orders o USING(order_id)
GROUP BY i.seller_id;
CREATE UNIQUE INDEX ix_seller_id ON analytics.seller_scorecard(seller_id);
