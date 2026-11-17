# SQL questions

The scripts run on PostgreSQL 16. The loader creates staging views, clean views, `analytics.fact_orders`, and `analytics.seller_scorecard`, then executes every business query and the reconciliation check.

| Business question | SQL technique | File |
|---|---|---|
| How did order value change month to month? | `LAG`, contiguous months, minimum sample | `04_analysis/01_monthly_growth.sql` |
| Which customer states have the most late-order merchandise? | filtered aggregation | `04_analysis/02_late_value_by_state.sql` |
| Is cross-state delivery more vulnerable? | conditional grouping, single-seller filter | `04_analysis/03_cross_state.sql` |
| Which top sellers entered or exited? | window ranking and `FULL JOIN` | `04_analysis/04_monthly_seller_rank.sql` |
| How did seller performance evolve? | 30-day window over delivery date | `04_analysis/05_seller_rolling_30d.sql` |
| Which sellers had three consecutive bad weeks? | gaps-and-islands | `04_analysis/06_three_bad_weeks.sql` |
| Where is the long delivery-time tail? | `PERCENTILE_CONT` | `04_analysis/07_delivery_percentiles.sql` |
| How many orders missed by 1–3, 4–9, and 10+ days? | date arithmetic, conditional aggregates | `04_analysis/08_late_miss_severity.sql` |
| Which lane/month has the greatest excess against the same-state rate? | CTE benchmark, grouped comparison | `04_analysis/09_lane_excess_by_month.sql` |

`05_quality/01_reconciliation.sql` checks fact-row uniqueness and merchandise allocation.

To run every file after loading the database:

```powershell
$env:DATABASE_URL="postgresql://olist:olist@localhost:5433/olist"
.\.venv\Scripts\python.exe -m src.delivery_analytics.cli sql-check
```
