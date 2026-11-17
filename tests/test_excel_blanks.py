"""An empty month/lane should never be reported as a 0% late rate."""
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from src.delivery_analytics.analysis import calculate
from src.delivery_analytics.data import ORDERS_FILE
from src.delivery_analytics.excel import write_excel


def test_empty_month_lanes_are_blank(tmp_path: Path):
    result = calculate(pd.read_csv(ORDERS_FILE))
    file = tmp_path / 'scorecard.xlsx'
    write_excel(result, file)
    with ZipFile(file) as zipfile:
        names = zipfile.namelist()
        book = zipfile.read('xl/workbook.xml').decode()
        # The fifth worksheet is the month/lane matrix for the current design.
        assert 'Month x lane' in book
        sheets = [name for name in names if name.startswith('xl/worksheets/sheet') and name.endswith('.xml')]
        matrix = zipfile.read(sheets[3]).decode()  # Overview, Lane data, Scorecard, Matrix
        assert 'IF(SUMIFS(' in matrix
        assert '&quot;&quot;' in matrix or '""' in matrix
        assert 'IFERROR(' not in matrix
