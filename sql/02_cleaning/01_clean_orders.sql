-- Make quality decisions explicit; do not hide source inconsistencies.
-- The Python contract fails the run if keys, prices or GMV do not reconcile.
CREATE OR REPLACE VIEW analytics.clean_orders AS
SELECT * FROM analytics.stg_orders
WHERE order_id IS NOT NULL AND purchase_at IS NOT NULL
      AND estimated_date IS NOT NULL AND gmv >= 0
      AND (delivered_at IS NULL OR delivered_at >= purchase_at);

CREATE OR REPLACE VIEW analytics.clean_items AS
SELECT * FROM analytics.stg_items
WHERE order_id IS NOT NULL AND order_item_id IS NOT NULL AND price >= 0;
