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

$(BIN)/activate: requirements.txt
	uv venv
	source $(BIN)/activate && uv pip install -r requirements.txt

init: ## Initialize the project environment (venv & pre-commit)
	@$(MAKE) $(BIN)/activate
	@$(MAKE) update

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
	@rm -rf *.xlsx
	@rm -rf *.sqlite

bump: ## Show the next version
	@bump-my-version show-bump

bump-patch: $(BIN)/activate ## Bump patch version
	@printf "Applying patch bump\n"
	@$(BIN)/bump-my-version bump patch
	@$(MAKE) bump

bump-minor: $(BIN)/activate ## Bump minor version
	@printf "Applying minor bump\n"
	@$(BIN)/bump-my-version bump minor
	@$(MAKE) bump

bump-major: $(BIN)/activate ## Bump major version
	@printf "Applying major bump\n"
	@$(BIN)/bump-my-version bump major
	@$(MAKE) bump

update: $(BIN)/activate ## Update pip and pre-commit
	$(PYTHON) -m pre_commit autoupdate

lint: $(BIN)/activate ## Run pre-commit hooks
	$(PYTHON) -m pre_commit install --install-hooks
	$(PYTHON) -m pre_commit run --all-files

test: $(BIN)/activate ## Run unit tests
	$(PYTHON) -m $(TEST)

build-dist: $(BIN)/activate ## Generate distribution packages
	$(PYTHON) -m build

build-docker: ## Build the docker image
	@docker build -t crosstab .

build-docs: $(BIN)/activate ## Generate documentation
	@printf "Building documentation\n"
	@mkdocs build -c -q
	@open site/index.html

preview-docs: $(BIN)/activate ## Serve documentation
	@mkdocs serve -w .

publish: $(BIN)/activate ## Publish to PyPI
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) build-dist
	$(PYTHON) -m twine upload --repository pypi dist/*
	$(MAKE) clean

build: $(BIN)/activate ## Build the project
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) build-dist
	$(MAKE) build-docker
	$(MAKE) build-docs
