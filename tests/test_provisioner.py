from __future__ import annotations

import asyncio
import enum
from pathlib import Path
import shutil

import pytest
import jupyter_client.kernelspec
from jupyter_client.kernelspec import KernelSpec
from jupyter_client.provisioning import KernelProvisionerFactory as KPF  # type: ignore
from traitlets.config import Config


from pyproject_local_kernel.provisioner import PyprojectKernelProvisioner
from pyproject_local_kernel import KERNEL_SPECS
from pyproject_local_kernel import ProjectKind


pytestmark = pytest.mark.unit


@pytest.fixture(scope="function", params=KERNEL_SPECS)
def kernel_spec(request: pytest.FixtureRequest) -> KernelSpec:
    return jupyter_client.kernelspec.get_kernel_spec(request.param)


def test_instantiate(kernel_spec: KernelSpec):
    prov = KPF.instance().create_provisioner_instance("id", kernel_spec, parent=None)
    assert isinstance(prov, PyprojectKernelProvisioner)
    assert prov.python_kernel_args
    assert prov.sanity_check


class Expected(enum.Enum):
    Venv = enum.auto()
    Uv = enum.auto()
    Fallback = enum.auto()
    NoPyproject = enum.auto()


KS_REGULAR = KERNEL_SPECS[0]
KS_VENV = KERNEL_SPECS[1]


@pytest.mark.parametrize("scenario,expected,sanity,kernel_spec", [
    ("", Expected.NoPyproject, False, KS_REGULAR),
    ("", Expected.NoPyproject, False, KS_VENV),
    ("client-venv", Expected.Venv, False, KS_REGULAR),
    ("client-venv", Expected.Venv, False, KS_VENV),
    ("client-uv", Expected.Uv, False, KS_REGULAR),
    ("client-uv", Expected.Venv, False, KS_VENV),
    ("client-uv", Expected.Fallback, True, KS_REGULAR),
    ("client-uv", Expected.Fallback, True, KS_VENV),
], indirect=["kernel_spec"])
def test_pre_launch(scenario: str, expected, sanity: bool, kernel_spec: KernelSpec,
                    tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    prov = PyprojectKernelProvisioner(
        use_venv=".venv",
        sanity_check=sanity,
        kernel_spec=kernel_spec,
        python_kernel_args=["command", "-f", "{connection_file}"],
    )
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

    if expected == Expected.Venv:
        assert python_cmd[0].startswith(str(cwd.absolute() / ".venv"))
    elif expected == Expected.Uv:
        uv_cmd = list(ProjectKind.Uv.python_cmd() or ["x"])
        assert python_cmd[:len(uv_cmd)] == uv_cmd
    elif expected == Expected.Fallback:
        assert python_cmd[1] == "--fallback-kernel=not sane"
    elif expected == Expected.NoPyproject:
        assert python_cmd[1].startswith("--fallback-kernel")
        assert 'no pyproject.toml' in python_cmd[1]
    else:
        raise NotImplementedError


def test_venv_config():
    default = ".venv"
    config_value = "foof"
    config_kw = "babbo"

    config = Config()
    config.PyprojectKernelProvisioner.use_venv = config_value

    prov = PyprojectKernelProvisioner()
    assert prov.use_venv == default

    prov = PyprojectKernelProvisioner(use_venv=config_kw)
    assert prov.use_venv == config_kw

    prov = PyprojectKernelProvisioner(config=config, use_venv=config_kw)
    assert prov.use_venv == config_kw

    prov = PyprojectKernelProvisioner(config=config)
    assert prov.use_venv == config_value
