"""Executable Python/SQL parity checks when PostgreSQL is provided by CI."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from src.delivery_analytics.analysis import calculate
from src.delivery_analytics.data import ORDERS_FILE, ITEMS_FILE, ROOT
from src.delivery_analytics.db import install_database


@pytest.mark.skipif(not os.getenv('RUN_DB_TESTS'),
                    reason='Set RUN_DB_TESTS=1 and DATABASE_URL with PostgreSQL')
def test_postgresql_matches_python_on_business_grains():
    import psycopg

    orders = pd.read_csv(ORDERS_FILE)
    items = pd.read_csv(ITEMS_FILE)
    expected = calculate(orders)
    install_database(orders, items)
    with psycopg.connect(os.environ['DATABASE_URL']) as con:
        count, late, total, diff = con.execute('''
            SELECT COUNT(*), SUM(is_late), SUM(gmv), SUM(gmv-item_gmv)
            FROM analytics.fact_orders
        ''').fetchone()
        assert count == expected['kpis']['total_orders']
        assert late == expected['kpis']['late_orders']
        assert float(total) == pytest.approx(expected['kpis']['gmv_brl'], abs=.01)
        assert float(diff) == pytest.approx(0, abs=.01)

        state_sql = (ROOT / 'sql/04_analysis/02_late_value_by_state.sql').read_text()
        state_rows = con.execute(state_sql).fetchall()
        state_map = {r[0]: r for r in state_rows}
        python_states = expected['states'].set_index('customer_state')
        for state in ('RJ', 'AL', 'SP'):
            assert state_map[state][1] == int(python_states.loc[state, 'orders'])
            assert state_map[state][2] == int(python_states.loc[state, 'late_orders'])

        lane_sql = (ROOT / 'sql/04_analysis/09_lane_excess_by_month.sql').read_text()
        lane_rows = con.execute(lane_sql).fetchall()
        march = next(r for r in lane_rows if r[0] == 'SP' and r[1] == 'RJ'
                     and str(r[2]) == '2018-03-01')
        match = expected['lane_monthly']
        match = match.loc[(match.lane == 'SP → RJ') & (match.month == '2018-03')].iloc[0]
        assert march[3] == int(match.orders)
        assert march[4] == int(match.late_orders)
        assert float(march[5]) == pytest.approx(match.late_gmv_brl, abs=.01)

        # Seller-day counts must reflect distinct sellers on item rows, not an
        # arbitrary order-level representative seller.
        seller_sql = (ROOT / 'sql/04_analysis/05_seller_rolling_30d.sql').read_text()
        seller_records = con.execute(seller_sql).fetchall()
        seller, day, _, thirty, thirty_late, _ = max(
            seller_records, key=lambda rec: (rec[3], str(rec[0])))
        seller_orders = items.loc[items.seller_id.eq(seller), 'order_id'].drop_duplicates()
        sample = expected['orders'].loc[expected['orders'].order_id.isin(seller_orders)]
        dates = sample.delivered_at.dt.normalize()
        in_window = sample.loc[dates.ge(pd.Timestamp(day) - pd.Timedelta(days=29))
                               & dates.le(pd.Timestamp(day)) & sample.assessed]
        assert thirty == len(in_window)
        assert thirty_late == int(in_window.late.sum())
