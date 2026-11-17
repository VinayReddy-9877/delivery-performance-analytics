"""Prepare an order-level delivery extract from the nine public Olist CSVs.

Create the reporting tables from public Olist exports. The results depend
on the source release and how missing ZIP-level coordinates are handled.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.delivery_analytics.data import ITEM_COLUMNS, ORDER_COLUMNS, check_data

FILES = {
    'orders': 'olist_orders_dataset.csv',
    'items': 'olist_order_items_dataset.csv',
    'customers': 'olist_customers_dataset.csv',
    'sellers': 'olist_sellers_dataset.csv',
    'products': 'olist_products_dataset.csv',
    'categories': 'product_category_name_translation.csv',
    'geolocations': 'olist_geolocation_dataset.csv',
    'payments': 'olist_order_payments_dataset.csv',
    'reviews': 'olist_order_reviews_dataset.csv',
}


def load_raw(folder: Path) -> dict[str, pd.DataFrame]:
    missing = [filename for filename in FILES.values() if not (folder / filename).exists()]
    if missing:
        raise FileNotFoundError('Missing Olist source files: ' + ', '.join(missing))
    # Payments and reviews are checked as part of the nine-table source, but
    # they are not joined: doing so would multiply order items and inflate GMV.
    return {name: pd.read_csv(folder / filename) for name, filename in FILES.items()}


def prepare(source: Path, destination: Path) -> None:
    tables = load_raw(source)
    orders = tables['orders']
    items = tables['items']
    customers = tables['customers']
    sellers = tables['sellers']
    products = tables['products']
    categories = tables['categories']
    geos = tables['geolocations']

    # This report studies delivery time for orders that reached delivered status.
    # Undelivered orders need a separate failure-rate measure.
    orders = orders.loc[orders.order_status.eq('delivered')].copy()
    items = items.loc[items.order_id.isin(orders.order_id)].copy()
    orders = orders.loc[orders.order_id.isin(items.order_id)].copy()

    products = products[['product_id', 'product_category_name']].merge(
        categories, on='product_category_name', how='left', validate='m:1')
    items = items.merge(products, on='product_id', how='left', validate='m:1')
    items['category'] = items.product_category_name_english.fillna('Unknown')
    items_out = items[['order_id', 'order_item_id', 'seller_id', 'category', 'price']].copy()

    item_rollup = items.groupby('order_id').agg(
        gmv=('price', 'sum'), seller_count=('seller_id', 'nunique'),
        earliest_deadline=('shipping_limit_date', 'min')).reset_index()
    # Representative seller is deliberately omitted when multiple sellers
    # contribute to an order. Those orders cannot be assigned to one route.
    unique_seller = items[['order_id', 'seller_id']].drop_duplicates()
    single_seller = unique_seller.merge(
        item_rollup[['order_id', 'seller_count']], on='order_id', validate='m:1')
    single_seller = single_seller.loc[single_seller.seller_count.eq(1),
                                      ['order_id', 'seller_id']]
    # Main category: highest merchandise value, stable lexical tie-break.
    category_values = items.groupby(['order_id', 'category'], as_index=False).price.sum()
    main_category = (category_values.sort_values(
        ['order_id', 'price', 'category'], ascending=[True, False, True])
        .drop_duplicates('order_id')[['order_id', 'category']]
        .rename(columns={'category': 'main_category'}))

    joined = (orders.merge(customers[['customer_id', 'customer_unique_id',
                                      'customer_state', 'customer_zip_code_prefix']],
                           on='customer_id', validate='m:1')
              .merge(item_rollup, on='order_id', validate='1:1')
              .merge(single_seller, on='order_id', how='left', validate='1:1')
              .merge(main_category, on='order_id', validate='1:1'))
    seller_cols = sellers[['seller_id', 'seller_state', 'seller_zip_code_prefix']]
    joined = joined.merge(seller_cols, on='seller_id', how='left', validate='m:1')
    joined['seller_state'] = joined.seller_state.fillna('Unknown')

    # Median coordinates per ZIP prefix reduce sensitivity to duplicate points.
    zip_point = geos.groupby('geolocation_zip_code_prefix', as_index=False).agg(
        lat=('geolocation_lat', 'median'), lon=('geolocation_lng', 'median'))
    joined = joined.merge(zip_point.rename(columns={
        'geolocation_zip_code_prefix': 'customer_zip_code_prefix',
        'lat': 'customer_lat', 'lon': 'customer_lon'}),
        on='customer_zip_code_prefix', how='left', validate='m:1')
    joined = joined.merge(zip_point.rename(columns={
        'geolocation_zip_code_prefix': 'seller_zip_code_prefix',
        'lat': 'seller_lat', 'lon': 'seller_lon'}),
        on='seller_zip_code_prefix', how='left', validate='m:1')
    # Haversine straight-line distance, not courier road distance.
    lat1, lat2 = np.radians(joined.customer_lat), np.radians(joined.seller_lat)
    dlat = lat2 - lat1
    dlon = np.radians(joined.seller_lon - joined.customer_lon)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    joined['distance_km'] = 6371 * 2 * np.arcsin(np.sqrt(a.clip(0, 1)))

    purchase = pd.to_datetime(joined.order_purchase_timestamp)
    promise = pd.to_datetime(joined.order_estimated_delivery_date)
    joined['promise_days'] = (promise - purchase).dt.total_seconds() / 86400
    joined['order_estimated_delivery_date'] = promise.dt.strftime('%Y-%m-%d')
    output = joined.reindex(columns=ORDER_COLUMNS).copy()
    # Cast gmv after input grouping so the audit compares the same prices.
    output['gmv'] = output['gmv'].round(5)
    items_out = items_out.reindex(columns=ITEM_COLUMNS)
    audit = check_data(output, items_out)
    destination.mkdir(parents=True, exist_ok=True)
    output.to_csv(destination / 'orders_history.csv', index=False)
    items_out.to_csv(destination / 'order_items.csv', index=False)
    print(f"Prepared {audit['orders']:,} delivered-status orders and "
          f"{audit['items']:,} item rows; GMV difference "
          f"R$ {audit['gmv_difference_brl']:.2f}")
    print('Missing delivery outcomes remain visible and are not classified as on-time.')


def main() -> None:
    parser = argparse.ArgumentParser(description='Prepare Olist public raw files')
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('data/generated'))
    args = parser.parse_args()
    prepare(args.raw, args.out)


if __name__ == '__main__':
    main()
