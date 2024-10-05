from __future__ import annotations

import asyncio
import enum
from pathlib import Path
import shutil

import pytest
import jupyter_client.kernelspec

from pyproject_local_kernel.provisioner import PyprojectKernelProvisioner
from pyproject_local_kernel import KERNEL_SPEC_NAME
from pyproject_local_kernel import ProjectKind


pytestmark = pytest.mark.unit


class Expected(enum.Enum):
    Venv = enum.auto()
    Uv = enum.auto()
    Fallback = enum.auto()
    NoPyproject = enum.auto()


@pytest.mark.parametrize("scenario,python_case,use_venv,sanity", [
    ("", Expected.NoPyproject, None, False),
    ("client-venv", Expected.Venv, None, False),
    ("client-venv", Expected.Fallback, None, True),
    ("client-uv", Expected.Uv, None, False),
    ("client-uv", Expected.Fallback, None, True),
    ("client-uv", Expected.Venv, ".venv", False),
])
def test_prov(scenario: str, python_case, use_venv: bool | None, sanity: bool,
              tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    prov = PyprojectKernelProvisioner()
    prov.use_venv = use_venv
    prov.python_kernel_args = ["command", "-f", "{connection_file}"]
    prov.sanity_check = sanity

    kernel_spec = jupyter_client.kernelspec.get_kernel_spec(KERNEL_SPEC_NAME)
    prov.kernel_spec = kernel_spec

    cwd = tmp_path
    if scenario:
        scenario_dir = Path("tests/server-client") / scenario
        shutil.copy(scenario_dir / "pyproject.toml", cwd)

    def fail_sanity(*args, **kwargs):
        raise RuntimeError("not sane")

    if sanity:
        monkeypatch.setattr(prov, "_python_environment_sanity_check", fail_sanity)

    asyncio.run(prov.pre_launch(cwd=cwd))

    python_cmd = list(prov.kernel_spec.argv)

    if python_case == Expected.Venv:
        assert python_cmd[0].startswith(str(cwd.absolute() / ".venv"))
    elif python_case == Expected.Uv:
        uv_cmd = list(ProjectKind.Uv.python_cmd() or ["x"])
        assert python_cmd[:len(uv_cmd)] == uv_cmd
    elif python_case == Expected.Fallback:
        assert python_cmd[1] == "--fallback-kernel=not sane"
    elif python_case == Expected.NoPyproject:
        assert python_cmd[1].startswith("--fallback-kernel")
        assert 'no pyproject.toml' in python_cmd[1]
    else:
        raise NotImplementedError
