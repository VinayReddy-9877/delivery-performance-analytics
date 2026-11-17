-- The order grain is protected by aggregating items BEFORE joining.
DROP TABLE IF EXISTS analytics.fact_orders CASCADE;
CREATE TABLE analytics.fact_orders AS
WITH item_totals AS (
    SELECT order_id, COUNT(*) AS item_count,
           COUNT(DISTINCT seller_id) AS distinct_sellers,
           SUM(price) AS item_gmv
    FROM analytics.clean_items GROUP BY order_id
)
SELECT o.*, i.item_count, i.distinct_sellers, i.item_gmv
FROM analytics.clean_orders o
JOIN item_totals i USING (order_id);
CREATE UNIQUE INDEX ix_order_id ON analytics.fact_orders(order_id);
CREATE INDEX ix_order_purchase ON analytics.fact_orders(purchase_at);
CREATE INDEX ix_order_customer_state ON analytics.fact_orders(customer_state);
CREATE INDEX ix_order_seller_delivered ON analytics.fact_orders(seller_id,delivered_at);
