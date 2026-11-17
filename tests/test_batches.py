from pathlib import Path

import pandas as pd
import pytest

from src.delivery_analytics import data


def sample_tables():
    orders = pd.read_csv(data.ORDERS_FILE, nrows=1)
    items = pd.read_csv(data.ITEMS_FILE)
    items = items[items.order_id.isin(orders.order_id)].copy()
    return orders, items


def example(name):
    return data.ROOT / 'data/incoming/examples' / name


def test_batch_files_have_schema():
    orders, items = data.read_batch(example('new_order'))
    assert list(orders.columns) == data.ORDER_COLUMNS
    assert list(items.columns) == data.ITEM_COLUMNS


def test_new_order_is_inserted():
    orders = pd.read_csv(data.ORDERS_FILE)
    items = pd.read_csv(data.ITEMS_FILE)
    new_orders, new_items = data.read_batch(example('new_order'))
    merged_orders, merged_items, added, corrected = data.apply_batch(
        orders, items, new_orders, new_items)
    assert len(merged_orders) == len(orders) + 1
    assert added == 1 and corrected == 0
    assert data.check_data(merged_orders, merged_items)['gmv_difference_brl'] == 0


def test_existing_order_update_is_not_a_second_order():
    orders = pd.read_csv(data.ORDERS_FILE)
    items = pd.read_csv(data.ITEMS_FILE)
    added, item_rows = data.read_batch(example('new_order'))
    updated, _ = data.read_batch(example('correction'))
    orders, items, _, _ = data.apply_batch(orders, items, added, item_rows)
    orders2, items2, inserted, corrected = data.apply_batch(orders, items, updated, pd.DataFrame(columns=data.ITEM_COLUMNS))
    assert len(orders2) == len(orders)
    assert inserted == 0 and corrected == 1
    assert data.check_data(orders2, items2)['gmv_difference_brl'] == 0


def test_bad_order_price_is_rejected():
    orders, items = sample_tables()
    orders.loc[:, 'gmv'] = 100000
    with pytest.raises(ValueError, match='reconcile'):
        data.check_data(orders, items)


def test_duplicate_keys_are_rejected():
    orders, items = sample_tables()
    with pytest.raises(ValueError, match='repeated'):
        data.check_data(pd.concat([orders, orders], ignore_index=True), items)


def test_unknown_item_reference_is_rejected():
    orders, items = sample_tables()
    items.loc[:, 'order_id'] = 'missing-from-orders'
    with pytest.raises(ValueError, match='unknown order'):
        data.check_data(orders, items)


def test_missing_purchase_date_is_rejected():
    orders, items = sample_tables()
    orders.loc[:, 'order_purchase_timestamp'] = ''
    with pytest.raises(ValueError, match='timestamp'):
        data.check_data(orders, items)


def test_batch_hash_changes_when_input_changes(tmp_path):
    folder = tmp_path / 'sample'
    folder.mkdir()
    file = folder / 'orders_history.csv'
    file.write_text('one', encoding='utf-8')
    first = data.batch_signature(folder)
    file.write_text('two', encoding='utf-8')
    assert data.batch_signature(folder) != first


def test_missing_orders_csv_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        data.read_batch(tmp_path)


def test_late_correction_does_not_change_item_count():
    orders, items = sample_tables()
    fixed = orders.copy()
    fixed['order_delivered_customer_date'] = '2016-11-10 12:00:00'
    new_orders, new_items, inserted, updated = data.apply_batch(orders, items, fixed, pd.DataFrame(columns=data.ITEM_COLUMNS))
    assert inserted == 0 and updated == 1
    assert len(new_items) == len(items)
