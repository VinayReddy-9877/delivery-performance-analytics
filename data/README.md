# Data

**Source:** [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Read [DATA_LICENSE.md](../DATA_LICENSE.md) before reusing the data.

`prepared/` contains the order and item extracts used for the historical reports. The included files are not the full nine-table Olist release. They do not support claims about all undelivered orders, carrier handoff duration or review-score impact.

## Incoming CSV batches

Use the headers from `data/prepared/orders_history.csv` and `data/prepared/order_items.csv` exactly. The order file includes enriched columns such as `promise_days`, `distance_km` and `main_category`; this is a defined delivery-data interface, **not an arbitrary CSV analyser**.

- `orders_history.csv` is required. Each `order_id` must appear once in the batch.
- New orders require item rows in `order_items.csv`. The sum of item prices must agree with the order's merchandise GMV to within R$0.01.
- To correct an existing order, provide its full updated order row. Item rows can be omitted when the items have not changed.
- The item key is `(order_id, order_item_id)`; the order key is `order_id`.
- Use a new folder name for each batch. Reusing a folder name with different content is rejected.

Put new batches in `data/incoming/batches/`. The folders under `data/incoming/examples/` contain synthetic test records.

## Prepare data from Olist's nine raw tables

Download the original nine CSVs into `data/raw/`, then run:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_olist --raw data/raw --out data/generated
```

The preparation script uses delivered-status orders with item rows, joins customer and seller geography, aggregates item prices before joining to orders, and estimates straight-line distance from ZIP-prefix locations. It checks the payment and review file names but does not join those tables, which would change the reporting grain. The resulting extract is **separate from the bundled one**; compare counts and KPI definitions before using it to replace a published report.
