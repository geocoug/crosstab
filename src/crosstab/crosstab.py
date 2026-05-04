#!/usr/bin/env python

from __future__ import annotations

import datetime
import getpass
import logging
import os
import warnings
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import duckdb
import xlsxwriter

__title__ = "crosstab"
__author__ = "Caleb Grant"
__url__ = "https://github.com/geocoug/crosstab"
__author_email__ = "grantcaleb22@gmail.com"
__license__ = "GNU GPLv3"
__description__ = "Rearrange data from a normalized CSV format to a crosstabulated format, with styling."

try:
    __version__ = version("crosstab")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.NullHandler()],
)
logger = logging.getLogger(__name__)

# 1-indexed coordinates of the top-left of the crosstab table on the output sheet.
XTAB_START_ROW = 1
XTAB_START_COL = 1


def _current_user() -> str:
    """Best-effort username for the README metadata sheet.

    ``getpass.getuser()`` raises ``ModuleNotFoundError`` on Windows when
    none of the standard env vars are set (it falls back to ``import pwd``,
    which is Unix-only). We try the env vars first and fall back to
    ``"unknown"`` so a crosstab run never fails over a metadata field.
    """
    for var in ("USERNAME", "USER", "LOGNAME", "LNAME"):
        value = os.environ.get(var)
        if value:
            return value
    try:
        return getpass.getuser()
    except Exception:  # pragma: no cover
        return "unknown"


def _quote_ident(name: str) -> str:
    """Quote a SQL identifier for DuckDB by doubling internal double quotes.

    Allows arbitrary CSV column names — including spaces, parentheses,
    embedded quotes, unicode, leading digits, and SQL reserved words — to
    appear unmodified in DuckDB queries.
    """
    return '"' + str(name).replace('"', '""') + '"'


