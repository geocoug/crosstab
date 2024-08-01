#!/usr/bin/env python

import logging
import tempfile
from pathlib import Path

import openpyxl
import pytest

from crosstab.crosstab import Crosstab

logger = logging.getLogger(__name__)

# Sample data for tests
CSV_CONTENT = """header1,header2,header3,value
A,1,2018,10
A,1,2019,20
B,2,2018,30
B,2,2019,40
"""


@pytest.fixture(scope="session")
def global_variables():
    """Set global variables for the test session."""
    try:
        return {
            "SAMPLE_DATA_1": Path(__file__).parent / "data/sample1.csv",
            "SAMPLE_DATA_2": Path(__file__).parent / "data/sample2.csv",
        }
    except Exception:
        return None


def test_crosstab_init(global_variables):
    assert 1 == 1


@pytest.fixture
def temp_csv_file():
    """Fixture to create a temporary CSV file"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as f:
        f.write(CSV_CONTENT)
        f.seek(0)
        yield Path(f.name)
    Path(f.name).unlink()  # Clean up


@pytest.fixture
def temp_xlsx_file():
    """Fixture to create a temporary XLSX file"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        yield Path(f.name)
    Path(f.name).unlink()  # Clean up


def test_validate_args(temp_csv_file, temp_xlsx_file):
    """Test the validation of arguments."""
    crosstab = Crosstab(
        incsv=temp_csv_file,
        outxlsx=temp_xlsx_file,
        row_headers=("header1",),
        col_headers=("header2",),
        value_cols=("value",),
    )
    assert crosstab.incsv == temp_csv_file
    assert crosstab.outxlsx == temp_xlsx_file


def test_invalid_args_missing_file():
    """Test with missing CSV file"""
    with pytest.raises(ValueError, match="Input file .* does not exist."):
        Crosstab(
            incsv=Path("missing.csv"),
            outxlsx=Path("output.xlsx"),
            row_headers=("header1",),
            col_headers=("header2",),
            value_cols=("value",),
        )


def test_invalid_args_empty_file():
    """Test with an empty CSV file."""
    # Create an empty temporary CSV file
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        temp_csv = Path(f.name)
    with pytest.raises(ValueError, match="Input file .* is empty."):
        Crosstab(
            incsv=temp_csv,
            outxlsx=Path("output.xlsx"),
            row_headers=("header1",),
            col_headers=("header2",),
            value_cols=("value",),
        )
    temp_csv.unlink()


def test_csv_to_sqlite(temp_csv_file):
    """Test the conversion of a CSV file to SQLite."""
    crosstab = Crosstab(
        incsv=temp_csv_file,
        outxlsx=Path("output.xlsx"),
        row_headers=("header1",),
        col_headers=("header2",),
        value_cols=("value",),
    )
    conn = crosstab._csv_to_sqlite()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data';")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "data"
    conn.close()


def test_crosstab_creation(temp_csv_file, temp_xlsx_file):
    """Test the creation of a crosstab file."""
    crosstab = Crosstab(
        incsv=temp_csv_file,
        outxlsx=temp_xlsx_file,
        row_headers=("header1",),
        col_headers=("header2", "header3"),
        value_cols=("value",),
        keep_sqlite=True,
        keep_src=True,
    )
    crosstab.crosstab()
    assert temp_xlsx_file.exists()
    # Test that the xlsx file has 3 sheets
    wb = openpyxl.load_workbook(temp_xlsx_file)
    assert len(wb.sheetnames) == 3
