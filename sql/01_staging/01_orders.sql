-- The same staging view is used by the prepared snapshot and nine-table rebuild.
CREATE OR REPLACE VIEW analytics.stg_orders AS
SELECT order_id, customer_unique_id, seller_id,
       NULLIF(seller_count,'')::integer AS seller_count,
       NULLIF(order_purchase_timestamp,'')::timestamp AS purchase_at,
       NULLIF(order_delivered_customer_date,'')::timestamp AS delivered_at,
       NULLIF(order_estimated_delivery_date,'')::date AS estimated_date,
       customer_state, NULLIF(gmv,'')::numeric(14,2) AS gmv,
       NULLIF(promise_days,'')::numeric AS promise_days,
       NULLIF(distance_km,'')::numeric AS distance_km,
       NULLIF(earliest_deadline,'')::timestamp AS shipping_deadline,
       COALESCE(NULLIF(main_category,''),'Unknown') AS main_category,
       COALESCE(NULLIF(seller_state,''),'Unknown') AS seller_state,
       CASE WHEN NULLIF(order_delivered_customer_date,'') IS NOT NULL
                 AND NULLIF(order_estimated_delivery_date,'') IS NOT NULL
            THEN (NULLIF(order_delivered_customer_date,'')::date >
                  NULLIF(order_estimated_delivery_date,'')::date)::integer END AS is_late
FROM raw.orders_history;
