import os
import sys

import pytest

# for testlib
sys.path.append(os.path.dirname(__file__))


def is_debugging():
    "https://stackoverflow.com/a/75438209"
    return "debugpy" in sys.modules


if is_debugging():
    # enable_stop_on_exceptions if the debugger is running during a test
    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value


def pytest_addoption(parser):
    parser.addoption("--use-python", type=str, default=None,
                     help="Run integration tests vs these python major versions, space separated")


class CurrentPython:
    @pytest.fixture(scope="session")
    def python_version(self):
        "python major version to use"
        return ".".join(str(elt) for elt in sys.version_info[:2])


def python_versions_fixture_from_str(versions: str):
    pyversions = versions.split()

    class ConfiguredPython:
        @pytest.fixture(scope="session", params=pyversions)
        def python_version(self, request: pytest.FixtureRequest):
            "python major version(s) to use"
            return request.param

    return ConfiguredPython()


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "server_args: extra uv sync arguments for server directory")
    config.addinivalue_line("markers", "unit: unit test")
    config.addinivalue_line("markers", "jupyter: jupyter integration test")

    if config.option.use_python:
        config.pluginmanager.register(python_versions_fixture_from_str(config.option.use_python))
    else:
        config.pluginmanager.register(CurrentPython())