class Crosstab:
    """Rearrange a normalized CSV into a crosstabulated XLSX workbook.

    The crosstab is computed by DuckDB in a single pass: the CSV is read
    via ``read_csv`` (with ``all_varchar=True`` to preserve string semantics),
    duplicate row/column key combinations are detected with a
    ``GROUP BY ... HAVING COUNT(*) > 1`` query, and the pivoted long-format
    result is materialized with one aggregate query before being written to
    the output workbook with ``xlsxwriter``.

    The output workbook contains:

    1. **README** — metadata about the run (timestamp, user, script version,
       input/output file paths).
    2. **Crosstab** — the pivoted table. Row-header values appear on the
       left; column-header values fan out across the top, grouped per
       value-column. ``autofilter`` is applied to the row-header row and
       the column-header rows are frozen.
    3. **Source Data** *(optional)* — the raw input CSV, included when
       ``keep_src=True``.

    Example
    -------
    Given an input CSV like

    ```
    location,sample,parameter,result,units
    Loc1,Samp1,pH,7.2,
    Loc1,Samp1,Hardness,120,mg/L
    Loc2,Samp2,pH,8.0,
    Loc2,Samp2,Hardness,3.23,mg/L
    ```

    a call such as

    ```python
    Crosstab(
        incsv=Path("input.csv"),
        row_headers=("location", "sample"),
        col_headers=("parameter",),
        value_cols=("result", "units"),
    ).crosstab()
    ```

    produces a crosstab table with row keys ``(location, sample)``, one
    column block per distinct ``parameter`` value, and two sub-columns
    (``result`` and ``units``) inside each block.
    """

    def __init__(
        self: Crosstab,
        incsv: Path,
        row_headers: tuple,
        col_headers: tuple,
        value_cols: tuple,
        outxlsx: Path | None = None,
        keep_sqlite: bool = False,
        keep_src: bool = False,
    ) -> None:
        self.incsv = Path(incsv)
        if outxlsx is None:
            outxlsx = self.incsv.with_name(self.incsv.stem + "_crosstab.xlsx")
        self.outxlsx = Path(outxlsx)
        self.row_headers = tuple(row_headers)
        self.col_headers = tuple(col_headers)
        self.value_cols = tuple(value_cols)
        self.keep_src = keep_src
        self.keep_sqlite = keep_sqlite
        if keep_sqlite:
            warnings.warn(
                "keep_sqlite is deprecated and ignored: the engine no longer uses SQLite.",
                DeprecationWarning,
                stacklevel=2,
            )
        logger.debug(self)
        self._validate_args()
        self._con = duckdb.connect()
        self.csv_columns = self._read_columns()
        self._validate_csv_headers()

    def __repr__(self: Crosstab) -> str:
        return (
            f"Crosstab(incsv={self.incsv!r}, outxlsx={self.outxlsx!r}, "
            f"row_headers={self.row_headers!r}, col_headers={self.col_headers!r}, "
            f"value_cols={self.value_cols!r}, keep_sqlite={self.keep_sqlite!r})"
        )

    def _validate_args(self: Crosstab) -> None:
        if not self.incsv.exists():
            raise ValueError(f"Input file {self.incsv} does not exist.")
        if not self.incsv.is_file():
            raise ValueError(f"Input file {self.incsv} is not a file.")
        if not self.incsv.stat().st_size:
            raise ValueError(f"Input file {self.incsv} is empty.")
        if self.incsv.suffix.lower() != ".csv":
            raise ValueError(f"Input file {self.incsv} is not a CSV file.")
        if self.outxlsx.suffix.lower() != ".xlsx":
            raise ValueError("Output file must have an XLSX extension.")
        if not self.row_headers:
            raise ValueError("No row headers specified.")
        if not self.col_headers:
            raise ValueError("No column headers specified.")
        if not self.value_cols:
            raise ValueError("No value columns specified.")

    def _read_columns(self: Crosstab) -> tuple[str, ...]:
        rel = self._con.read_csv(str(self.incsv), all_varchar=True)
        return tuple(rel.columns)

    def _validate_csv_headers(self: Crosstab) -> None:
        bad = [h for h in self.row_headers + self.col_headers + self.value_cols if h not in self.csv_columns]
        if bad:
            raise ValueError(f"Headers not found in CSV file: {', '.join(bad)}.")

    def crosstab(self: Crosstab) -> None:
        """Compute the crosstab and write it to ``self.outxlsx``."""
        logger.info(f"Creating crosstab table from {self.incsv}.")

        # Stage the CSV as a DuckDB view named ``input_data``.
        self._con.register(
            "input_data",
            self._con.read_csv(str(self.incsv), all_varchar=True),
        )

        rh_q = [_quote_ident(h) for h in self.row_headers]
        ch_q = [_quote_ident(h) for h in self.col_headers]
        vc_q = [_quote_ident(v) for v in self.value_cols]

        rh_list = ", ".join(rh_q)
        ch_list = ", ".join(ch_q)
        all_keys = ", ".join(rh_q + ch_q)

        # Duplicate detection: any (row_key, col_key) appearing more than once
        # is a fatal error — the crosstab cannot represent it without losing
        # information.
        logger.debug("Checking for duplicate row/column key combinations.")
        dup_sql = f"SELECT {all_keys} FROM input_data GROUP BY {all_keys} HAVING COUNT(*) > 1 LIMIT 1"
        if self._con.execute(dup_sql).fetchone():
            raise ValueError("Multiple values found for the row/column combination(s).")

        # Distinct row keys and col keys, sorted for deterministic output.
        logger.debug("Fetching distinct row-header values.")
        row_keys = self._con.execute(
            f"SELECT DISTINCT {rh_list} FROM input_data ORDER BY {rh_list}",
        ).fetchall()
        logger.debug("Fetching distinct column-header values.")
        col_keys = self._con.execute(
            f"SELECT DISTINCT {ch_list} FROM input_data ORDER BY {ch_list}",
        ).fetchall()

        # Aggregated long-format result: one row per (row_key, col_key) with
        # value columns. ``any_value`` is safe because duplicates are detected
        # above, so each group has exactly one input row.
        logger.debug("Fetching aggregated value rows.")
        agg_select = ", ".join(rh_q + ch_q + [f"any_value({v}) AS {v}" for v in vc_q])
        agg_rows = self._con.execute(
            f"SELECT {agg_select} FROM input_data GROUP BY {all_keys}",
        ).fetchall()

        n_rh = len(self.row_headers)
        n_ch = len(self.col_headers)
        cells: dict[tuple[tuple, tuple], tuple] = {}
        for r in agg_rows:
            row_key = r[:n_rh]
            col_key = r[n_rh : n_rh + n_ch]
            cells[(row_key, col_key)] = r[n_rh + n_ch :]

        self._write_xlsx(row_keys, col_keys, cells)

    def _write_xlsx(
        self: Crosstab,
        row_keys: list[tuple],
        col_keys: list[tuple],
        cells: dict[tuple[tuple, tuple], tuple],
    ) -> None:
        n_rh = len(self.row_headers)
        n_ch = len(self.col_headers)
        n_vc = len(self.value_cols)

        wb = xlsxwriter.Workbook(str(self.outxlsx))
        try:
            title_fmt = wb.add_format(
                {
                    "font_name": "Arial",
                    "bold": True,
                    "font_size": 11,
                    "font_color": "#005782",
                    "align": "center",
                    "valign": "vcenter",
                },
            )
            primary_hdr = wb.add_format(
                {
                    "bold": True,
                    "font_size": 12,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "border_color": "#000000",
                },
            )
            secondary_hdr = wb.add_format(
                {
                    "bold": True,
                    "font_size": 12,
                    "bg_color": "#F2F2F2",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "border_color": "#000000",
                },
            )
            data_fmt = wb.add_format(
                {
                    "font_size": 12,
                    "bg_color": "#FFFFFF",
                    "align": "left",
                    "valign": "vcenter",
                    "border": 1,
                    "border_color": "#000000",
                },
            )
            meta_item = wb.add_format(
                {
                    "bold": True,
                    "font_size": 12,
                    "align": "right",
                    "valign": "vcenter",
                    "border": 1,
                    "border_color": "#000000",
                },
            )
            meta_value = wb.add_format(
                {
                    "font_size": 12,
                    "align": "left",
                    "valign": "vcenter",
                    "border": 1,
                    "border_color": "#000000",
                },
            )

            # README sheet
            readme = wb.add_worksheet("README")
            readme.merge_range(0, 0, 0, 1, "Crosstab Metadata", title_fmt)
            readme.write(1, 0, "Item", primary_hdr)
            readme.write(1, 1, "Value", primary_hdr)
            metadata = [
                (
                    "Creation Time",
                    datetime.datetime.now().isoformat(sep=" ", timespec="seconds"),
                ),
                ("User", _current_user()),
                ("Script Version", __version__),
                ("Input File", self.incsv.resolve().as_posix()),
                ("Output File", self.outxlsx.resolve().as_posix()),
            ]
            for row_idx, (k, v) in enumerate(metadata, start=2):
                readme.write(row_idx, 0, k, meta_item)
                readme.write(row_idx, 1, v, meta_value)
            readme.autofit()

            # Crosstab sheet
            sheet = wb.add_worksheet("Crosstab")

            # Column-header labels (one row per col_header level), placed in
            # the column immediately to the left of the data.
            for c, ch in enumerate(self.col_headers):
                sheet.write(c, n_rh - 1, ch, secondary_hdr)

            # Column-header value cells, merged across n_vc value columns
            # when multiple value columns are configured.
            for i, col_key in enumerate(col_keys):
                first_col = n_rh + i * n_vc
                last_col = first_col + n_vc - 1
                for c in range(n_ch):
                    cell_val = col_key[c]
                    if n_vc > 1:
                        sheet.merge_range(
                            c,
                            first_col,
                            c,
                            last_col,
                            cell_val,
                            primary_hdr,
                        )
                    else:
                        sheet.write(c, first_col, cell_val, primary_hdr)
                # Value-column label row (just below the column-header rows).
                for j, vc in enumerate(self.value_cols):
                    sheet.write(n_ch, first_col + j, vc, secondary_hdr)

            # Row-header labels live on the same row as the value-column labels.
            for h, rh in enumerate(self.row_headers):
                sheet.write(n_ch, h, rh, primary_hdr)

            # Data rows
            data_row_start = n_ch + 1
            for r, row_key in enumerate(row_keys):
                row_idx = data_row_start + r
                for h in range(n_rh):
                    sheet.write(row_idx, h, row_key[h], data_fmt)
                for i, col_key in enumerate(col_keys):
                    values = cells.get((row_key, col_key))
                    for j in range(n_vc):
                        col_idx = n_rh + i * n_vc + j
                        val = values[j] if values is not None else None
                        if val is None:
                            sheet.write_blank(row_idx, col_idx, None, data_fmt)
                        else:
                            sheet.write(row_idx, col_idx, val, data_fmt)

            sheet.autofilter(n_ch, 0, n_ch, n_rh - 1)
            sheet.freeze_panes(data_row_start, 0)
            sheet.autofit()

            # Optional Source Data sheet — verbatim copy of the input CSV.
            if self.keep_src:
                src = wb.add_worksheet("Source Data")
                src.write_row(0, 0, list(self.csv_columns))
                src_rows = self._con.execute("SELECT * FROM input_data").fetchall()
                for r_idx, row in enumerate(src_rows, start=1):
                    src.write_row(r_idx, 0, list(row))
                src.autofit()

            logger.info(f"Saving output to {self.outxlsx}.")
        finally:
            wb.close()

    def close(self: Crosstab) -> None:
        """Release the DuckDB connection."""
        self._con.close()
