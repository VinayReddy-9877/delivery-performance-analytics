import os
from pathlib import Path

import pytest

from src.delivery_analytics.data import ROOT


def test_nine_business_queries_are_present():
    files = sorted((ROOT / 'sql/04_analysis').glob('*.sql'))
    assert len(files) == 9
    assert files[-1].name == '09_lane_excess_by_month.sql'


def test_delivery_severity_uses_real_fact_column():
    sql = (ROOT / 'sql/04_analysis/08_late_miss_severity.sql').read_text()
    assert 'estimated_date' in sql
    assert 'estimated_at' not in sql


@pytest.mark.skipif(not os.getenv('RUN_DB_TESTS'), reason='Set RUN_DB_TESTS=1 with an available Postgres instance')
def test_postgres_executes_all_queries():
    from src.delivery_analytics.db import check_sql
    assert len(check_sql()) == 9
