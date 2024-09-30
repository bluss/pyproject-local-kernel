import contextlib
import json
from pathlib import Path
import shutil
import signal
import sys

import pytest

from testlib import popen_capture, run, save_restore_file


_REINSTALL = "--reinstall-package pyproject-local-kernel"

def _pyversion(version_tuple):
    return ".".join(map(str, version_tuple[:2]))


TEST_VENV = "venv"
TEST_FALLBACK = "nokernel"
TEST_INTERRUPT = "interrupt"
SPECIAL_SCENARIOS = (TEST_VENV, TEST_FALLBACK, TEST_INTERRUPT)


@pytest.mark.parametrize("scenario", [
    "rye",
    "uv",
    "hatch",
    *SPECIAL_SCENARIOS,
])
def test_project_manager(scenario, monkeypatch, tmp_path_factory):
    """
    Test papermill and pyproject-local-kernel for notebook side vs uv / rye / hatch for project side
    """
    return impl_project_manager(_pyversion(sys.version_info), scenario, monkeypatch, tmp_path_factory)


def impl_project_manager(python: str, scenario: str,
                         monkeypatch: pytest.MonkeyPatch,
                         tmp_path_factory: pytest.TempPathFactory):
    if scenario not in SPECIAL_SCENARIOS and shutil.which(scenario) is None:
        pytest.skip(f"{scenario} not installed")

    uv = "uv"
    server_args = f"{_REINSTALL}"
    update = "-U" if python == "3.12" else ""
    papermill_args = ""
    notebook = "notebook.py"
    if scenario == TEST_FALLBACK:
        server_args += " --extra kernel"
    elif scenario == TEST_INTERRUPT:
        papermill_args += " --execution-timeout 1"
        notebook = "notebook-interrupt.py"


    monkeypatch.chdir("tests/server-client")

    client_dir = f"client-{scenario}"
    with contextlib.ExitStack() as stack:
        stack.enter_context(save_restore_file(Path("server/uv.lock"), tmp_path_factory.mktemp("server")))
        stack.enter_context(save_restore_file(Path(f"{client_dir}/uv.lock"), tmp_path_factory.mktemp("client")))

        with monkeypatch.context() as m:
            m.chdir("server")
            run(f"{uv} python pin -q {python}")
            run(f"{uv} sync -q {server_args} {update}")

        with monkeypatch.context() as m:
            m.chdir(client_dir)
            if scenario == "hatch":
                run("hatch env remove")
                run(f"env HATCH_PYTHON={python} hatch env run -- python -c ''")
            else:
                run(f"{uv} python pin -q {python}")
                run(f"{uv} sync -q {update}")

        # enable debug logging so we can assert on it
        monkeypatch.setenv("PYPROJECT_LOCAL_KERNEL_DEBUG", "1")

        run(f"cp -v {notebook} {client_dir}/notebook.py")
        run(f"{uv} run --project server jupytext --to ipynb {client_dir}/notebook.py")

        args = f"{uv} run --project server papermill {papermill_args} --cwd {client_dir} {client_dir}/notebook.ipynb {client_dir}/notebook_out.ipynb"
        proc = popen_capture(args)
        returncode = proc.returncode

        if scenario == TEST_FALLBACK:
            assert "Failed to start kernel! The detected project type is: UseVenv" in proc.stderr
            assert "ModuleNotFoundError: No module named 'jinja2'" in proc.stderr
        elif scenario == TEST_INTERRUPT:
            assert 'A cell timed out while it was being executed' in proc.stderr
            assert 'Parent appears to have exited' not in proc.stderr
            _assert_notebook_recorded_interrupt(Path(client_dir) / "notebook_out.ipynb")
        else:
            assert "Traceback" not in proc.stderr
            assert "Failed to start kernel" not in proc.stderr
            assert returncode == 0
            # Ensure signal forwarding is working
            assert f'Forwarding signal to kernel: {signal.SIGINT:d}' in proc.stderr



def _assert_notebook_recorded_interrupt(nb_path: Path):
    # One cell output will record the KeyboardInterrupt error
    with open(nb_path, "r") as nb_file:
        notebook_text = nb_file.read()
        notebook_json = json.loads(notebook_text)
    try:
        assert any('KeyboardInterrupt' in str(cell["outputs"]) for cell in notebook_json["cells"])
    except AssertionError:
        print("Notebook file", nb_path.name, file=sys.stderr)
        print(notebook_text, file=sys.stderr)
        raise
