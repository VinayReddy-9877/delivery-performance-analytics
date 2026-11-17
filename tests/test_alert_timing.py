"""Guard against purchase-week look-ahead in delivery alerts."""

import pandas as pd
import pytest

from src.delivery_analytics.analysis import calculate, lane_alerts, weekly_deliveries
from src.delivery_analytics.data import ORDERS_FILE


@pytest.fixture(scope='module')
def result():
    return calculate(pd.read_csv(ORDERS_FILE))


def test_completed_deliveries_not_purchase_weeks(result):
    current = weekly_deliveries(result, '2018-03-05')
    assert current['orders'] == 1556
    assert current['late_orders'] == 122
    assert current['baseline'] == pytest.approx(.034263206, abs=1e-7)
    assert 'SP → RJ' in lane_alerts(result, '2018-03-05').lane.tolist()


def test_future_completed_orders_do_not_leak_into_past_alert():
    rows = []
    for i in range(110):
        rows.append(dict(
            order_id=f'old-{i}', order_purchase_timestamp='2018-01-01 09:00:00',
            order_delivered_customer_date='2018-02-01 09:00:00',
            order_estimated_delivery_date='2018-01-28',
            seller_count=1, seller_state='SP', customer_state='SP', gmv=50.0,
        ))
    rows.append(dict(
        order_id='future-late', order_purchase_timestamp='2018-03-05 09:00:00',
        order_delivered_customer_date='2018-03-16 09:00:00',
        order_estimated_delivery_date='2018-03-10',
        seller_count=1, seller_state='SP', customer_state='RJ', gmv=50.0,
    ))
    result = calculate(pd.DataFrame(rows))
    week1 = weekly_deliveries(result, '2018-03-05')
    week2 = weekly_deliveries(result, '2018-03-12')
    assert week1['orders'] == 0
    assert week2['orders'] == 1
    assert week2['late_orders'] == 1
    assert lane_alerts(result, '2018-03-05').empty


def test_cross_state_sensitivity(result):
    assert result['comparison_rates']['same_state'] == pytest.approx(.04556873, abs=1e-6)
    assert result['comparison_rates']['all_cross_state'] == pytest.approx(.0813799, abs=1e-6)
    assert result['comparison_rates']['other_cross_state_excluding_sp_rj'] == pytest.approx(
        .072080585, abs=1e-6)
    lane = result['priority']
    assert 566 < lane['late_orders'] - lane['orders'] * result['comparison_rates'][
        'other_cross_state_excluding_sp_rj'] < 568
