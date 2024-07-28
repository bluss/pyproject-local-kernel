
.PHONY: test
test:
	# Test just current code / current version
	uv run -q --with pytest pytest $(ARGS)

.PHONY: test-all
test-all:
	uvx -q nox --no-venv $(ARGS)

.PHONY: build
build:
	uvx --from build pyproject-build -s -w --installer uv $(ARGS)

.PHONY: build-test
build-test:
	# TODO: drop -n in next uv version
	uvx -n --reinstall --with dist/*.whl pytest $(ARGS)
