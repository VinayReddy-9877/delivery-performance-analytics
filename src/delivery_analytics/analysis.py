"""Order-level KPIs and the lane prioritisation used in management reports."""
from __future__ import annotations

import math

import pandas as pd


def wilson_interval(successes: int, total: int, z: float = 1.96):
    if not total:
        return 0.0, 0.0
    p = successes / total
    divisor = 1 + z * z / total
    midpoint = (p + z * z / (2 * total)) / divisor
    spread = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / divisor
    return midpoint - spread, midpoint + spread


def calculate(orders: pd.DataFrame) -> dict:
    df = orders.copy()
    df['purchase_at'] = pd.to_datetime(df.order_purchase_timestamp, format='mixed')
    df['delivered_at'] = pd.to_datetime(df.order_delivered_customer_date, format='mixed', errors='coerce')
    df['promised_at'] = pd.to_datetime(df.order_estimated_delivery_date, format='mixed', errors='coerce')
    df['assessed'] = df.delivered_at.notna() & df.promised_at.notna()
    df['late'] = df.assessed & (df.delivered_at.dt.normalize() > df.promised_at.dt.normalize())
    df['late_gmv'] = df.gmv.where(df.late, 0.0)
    df['month'] = df.purchase_at.dt.to_period('M').astype(str)
    assessed = df.loc[df.assessed].copy()

    kpis = {
        'total_orders': int(len(df)),
        'assessed_orders': int(df.assessed.sum()),
        'late_orders': int(df.late.sum()),
        'late_rate': float(df.late.sum() / max(1, df.assessed.sum())),
        'gmv_brl': round(float(df.gmv.sum()), 2),
        'late_gmv_brl': round(float(df.late_gmv.sum()), 2),
        'unassessed_in_extract': int((~df.assessed).sum()),
    }

    monthly = assessed.groupby('month', as_index=False).agg(
        orders=('order_id', 'count'), late_orders=('late', 'sum'),
        late_gmv_brl=('late_gmv', 'sum'),
    )
    monthly['late_rate'] = monthly.late_orders / monthly.orders

    states = assessed.groupby('customer_state', as_index=False).agg(
        orders=('order_id', 'count'), late_orders=('late', 'sum'),
        late_gmv_brl=('late_gmv', 'sum'),
    )
    states['late_rate'] = states.late_orders / states.orders
    states['share_of_all_late'] = states.late_orders / max(1, kpis['late_orders'])
    states[['ci_low', 'ci_high']] = states.apply(
        lambda row: pd.Series(wilson_interval(int(row.late_orders), int(row.orders))), axis=1,
    )
    states = states.sort_values('late_orders', ascending=False).reset_index(drop=True)

    # Orders with more than one seller do not have one unambiguous origin state.
    routes = assessed.loc[
        assessed.seller_count.eq(1)
        & assessed.seller_state.notna()
        & assessed.seller_state.ne('Unknown')
        & assessed.customer_state.notna()
    ].copy()
    same = routes.loc[routes.seller_state.eq(routes.customer_state)]
    baseline = float(same.late.mean())
    # Sensitivity checks: compare the focus lane against shipments with a
    # similar cross-state route structure, not just the shorter same-state routes.
    cross = routes.loc[routes.seller_state.ne(routes.customer_state)]
    other_cross = cross.loc[~(cross.seller_state.eq('SP') & cross.customer_state.eq('RJ'))]
    comparison_rates = {
        'same_state': baseline,
        'all_cross_state': float(cross.late.mean()),
        'other_cross_state_excluding_sp_rj': float(other_cross.late.mean()),
    }
    routes['lane'] = routes.seller_state + ' → ' + routes.customer_state
    lanes = routes.groupby(['seller_state', 'customer_state', 'lane'], as_index=False).agg(
        orders=('order_id', 'count'), late_orders=('late', 'sum'),
        gmv_brl=('gmv', 'sum'), late_gmv_brl=('late_gmv', 'sum'),
    )
    lanes['late_rate'] = lanes.late_orders / lanes.orders
    lanes['benchmark_late'] = lanes.orders * baseline
    lanes['excess_late'] = lanes.late_orders - lanes.benchmark_late
    lanes['share_of_all_late'] = lanes.late_orders / max(1, kpis['late_orders'])
    lanes = lanes.sort_values('excess_late', ascending=False).reset_index(drop=True)

    lane_monthly = routes.groupby(['month', 'lane'], as_index=False).agg(
        orders=('order_id', 'count'), late_orders=('late', 'sum'),
        late_gmv_brl=('late_gmv', 'sum'),
    )
    lane_monthly['late_rate'] = lane_monthly.late_orders / lane_monthly.orders
    lane_monthly['baseline_rate'] = baseline
    lane_monthly['excess_late'] = lane_monthly.late_orders - lane_monthly.orders * baseline

    return {
        'orders': df, 'kpis': kpis, 'monthly': monthly, 'states': states,
        'lanes': lanes, 'lane_monthly': lane_monthly, 'baseline': baseline,
        'comparison_rates': comparison_rates,
        'priority': lanes.iloc[0].to_dict(),
    }



