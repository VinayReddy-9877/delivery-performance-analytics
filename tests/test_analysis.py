import pandas as pd
import pytest

from src.delivery_analytics.analysis import calculate, lane_alerts, wilson_interval
from src.delivery_analytics.data import check_data, ORDERS_FILE, ITEMS_FILE


@pytest.fixture(scope='module')
def dataset():
    orders, items = pd.read_csv(ORDERS_FILE), pd.read_csv(ITEMS_FILE)
    check_data(orders, items)
    return orders, items


@pytest.fixture(scope='module')
def report(dataset):
    return calculate(dataset[0])


def test_known_source_counts(dataset):
    orders, items = dataset
    assert len(orders) == 96_478
    assert len(items) >= 100_000


def test_reconciliation_exact(dataset):
    assert check_data(*dataset)['gmv_difference_brl'] == 0.0


def test_assessed_and_late_counts(report):
    assert report['kpis']['assessed_orders'] == 96_470
    assert report['kpis']['late_orders'] == 6_534


def test_late_value(report):
    assert report['kpis']['late_gmv_brl'] == pytest.approx(985_924.34, abs=.01)


def test_sp_rj_is_highest_excess_lane(report):
    first = report['priority']
    assert first['lane'] == 'SP → RJ'
    assert first['orders'] == 8048
    assert first['late_orders'] == 1147
    assert 779 < first['excess_late'] < 781


def test_rj_carries_more_volume_than_al(report):
    states = report['states'].set_index('customer_state')
    assert states.loc['RJ', 'late_orders'] == 1495
    assert states.loc['AL', 'late_orders'] == 85
    assert states.loc['AL', 'orders'] == 397


def test_same_state_benchmark(report):
    assert report['baseline'] == pytest.approx(.04556873, abs=.000001)


def test_monthly_lane_spike(report):
    month = report['lane_monthly']
    march = month[(month.lane == 'SP → RJ') & (month.month == '2018-03')].iloc[0]
    assert march.orders == 582
    assert march.late_orders == 247
    assert .42 < march.late_rate < .43


def test_top_five_excess(report):
    excess = report['lanes'].head(5).excess_late.sum()
    assert 1290 < excess < 1300


def test_unassessed_not_counted_as_on_time(report):
    assert report['kpis']['unassessed_in_extract'] == 8


def test_state_confidence_interval(report):
    al = report['states'].set_index('customer_state').loc['AL']
    low, high = wilson_interval(85, 397)
    assert low < 85/397 < high
    assert al.ci_low == pytest.approx(low)


def test_weekly_alerts_require_substantial_volume(report):
    alerts = lane_alerts(report, '2018-03-05')
    assert not alerts.empty
    assert (alerts.orders >= 50).all()
    assert (alerts.multiple >= 2).all()


def test_empty_week_has_no_alert(report):
    alerts = lane_alerts(report, '2020-01-06')
    assert alerts.empty
