CREATE OR REPLACE VIEW analytics.stg_items AS
SELECT order_id, NULLIF(order_item_id,'')::integer AS order_item_id,
       seller_id, COALESCE(NULLIF(category,''),'Unknown') AS category,
       NULLIF(price,'')::numeric(14,2) AS price
FROM raw.order_items;
