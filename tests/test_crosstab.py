#!/usr/bin/env python

import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import openpyxl
import pytest

from crosstab.crosstab import Crosstab, cli, clparser

logger = logging.getLogger(__name__)

# Sample data for tests
CSV_CONTENT = """header1,header2,header3,value,unit
A,1,2018,10,%
A,1,2019,20,%
B,2,2018,30,%
B,2,2019,40,%
"""

CSV_DUPLICATE_CONTENT = """header1,header2,header3,value,unit
A,1,2018,10,%
A,1,2018,11,%
B,2,2019,40,%
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
def temp_csv_with_duplicates():
    """Fixture for a CSV file containing duplicate row/col combinations."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as f:
        f.write(CSV_DUPLICATE_CONTENT)
        f.seek(0)
        yield Path(f.name)
    Path(f.name).unlink()


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
        value_cols=("value", "unit"),
    )
    assert crosstab.incsv == temp_csv_file
    assert crosstab.outxlsx == temp_xlsx_file


def test_default_output_path(temp_csv_file):
    """When outxlsx is not provided, default to <stem>_crosstab.xlsx alongside the input."""
    crosstab = Crosstab(
        incsv=temp_csv_file,
        row_headers=("header1",),
        col_headers=("header2",),
        value_cols=("value",),
    )
    assert crosstab.outxlsx == temp_csv_file.with_name(temp_csv_file.stem + "_crosstab.xlsx")


def test_repr_contains_paths(temp_csv_file, temp_xlsx_file):
    """__repr__ should contain the configured paths and headers."""
    crosstab = Crosstab(
        incsv=temp_csv_file,
        outxlsx=temp_xlsx_file,
        row_headers=("header1",),
        col_headers=("header2",),
        value_cols=("value",),
    )
    rep = repr(crosstab)
    assert "Crosstab(" in rep
    assert str(temp_csv_file) in rep
    assert str(temp_xlsx_file) in rep
    assert "header1" in rep
    assert "header2" in rep
    assert "value" in rep


def test_invalid_args_missing_file():
    """Test with missing CSV file"""
    with pytest.raises(ValueError, match="Input file .* does not exist."):
        Crosstab(
            incsv=Path("missing.csv"),
            outxlsx=Path("output.xlsx"),
            row_headers=("header1",),
            col_headers=("header2",),
            value_cols=("value", "unit"),
        )


def test_invalid_args_not_a_file(tmp_path):
    """Test with a directory passed as incsv."""
    directory = tmp_path / "not_a_file.csv"
    directory.mkdir()
    with pytest.raises(ValueError, match="is not a file"):
        Crosstab(
            incsv=directory,
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
            value_cols=("value", "unit"),
        )
    temp_csv.unlink()


def test_invalid_args_wrong_csv_extension(tmp_path):
    """Input must have a .csv extension."""
    bad = tmp_path / "input.txt"
    bad.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="is not a CSV file"):
        Crosstab(
            incsv=bad,
            outxlsx=Path("output.xlsx"),
            row_headers=("a",),
            col_headers=("b",),
            value_cols=("a",),
        )


def test_invalid_args_wrong_xlsx_extension(temp_csv_file, tmp_path):
    """Output must have a .xlsx extension."""
    bad = tmp_path / "output.csv"
    with pytest.raises(ValueError, match="must have an XLSX extension"):
        Crosstab(
            incsv=temp_csv_file,
            outxlsx=bad,
            row_headers=("header1",),
            col_headers=("header2",),
            value_cols=("value",),
        )


def test_invalid_args_empty_row_headers(temp_csv_file, temp_xlsx_file):
    with pytest.raises(ValueError, match="No row headers specified."):
        Crosstab(
            incsv=temp_csv_file,
            outxlsx=temp_xlsx_file,
            row_headers=(),
            col_headers=("header2",),
            value_cols=("value",),
        )


def test_invalid_args_empty_col_headers(temp_csv_file, temp_xlsx_file):
    with pytest.raises(ValueError, match="No column headers specified."):
        Crosstab(
            incsv=temp_csv_file,
            outxlsx=temp_xlsx_file,
            row_headers=("header1",),
            col_headers=(),
            value_cols=("value",),
        )


def test_invalid_args_empty_value_cols(temp_csv_file, temp_xlsx_file):
    with pytest.raises(ValueError, match="No value columns specified."):
        Crosstab(
            incsv=temp_csv_file,
            outxlsx=temp_xlsx_file,
            row_headers=("header1",),
            col_headers=("header2",),
            value_cols=(),
        )


def test_invalid_args_unknown_header(temp_csv_file, temp_xlsx_file):
    """Requesting a column that does not exist in the CSV should raise."""
    with pytest.raises(ValueError, match="Headers not found in CSV file"):
        Crosstab(
            incsv=temp_csv_file,
            outxlsx=temp_xlsx_file,
            row_headers=("not_a_real_column",),
            col_headers=("header2",),
            value_cols=("value",),
        )


