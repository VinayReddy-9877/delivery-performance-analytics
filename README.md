# Delivery Performance Analytics

**Finding the shipping lanes that contribute most to late deliveries — and automating the follow-up.**

[![Tests and PostgreSQL analysis](https://github.com/VinayReddy-9877/delivery-performance-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/VinayReddy-9877/delivery-performance-analytics/actions/workflows/ci.yml)
[![Historical weekly lane alerts](https://github.com/VinayReddy-9877/delivery-performance-analytics/actions/workflows/weekly_report.yml/badge.svg)](https://github.com/VinayReddy-9877/delivery-performance-analytics/actions/workflows/weekly_report.yml)

**Python · PostgreSQL · SQL · pandas · Excel · GitHub Actions**

**[Live dashboard](https://vinayreddy-9877.github.io/delivery-performance-analytics/)** · **[Sample Excel workbook](report/sample/operations_workbook.xlsx)** · **[One-page operations memo](report/sample/01_insight_memo.pdf)** · **[Sample HTML report](report/sample/weekly_brief.html)** · **[Automated lane alert](https://github.com/VinayReddy-9877/delivery-performance-analytics/issues/1)**

[![Live delivery performance dashboard — week of November 13, 2017](docs/images/live_dashboard.png)](https://vinayreddy-9877.github.io/delivery-performance-analytics/)

*Published historical weekly dashboard, with delivery KPIs and flagged shipping lanes. [Open the current dashboard](https://vinayreddy-9877.github.io/delivery-performance-analytics/).*

## Business problem

An e-commerce operations team cannot investigate every delayed delivery. It needs to know **which shipping lanes account for the largest number of late orders**, whether the problem is persistent or concentrated in particular periods, and when to investigate an unusual increase.

I used historical orders from the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) to answer that question. The project combines order-level analysis, PostgreSQL queries, an Excel scorecard, a management report, and a scheduled historical reporting workflow. The emphasis is on **decision-making and reproducible analysis**, not prediction.

## Key findings

| Finding | Evidence | Operational takeaway |
|---|---|---|
| Overall delivery performance | **6,534 of 96,470 assessed orders (6.77%)** arrived after the promised date | Monitor the count and rate of late deliveries together |
| Merchandise associated with delays | **BRL 985,924.34** of merchandise GMV was on late orders, out of **BRL 13.22M** overall | Prioritize exposure, but do not treat this value as lost revenue |
| Highest-volume lane for investigation | **São Paulo → Rio de Janeiro (SP → RJ): 1,147 late out of 8,048 orders (14.3%)** | Investigate the lane with the largest excess late-order count |
| Benchmark comparison | SP → RJ had about **780 more late orders** than a 4.56% same-state benchmark; approximately **567 more** than a 7.21% *other cross-state* benchmark | The lane remains a priority with a stricter comparison group |
| Timing matters | SP → RJ reached **42.4% late in March 2018** | Watch for episodic spikes instead of assuming the rate is constant |

**The recommendation:** review SP → RJ by completed-delivery week, investigate the sellers, carriers and periods behind spikes, and test any intervention before estimating financial benefit. The benchmark differences are **descriptive comparisons, not estimates of preventable delays**.

## Analysis charts

These charts come from the project’s included historical extract. The monthly charts use purchase months; the operational alert chart uses **weeks of completed deliveries** so it does not rely on outcomes that were unknown at purchase time.

### 1. SP → RJ: monthly late-delivery rate

![SP to RJ late-delivery rate by purchase month](report/sample/figures/sp_rj_by_month.png)

*The highest-volume priority lane experienced several spikes, including March 2018; the full-period average hides this variation.*

### 2. Shipping lanes ranked by excess late orders

![Shipping lanes ranked by excess late deliveries relative to the benchmark](report/sample/figures/lane_excess.png)

*Prioritizing by the count of late deliveries above a descriptive benchmark helps focus on operational volume rather than the highest percentage alone.*

### 3. Late-delivery rate across all months

![Overall historical late-delivery rate by month](report/sample/figures/all_months.png)

*Monthly volatility is important when interpreting an overall average.*

### 4. SP → RJ: completed-delivery weekly trend

![SP to RJ weekly completed-delivery late rates and historical benchmark](report/sample/figures/sp_rj_delivery_weeks.png)

*The operational alert is evaluated after deliveries finish and uses earlier completed deliveries for its baseline.*

See the [methodology and benchmark sensitivity checks](docs/method.md) for definitions, sample rules and limitations.

## What the project delivers

| Deliverable | Purpose |
|---|---|
| [Live weekly dashboard](https://vinayreddy-9877.github.io/delivery-performance-analytics/) | Shows completed deliveries, late rates, flagged lanes and historical trend charts |
| [Excel operations workbook](report/sample/operations_workbook.xlsx) | Includes lane-level source rows, `SUMIFS` scorecards, a month-by-lane comparison and an adjustable alert multiplier |
| [One-page decision memo](report/sample/01_insight_memo.pdf) | Summarizes the finding, why it matters and the next operational checks |
| [Nine SQL analyses](sql/README.md) | Demonstrates analytical joins, CTEs, window functions, rolling periods, percentiles and lane benchmarking |
| GitHub Actions reports | Runs quality checks and historical weekly reporting; uploads report artifacts |
| [GitHub lane alert example](https://github.com/VinayReddy-9877/delivery-performance-analytics/issues/1) | Records an automatically flagged lane for follow-up |

## Excel scorecard preview

![Excel lane review scorecard with SUMIFS-based KPI calculations and adjustable alert threshold](docs/images/excel_scorecard.png)

*The workbook contains lane source data, calculated scorecards, a month-by-lane comparison and an editable alert multiplier. [Open the workbook](report/sample/operations_workbook.xlsx).*

## How the analysis works

```text
Prepared Olist order + item data
           |
           v
Validate IDs, timestamps, order grain and merchandise totals
           |
           v
Calculate delivery KPIs, state/lane comparisons and monthly trends
           |
           +--> PostgreSQL analytical tables + nine SQL analyses
           |
           +--> Excel scorecard + charts + one-page memo + HTML report
           |
           v
Historical weekly replay (completed deliveries only)
           |
           v
Compare lane late rates with earlier completed-delivery baseline
           |
           +--> Save weekly report artifact
           +--> Create/update GitHub issue when alert rule is met
           +--> Publish latest HTML dashboard to GitHub Pages
```

### Metric definitions

- **Order grain:** each row in `orders_history.csv` represents one order; `order_items.csv` contains its items. Order-level delivery KPIs count each order once.
- **Late delivery:** actual delivery **calendar date** is later than the estimated delivery **calendar date**. An order must have both dates to enter the assessed-order denominator.
- **Late-delivery rate:** `late orders / assessed orders`. The included extract has **96,478 orders**, of which **96,470** have assessable delivery outcomes.
- **Merchandise GMV:** sum of item prices, excluding freight. The order and item totals reconcile to **BRL 0.00** difference.
- **Shipping lane:** seller state → customer state. Direct lane comparisons use **single-seller orders** so one order has one clear seller origin.
- **Excess versus benchmark:** `observed late orders − (assessed lane orders × benchmark late rate)`. It is a ranking aid, **not a causal savings forecast**.

Seller-level SQL uses distinct `(order_id, seller_id)` pairs to avoid counting multiple items from the same seller as multiple seller orders. Because a multi-seller order can be attributed to multiple participants, seller-attributed counts should not be summed as unique orders. Details are in [docs/method.md](docs/method.md).

## Automated reporting

There are **two separate workflows**:

**1. Tests and PostgreSQL analysis — [CI workflow](.github/workflows/ci.yml)**  
On a push or pull request, GitHub Actions starts PostgreSQL 16, installs the Python dependencies, builds analytical tables, runs the Python test suite, executes the nine business queries and uploads a report preview. The local database-enabled run passed **38 tests**, and the hosted CI workflow has also completed successfully.

**2. Historical weekly lane alerts — [reporting workflow](.github/workflows/weekly_report.yml)**  
The workflow runs on a Monday schedule or by manual dispatch. It advances a saved historical-week watermark, analyzes **deliveries completed during that week**, and compares lane rates with a same-state baseline calculated from **earlier completed deliveries**. An alert requires **at least 50 completed lane orders** and a late rate **at least twice the prior baseline**. If a lane is flagged, the workflow creates an open GitHub issue or comments on the existing one instead of opening duplicates. It uploads the reports and deploys the latest HTML report through GitHub Pages.

The hosted replay, issue creation and Pages deployment have been demonstrated. For example, [Issue #1](https://github.com/VinayReddy-9877/delivery-performance-analytics/issues/1) records the historical week of **2017-11-06** for SP → RJ: **89 completed deliveries, 6 late (6.7%)**, or approximately **2.2×** the earlier same-state baseline. The [published dashboard](https://vinayreddy-9877.github.io/delivery-performance-analytics/) shows the most recently published historical reporting week.

**Important:** this is a replay of **2016–2018 historical data**, not a live order feed or a purchase-time prediction service. Alerts become available after the relevant deliveries have completed.

## Project structure

```text
delivery-performance-analytics/
├── README.md
├── requirements.txt
├── run_project.bat
├── compose.yaml
├── data/
│   ├── prepared/                # Historical order and item extracts
│   └── incoming/examples/       # Synthetic insert and correction examples
├── sql/
│   ├── 01_staging/              # Source views
│   ├── 02_cleaning/             # Cleaned order view
│   ├── 03_marts/                # Fact orders and seller scorecard
│   ├── 04_analysis/             # Nine business queries
│   └── 05_quality/              # Reconciliation SQL
├── src/delivery_analytics/      # Data, analysis, reports, refresh and CLI
├── report/sample/              # Curated Excel, HTML, PDF and figures
├── docs/images/                 # Dashboard, workbook and automation screenshots
├── scripts/                    # Raw preparation and GitHub issue updates
├── tests/                      # Business-rule, report, batch and SQL tests
├── automation/README.md        # Workflow and refresh explanation
├── docs/method.md              # Metric definitions and sensitivity tests
└── .github/workflows/          # CI and weekly historical replay
```

## Run locally (Windows / PowerShell)

**Requirements:** Python 3.12. Docker Desktop is needed only for the PostgreSQL path.

```powershell
# From the repository folder
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Python tests and a new report
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli build
```

You can also run `run_project.bat`. Each normal build creates its own folder under `report/runs/`; older published reports are not overwritten.

### PostgreSQL and all SQL checks

```powershell
docker compose up -d
$env:DATABASE_URL = "postgresql://olist:olist@localhost:5433/olist"

.\.venv\Scripts\python.exe -m src.delivery_analytics.cli build --postgres
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli sql-check

$env:RUN_DB_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -q
```

The PostgreSQL service uses **PostgreSQL 16**, exposed as `localhost:5433`. The verified local results were **96,478 fact orders, nine SQL analyses executed and 38 tests passed**.

### Run a historical reporting week

```powershell
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli replay --next
```

Output is written under `report/weekly/<week-start>/`. The watermark records the last completed historical replay week.

### Try an incremental data refresh

```powershell
# Synthetic demonstration: one new order and then a correction
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli refresh --batch data/incoming/examples/new_order
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli refresh --batch data/incoming/examples/correction
```

The refresh validates compatible CSV batches, inserts new orders, replaces corrected order records, checks item-level GMV and prevents unchanged batches from being applied twice. It saves new versioned reports under `report/refreshes/` and retains previous reports. **The example records are synthetic and are not part of the published historical findings.**

For your own data, follow the exact input contract in [data/README.md](data/README.md). This pipeline does **not** automatically interpret unrelated CSV datasets.

## Data source and reproducibility

The project uses the [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). The committed `data/prepared/` extracts support the demonstrated historical analysis, but they are **not the complete nine-table Olist release**.

To prepare a separate dataset from the original nine downloaded CSVs:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_olist --raw data/raw --out data/generated
```

The script checks for all nine source files, constructs order/item extracts, joins customer and seller locations, and estimates straight-line distances from ZIP-prefix coordinates. Payment and review files are checked but are **not joined into the reporting grain**. The generated output should be validated separately before replacing any published results; this full raw-data path has not yet been verified against the original nine tables in this repository.

## Testing and reliability

The tests cover metric calculations, delivery-week timing, missing-month Excel behavior, batch corrections, duplicate batch prevention, report integrity, SQL business rules and Python/PostgreSQL parity. Data-quality checks prevent invalid order identifiers, inconsistent merchandise totals and malformed updates from being silently published.

- **38/38 local tests passed** with PostgreSQL enabled.
- **Nine PostgreSQL business queries executed** successfully on the local database.
- **Hosted GitHub Actions CI and historical replay passed**, and a lane alert issue and Pages deployment were created.

See [CI runs](https://github.com/VinayReddy-9877/delivery-performance-analytics/actions/workflows/ci.yml) and [weekly workflow runs](https://github.com/VinayReddy-9877/delivery-performance-analytics/actions/workflows/weekly_report.yml) for the hosted execution history.

## Limitations and next steps

This analysis describes a historical, primarily delivered-order extract. It does not measure all never-delivered or cancelled orders in the full Olist dataset. The data does not support a complete seller-handoff versus carrier-transit decomposition or a reliable review-score impact analysis in this project. Same-state routes are not distance-matched controls for cross-state routes, so the benchmark differences should not be interpreted as causal effects or expected savings. A real operational deployment would need a current order feed, carrier tracking data, monitoring of input freshness and evaluation of interventions.

## License and attribution

Project code is released under the [MIT License](LICENSE). The Olist dataset is separately licensed under **CC BY-NC-SA 4.0**; derived data and reports have their own attribution and reuse conditions. See [DATA_LICENSE.md](DATA_LICENSE.md). No affiliation with Olist is implied.

