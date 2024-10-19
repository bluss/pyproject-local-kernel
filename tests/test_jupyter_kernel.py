from __future__ import annotations

import contextlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import textwrap

import threading
import time

import pytest

from testlib import PopenResult, popen_capture, run, save_restore_file


pytestmark = pytest.mark.jupyter

_PACKAGE_REINSTALL = "--reinstall-package pyproject-local-kernel"
_UPDATE_VERSIONS = {"3.12", "3.13"}


@contextlib.contextmanager
def chdir(path):
    with pytest.MonkeyPatch.context() as m:
        m.chdir(path)
        yield


@pytest.fixture(scope="session")
def server_dir(python_version: str):
    "setup dirver side directory with python version and empty virtual environment"
    base_dir = Path("tests/server-client") / "server"
    with chdir(base_dir):
        run(f"uv python pin -q {python_version}")
        run("uv venv -q")
    yield base_dir
    with chdir(base_dir):
        run("uv venv -q")


@pytest.fixture(scope="function")
def server_sync(server_dir: Path, python_version: str,
                tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest):
    "sync driver/pyproject-local-kernel side project"
    extra_args = [m.args[0] for m in request.node.iter_markers() if m.name == "server_args"]
    update = python_version in _UPDATE_VERSIONS
    with save_restore_file(server_dir / "uv.lock", tmp_path_factory.mktemp("server")):
        with chdir(server_dir):
            server_args = _PACKAGE_REINSTALL + (" -U" if update else "")
            if extra_args:
                server_args += " " + extra_args[0]
            run(f"uv sync -q {server_args}")
        yield
        # now we can restore uv.lock


@pytest.fixture(scope="function")
def scenario_setup(server_sync, python_version: str, tmp_path_factory: pytest.TempPathFactory):
    "setup project manager side and notebook"
    with contextlib.ExitStack() as stack:
        yield ScenarioSetup(python_version, stack, tmp_path_factory)


class ScenarioSetup:
    def __init__(self, python_version: str, stack: contextlib.ExitStack, tmp: pytest.TempPathFactory):
        self.python = python_version
        self.stack = stack
        self.tmp_path_factory = tmp
        self.base_dir = Path("tests/server-client")
        self.client_dir = None
        notebook_dir = tmp.mktemp("notebook")
        self.notebook_in = notebook_dir / "notebook.ipynb"
        self.notebook_out = notebook_dir / "notebook_out.ipynb"

    def scenario(self, name: str, update: bool = False, notebook: str | None = "notebook.py"):
        "prepare the ipykernel side project"
        client_dir = f"client-{name}"
        with chdir(self.base_dir / client_dir):
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
            with chdir(self.base_dir):
                run(f"uv run --project server jupytext --to ipynb {notebook} -o {self.notebook_in.as_posix()}")

    def papermill(self, papermill_args: str = "", launch_callback=None, timeout=None) -> PopenResult:
        "Run papermill on scenario notebook and return result with stdout/stderr"
        assert self.client_dir, "Have client directory"
        client_dir = self.client_dir.name

        with pytest.MonkeyPatch.context() as m:
            m.chdir(self.base_dir)
            # enable debug logging so we can assert on it
            m.setenv("PYPROJECT_LOCAL_KERNEL_DEBUG", "1")

            args = (f"uv run --project server papermill {papermill_args} --cwd {client_dir} "
                    f"{self.notebook_in.as_posix()} {self.notebook_out.as_posix()}")
            proc = popen_capture(args, launch_callback=launch_callback, timeout=timeout)
            return proc

    def nbconvert(self, args: str = "", launch_callback=None, timeout=None) -> PopenResult:
        "Run nbconvert on scenario notebook and return result with stdout/stderr"
        assert self.client_dir, "Have client directory"
        client_dir = self.client_dir.name

        with pytest.MonkeyPatch.context() as m:
            m.chdir(self.base_dir)
            m.setenv("PYPROJECT_LOCAL_KERNEL_DEBUG", "1")
            # Temporary location for notebook nested under client dir
            with tempfile.TemporaryDirectory(dir=self.client_dir) as client_tmp:
                nb = Path(client_tmp) / self.notebook_in.name
                shutil.copy(self.notebook_in, nb)
                args = f"uv run --project ../server jupyter-nbconvert --execute --inplace {args} {nb.as_posix()}"
                proc = popen_capture(args, launch_callback=launch_callback, timeout=timeout,
                                     popen_kwargs=dict(cwd=client_dir))
                return proc


