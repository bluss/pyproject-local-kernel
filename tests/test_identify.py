import pathlib
import os
import shutil

import pytest

from pyproject_local_kernel import ProjectKind
from pyproject_local_kernel import identify
import testlib


@pytest.mark.parametrize("path,expected", [
    ("tests/identify/rye", ProjectKind.Rye),
    ("tests/identify/poetry", ProjectKind.Poetry),
    ("tests/identify/pdm", ProjectKind.Pdm),
    ("tests/identify/hatch", ProjectKind.Hatch),
    ("tests/identify/uv", ProjectKind.Uv),
    ("tests/identify/broken", ProjectKind.InvalidData),
    ("tests/identify/unknown", ProjectKind.Unknown),
])
def test_ident(path, expected):
    pd = identify(path)
    assert pd.kind == expected
    assert pd.path is not None and pd.path.name == "pyproject.toml"


@pytest.mark.parametrize("path,cmd", [
    ("tests/identify/custom", ["my", "cmd"]),
    ("tests/identify/custom_string", ['uv', 'run', '--with', 'custom string', '-BI']),
    # uv must be on the path, then we pick this fallback
    ("tests/identify/fallback", ["uv", "run", "--with", "ipykernel", "python"]),
])
def test_custom(path, cmd):
    pd = identify(path)
    assert pd.get_python_cmd() == cmd
    assert pd.path is not None and pd.path.name == "pyproject.toml"


@pytest.mark.parametrize("path", [
    "tests/identify/hatch",
])
def test_hatch(path, monkeypatch: pytest.MonkeyPatch):
    if not shutil.which("hatch"):
        pytest.skip("Skip: hatch not installed")
    file_dir = pathlib.Path(__file__).parent
    hatch_config = str(file_dir / "hatch_config.toml")
    monkeypatch.setenv("HATCH_CONFIG", hatch_config)

    venv_dir = pathlib.Path(path).absolute() / "the_virtualenv"
    pd = identify(path)
    assert pd.path is not None and pd.path.name == "pyproject.toml"

    cmd = pd.get_python_cmd(allow_hatch_workaround=True)
    assert cmd and len(cmd) == 1

    python_path = cmd[0]
    assert isinstance(python_path, pathlib.Path)
    assert testlib.is_relative_to(python_path, venv_dir)


@pytest.mark.parametrize("path,unix_cmd,win_cmd", [
    ("tests/identify/use-venv", ".myvenv/bin/python", r".myvenv\Scripts\python.exe"),
])
def test_use_venv(path, unix_cmd, win_cmd):
    # venv resolves to absolute path
    pd = identify(path)
    base_dir = pathlib.Path(path).absolute()
    expected = base_dir / (win_cmd if is_windows() else unix_cmd)
    assert pd.get_python_cmd() == [pathlib.Path(expected)]
    assert pd.path is not None and pd.path.name == "pyproject.toml"


def is_windows():
    return os.name == "nt"


@pytest.mark.parametrize("path", [
    "tests/identify/custom_broken",
    "tests/identify/custom_broken2",
])
def test_custom_error(path, caplog):
    # Test log error
    identify(path)
    assert any("invalid config python-cmd =" in rec.message for rec in caplog.records)


@pytest.mark.parametrize("path", [
    "tests/identify/custom",
])
def test_custom_ignored_key(path, caplog):
    # Test log error
    identify(path)
    assert any("unknown configuration key 'not-valid'" in rec.message for rec in caplog.records)


def test_no_project(tmp_path):
    pd = identify(tmp_path)
    assert pd.kind == ProjectKind.NoProject
    assert pd.path is None
