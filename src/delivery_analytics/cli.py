"""Command-line entry point: build, refresh, replay and SQL verification."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .analysis import calculate
from .data import ROOT, POINTER_FILE, apply_batch, batch_signature, check_data, read_batch, read_tables
from .db import check_sql, install_database
from .reports import write_reports


def unique_run_folder(parent: Path, prefix: str) -> Path:
    return parent / f'{prefix}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid4().hex[:6]}'


def report_run(orders, items, out: Path, week: str | None = None, postgres=False):
    audit = check_data(orders, items)
    if postgres:
        count = install_database(orders, items)
        checked = check_sql()
        print(f'PostgreSQL: {count:,} fact orders; {len(checked)} SQL analyses checked')
    result, alerts = write_reports(orders, items, out, week)
    print(f'REPORT | {out} | {audit["orders"]:,} orders | '
          f'{result["kpis"]["late_orders"]:,} late | {len(alerts)} alerts')
    return result


def refresh(batches: list[Path], *, postgres=False):
    orders, items = read_tables()
    before = calculate(orders)['kpis']
    # The snapshot and its batch ledger share one atomic pointer file.
    state = json.loads(POINTER_FILE.read_text()) if POINTER_FILE.exists() else {}
    ledger = state.get('batches', {})
    changes = []
    for batch in batches:
        signature = batch_signature(batch)
        if batch.name in ledger:
            if signature != ledger[batch.name]:
                raise ValueError(f'{batch.name}: an applied batch was edited; use a new folder')
            continue
        new_orders, new_items = read_batch(batch)
        orders, items, inserted, updated = apply_batch(orders, items, new_orders, new_items)
        changes.append({'batch': batch.name, 'inserted': inserted, 'updated': updated})
        ledger[batch.name] = signature
    if not changes:
        print('NO_CHANGES | all selected batches already applied')
        return None

    # A new report is published before the snapshot pointer changes. Previous reports
    # are never removed, even if someone has opened the Excel workbook in Windows.
    output = unique_run_folder(ROOT / 'report/refreshes', 'refresh')
    report_run(orders, items, output, postgres=postgres)
    after = calculate(orders)['kpis']
    keys = ('total_orders', 'assessed_orders', 'late_orders', 'gmv_brl', 'late_gmv_brl')
    comparison = {'before': {k: before[k] for k in keys},
                  'after': {k: after[k] for k in keys}, 'batches': changes}
    (output / 'before_after.json').write_text(json.dumps(comparison, indent=2), encoding='utf-8')

    snapshot_name = f'{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid4().hex[:8]}'
    snapshot = ROOT / 'data/snapshots' / snapshot_name
    snapshot.mkdir(parents=True)
    try:
        orders.to_csv(snapshot / 'orders_history.csv', index=False)
        items.to_csv(snapshot / 'order_items.csv', index=False)
        state = ROOT / 'state'
        state.mkdir(parents=True, exist_ok=True)
        temp_pointer = state / f'.snapshot-{uuid4().hex}.json'
        temp_pointer.write_text(json.dumps({
            'snapshot': snapshot_name, 'batches': ledger
        }, indent=2), encoding='utf-8')
        temp_pointer.replace(POINTER_FILE)
    except Exception:
        shutil.rmtree(snapshot, ignore_errors=True)
        raise
    print(f'REFRESH | {len(changes)} batch(es), {after["total_orders"]:,} total orders')
    return output


def replay(next_week: bool, week: str | None, postgres=False):
    watermark = ROOT / 'state/replay_watermark.txt'
    first = pd.Timestamp('2017-11-06')
    last = pd.Timestamp('2018-08-20')
    if next_week:
        previous = (pd.Timestamp(watermark.read_text().strip()) if watermark.exists()
                    else first - pd.Timedelta(days=7))
        week = str((previous + pd.Timedelta(days=7)).date())
    start = pd.Timestamp(week)
    if start > last:
        print('NO_MORE_WEEKS | historical dataset has reached its final reporting period')
        return None
    orders, items = read_tables()
    # The report summary spans the historical extract; alerts are week-scoped.
    output = ROOT / 'report' / 'weekly' / str(start.date())
    if output.exists():
        raise FileExistsError(f'{output} exists; a replay week is never overwritten')
    report_run(orders, items, output, str(start.date()), postgres=postgres)
    if next_week:
        watermark.parent.mkdir(parents=True, exist_ok=True)
        watermark.write_text(str(start.date()) + '\n', encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description='Delivery analytics and reporting')
    command = parser.add_subparsers(dest='command', required=True)
    build = command.add_parser('build', help='Build a report from the current snapshot')
    build.add_argument('--out', type=Path)
    build.add_argument('--postgres', action='store_true')
    build.add_argument('--week', help='Optional historical week for alert examples')
    change = command.add_parser('refresh', help='Apply batches of compatible orders')
    selection = change.add_mutually_exclusive_group(required=True)
    selection.add_argument('--batch', type=Path)
    selection.add_argument('--all', action='store_true')
    change.add_argument('--postgres', action='store_true')
    run = command.add_parser('replay', help='Run a historical weekly alert and report')
    selection = run.add_mutually_exclusive_group(required=True)
    selection.add_argument('--week')
    selection.add_argument('--next', action='store_true')
    run.add_argument('--postgres', action='store_true')
    command.add_parser('sql-check', help='Execute all analysis and quality SQL on PostgreSQL')
    args = parser.parse_args()
    if args.command == 'build':
        orders, items = read_tables()
        output = args.out or unique_run_folder(ROOT / 'report/runs', 'report')
        report_run(orders, items, output, week=args.week, postgres=args.postgres)
    elif args.command == 'refresh':
        folders = (sorted(folder for folder in (ROOT / 'data/incoming/batches').glob('*')
                          if folder.is_dir()) if args.all else [args.batch])
        refresh(folders, postgres=args.postgres)
    elif args.command == 'replay':
        replay(args.next, getattr(args, 'week', None), postgres=args.postgres)
    elif args.command == 'sql-check':
        print('SQL CHECK |', len(check_sql()), 'analysis files executed')


if __name__ == '__main__':
    main()
