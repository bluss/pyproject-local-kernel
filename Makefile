root_dir:=$(dir $(realpath $(firstword $(MAKEFILE_LIST))))

.PHONY: test
test:
	# Test just current code / current version
	uv run -q --with pytest pytest $(ARGS)

.PHONY: test-all
test-all:
	uvx -q nox --no-venv $(ARGS)

.PHONY: build
build:
	cd ./tools/py-build/;  uv run --locked python -m build -s -w --installer uv $(ARGS) $(root_dir)

.PHONY: build-test
build-test:
	# TODO: drop -n in next uv version
	uvx -n -q --reinstall --with dist/*.whl pytest $(ARGS)
