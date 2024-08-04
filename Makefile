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
	cd ./tools/build-tool/;  uv run --locked python -m build -s -w --installer uv $(ARGS) $(root_dir)

.PHONY: build-test
build-test:
	uvx --reinstall --with dist/*.whl pytest $(ARGS)

.PHONY: docs-serve
docs-serve:
	cd ./tools/mkdocs-tool/;  uv run --locked mkdocs serve $(ARGS) -f $(root_dir)/mkdocs.yml