def test_csv_to_sqlite(temp_csv_file):
    """Test the conversion of a CSV file to SQLite."""
    crosstab = Crosstab(
        incsv=temp_csv_file,
        outxlsx=Path("output.xlsx"),
        row_headers=("header1",),
        col_headers=("header2",),
        value_cols=("value", "unit"),
    )
    conn = crosstab._csv_to_sqlite()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data';")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "data"
    conn.close()


def test_keep_sqlite_overwrites_existing(tmp_path):
    """Pre-existing SQLite file at the target path is removed before re-creation."""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(CSV_CONTENT)
    sqlite_path = csv_path.with_suffix(".sqlite")
    sqlite_path.write_bytes(b"stale")
    assert sqlite_path.exists()

    crosstab = Crosstab(
        incsv=csv_path,
        outxlsx=tmp_path / "out.xlsx",
        row_headers=("header1",),
        col_headers=("header2",),
        value_cols=("value",),
        keep_sqlite=True,
    )
    crosstab.conn.close()
    # File was replaced, not appended-to.
    assert sqlite_path.exists()
    assert sqlite_path.read_bytes() != b"stale"


def test_duplicate_row_col_combination_raises(temp_csv_with_duplicates, temp_xlsx_file):
    """When the same row/col combination appears twice, crosstab() should raise."""
    crosstab = Crosstab(
        incsv=temp_csv_with_duplicates,
        outxlsx=temp_xlsx_file,
        row_headers=("header1",),
        col_headers=("header2", "header3"),
        value_cols=("value",),
    )
    with pytest.raises(ValueError, match="Multiple values found"):
        crosstab.crosstab()


def test_crosstab_creation(temp_csv_file, temp_xlsx_file):
    """Test the creation of a crosstab file."""
    crosstab = Crosstab(
        incsv=temp_csv_file,
        outxlsx=temp_xlsx_file,
        row_headers=("header1",),
        col_headers=("header2", "header3"),
        value_cols=("value", "unit"),
        keep_sqlite=True,
        keep_src=True,
    )
    crosstab.crosstab()
    assert temp_xlsx_file.exists()
    # Test that the xlsx file has 3 sheets
    wb = openpyxl.load_workbook(temp_xlsx_file)
    assert len(wb.sheetnames) == 3


def test_crosstab_omits_source_sheet_when_keep_src_false(temp_csv_file, temp_xlsx_file):
    """With keep_src=False the Source Data sheet should not be created."""
    Crosstab(
        incsv=temp_csv_file,
        outxlsx=temp_xlsx_file,
        row_headers=("header1",),
        col_headers=("header2", "header3"),
        value_cols=("value",),
        keep_src=False,
    ).crosstab()
    wb = openpyxl.load_workbook(temp_xlsx_file)
    assert "Source Data" not in wb.sheetnames
    assert "Crosstab" in wb.sheetnames
    assert "README" in wb.sheetnames


def test_crosstab_rows_single_value_column(temp_csv_file, temp_xlsx_file):
    """Test that values are correctly placed in the crosstab with one value column."""
    Crosstab(
        incsv=temp_csv_file,
        outxlsx=temp_xlsx_file,
        row_headers=("header1",),
        col_headers=("header2", "header3"),
        value_cols=("value",),
        keep_sqlite=False,
        keep_src=True,
    ).crosstab()
    wb = openpyxl.load_workbook(temp_xlsx_file)
    ws = wb["Crosstab"]
    # Check the row headers
    assert ws["A1"].value == "header2"
    assert ws["A2"].value == "header3"
    assert ws["A3"].value == "header1"
    assert ws["A4"].value == "A"
    assert ws["A5"].value == "B"
    # Check the column headers
    assert ws["B1"].value == "1"
    assert ws["C1"].value == "1"
    assert ws["D1"].value == "2"
    assert ws["E1"].value == "2"
    assert ws["B2"].value == "2018"
    assert ws["C2"].value == "2019"
    assert ws["D2"].value == "2018"
    assert ws["E2"].value == "2019"
    assert ws["B3"].value == "value"
    assert ws["C3"].value == "value"
    assert ws["D3"].value == "value"
    assert ws["E3"].value == "value"
    # Check the values
    assert ws["B4"].value == "10"
    assert ws["C4"].value == "20"
    assert ws["D4"].value is None
    assert ws["E4"].value is None
    assert ws["B5"].value is None
    assert ws["C5"].value is None
    assert ws["D5"].value == "30"
    assert ws["E5"].value == "40"
    wb.close()


