VENV = .venv
BIN = $(VENV)/bin
PYTHON = $(BIN)/python
TEST = pytest

# Self documenting commands
.DEFAULT_GOAL := help
.PHONY: help
help: ## show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%s\033[0m|%s\n", $$1, $$2}' \
	| column -t -s '|'

$(BIN)/activate:
	uv venv
	source $(BIN)/activate && uv sync --all-extras

.PHONY: init
init: ## Initialize the project environment (venv & pre-commit)
	@$(MAKE) $(BIN)/activate
	@$(MAKE) update

.PHONY: clean
clean: ## Remove temporary files
	@rm -rf .ipynb_checkpoints
	@rm -rf **/.ipynb_checkpoints
	@rm -rf __pycache__
	@rm -rf **/__pycache__
	@rm -rf **/**/__pycache__
	@rm -rf .pytest_cache
	@rm -rf **/.pytest_cache
	@rm -rf .ruff_cache
	@rm -rf .coverage
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@rm -rf site/
	@rm -rf .mypy_cache
	@rm -rf **/**/*.xlsx
	@rm -rf **/**/*.sqlite

.PHONY: bump
bump: ## Show the next version
	@bump-my-version show-bump

.PHONY: bump-patch
bump-patch: $(BIN)/activate ## Bump patch version
	@printf "Applying patch bump\n"
	@$(BIN)/bump-my-version bump patch
	@$(MAKE) bump

.PHONY: bump-minor
bump-minor: $(BIN)/activate ## Bump minor version
	@printf "Applying minor bump\n"
	@$(BIN)/bump-my-version bump minor
	@$(MAKE) bump

.PHONY: bump-major
bump-major: $(BIN)/activate ## Bump major version
	@printf "Applying major bump\n"
	@$(BIN)/bump-my-version bump major
	@$(MAKE) bump

.PHONY: update
update: $(BIN)/activate ## Update pre-commit hooks
	$(PYTHON) -m pre_commit autoupdate

.PHONY: lint
lint: $(BIN)/activate ## Run pre-commit hooks
	$(PYTHON) -m pre_commit install --install-hooks
	$(PYTHON) -m pre_commit run --all-files

.PHONY: test
test: $(BIN)/activate ## Run unit tests
	$(PYTHON) -m $(TEST)

.PHONY: build-dist
build-dist: $(BIN)/activate ## Generate distribution packages
	$(PYTHON) -m build

.PHONY: build-docker
build-docker: ## Build the docker image
	@docker build -t crosstab .

.PHONY: build-docs
build-docs: $(BIN)/activate ## Generate documentation
	@printf "Building documentation\n"
	@mkdocs build -c -q

.PHONY: preview-docs
preview-docs: $(BIN)/activate ## Serve documentation
	@mkdocs serve -w .

.PHONY: publish
publish: $(BIN)/activate ## Publish to PyPI
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) build-dist
	$(PYTHON) -m twine upload --repository pypi dist/*
	$(MAKE) clean

.PHONY: build
build: $(BIN)/activate ## Build the project
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) build-dist
	$(MAKE) build-docker
	$(MAKE) build-docs
	$(MAKE) clean
