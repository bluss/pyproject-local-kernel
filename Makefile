root_dir:=$(dir $(realpath $(firstword $(MAKEFILE_LIST))))

.PHONY: test
test:
	# Test just current code / current version
	uv run --with pytest pytest $(ARGS)

.PHONY: test-all
test-all:
	uvx nox --no-venv $(ARGS)

.PHONY: build
build:
	uv build $(ARGS)

.PHONY: build-test
build-test:
	uvx --refresh-package pyproject-local-kernel --with dist/*.whl pytest $(ARGS)

.PHONY: docs-serve
docs-serve:
	# I am: uv run --project ./tools/mkdocs-tool mkdocs serve
	$(eval MKDOCS_PY := $(shell cd ./tools/mkdocs-tool && uv sync --locked && uv python find))
	$(MKDOCS_PY) -m mkdocs serve $(ARGS)
