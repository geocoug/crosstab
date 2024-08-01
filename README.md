# crosstab

[![ci/cd](https://github.com/geocoug/crosstab/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/geocoug/crosstab/actions/workflows/ci-cd.yml)
[![Documentation Status](https://readthedocs.org/projects/pg-upsert/badge/?version=latest)](https://pg-upsert.readthedocs.io/en/latest/?badge=latest)
[![PyPI Latest Release](https://img.shields.io/pypi/v/crosstab.svg)](https://pypi.org/project/crosstab/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/crosstab.svg?label=pypi%20downloads)](https://pypi.org/project/crosstab/)
[![Python Version Support](https://img.shields.io/pypi/pyversions/crosstab.svg)](https://pypi.org/project/crosstab/)

**crosstab** is a Python package that rearranges data from a normalized CSV format to a crosstabulated format, with styling.

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

The following examples demonstrate how to use **crosstab** to crosstabulate a CSV file. By default, the output is an Excel file with two sheets: one that contains metadata about the crosstabulation (ie. who ran the script, when it was run, etc.) and another with the data crosstabulated. If the `keep_sqlite` parameter is set to `True`, the SQLite database used to store the source data is kept. The SQLite file will have the same basename as the output Excel file, but with a `.sqlite` extension. If the `keep_src` parameter is set to `True`, the source CSV data is copied to the Excel file as a third sheet.

Each of the examples below will produce the exact same output.

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
    keep_sqlite=True,
    keep_src=True,
).crosstab()
```

### Command Line

```bash
crosstab -k -s -f data.csv -o crosstabbed_data.xlsx -r location sample -c cas_rn parameter -v concentration units
```

### Docker

```bash
docker run --rm -v $(pwd):/data ghcr.io/geocoug/crosstab:latest -k -s -f /data/data.csv -o /data/crosstabbed_data.xlsx -r location sample -c cas_rn parameter -v concentration units
```
