import contextlib
from pathlib import Path
import shutil
import sys

import pytest

from testlib import popen_capture, run, save_restore_file


_REINSTALL = "--reinstall-package pyproject-local-kernel"

def _pyversion(version_tuple):
    return ".".join(map(str, version_tuple[:2]))


@pytest.mark.flaky(retries=2, delay=1, condition=sys.platform.startswith('win32'))
@pytest.mark.parametrize("manager", [
    "rye",
    "uv",
    "hatch",
])
def test_project_manager(manager, monkeypatch, tmp_path_factory):
    """
    Test papermill and pyproject-local-kernel for notebook side vs uv / rye / hatch for project side
    """
    return impl_project_manager(_pyversion(sys.version_info), manager, monkeypatch, tmp_path_factory)


def impl_project_manager(python: str, manager, monkeypatch, tmp_path_factory):
    if shutil.which(manager) is None:
        pytest.skip()

    uv = "uv"
    server_args = f"{_REINSTALL}"
    update = "-U" if python == "3.12" else ""

    monkeypatch.chdir("tests/server-client")

    client_dir = f"client-{manager}"
    with contextlib.ExitStack() as stack:
        stack.enter_context(save_restore_file(Path("server/uv.lock"), tmp_path_factory.mktemp("server")))
        stack.enter_context(save_restore_file(Path(f"{client_dir}/uv.lock"), tmp_path_factory.mktemp("client")))

        with monkeypatch.context() as m:
            m.chdir("server")
            run(f"{uv} python pin -q {python}")
            run(f"{uv} sync -q {server_args} {update}")

        with monkeypatch.context() as m:
            m.chdir(client_dir)
            if manager == "hatch":
                run("hatch env remove")
                run(f"env HATCH_PYTHON={python} hatch env run -- python -c ''")
            else:
                run(f"{uv} python pin -q {python}")
                run(f"{uv} sync -q {update}")

        run(f"cp -v notebook.py {client_dir}")
        run(f"{uv} run --project server jupytext --to ipynb {client_dir}/notebook.py")

        args = f"{uv} run --project server papermill --cwd {client_dir} {client_dir}/notebook.ipynb {client_dir}/notebook_out.ipynb"
        proc = popen_capture(args)
        returncode = proc.returncode

        assert "Traceback" not in proc.stderr
        assert "Failed to start kernel" not in proc.stderr
        assert returncode == 0
