# Reporting and refresh

The project has two ways to run: a historical weekly replay and an incoming batch refresh. Neither requires a live order API.

## Weekly replay

The `weekly_report.yml` workflow advances to the next reporting week from `state/replay_watermark.txt`. It measures orders **delivered during that week** and compares each shipping lane with a late-rate benchmark from **earlier completed same-state deliveries**. At least 50 completed lane orders and a rate at least 2 times the benchmark are required for an alert.

The report is generated after the delivery week ends. The workflow uploads it as an artifact and can create or comment on one open GitHub issue per alerted lane. GitHub Pages publishing is optional (`PUBLISH_PAGES=true`). These hosted actions must be checked after the repository is published.

To replay locally:

```powershell
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli replay --next
```

## Incoming order batches

Place a folder with compatible `orders_history.csv` and, for new orders, `order_items.csv` under `data/incoming/batches/`. The CSV contract is described in [data/README.md](../data/README.md).

```powershell
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli refresh --batch data/incoming/batches/<batch-name>
```

The refresh checks identifiers, dates and merchandise totals; inserts new order IDs; replaces corrected order rows; and saves reports under a new version. It tracks batch fingerprints so an unchanged batch is not processed again. The snapshot and batch ledger are switched together after the report is written.

The two folders under `data/incoming/examples/` are synthetic demonstrations of an insert and a correction, not new Olist transactions.
