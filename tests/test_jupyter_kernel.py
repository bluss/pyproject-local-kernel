from __future__ import annotations

import contextlib
import json
from pathlib import Path
import shutil
import signal
import sys
import threading
import time

import pytest

from testlib import PopenResult, popen_capture, run, save_restore_file


pytestmark = pytest.mark.jupyter

_PACKAGE_REINSTALL = "--reinstall-package pyproject-local-kernel"


@pytest.fixture(scope="session")
def python_version() -> str:
    "current python major version, like '3.12'"
    version_tuple = sys.version_info
    return ".".join(map(str, version_tuple[:2]))


@pytest.fixture(scope="function")
def scenario_setup(python_version: str, monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory):
    with contextlib.ExitStack() as stack:
        yield ScenarioSetup(python_version, stack, monkeypatch, tmp_path_factory)


class ScenarioSetup:
    def __init__(self, python_version: str, stack: contextlib.ExitStack,
                 mp: pytest.MonkeyPatch, tmp: pytest.TempPathFactory):
        self.python = python_version
        self.stack = stack
        self.monkeypatch = mp
        self.tmp_path_factory = tmp
        self.base_dir = Path("tests/server-client")
        self.client_dir = None

    def get_client_dir(self) -> Path:
        if self.client_dir is None:
            raise RuntimeError("Did not build client directory")
        return self.client_dir

    def server(self, server_args: str = _PACKAGE_REINSTALL, update: bool = False):
        "prepare driver/pyproject-local-kernel side project"
        with self.monkeypatch.context() as m:
            m.chdir(self.base_dir / "server")
            self.stack.enter_context(save_restore_file(Path("uv.lock"), self.tmp_path_factory.mktemp("server")))
            server_args += " -U" if update else ""
            run(f"uv python pin -q {self.python}")
            run("uv venv -q")
            run(f"uv sync -q {server_args}")

    def scenario(self, name: str, update: bool = False, notebook: str | None = "notebook.py") -> str:
        "prepare the ipykernel side project"
        client_dir = f"client-{name}"
        with self.monkeypatch.context() as m:
            m.chdir(self.base_dir / client_dir)
            self.stack.enter_context(save_restore_file(Path("uv.lock"), self.tmp_path_factory.mktemp(client_dir)))
            if name == "hatch":
                run("hatch env remove")
                run(f"env HATCH_PYTHON={self.python} hatch env run -- python -c ''")
            else:
                update_arg = "-U" if update else ""
                run(f"uv python pin -q {self.python}")
                run("uv venv -q")
                run(f"uv sync -q {update_arg}")
        self.client_dir = (self.base_dir / client_dir).absolute()
        if notebook:
            with self.monkeypatch.context() as m:
                m.chdir(self.base_dir)
                run(f"uv run --project server jupytext --to ipynb {notebook} -o {client_dir}/notebook.ipynb")
        return client_dir

    def papermill(self, client_dir: str, papermill_args: str = "", launch_callback=None) -> PopenResult:
        "Run papermill and return result with stdout/stderr"
        with self.monkeypatch.context() as m:
            m.chdir(self.base_dir)
            # enable debug logging so we can assert on it
            m.setenv("PYPROJECT_LOCAL_KERNEL_DEBUG", "1")

            args = f"uv run --project server papermill {papermill_args} --cwd {client_dir} {client_dir}/notebook.ipynb {client_dir}/notebook_out.ipynb"
            proc = popen_capture(args, launch_callback=launch_callback)
            return proc



@pytest.mark.parametrize("scenario", [
    "rye",
    "uv",
    "hatch",
    "venv",
])
def test_project_manager(scenario: str, python_version: str, scenario_setup: ScenarioSetup):
    """
    Test papermill and pyproject-local-kernel for notebook side vs uv / rye / hatch / venv for project side
    """
    if scenario != "venv" and shutil.which(scenario) is None:
        pytest.skip(f"{scenario} not installed")

    update = python_version == "3.12"

    scenario_setup.server(update=update)
    dir = scenario_setup.scenario(scenario, update)
    proc = scenario_setup.papermill(dir)
    returncode = proc.returncode

    assert "Traceback" not in proc.stderr
    assert "Failed to start kernel" not in proc.stderr
    assert returncode == 0
    # Ensure signal forwarding is working
    assert f'Forwarding signal to kernel: {signal.SIGINT:d}' in proc.stderr


def test_no_kernel(scenario_setup: ScenarioSetup):
    "Project with no kernel installed"
    scenario = "nokernel"
    server_args = _PACKAGE_REINSTALL
    server_args += " --extra kernel"

    scenario_setup.server(server_args)
    dir = scenario_setup.scenario(scenario)
    proc = scenario_setup.papermill(dir)

    assert "Failed to start kernel! The detected project type is: UseVenv" in proc.stderr
    assert "ModuleNotFoundError: No module named 'jinja2'" in proc.stderr


def test_interrupt(python_version: str, scenario_setup: ScenarioSetup):
    "Interrupt running computation"
    scenario = "interrupt"
    papermill_args = "--execution-timeout 1"
    notebook = "notebook-interrupt.py"
    update = python_version == "3.12"

    scenario_setup.server(update=update)
    dir = scenario_setup.scenario(scenario, update=update, notebook=notebook)
    proc = scenario_setup.papermill(dir, papermill_args)

    assert 'A cell timed out while it was being executed' in proc.stderr
    assert 'Parent appears to have exited' not in proc.stderr
    # assert that notebook recorded interrupt
    notebook_path = scenario_setup.get_client_dir() / "notebook_out.ipynb"

    # One cell output will record the KeyboardInterrupt error
    with open(notebook_path, "r") as nb_file:
        notebook_text = nb_file.read()
        notebook_json = json.loads(notebook_text)
    try:
        assert any('KeyboardInterrupt' in str(cell["outputs"]) for cell in notebook_json["cells"])
    except AssertionError:
        print("Notebook file", notebook_path.name, file=sys.stderr)
        print(notebook_text, file=sys.stderr)
        raise


def test_interrupt_parent_gone(scenario_setup: ScenarioSetup):
    scenario = "interrupt"
    papermill_args = "--execution-timeout 10"
    notebook = "notebook-interrupt.py"

    scenario_setup.server()
    dir = scenario_setup.scenario(scenario, notebook=notebook)
    proc = scenario_setup.papermill(dir, papermill_args, launch_callback=_kill_the_parent)
    returncode = proc.returncode

    assert 'Parent appears to have exited' in proc.stderr
    assert returncode != 0


def _kill_the_parent(proc):
    # local import - so that unit tests don't need to depend on it
    import psutil

    def thread_body():
        has_kernel = False
        while True:
            try:
                for child in psutil.Process(proc.pid).children(recursive=True):
                    if "ipykernel_launcher" in child.cmdline():
                        has_kernel = True
                    elif has_kernel and (child.name().startswith("papermill") or
                        any("bin/papermill" in part for part in child.cmdline())):
                        print("terminating process", child)
                        child.terminate()
            except psutil.NoSuchProcess:
                break
            time.sleep(0.3)
    thread = threading.Thread(target=thread_body, daemon=True)
    thread.start()


def test_no_pyproject_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pytestconfig: pytest.Config):
    monkeypatch.chdir(tmp_path)
    proc = popen_capture(f"uv run --project '{pytestconfig.rootpath}' python -m pyproject_local_kernel")

    assert 'No pyproject.toml found - do you need to create a new project?' in proc.stderr
    assert proc.returncode != 0
