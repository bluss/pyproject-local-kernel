from __future__ import annotations

import asyncio
import enum
import os
from pathlib import Path
import shutil

import pytest
import jupyter_client.kernelspec
from jupyter_client.kernelspec import KernelSpec
from jupyter_client.provisioning import KernelProvisionerFactory as KPF  # type: ignore
from traitlets.config import Config


from pyproject_local_kernel.provisioner import PyprojectKernelProvisioner
from pyproject_local_kernel._identify import KERNEL_SPECS, ProjectKind, get_venv_bin_python


pytestmark = pytest.mark.unit


@pytest.fixture(scope="function", params=KERNEL_SPECS)
def kernel_spec(request: pytest.FixtureRequest) -> KernelSpec:
    return jupyter_client.kernelspec.get_kernel_spec(request.param)


def test_instantiate(kernel_spec: KernelSpec):
    prov = KPF.instance().create_provisioner_instance("id", kernel_spec, parent=None)
    assert isinstance(prov, PyprojectKernelProvisioner)
    assert prov.python_kernel_args
    assert prov.sanity_check
    assert prov.use_venv


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

    config = kernel_spec.metadata['kernel_provisioner']['config']
    prov = PyprojectKernelProvisioner(
        kernel_spec=kernel_spec,
        use_venv=".venv",
        sanity_check=sanity,
        **config,
    )
    cwd = tmp_path

    if scenario:
        scenario_dir = Path("tests/server-client") / scenario
        shutil.copy(scenario_dir / "pyproject.toml", cwd)

    def fail_sanity(*args, **kwargs):
        raise RuntimeError("not sane")

    if sanity:
        monkeypatch.setattr(prov, "_python_environment_sanity_check", fail_sanity)

    kwargs = asyncio.run(prov.pre_launch(cwd=cwd, extra_arguments=["extra"]))
    cmd = kwargs.pop("cmd")
    assert prov.kernel_spec.argv == cmd[:len(prov.kernel_spec.argv)]

    if expected == Expected.Venv:
        assert cmd[0].startswith(str(cwd.absolute() / ".venv"))
    elif expected == Expected.Uv:
        uv_cmd = list(ProjectKind.Uv.python_cmd() or ["x"])
        assert cmd[:len(uv_cmd)] == uv_cmd
    elif expected == Expected.Fallback:
        assert cmd[3] == "--fallback-kernel=not sane"
    elif expected == Expected.NoPyproject:
        assert cmd[3].startswith("--fallback-kernel")
        assert 'no pyproject.toml' in cmd[3]
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


@pytest.mark.parametrize("env,expected", [
    ({"VIRTUAL_ENV": "/jupyterlab/env", "PATH": "/usr/bin", "CUSTOM": "keep"},
     {"PATH": "/usr/bin", "CUSTOM": "keep"}),
    ({"VIRTUAL_ENV": "/jupyterlab/env"}, {}),
    ({"VIRTUAL_ENV": ""}, {}),
    ({"PATH": "/usr/bin", "CUSTOM": "keep"}, {"PATH": "/usr/bin", "CUSTOM": "keep"}),
    ({"VIRTUAL_ENV": "/jupyter lab/env", "PATH": "/usr/bin"}, {"PATH": "/usr/bin"}),
])
def test_pre_launch_env_custom_cmd(tmp_path: Path, env, expected):
    shutil.copy("tests/identify/config_cmd/pyproject.toml", tmp_path / "pyproject.toml")
    spec = KernelSpec(argv=["placeholder"], display_name="t", language="python")
    prov = PyprojectKernelProvisioner(
        kernel_spec=spec, python_kernel_args=["-m", "ipykernel"], sanity_check=False
    )
    launch_env = dict(env)
    kwargs = asyncio.run(prov.pre_launch(cwd=tmp_path, env=launch_env))
    cmd = kwargs.pop("cmd")
    assert cmd == ["my", "cmd", "-m", "ipykernel"]
    assert prov.kernel_spec.argv == cmd
    assert kwargs["env"] == expected
    assert kwargs["env"] is not launch_env
    assert launch_env == env


def test_pre_launch_env_custom_cmd_repeated(tmp_path: Path):
    shutil.copy("tests/identify/config_cmd/pyproject.toml", tmp_path / "pyproject.toml")
    spec = KernelSpec(argv=["placeholder"], display_name="t", language="python")
    prov = PyprojectKernelProvisioner(
        kernel_spec=spec, python_kernel_args=["-m", "ipykernel"], sanity_check=False
    )
    first_env = {"VIRTUAL_ENV": "/jupyterlab/env", "PATH": "/usr/bin"}
    first = asyncio.run(prov.pre_launch(cwd=tmp_path, env=first_env))
    second_env = {"VIRTUAL_ENV": "/other/env", "PATH": "/bin", "CUSTOM": "keep"}
    second = asyncio.run(prov.pre_launch(cwd=tmp_path, env=second_env))
    assert first["env"] == {"PATH": "/usr/bin"}
    assert second["env"] == {"PATH": "/bin", "CUSTOM": "keep"}
    assert first["cmd"] == second["cmd"] == ["my", "cmd", "-m", "ipykernel"]
    assert first_env == {"VIRTUAL_ENV": "/jupyterlab/env", "PATH": "/usr/bin"}
    assert second_env == {"VIRTUAL_ENV": "/other/env", "PATH": "/bin", "CUSTOM": "keep"}


@pytest.mark.parametrize("env", [
    {"VIRTUAL_ENV": "/jupyterlab/env", "PATH": "/usr/bin", "CUSTOM": "keep"},
    {"VIRTUAL_ENV": "/jupyterlab/env", "CUSTOM": "keep"},
    {"PATH": "/usr/bin"},
])
def test_pre_launch_env_use_venv(tmp_path: Path, env):
    shutil.copy("tests/identify/use-venv/pyproject.toml", tmp_path / "pyproject.toml")
    spec = KernelSpec(argv=["placeholder"], display_name="t", language="python")
    prov = PyprojectKernelProvisioner(
        kernel_spec=spec, python_kernel_args=["-m", "ipykernel"], sanity_check=False
    )
    venv_python = tmp_path / get_venv_bin_python(Path(".myvenv"))
    venv_bin = str(venv_python.parent)
    launch_env = dict(env)
    kwargs = asyncio.run(prov.pre_launch(cwd=tmp_path, env=launch_env))
    cmd = kwargs.pop("cmd")
    assert cmd == [str(venv_python), "-m", "ipykernel"]
    assert prov.kernel_spec.argv == cmd
    expected = dict(env)
    path = expected.get("PATH", os.defpath)
    if not path.split(os.pathsep) or path.split(os.pathsep)[0] != venv_bin:
        expected["PATH"] = os.pathsep.join([venv_bin, path])
    assert kwargs["env"] == expected