def weekly_deliveries(result: dict, week: str | None) -> dict | None:
    """Report completed deliveries, not eventual outcomes of purchases that week.

    Only earlier *completed* deliveries can contribute to the comparison rate.
    The historical replay is evaluated after the seven-day window closes.
    """
    if week is None:
        return None

    start = pd.Timestamp(week)
    end = start + pd.Timedelta(days=7)
    data = result['orders']
    eligible = data.loc[
        data.assessed & data.seller_count.eq(1)
        & data.seller_state.notna() & data.customer_state.notna()
        & data.seller_state.ne('Unknown')
    ].copy()
    eligible['lane'] = eligible.seller_state + ' → ' + eligible.customer_state

    # A report for this week becomes available after the week ends. It cannot
    # flag orders purchased this week but not delivered until weeks later.
    current = eligible.loc[(eligible.delivered_at >= start) & (eligible.delivered_at < end)]
    history = eligible.loc[eligible.delivered_at < start]
    same_history = history.loc[history.seller_state.eq(history.customer_state)]
    baseline = float(same_history.late.mean()) if len(same_history) >= 100 else None

    by_lane = current.groupby('lane', as_index=False).agg(
        orders=('order_id', 'size'), late_orders=('late', 'sum'))
    by_lane['late_rate'] = by_lane.late_orders / by_lane.orders
    by_lane['baseline'] = baseline
    by_lane['multiple'] = by_lane.late_rate / baseline if baseline else float('nan')
    by_lane = by_lane.sort_values(['late_orders', 'orders'], ascending=False)

    # Plot delivery outcomes as they became observable, one completed week at
    # a time. Current week is included, future deliveries are excluded.
    past = eligible.loc[(eligible.delivered_at < end) &
                        eligible.lane.eq('SP → RJ')].copy()
    past['delivery_week'] = (past.delivered_at - pd.to_timedelta(
        past.delivered_at.dt.weekday, unit='D')).dt.normalize()
    trend = past.groupby('delivery_week', as_index=False).agg(
        orders=('order_id', 'size'), late_orders=('late', 'sum'))
    trend['late_rate'] = trend.late_orders / trend.orders
    trend = trend[trend.delivery_week <= start].tail(12).copy()

    return {
        'week_start': str(start.date()), 'week_end_exclusive': str(end.date()),
        'orders': int(len(current)), 'late_orders': int(current.late.sum()),
        'late_rate': float(current.late.mean()) if len(current) else None,
        'baseline': baseline, 'by_lane': by_lane, 'trend': trend,
    }


def lane_alerts(result: dict, week: str | None, min_orders: int = 50,
                multiple: float = 2.0) -> pd.DataFrame:
    """Flag completed-delivery lanes after the week closes; no future outcomes."""
    columns = ['week', 'lane', 'orders', 'late_orders', 'late_rate', 'baseline', 'multiple']
    current = weekly_deliveries(result, week)
    if current is None or current['baseline'] is None or current['baseline'] <= 0:
        return pd.DataFrame(columns=columns)
    alerts = current['by_lane'].loc[
        (current['by_lane'].orders >= min_orders) &
        (current['by_lane'].multiple >= multiple)
    ].copy()
    if alerts.empty:
        return pd.DataFrame(columns=columns)
    alerts.insert(0, 'week', current['week_start'])
    return alerts[columns].sort_values('late_orders', ascending=False)
