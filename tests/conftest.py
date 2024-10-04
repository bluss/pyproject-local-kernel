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


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "server_args: extra uv sync arguments for server directory")
    config.addinivalue_line("markers", "unit: unit test")
    config.addinivalue_line("markers", "jupyter: jupyter integration test")
