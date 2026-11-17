"""Create one open GitHub issue per alerted lane, then add weekly comments."""
from __future__ import annotations

import csv
import json
import os
import subprocess
from pathlib import Path


def gh(*args: str) -> str:
    response = subprocess.run(['gh', *args], check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return response.stdout.strip()


def main() -> None:
    watermark = Path('state/replay_watermark.txt')
    if not watermark.exists():
        raise FileNotFoundError('Replay watermark missing: no completed replay')
    week = watermark.read_text(encoding='utf-8').strip()
    filename = Path('report/weekly') / week / 'alerts.csv'
    if not filename.is_file():
        raise FileNotFoundError(f'No alerts.csv for completed week {week}')
    with filename.open(newline='', encoding='utf-8') as stream:
        alerts = list(csv.DictReader(stream))
    if not alerts:
        print('No lane issues: no alerts this week')
        return

    current_issues = json.loads(gh('issue', 'list', '--state', 'open',
                                   '--limit', '500', '--json', 'number,title'))
    existing = {issue['title']: issue['number'] for issue in current_issues}
    base = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
    run = f"{base}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    for alert in alerts:
        title = 'Lane alert: ' + alert['lane']
        body = (f"Completed-delivery week: {week}\n\n"
                f"- Deliveries completed: {alert['orders']}\n"
                f"- Delivered late: {alert['late_orders']}\n"
                f"- Late rate: {float(alert['late_rate']):.1%}\n"
                f"- Prior completed-delivery same-state baseline: "
                f"{float(alert['baseline']):.1%}\n"
                f"- Rate multiple: {float(alert['multiple']):.1f}x\n\n"
                f"Historical outcomes, not purchase-day predictions. [Workflow run]({run})")
        if title in existing:
            gh('issue', 'comment', str(existing[title]), '--body', body)
            print(f'Updated lane issue: {title}')
        else:
            gh('issue', 'create', '--title', title, '--body', body)
            print(f'Opened lane issue: {title}')


if __name__ == '__main__':
    main()
