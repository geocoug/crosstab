# crosstab

[![ci/cd](https://github.com/geocoug/crosstab/actions/workflows/ci-cd.yaml/badge.svg)](https://github.com/geocoug/crosstab/actions/workflows/ci-cd.yaml)
[![Documentation Status](https://readthedocs.org/projects/crosstab/badge/?version=latest)](https://crosstab.readthedocs.io/en/latest/?badge=latest)
[![PyPI Latest Release](https://img.shields.io/pypi/v/crosstab.svg)](https://pypi.org/project/crosstab/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/crosstab.svg?label=pypi%20downloads)](https://pypi.org/project/crosstab/)
[![Python Version Support](https://img.shields.io/pypi/pyversions/crosstab.svg)](https://pypi.org/project/crosstab/)

**crosstab** rearranges data from a normalized CSV format to a crosstabulated
XLSX workbook, with styling. The pivot is computed in a single pass by
[DuckDB](https://duckdb.org/) and the workbook is produced by
[XlsxWriter](https://xlsxwriter.readthedocs.io/), so even very large inputs
crosstab in seconds. Column names containing spaces, parentheses, embedded
quotes, unicode, leading digits, or SQL reserved words pass through
unmodified.

Go from this:

![Crosstab Input](https://raw.githubusercontent.com/geocoug/crosstab/main/crosstab-input.png)

To this:

![Crosstab Output](https://raw.githubusercontent.com/geocoug/crosstab/main/crosstab-output.png)

## Installation

You can install **crosstab** via pip from PyPI:

```bash
pip install crosstab
```

There is also a Docker image available on the GitHub Container Registry:

```bash
docker pull ghcr.io/geocoug/crosstab:latest
```

## Usage

The output workbook contains:

1. **README** — metadata about the run (timestamp, user, script version,
    input/output paths).
1. **Crosstab** — the pivoted table. Row-header values are listed on the
    left; each distinct combination of column-header values fans out across
    the top, with one sub-column per requested value column.
1. **Source Data** *(optional)* — a verbatim copy of the input CSV, written
    when `keep_src=True`.

Each of the examples below produces the same output.

### Python

```python
from pathlib import Path

from crosstab import Crosstab

Crosstab(
    incsv=Path("data.csv"),
    outxlsx=Path("crosstabbed_data.xlsx"),
    row_headers=("location", "sample"),
    col_headers=("cas_rn", "parameter"),
    value_cols=("concentration", "units"),
    keep_src=True,
).crosstab()
```

### Command Line

`-r`, `-c`, and `-v` each accept one or more column names following the flag:

```bash
crosstab -s \
    -f data.csv \
    -o crosstabbed_data.xlsx \
    -r location sample \
    -c cas_rn parameter \
    -v concentration units
```

Run `crosstab --help` for the full option list.

### Docker

```bash
docker run --rm -v $(pwd):/data ghcr.io/geocoug/crosstab:latest \
    -s -f /data/data.csv -o /data/crosstabbed_data.xlsx \
    -r location sample \
    -c cas_rn parameter \
    -v concentration units
```

## Behavior

- **Strings preserved.** All CSV cells are read as strings via DuckDB's
    `read_csv(..., all_varchar=True)`, so values like `01` and `2026-05-04`
    are not coerced to numbers or dates.
- **Deterministic ordering.** Row keys and column keys are sorted before
    being written, so re-running the same input produces a byte-identical
    output (modulo the timestamp on the README sheet).
- **Strict duplicate detection.** If any `(row_key, col_key)` combination
    appears more than once in the input, the run fails with a clear
    `ValueError` rather than silently dropping data.
