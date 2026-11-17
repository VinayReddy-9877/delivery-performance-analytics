
import csv
import json
import subprocess
import sys
import zipfile

from pathlib import Path

import pandas as pd
import pytest

from src.delivery_analytics.data import ROOT, ORDERS_FILE, ITEMS_FILE
from src.delivery_analytics.reports import write_reports


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    base = tmp_path_factory.mktemp("report_test") / "run"

    orders = pd.read_csv(ORDERS_FILE, encoding="utf-8")
    items = pd.read_csv(ITEMS_FILE, encoding="utf-8")

    write_reports(orders, items, base, week="2018-03-05")

    return base


def test_html_contains_priority_and_caveats(artifact):
    html = (artifact / "weekly_brief.html").read_text(
        encoding="utf-8"
    )

    assert "SP → RJ" in html
    assert "not a causal estimate" in html


def test_workbook_is_readable_and_formula_driven(artifact):
    with zipfile.ZipFile(artifact / "operations_workbook.xlsx") as archive:
        workbook = archive.read("xl/workbook.xml").decode("utf-8")

        formulas = sum(
            archive.read(name).count(b"<f>")
            for name in archive.namelist()
            if name.startswith("xl/worksheets/sheet")
        )

        assert "Lane data" in workbook
        assert "Lane scorecard" in workbook
        assert "Month x lane" in workbook
        assert formulas > 100


def test_pdf_is_one_page(artifact):
    from pypdf import PdfReader

    pdf = PdfReader(artifact / "01_insight_memo.pdf")
    assert len(pdf.pages) == 1


def test_exported_csv_contains_sp_rj(artifact):
    csv_path = artifact / "lane_priorities.csv"

    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8"
    ) as f:
        row = next(csv.DictReader(f))

    assert row["lane"] == "SP → RJ"


def test_alert_csv_contains_real_rule(artifact):
    csv_path = artifact / "alerts.csv"

    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8"
    ) as f:
        alerts = list(csv.DictReader(f))

    assert alerts
    assert all(
        float(row["multiple"]) >= 2
        for row in alerts
    )


def test_metrics_match(artifact):
    metrics_path = artifact / "metrics.json"

    metrics = json.loads(
        metrics_path.read_text(encoding="utf-8")
    )

    assert metrics["late_orders"] == 6534


def test_source_preparation_command_is_available():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.prepare_olist",
            "--help"
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False
    )

    assert result.returncode == 0, result.stderr
    assert "--raw" in result.stdout


