import pathlib
import os

import pytest

from pyproject_local_kernel import ProjectKind
from pyproject_local_kernel import identify


@pytest.mark.parametrize("path,expected", [
    ("tests/identify/rye", ProjectKind.Rye),
    ("tests/identify/poetry", ProjectKind.Poetry),
    ("tests/identify/pdm", ProjectKind.Pdm),
    ("tests/identify/hatch", ProjectKind.Hatch),
    ("tests/identify/broken", ProjectKind.InvalidData),
    ("tests/identify/unknown", ProjectKind.Unknown),
])
def test_ident(path, expected):
    pd = identify(path)
    assert pd.kind == expected
    assert pd.path is not None and pd.path.name == "pyproject.toml"


@pytest.mark.parametrize("path,cmd", [
    ("tests/identify/custom", ["my", "cmd"])
])
def test_custom(path, cmd):
    pd = identify(path)
    assert pd.get_python_cmd() == cmd
    assert pd.path is not None and pd.path.name == "pyproject.toml"


@pytest.mark.parametrize("path,unix_cmd,win_cmd", [
    ("tests/identify/use-venv", ".myvenv/bin/python", r".myvenv\Scripts\python.exe"),
    ("tests/identify/uv", ".venv/bin/python", r".venv\Scripts\python.exe"),
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
])
def test_custom_error(path, caplog):
    # Test log error
    identify(path)
    assert any('Is not a list or string' in rec.message for rec in caplog.records)

def test_no_project(tmp_path):
    pd = identify(tmp_path)
    assert pd.kind == ProjectKind.NoProject
    assert pd.path is None
