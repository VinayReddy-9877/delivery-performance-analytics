"""Generate one self-contained set of outputs for a reporting run."""
import json
from pathlib import Path

from .analysis import calculate, lane_alerts, weekly_deliveries
from .charts import save_charts
from .excel import write_excel
from .memo import write_memo
from .report_html import build_html


def write_reports(orders, items, directory: Path, week: str | None = None):
    directory.mkdir(parents=True, exist_ok=False)
    result = calculate(orders)
    weekly = weekly_deliveries(result, week)
    alerts = lane_alerts(result, week)
    result['lanes'].to_csv(directory / 'lane_priorities.csv', index=False)
    result['lane_monthly'].to_csv(directory / 'lane_monthly.csv', index=False)
    result['states'].to_csv(directory / 'states.csv', index=False)
    result['monthly'].to_csv(directory / 'monthly.csv', index=False)
    alerts.to_csv(directory / 'alerts.csv', index=False)
    if weekly is not None:
        weekly['by_lane'].to_csv(directory / 'week_lane_deliveries.csv', index=False)
        weekly['trend'].to_csv(directory / 'week_lane_trend.csv', index=False)
        (directory / 'weekly_metrics.json').write_text(json.dumps({
            key: value for key, value in weekly.items()
            if key not in ('by_lane', 'trend')
        }, indent=2), encoding='utf-8')
    (directory / 'metrics.json').write_text(json.dumps(result['kpis'], indent=2), encoding='utf-8')
    save_charts(result, directory / 'figures', weekly=weekly)
    write_excel(result, directory / 'operations_workbook.xlsx', weekly=weekly)
    write_memo(result, directory / '01_insight_memo.pdf')
    build_html(result, directory / 'weekly_brief.html', week, alerts, weekly)
    return result, alerts
