"""The charts used in the report and the README."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def save_charts(result: dict, target: Path, weekly: dict | None = None):
    target.mkdir(parents=True, exist_ok=True)
    history = result['lane_monthly']
    lane = history[history.lane.eq('SP → RJ')].copy().sort_values('month')
    lane = lane[lane.orders >= 30]

    fig, ax = plt.subplots(figsize=(9, 3.7))
    ax.plot(lane.month, lane.late_rate * 100, linewidth=2, marker='o', markersize=4)
    ax.axhline(result['baseline'] * 100, linestyle='--', linewidth=1.2,
               label=f'Same-state benchmark: {result["baseline"]:.1%}')
    ax.set_title('SP to RJ: delivery delays spiked, then fell')
    ax.set_ylabel('Orders delivered late (%)')
    ax.tick_params(axis='x', labelrotation=55)
    ax.grid(axis='y', alpha=.2)
    ax.legend(loc='upper left')
    fig.tight_layout()
    fig.savefig(target / 'sp_rj_by_month.png', dpi=150)
    plt.close(fig)

    top = result['lanes'].query('excess_late > 0').head(8).sort_values('excess_late')
    fig, ax = plt.subplots(figsize=(8.8, 3.9))
    ax.barh(top.lane.str.replace(' → ', ' to ', regex=False), top.excess_late)
    ax.set_title('Largest excess counts against the same-state benchmark')
    ax.set_xlabel('Excess late orders (benchmark comparison)')
    ax.grid(axis='x', alpha=.2)
    fig.tight_layout()
    fig.savefig(target / 'lane_excess.png', dpi=150)
    plt.close(fig)

    m = result['monthly'].query('orders >= 500')
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(m.month, m.late_rate * 100, marker='o', linewidth=1.8)
    ax.set_title('Monthly delivery performance: assessed orders only')
    ax.set_ylabel('Late-delivery rate (%)')
    ax.tick_params(axis='x', labelrotation=55)
    ax.grid(axis='y', alpha=.2)
    fig.tight_layout()
    fig.savefig(target / 'all_months.png', dpi=150)
    plt.close(fig)

    if weekly is not None:
        trend = weekly['trend']
        fig, ax = plt.subplots(figsize=(8.8, 3.5))
        if not trend.empty:
            labels = trend.delivery_week.dt.strftime('%b %d')
            ax.plot(labels, trend.late_rate * 100, marker='o', linewidth=1.8)
            ax.tick_params(axis='x', labelrotation=50)
        else:
            ax.text(.5, .5, 'No completed deliveries in this window',
                    ha='center', transform=ax.transAxes)
        if weekly['baseline'] is not None:
            ax.axhline(weekly['baseline'] * 100, linestyle='--', linewidth=1,
                       label='Earlier completed same-state deliveries')
            ax.legend(loc='upper left', fontsize=8)
        ax.set_title('SP to RJ: completed-delivery week late rates')
        ax.set_ylabel('Delivered late (%)')
        ax.grid(axis='y', alpha=.2)
        fig.tight_layout()
        fig.savefig(target / 'sp_rj_delivery_weeks.png', dpi=150)
        plt.close(fig)
