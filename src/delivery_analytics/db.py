"""Load PostgreSQL and execute the same analysis SQL that reviewers can inspect."""
from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd

from .data import ROOT


def _upload(connection, table: str, frame: pd.DataFrame):
    from psycopg import sql
    columns = list(frame.columns)
    identifiers = sql.SQL(', ').join(sql.Identifier(name) for name in columns)
    fields = sql.SQL(', ').join(
        sql.SQL('{} text').format(sql.Identifier(name)) for name in columns
    )
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL('DROP TABLE IF EXISTS raw.{} CASCADE').format(sql.Identifier(table)))
        cursor.execute(sql.SQL('CREATE TABLE raw.{} ({})').format(sql.Identifier(table), fields))
        raw_text = io.StringIO()
        frame.to_csv(raw_text, index=False, header=False, na_rep='')
        raw_text.seek(0)
        statement = sql.SQL("COPY raw.{} ({}) FROM STDIN WITH (FORMAT CSV, NULL '')").format(
            sql.Identifier(table), identifiers,
        )
        with cursor.copy(statement) as writer:
            while chunk := raw_text.read(1024 * 1024):
                writer.write(chunk)


def install_database(orders: pd.DataFrame, items: pd.DataFrame, url: str | None = None):
    url = url or os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError('DATABASE_URL is required for the PostgreSQL step.')
    import psycopg
    with psycopg.connect(url) as connection:
        connection.execute('CREATE SCHEMA IF NOT EXISTS raw')
        connection.execute('CREATE SCHEMA IF NOT EXISTS analytics')
        _upload(connection, 'orders_history', orders)
        _upload(connection, 'order_items', items)
        for folder in ('01_staging', '02_cleaning', '03_marts'):
            for file in sorted((ROOT / 'sql' / folder).glob('*.sql')):
                connection.execute(file.read_text(encoding='utf-8'))
        count, delta = connection.execute(
            'SELECT COUNT(*), COALESCE(SUM(gmv - item_gmv), 0) FROM analytics.fact_orders'
        ).fetchone()
        if count != len(orders) or abs(delta) > 0.01:
            raise AssertionError(f'PostgreSQL reconciliation failed: {count=} {delta=}')
    return int(count)


def check_sql(url: str | None = None):
    url = url or os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError('DATABASE_URL is required to check the SQL files.')
    import psycopg
    results = []
    with psycopg.connect(url) as connection:
        for file in sorted((ROOT / 'sql' / '04_analysis').glob('*.sql')):
            with connection.cursor() as cursor:
                cursor.execute(file.read_text(encoding='utf-8'))
                count = len(cursor.fetchmany(3))
                # A correct analytical query may legitimately return no rows.
                # Syntax/runtime errors still stop the build.
                results.append((file.name, count))
        for file in sorted((ROOT / 'sql' / '05_quality').glob('*.sql')):
            with connection.cursor() as cursor:
                cursor.execute(file.read_text(encoding='utf-8'))
                row = cursor.fetchone()
                if row is None or row[1] or row[2] or abs(row[3]) > 0.01:
                    raise AssertionError(f'{file.name}: quality check failed: {row}')
    return results
