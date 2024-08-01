# Copyright 2023-2024 Ulrik Sverdrup "bluss"
# Copyright 2021 Pathbird Inc
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from dataclasses import dataclass
import enum
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
import typing as t

try:
    import tomllib as tomli
except ImportError:
    import tomli as tomli


_logger = logging.getLogger(__name__)

MY_TOOL_NAME = "pyproject-local-kernel"  # name of tool section in pyproject.toml for this tool


class ProjectKind(enum.Enum):
    "detected project type"
    CustomConfiguration = enum.auto()
    UseVenv = enum.auto()
    Rye = enum.auto()
    Poetry = enum.auto()
    Pdm = enum.auto()
    Hatch = enum.auto()
    Uv = enum.auto()
    Unknown = enum.auto()
    NoProject = enum.auto()
    InvalidData = enum.auto()

    def python_cmd(self):
        if self == ProjectKind.Rye:
            return ["rye", "run", "python"]
        if self == ProjectKind.Poetry:
            return ['poetry', 'run', 'python']
        if self == ProjectKind.Pdm:
            return ['pdm', 'run', 'python']
        if self == ProjectKind.Hatch:
            return ['hatch', 'run', 'python']
        if self == ProjectKind.Uv:
            return ['uv', 'run', '--with', 'ipykernel', 'python']
        return None


@dataclass
class ProjectDetection:
    # pyproject.toml file path
    path: t.Optional[Path]
    kind: ProjectKind
    python_cmd: t.Optional[t.List[str]] = None
    use_venv: t.Optional[str] = None

    def get_python_cmd(self, allow_fallback=True, allow_hatch_workaround=False):
        """
        allow_hatch_workaround: call out to `hatch env find`
        """
        # hatch quirk
        use_venv = self.use_venv
        if self.kind == ProjectKind.Hatch and allow_hatch_workaround:
            assert self.path is not None
            if hatch_env := get_hatch_venv(self.path):
                use_venv = hatch_env

        # configuration: use-venv
        if use_venv is not None:
            assert self.path is not None
            return [self.path.parent / get_venv_bin_python(Path(use_venv))]

        # configuration: python-cmd
        if self.python_cmd is not None:
            return self.python_cmd

        # project detection
        result = self.kind.python_cmd()

        if (result is None and allow_fallback and
            self.kind not in (ProjectKind.NoProject, ProjectKind.InvalidData)):
            return self._fallback_project_kind().python_cmd()

        return result

    @classmethod
    def _fallback_project_kind(cls) -> ProjectKind:
        if shutil.which("uv") is not None:
            return ProjectKind.Uv
        if shutil.which("rye") is not None:
            return ProjectKind.Rye
        return ProjectKind.Unknown


def find_pyproject_file_from(curdir, basename="pyproject.toml"):
    cwd = Path(curdir).resolve()
    candidate_dirs = [cwd, *cwd.parents]
    for dirs in candidate_dirs:
        pyproject_file = dirs / basename
        if pyproject_file.exists():
            return pyproject_file
    return None


def get_dotkey(data: dict, dotkey, default):
    parts = dotkey.split(".")
    root = data
    for part in parts:
        try:
            root = root[part]
        except KeyError:
            return default
    return root


def is_rye(data: dict):
    return get_dotkey(data, 'tool.rye.managed', False) is True


def is_poetry(data: dict):
    return bool(get_dotkey(data, 'tool.poetry.name', ""))


def is_pdm(data: dict):
    return get_dotkey(data, 'tool.pdm', None) is not None


def is_hatch(data: dict):
    return (get_dotkey(data, 'tool.hatch.version', None) is not None or
            get_dotkey(data, 'tool.hatch.envs', None) is not None)

def is_custom(data: dict):
    python_cmd = get_dotkey(data, f'tool.{MY_TOOL_NAME}.python-cmd', None)
    if isinstance(python_cmd, str):
        python_cmd = [python_cmd]
    if python_cmd is not None and not isinstance(python_cmd, (tuple, list)):
        _logger.error("Is not a list or string: tool.%s.python-cmd=%r", MY_TOOL_NAME, python_cmd)
        python_cmd = None
    return python_cmd is not None, {'python_cmd': python_cmd}


def is_uv(data: dict):
    return get_dotkey(data, 'tool.uv', None) is not None

def is_use_venv(data: dict):
    use_venv = get_dotkey(data, f'tool.{MY_TOOL_NAME}.use-venv', None)
    if use_venv is not None and not isinstance(use_venv, str):
        use_venv = None
    return use_venv is not None, {'use_venv': use_venv}


IDENTIFY_FUNCTIONS = {
    ProjectKind.Rye: is_rye,
    ProjectKind.Pdm: is_pdm,
    ProjectKind.Poetry: is_poetry,
    ProjectKind.Hatch: is_hatch,
    ProjectKind.Uv: is_uv,
}


def _identify_toml(data):
    if not isinstance(data, dict):
        return ProjectKind.InvalidData, {}
    custom, extra_vars = is_custom(data)
    if custom:
        return ProjectKind.CustomConfiguration, extra_vars
    use_venv, extra_vars = is_use_venv(data)
    if use_venv:
        return ProjectKind.UseVenv, extra_vars
    for kind, func in IDENTIFY_FUNCTIONS.items():
        if func(data):
            return kind, {}
    return ProjectKind.Unknown, {}


def identify(file):
    pyproj = find_pyproject_file_from(file)
    extra_vars = {}
    if pyproj is None:
        identity = ProjectKind.NoProject
    else:
        try:
            with open(pyproj, "rb") as tf:
                toml_structure = tomli.load(tf)
                identity, extra_vars = _identify_toml(toml_structure)
        except (IOError, tomli.TOMLDecodeError) as exc:
            print("Error: ", exc, file=sys.stderr)
            kind = ProjectKind.InvalidData
            return ProjectDetection(pyproj, kind)

    return ProjectDetection(pyproj, identity, **extra_vars)


def get_venv_bin_python(base_venv: Path):
    is_windows = os.name == "nt"
    script_dir = "Scripts" if is_windows else "bin"
    extension = ".exe" if is_windows else ""
    return base_venv / script_dir / Path("python").with_suffix(extension)


def get_hatch_venv(pyproject_toml: Path):
    """
    query hatch to get environment location.
    Note that the path doesn't necessarily exist.
    """
    try:
        proc = subprocess.run(["hatch", "env", "find"],
                              cwd=pyproject_toml.parent,
                              timeout=3, capture_output=True, check=True, encoding="utf-8")
        return proc.stdout.strip()
    except OSError as exc:
        _logger.exception("Error calling hatch: %s", exc)
        return None
