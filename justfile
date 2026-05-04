# Install: brew install just  |  cargo install just  |  uv tool install rust-just
# Usage:   just <recipe>

set quiet

[private]
default:
    @just --list --unsorted

# ── Dependencies ──────────────────────────────────────────────────────────────

# Sync dependencies from lockfile
[group('deps')]
sync:
    uv sync --all-extras

# Update pre-commit hooks
[group('deps')]
update-hooks:
    uv run pre-commit autoupdate


# ── Code Quality ──────────────────────────────────────────────────────────────

# Lint, format, and test
[group('quality')]
check: lint format test

# Run linter
[group('quality')]
lint:
    uv run ruff check .

# Run formatter
[group('quality')]
format:
    uv run ruff format .

# Run pre-commit hooks on all files
[group('quality')]
pre-commit:
    uv run pre-commit run --all-files

# Run tests
[group('quality')]
test *ARGS:
    uv run tox -e py -- {{ ARGS }}

# Run tests across all supported Python versions
[group('quality')]
test-all:
    uv run tox run-parallel

# Run only the benchmark suite
[group('quality')]
benchmark:
    uv run pytest --benchmark-only

# Run tests with coverage report printed to terminal
[group('quality')]
coverage:
    uv run pytest --cov-report=term-missing

# Clean up Python build artifacts and caches
[group('quality')]
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +
    find . -type d -name "dist" -exec rm -rf {} +
    find . -type d -name "build" -exec rm -rf {} +
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    find . -type d -name ".ruff_cache" -exec rm -rf {} +
    find . -type d -name "site" -exec rm -rf {} +
    find . -type d -name ".benchmarks" -exec rm -rf {} +
    find . -type f -name "*.pyc" -exec rm -f {} +
    find . -type f -name "*.pyo" -exec rm -f {} +
    find . -type f -name ".coverage" -exec rm -rf {} +
    find . -type f -name "coverage.xml" -exec rm -rf {} +


# ── Documentation ─────────────────────────────────────────────────────────────

# Copy README and CHANGELOG into the docs source tree
[private]
_sync-docs:
    cp README.md docs/index.md
    cp CHANGELOG.md docs/change_log.md

# Build documentation
[group('docs')]
docs: _sync-docs
    uv run zensical build

# Serve documentation locally
[group('docs')]
docs-serve: _sync-docs
    uv run zensical serve


# ── Versioning ────────────────────────────────────────────────────────────────

# Show the next available version bumps
[group('version')]
bump:
    uv run bump-my-version show-bump

# Bump patch version (e.g. 1.2.3 → 1.2.4)
[group('version')]
bump-patch:
    uv run bump-my-version bump patch

# Bump minor version (e.g. 1.2.3 → 1.3.0)
[group('version')]
bump-minor:
    uv run bump-my-version bump minor

# Bump major version (e.g. 1.2.3 → 2.0.0)
[group('version')]
bump-major:
    uv run bump-my-version bump major


# ── Build ─────────────────────────────────────────────────────────────────────

# Build sdist + wheel
[group('build')]
build:
    uv build

# Build the Docker image
[group('build')]
build-docker:
    docker build -t crosstab .
