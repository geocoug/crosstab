# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

______________________________________________________________________

## [Unreleased]

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