@pytest.mark.parametrize("scenario,notebook", [
    ("rye", "notebook.py"),
    ("uv", "notebook.py"),
    ("uv", "notebook_use_venv.py"),
    ("hatch", "notebook.py"),
    ("venv", "notebook.py"),
])
def test_project_papermill(scenario: str, notebook: str, python_version: str,
                           scenario_setup: ScenarioSetup, executable: str = "papermill"):
    """
    Test papermill and pyproject-local-kernel for notebook side vs uv / rye / hatch / venv for project side
    """
    if scenario != "venv" and shutil.which(scenario) is None:
        pytest.skip(f"{scenario} not installed")
    if scenario == "rye" and python_version[2:] >= "13":
        pytest.skip(f"{scenario} does not support 3.13")

    update = python_version in _UPDATE_VERSIONS

    scenario_setup.scenario(scenario, update, notebook=notebook)
    proc = getattr(scenario_setup, executable)()
    returncode = proc.returncode

    assert "Traceback" not in proc.stderr
    assert "Failed to start kernel" not in proc.stderr
    assert returncode == 0


@pytest.mark.server_args("--extra nbconvert")
@pytest.mark.parametrize("scenario,notebook", [
    ("uv", "notebook.py"),
    ("venv", "notebook.py"),
])
def test_project_nbconvert(scenario: str, notebook: str, python_version: str, scenario_setup: ScenarioSetup):
    """
    Test nbconvert and pyproject-local-kernel for notebook side vs project side
    """
    test_project_papermill(scenario, notebook, python_version, scenario_setup, executable="nbconvert")


@pytest.mark.server_args("--extra kernel")
def test_no_kernel(scenario_setup: ScenarioSetup):
    "Project with no kernel installed"
    scenario = "nokernel"

    scenario_setup.scenario(scenario)
    proc = scenario_setup.papermill()

    # from sanity check
    assert "Could not find `ipykernel` in environment" in proc.stderr
    assert "ModuleNotFoundError: No module named 'jinja2'" in proc.stderr


def test_interrupt(python_version: str, scenario_setup: ScenarioSetup):
    "Interrupt running computation"
    scenario = "interrupt"
    papermill_args = "--execution-timeout 1"
    notebook = "notebook-interrupt.py"
    update = python_version in _UPDATE_VERSIONS

    scenario_setup.scenario(scenario, update=update, notebook=notebook)
    proc = scenario_setup.papermill(papermill_args)

    assert 'A cell timed out while it was being executed' in proc.stderr
    assert 'Parent appears to have exited' not in proc.stderr
    # assert that notebook recorded interrupt
    notebook_path = scenario_setup.notebook_out

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


@pytest.mark.skipif(sys.platform != "win32", reason="windows only because of ipykernel")
def test_interrupt_parent_gone(scenario_setup: ScenarioSetup):
    scenario = "interrupt"
    papermill_args = "--execution-timeout 10"
    notebook = "notebook-interrupt.py"

    scenario_setup.scenario(scenario, notebook=notebook)
    proc = scenario_setup.papermill(papermill_args, launch_callback=_kill_the_parent, timeout=30)
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
                print()
                print()
                for child in psutil.Process(proc.pid).children(recursive=True):
                    print(child.name(), child.cmdline())
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


def test_no_pyproject_toml(python_version: str, tmp_path: Path, pytestconfig: pytest.Config):
    with chdir(tmp_path):
        proc = popen_capture(f"uv run --no-dev --isolated -p {python_version}  --project '{pytestconfig.rootpath}' python -m pyproject_local_kernel")

    assert 'no pyproject.toml' in proc.stderr
    assert proc.returncode != 0


def test_direct_run(python_version: str, tmp_path: Path, pytestconfig: pytest.Config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PYPROJECT_LOCAL_KERNEL_DEBUG", "1")
    pyproject = f"""
    [project]
    name = "x"
    version = "1"
    dependencies = []
    requires-python = ">={python_version}"
    [tool.pyproject-local-kernel]
    """

    with chdir(tmp_path):
        cfile = tmp_path / "connection.json"
        with open(".python-version", "w") as pv:
            pv.write(python_version)
        with open("pyproject.toml", "w") as pf:
            pf.write(textwrap.dedent(pyproject))
        proc = popen_capture(f"uv run --no-dev --with ipykernel --isolated -p {python_version} "
                             f"--project '{pytestconfig.rootpath}' pyproject_local_kernel -f '{cfile}' --test-interrupt --test-quit")

    assert re.search(r'send signal.*SIGINT', proc.stderr)
    assert re.search(r'send signal.*SIGTERM', proc.stderr)
    assert proc.returncode != 0
