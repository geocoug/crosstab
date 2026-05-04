# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

______________________________________________________________________

## [Unreleased]

### Changed

- Replaced the `argparse` CLI with a
    [rich-click](https://github.com/ewels/rich-click) app in
    `crosstab.cli` and routed the `crosstab` console-script entry point at
    it. Help output and log output use [Rich](https://rich.readthedocs.io/);
    validation errors come through Click with a non-zero exit code. The
    multi-value flags `-r`, `-c`, and `-v` keep the original
    space-separated UX (e.g. `-r loc sample`) via a small custom
    `OptionEatAll` Click option subclass.
- Replaced the SQLite-backed engine with a single-pass
    [DuckDB](https://duckdb.org/) pivot. CSV input is now read directly via
    `read_csv(..., all_varchar=True)`, duplicates are detected with one
    `GROUP BY ... HAVING COUNT(*) > 1` query, and the result is materialized
    in a single aggregate query rather than O(R × C) per-cell `SELECT`s. On
    a 100,000-cell pivot this is roughly two orders of magnitude faster.
- Replaced [openpyxl](https://openpyxl.readthedocs.io/) with
    [XlsxWriter](https://xlsxwriter.readthedocs.io/) for output. XlsxWriter
    is write-only and significantly faster and lower-memory for large
    workbooks; openpyxl remains a development dependency for reading
    workbooks in tests.
- Centralized SQL identifier quoting in `_quote_ident()`. Headers
    containing spaces, parentheses, embedded double quotes, unicode,
    leading digits, or SQL reserved words (e.g. `Depth Interval (ft)`,
    `select`, `Param "raw"`) now pass through end to end without being
    rewritten or breaking the engine.
- Row keys and column keys are now sorted before output, so re-running
    the same input produces a byte-identical workbook (modulo the README
    timestamp).

### Deprecated

- The `keep_sqlite` keyword argument and the `-k` / `--keep-sqlite` CLI
    flag are deprecated and ignored — the engine no longer uses SQLite.
    Passing `keep_sqlite=True` emits a `DeprecationWarning`. The argument
    will be removed in a future release.

### Added

- `pytest-benchmark` is a development dependency, with one baseline
    benchmark covering a 100,000-cell pivot.
- Test coverage for `_quote_ident` (parametrized over awkward identifier
    shapes) and an end-to-end round-trip test that exercises every
    problematic header category at once.

______________________________________________________________________

## [0.1.0] - 2026-05-04

### Changed

- Switched build backend from setuptools to hatchling and adopted the
    `src/crosstab/` package layout.
- Refreshed development toolchain to match `geocoug/execsql` and
    `geocoug/pg-upsert`: ruff 0.15.x, pre-commit hooks (gitleaks, uv-lock,
    mdformat, markdownlint, typos, ruff, validate-pyproject), tox-uv, and
    branch coverage with a 100% floor (defensive unreachable branches are
    marked `# pragma: no cover`).
- Expanded the test suite from 8 to 26 tests, covering all argument
    validation paths, the `__repr__`, the `keep_src=False` path, duplicate
    row/column detection, and the full CLI surface (`--version`,
    `--debug`, `--log`, error exit codes).
- Replaced MkDocs configuration with [zensical](https://zensical.org/),
    with `mkdocstrings-python` for auto-generated API reference.
- Replaced `Makefile` with a `justfile` for development tasks.
- Rewrote the GitHub Actions workflow: separate lint job, 3-OS × 5
    Python-version test matrix, OIDC PyPI publishing, and auto-generated
    GitHub releases on tag push.
- `__version__` is now read from package metadata via
    `importlib.metadata.version("crosstab")` rather than hard-coded in the
    source file. Versioning is driven by `bump-my-version`, which keeps
    `pyproject.toml` and this `CHANGELOG.md` in sync.

______________________________________________________________________

## [0.0.15] and earlier

See the project's git history for changes prior to the 0.1.0 toolchain
revamp.

<!-- Link reference definitions: maintained by bump-my-version. -->

[0.0.15]: https://github.com/geocoug/crosstab/releases/tag/v0.0.15
[0.1.0]: https://github.com/geocoug/crosstab/releases/tag/v0.1.0
[unreleased]: https://github.com/geocoug/crosstab/compare/v0.1.0...HEAD
