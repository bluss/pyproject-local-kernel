import dataclasses
from pathlib import Path
import os
import shutil
import typing

import pytest

from pyproject_local_kernel._identify import ProjectKind, identify
from pyproject_local_kernel._configdata import _type_name, Config
import testlib


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("path,expected", [
    ("tests/identify/rye", ProjectKind.Rye),
    ("tests/identify/poetry", ProjectKind.Poetry),
    ("tests/identify/pdm", ProjectKind.Pdm),
    ("tests/identify/hatch", ProjectKind.Hatch),
    ("tests/identify/uv", ProjectKind.Uv),
    ("tests/identify/invalid_toml", ProjectKind.InvalidData),
    ("tests/identify/unknown", ProjectKind.Unknown),
    ("tests/identify/no_project_section", ProjectKind.InvalidData),
    ("tests/identify/config_no_project_section", ProjectKind.UseVenv),
    ("tests/identify/config_cmd", ProjectKind.CustomConfiguration),
])
def test_ident(path, expected):
    pd = identify(path)
    assert pd.kind == expected
    assert pd.path is not None and pd.path.name == "pyproject.toml"


@pytest.mark.parametrize("path,cmd,sanity", [
    ("tests/identify/config_cmd", ["my", "cmd"], False),
    ("tests/identify/config_cmd_string", ['uv', 'run', '--with', 'custom string', '-BI'], None),
    # uv must be on the path, then we pick this fallback
    ("tests/identify/unknown", ["uv", "run", "--with", "ipykernel", "python"], None),
])
def test_custom_and_sanity(path, cmd, sanity):
    pd = identify(path)
    assert pd.get_python_cmd() == cmd
    assert pd.path is not None and pd.path.name == "pyproject.toml"
    assert pd.config.sanity_check == sanity


@pytest.mark.parametrize("path", [
    "tests/identify/hatch",
])
def test_hatch(path, monkeypatch: pytest.MonkeyPatch):
    if not shutil.which("hatch"):
        pytest.skip("hatch not installed")
    file_dir = Path(__file__).parent
    hatch_config = str(file_dir / "hatch_config.toml")
    monkeypatch.setenv("HATCH_CONFIG", hatch_config)

    venv_dir = Path(path).absolute() / "the_virtualenv"
    pd = identify(path)
    assert pd.path is not None and pd.path.name == "pyproject.toml"

    cmd = pd.get_python_cmd(allow_hatch_workaround=True)
    assert cmd and len(cmd) == 1

    python_path = cmd[0]
    assert isinstance(python_path, Path)
    assert testlib.is_relative_to(python_path, venv_dir)


@pytest.mark.parametrize("path,unix_cmd,win_cmd", [
    ("tests/identify/use-venv", ".myvenv/bin/python", r".myvenv\Scripts\python.exe"),
])
def test_use_venv(path, unix_cmd: str, win_cmd: str):
    # venv resolves to absolute path
    pd = identify(path)
    base_dir = Path(path).absolute()
    expected = base_dir / (win_cmd if is_windows() else unix_cmd)

    pres = pd.resolve()
    assert pres is not None
    assert pres.python_cmd == [expected]
    assert pd.path is not None and pd.path.name == "pyproject.toml"

    mock_path = os.pathsep.join(["use", "venv"])
    environment = {"PATH": mock_path}
    pres.update_environment(environment)
    path_components = environment["PATH"].split(os.pathsep)
    assert path_components == [str(expected.parent), *mock_path.split(os.pathsep)]


def is_windows():
    return os.name == "nt"


@pytest.mark.parametrize("path", [
    "tests/identify/config_cmd_invalid_type1",
    "tests/identify/config_cmd_invalid_type2",
])
def test_custom_error(path, caplog):
    # Test log error
    identify(path)
    assert any("invalid config python-cmd =" in rec.message for rec in caplog.records)


@pytest.mark.parametrize("path", [
    "tests/identify/config_cmd",
])
def test_custom_ignored_key(path, caplog):
    # Test log error
    identify(path)
    assert any("unknown (or duplicate) configuration key 'not-valid'" in rec.message for rec in caplog.records)


def test_no_project(tmp_path: Path):
    pd = identify(tmp_path)
    assert pd.kind == ProjectKind.NoProject
    assert pd.path is None
    assert pd.get_python_cmd() is None


def test_config_type_name():
    self_type_hints = typing.get_type_hints(Config)
    for field in dataclasses.fields(Config):
        assert _type_name(self_type_hints[field.name])

    assert _type_name(typing.Union[typing.List[str], None]) == "list[str] | None"