def test_crosstab_rows_multi_value_column(temp_csv_file, temp_xlsx_file):
    """Test that values are correctly placed in the crosstab with multiple value columns."""
    Crosstab(
        incsv=temp_csv_file,
        outxlsx=Path(temp_xlsx_file),
        row_headers=("header1",),
        col_headers=("header2", "header3"),
        value_cols=("value", "unit"),
        keep_sqlite=False,
        keep_src=True,
    ).crosstab()
    wb = openpyxl.load_workbook(temp_xlsx_file)
    ws = wb["Crosstab"]
    # Check the row headers
    assert ws["A1"].value == "header2"
    assert ws["A2"].value == "header3"
    assert ws["A3"].value == "header1"
    assert ws["A4"].value == "A"
    assert ws["A5"].value == "B"
    # Check the column headers
    assert ws["B1"].value == "1"
    assert ws["C1"].value is None
    assert ws["D1"].value == "1"
    assert ws["E1"].value is None
    assert ws["F1"].value == "2"
    assert ws["G1"].value is None
    assert ws["H1"].value == "2"
    assert ws["I1"].value is None
    assert ws["B2"].value == "2018"
    assert ws["C2"].value is None
    assert ws["D2"].value == "2019"
    assert ws["E2"].value is None
    assert ws["F2"].value == "2018"
    assert ws["G2"].value is None
    assert ws["H2"].value == "2019"
    assert ws["I2"].value is None
    assert ws["B3"].value == "value"
    assert ws["C3"].value == "unit"
    assert ws["D3"].value == "value"
    assert ws["E3"].value == "unit"
    assert ws["F3"].value == "value"
    assert ws["G3"].value == "unit"
    assert ws["H3"].value == "value"
    assert ws["I3"].value == "unit"
    # Check the values
    assert ws["B4"].value == "10"
    assert ws["C4"].value == "%"
    assert ws["D4"].value == "20"
    assert ws["E4"].value == "%"
    assert ws["F4"].value is None
    assert ws["G4"].value is None
    assert ws["H4"].value is None
    assert ws["I4"].value is None
    assert ws["B5"].value is None
    assert ws["C5"].value is None
    assert ws["D5"].value is None
    assert ws["E5"].value is None
    assert ws["F5"].value == "30"
    assert ws["G5"].value == "%"
    assert ws["H5"].value == "40"
    assert ws["I5"].value == "%"
    wb.close()


# ── CLI tests ─────────────────────────────────────────────────────────────────


def _cli_argv(*extra: str) -> list[str]:
    return ["crosstab", *extra]


def test_clparser_builds():
    """clparser should return a working ArgumentParser."""
    parser = clparser()
    args = parser.parse_args(
        ["-f", "x.csv", "-r", "a", "-c", "b", "-v", "v"],
    )
    assert args.incsv == Path("x.csv")
    assert args.row_headers == ["a"]
    assert args.col_headers == ["b"]
    assert args.value_cols == ["v"]
    assert args.keep_sqlite is False
    assert args.keep_src is False
    assert args.quiet is False
    assert args.debug is False


def test_cli_version_flag(capsys):
    """`--version` should print the version and exit 0."""
    with pytest.raises(SystemExit) as exc, patch.object(sys, "argv", _cli_argv("--version")):
        cli()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "crosstab" in out


def test_cli_runs_end_to_end(tmp_path):
    """Invoke the CLI with valid args and confirm the output XLSX is produced."""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(CSV_CONTENT)
    out_path = tmp_path / "out.xlsx"
    argv = _cli_argv(
        "-q",
        "-s",
        "-f",
        str(csv_path),
        "-o",
        str(out_path),
        "-r",
        "header1",
        "-c",
        "header2",
        "header3",
        "-v",
        "value",
    )
    with patch.object(sys, "argv", argv):
        cli()
    assert out_path.exists()
    wb = openpyxl.load_workbook(out_path)
    assert "Crosstab" in wb.sheetnames
    assert "Source Data" in wb.sheetnames
    wb.close()


def test_cli_debug_log_to_file(tmp_path):
    """`--debug` plus `--log` should write debug output to the log file."""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(CSV_CONTENT)
    out_path = tmp_path / "out.xlsx"
    log_path = tmp_path / "run.log"
    argv = _cli_argv(
        "-d",
        "-l",
        str(log_path),
        "-f",
        str(csv_path),
        "-o",
        str(out_path),
        "-r",
        "header1",
        "-c",
        "header2",
        "header3",
        "-v",
        "value",
    )
    with patch.object(sys, "argv", argv):
        cli()
    assert out_path.exists()
    assert log_path.exists()
    assert log_path.read_text()  # non-empty


def test_cli_value_error_exits_nonzero(tmp_path):
    """A ValueError from the engine should produce exit code 1."""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(CSV_DUPLICATE_CONTENT)
    out_path = tmp_path / "out.xlsx"
    argv = _cli_argv(
        "-q",
        "-f",
        str(csv_path),
        "-o",
        str(out_path),
        "-r",
        "header1",
        "-c",
        "header2",
        "header3",
        "-v",
        "value",
    )
    with patch.object(sys, "argv", argv), pytest.raises(SystemExit) as exc:
        cli()
    assert exc.value.code == 1


def test_cli_unexpected_error_exits_nonzero(tmp_path):
    """An unexpected exception from the engine should produce exit code 1."""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(CSV_CONTENT)
    out_path = tmp_path / "out.xlsx"
    argv = _cli_argv(
        "-q",
        "-f",
        str(csv_path),
        "-o",
        str(out_path),
        "-r",
        "header1",
        "-c",
        "header2",
        "header3",
        "-v",
        "value",
    )
    with (
        patch("crosstab.crosstab.Crosstab.crosstab", side_effect=RuntimeError("boom")),
        patch.object(sys, "argv", argv),
        pytest.raises(SystemExit) as exc,
    ):
        cli()
    assert exc.value.code == 1
