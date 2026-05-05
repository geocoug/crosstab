#!/usr/bin/env python

from __future__ import annotations

import logging
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
    result is materialized with one query before being written to the output
    workbook with ``xlsxwriter``.

    The output workbook contains:

    1. **Crosstab** — the pivoted table. Row-header values appear on the
       left; column-header values fan out across the top, grouped per
       value-column. ``autofilter`` is applied to the row-header row and
       the column-header rows are frozen.
    2. **Source Data** *(optional)* — a verbatim copy of the input CSV,
       included when ``keep_src=True``.

    Parameters
    ----------
    incsv:
        Path to the input CSV file.
    row_headers:
        Tuple of column names whose values become row keys.
    col_headers:
        Tuple of column names whose value combinations become column keys.
    value_cols:
        Tuple of column names whose values fill the crosstab cells.
    outxlsx:
        Output path. Defaults to ``<incsv stem>_crosstab.xlsx`` next to the
        input.
    fill:
        Value to write into empty cells. ``None`` (default) leaves them
        blank.
    keep_src:
        Append a "Source Data" sheet containing the verbatim input CSV.
    keep_duckdb:
        Persist the DuckDB database to disk at ``<incsv stem>.duckdb`` so
        the data can be queried again later.
    """

    def __init__(
        self: Crosstab,
        incsv: Path,
        row_headers: tuple,
        col_headers: tuple,
        value_cols: tuple,
        outxlsx: Path | None = None,
        fill: str | None = None,
        keep_src: bool = False,
        keep_duckdb: bool = False,
    ) -> None:
        self.incsv = Path(incsv)
        if outxlsx is None:
            outxlsx = self.incsv.with_name(self.incsv.stem + "_crosstab.xlsx")
        self.outxlsx = Path(outxlsx)
        self.row_headers = tuple(row_headers)
        self.col_headers = tuple(col_headers)
        self.value_cols = tuple(value_cols)
        self.fill = fill
        self.keep_src = keep_src
        self.keep_duckdb = keep_duckdb
        logger.debug(self)
        self._validate_args()

        if self.keep_duckdb:
            duckdb_path = self.incsv.with_suffix(".duckdb")
            if duckdb_path.exists():
                duckdb_path.unlink()
            self._con = duckdb.connect(str(duckdb_path))
        else:
            self._con = duckdb.connect()

        self.csv_columns = self._read_columns()
        self._validate_csv_headers()

    def __repr__(self: Crosstab) -> str:
        return (
            f"Crosstab(incsv={self.incsv!r}, outxlsx={self.outxlsx!r}, "
            f"row_headers={self.row_headers!r}, col_headers={self.col_headers!r}, "
            f"value_cols={self.value_cols!r}, fill={self.fill!r}, "
            f"keep_src={self.keep_src!r}, keep_duckdb={self.keep_duckdb!r})"
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

        # Stage the CSV as a DuckDB table named ``input_data``. We materialize
        # via CREATE TABLE (rather than register-a-view) so the data persists
        # in the on-disk database when ``keep_duckdb=True``.
        self._con.execute("DROP TABLE IF EXISTS input_data")
        self._con.execute(
            "CREATE TABLE input_data AS SELECT * FROM read_csv(?, all_varchar=true)",
            [str(self.incsv)],
        )

        rh_q = [_quote_ident(h) for h in self.row_headers]
        ch_q = [_quote_ident(h) for h in self.col_headers]
        vc_q = [_quote_ident(v) for v in self.value_cols]

        rh_list = ", ".join(rh_q)
        ch_list = ", ".join(ch_q)
        all_keys = ", ".join(rh_q + ch_q)

        # Strict mode: any (row_key, col_key) appearing more than once is a
        # fatal error — the crosstab cannot represent it without losing
        # information. The caller is expected to pre-aggregate the input
        # (with DuckDB, pandas, polars, etc.) if the source data contains
        # duplicates that should be combined.
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

        # Long-format result: one row per (row_key, col_key) with value
        # columns. The duplicate check above has already verified each group
        # has exactly one input row, so ``any_value()`` simply reads back
        # that single value — nothing is collapsed.
        logger.debug("Fetching value rows.")
        agg_select = ", ".join(
            rh_q + ch_q + [f"any_value({v}) AS {v}" for v in vc_q],
        )
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
                            val = self.fill
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
