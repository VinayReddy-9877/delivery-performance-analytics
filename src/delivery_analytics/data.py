"""Data contracts for the prepared Olist extract and incoming order batches."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ORDERS_FILE = ROOT / 'data/prepared/orders_history.csv'
ITEMS_FILE = ROOT / 'data/prepared/order_items.csv'
POINTER_FILE = ROOT / 'state/current_snapshot.json'

ORDER_COLUMNS = list(pd.read_csv(ORDERS_FILE, nrows=0).columns)
ITEM_COLUMNS = list(pd.read_csv(ITEMS_FILE, nrows=0).columns)


def read_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the latest successful refresh, otherwise use the historical extract."""
    if POINTER_FILE.exists():
        snapshot = json.loads(POINTER_FILE.read_text(encoding='utf-8'))['snapshot']
        base = ROOT / 'data/snapshots' / snapshot
        return pd.read_csv(base / 'orders_history.csv'), pd.read_csv(base / 'order_items.csv')
    return pd.read_csv(ORDERS_FILE), pd.read_csv(ITEMS_FILE)


def check_data(orders: pd.DataFrame, items: pd.DataFrame) -> dict:
    """Reject records that would make order-level or item-level metrics unreliable."""
    if set(orders.columns) != set(ORDER_COLUMNS):
        raise ValueError('Order columns do not match the documented CSV schema.')
    if set(items.columns) != set(ITEM_COLUMNS):
        raise ValueError('Item columns do not match the documented CSV schema.')
    if orders.order_id.isna().any() or orders.order_id.duplicated().any():
        raise ValueError('order_id is missing or repeated in orders_history.csv')
    if items[['order_id', 'order_item_id']].isna().any().any():
        raise ValueError('Item keys must not be empty.')
    if items.duplicated(['order_id', 'order_item_id']).any():
        raise ValueError('Each order item key must appear once.')
    if not items.order_id.isin(orders.order_id).all():
        raise ValueError('Items refer to an unknown order.')

    money = pd.to_numeric(orders.gmv, errors='coerce')
    price = pd.to_numeric(items.price, errors='coerce')
    if money.isna().any() or price.isna().any() or (money < 0).any() or (price < 0).any():
        raise ValueError('Merchandise values must be numeric and nonnegative.')
    item_total = items.assign(price=price).groupby('order_id').price.sum()
    if not orders.order_id.isin(item_total.index).all():
        raise ValueError('Every order must have at least one item.')
    difference = money.to_numpy() - item_total.reindex(orders.order_id).to_numpy()
    if (abs(difference) > 0.011).any():
        raise ValueError('Order GMV does not reconcile with item prices.')

    purchase = pd.to_datetime(orders.order_purchase_timestamp, errors='coerce', format='mixed')
    delivered = pd.to_datetime(orders.order_delivered_customer_date, errors='coerce', format='mixed')
    promised = pd.to_datetime(orders.order_estimated_delivery_date, errors='coerce', format='mixed')
    if purchase.isna().any() or promised.isna().any():
        raise ValueError('Purchase timestamp and promised date are required.')
    if (delivered.notna() & (delivered < purchase)).any():
        raise ValueError('Delivery cannot precede purchase.')
    return {
        'orders': int(len(orders)),
        'items': int(len(items)),
        'unassessed_in_extract': int((delivered.isna() | promised.isna()).sum()),
        'gmv_difference_brl': round(float(difference.sum()), 2),
    }


def batch_signature(folder: Path) -> str:
    digest = hashlib.sha256()
    for name in ('orders_history.csv', 'order_items.csv'):
        file = folder / name
        if file.exists():
            digest.update(name.encode('utf-8'))
            digest.update(file.read_bytes())
    return digest.hexdigest()


def read_batch(folder: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    orders_file = folder / 'orders_history.csv'
    items_file = folder / 'order_items.csv'
    if not orders_file.is_file():
        raise FileNotFoundError(f'{orders_file} not found')
    orders = pd.read_csv(orders_file)
    items = pd.read_csv(items_file) if items_file.exists() else pd.DataFrame(columns=ITEM_COLUMNS)
    if set(orders.columns) != set(ORDER_COLUMNS):
        raise ValueError('Incoming order columns differ from the prepared schema.')
    if set(items.columns) != set(ITEM_COLUMNS):
        raise ValueError('Incoming item columns differ from the prepared schema.')
    if orders.order_id.duplicated().any():
        raise ValueError('The incoming batch contains duplicate order IDs.')
    return orders[ORDER_COLUMNS], items[ITEM_COLUMNS]


def apply_batch(orders: pd.DataFrame, items: pd.DataFrame,
                new_orders: pd.DataFrame, new_items: pd.DataFrame):
    """Latest full order record wins; item updates use (order_id, order_item_id)."""
    old_order_ids = set(orders.order_id)
    inserted = int((~new_orders.order_id.isin(old_order_ids)).sum())
    updated = int(len(new_orders) - inserted)
    orders = pd.concat([orders[~orders.order_id.isin(new_orders.order_id)], new_orders],
                       ignore_index=True)
    if not new_items.empty:
        keys = pd.MultiIndex.from_frame(new_items[['order_id', 'order_item_id']])
        existing = pd.MultiIndex.from_frame(items[['order_id', 'order_item_id']])
        items = pd.concat([items[~existing.isin(keys)], new_items], ignore_index=True)
    check_data(orders, items)
    return orders, items, inserted, updated
