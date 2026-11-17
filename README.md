# Delivery Performance Analytics

**Python · PostgreSQL · pandas · Excel · GitHub Actions**

**Business question:** Where should a delivery operations team focus its limited investigation time?

I looked at late deliveries across customer states and shipping lanes, then built a repeatable way to report the results. The unit of analysis is an order, not an individual item. The dataset is a historical Olist extract from 2016–2018.

## The finding

- **6,534 of 96,470 assessable orders (6.8%)** arrived after the promised date. These orders contained **R$985,924** in merchandise value; that is not a measure of lost revenue.
- **SP → RJ is the highest-volume lane to investigate.** It had **1,147 late orders out of 8,048 (14.3%)**. At the 4.6% same-state benchmark, that is roughly **780 more late orders** than the benchmark predicts. Compared with *other cross-state* lanes, the difference is still approximately **567 orders**.
- The problem was uneven over time. **SP → RJ reached 42.4% late in March 2018**. I would monitor completed-delivery weeks and review carrier and seller records when the lane spikes, rather than change promises for every RJ customer.

![SP to RJ delivery performance by month](report/sample/figures/sp_rj_by_month.png)

**Open the results:** [HTML report](report/sample/weekly_brief.html) · [Excel workbook](report/sample/operations_workbook.xlsx) · [One-page decision memo](report/sample/01_insight_memo.pdf)

## Skills demonstrated

| Skill | Where to look |
|---|---|
| SQL | [Nine business questions](sql/README.md): joins, windows, rolling periods, percentiles and lane benchmarking |
| Python | [`src/delivery_analytics`](src/delivery_analytics): validation, analysis, reporting and refresh |
| Excel | Workbook with lane-month source rows, `SUMIFS` scorecard, month-by-lane matrix and editable alert threshold |
| Data quality | Order/item merchandise reconciliation, key checks and test cases |
| Automation | Historical weekly replay and compatible CSV batch refresh; each run has its own output folder |

## Run it

Requires **Python 3.12**. On Windows, run `run_project.bat` from the project folder. Alternatively:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli build
```

Reports are written to `report/runs/`; published output folders are not overwritten.

**PostgreSQL (optional for local reporting, required for SQL verification):**

```powershell
docker compose up -d
$env:DATABASE_URL = "postgresql://olist:olist@localhost:5433/olist"
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli build --postgres
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli sql-check
$env:RUN_DB_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -q
```

**Try an incoming batch:**

```powershell
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli refresh --batch data/incoming/examples/new_order
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli refresh --batch data/incoming/examples/correction
```

These example orders are **synthetic** and do not affect the historical findings above. Real batches must follow the [documented order and item schema](data/README.md). Refreshes write new reports to `report/refreshes/` and do not replace an Excel file you already have open.

## How the weekly report works

```text
Completed deliveries → validate → weekly lane rates
                              → compare with earlier completed deliveries
                              → report + lane alert (when threshold is crossed)
```

A weekly alert is evaluated **after delivery completion**, not when an order is purchased. The GitHub Actions workflows define SQL checks and historical replay. Hosted scheduling, GitHub issue creation and Pages deployment require verification in the destination repository; no live service is claimed here. See [automation notes](automation/README.md).

## Data and interpretation

The included extract has 96,478 orders, with eight lacking an assessable delivery outcome. It is **not the complete Olist order population**. Lane comparisons use single-seller orders; merchandise GMV excludes freight. The benchmark gaps are comparisons for prioritization, **not causal estimates of preventable delays**. Without complete carrier events and reviews, the project cannot prove why a lane was late or quantify customer impact.

See [method and benchmark checks](docs/method.md) and [source data instructions](data/README.md). The code is MIT licensed; the underlying Olist data has separate [attribution and reuse terms](DATA_LICENSE.md).
