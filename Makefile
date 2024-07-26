
.PHONY: test
test:
	uv run --with pytest pytest $(ARGS)
	# not using this because it caches '.' and doesn't want to reinstall it:
	#uvx -v --with . pytest $(ARGS)

.PHONY: build
build:
	uvx --from build pyproject-build -s -w --installer uv $(ARGS)

.PHONY: build-test
build-test:
	# TODO: drop -n in next uv version
	uvx -n --reinstall --with dist/*.whl pytest $(ARGS)
