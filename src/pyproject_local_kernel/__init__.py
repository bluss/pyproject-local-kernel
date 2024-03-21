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
import sys
from pathlib import Path
import typing

try:
    import tomllib as tomli
except ImportError:
    import tomli as tomli


_logger = logging.getLogger(__name__)

MY_TOOL_NAME = "pyproject-local-kernel"  # name of tool section in pyproject.toml for this tool
DEFAULT_RYE_RUN_CMD = ["rye", "run", "python"]


class ProjectKind(enum.Enum):
    "detected project type"
    CustomConfiguration = enum.auto()
    Rye = enum.auto()
    Poetry = enum.auto()
    Pdm = enum.auto()
    Hatch = enum.auto()
    Unknown = enum.auto()
    NoProject = enum.auto()
    InvalidData = enum.auto()

    def is_known_project(self):
        return self in (self.Rye, self.Poetry, self.Pdm, self.Hatch, self.CustomConfiguration)

    def python_cmd(self):
        if self == ProjectKind.Rye:
            return DEFAULT_RYE_RUN_CMD
        if self == ProjectKind.Poetry:
            return ['poetry', 'run', 'python']
        if self == ProjectKind.Pdm:
            return ['pdm', 'run', 'python']
        if self == ProjectKind.Hatch:
            return ['hatch', 'run', 'python']
        return None


@dataclass
class ProjectDetection:
    path: Path
    kind: ProjectKind
    python_cmd: typing.Optional[typing.List[str]] = None

    def get_python_cmd(self):
        if self.python_cmd is not None:
            return self.python_cmd
        return self.kind.python_cmd() or DEFAULT_RYE_RUN_CMD


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


IDENTIFY_FUNCTIONS = {
    ProjectKind.Rye: is_rye,
    ProjectKind.Pdm: is_pdm,
    ProjectKind.Poetry: is_poetry,
    ProjectKind.Hatch: is_hatch,
}


def _identify_toml(data):
    if not isinstance(data, dict):
        return ProjectKind.InvalidData, {}
    custom, extra_vars = is_custom(data)
    if custom:
        return ProjectKind.CustomConfiguration, extra_vars
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
            return ProjectDetection(file, kind)

    return ProjectDetection(file, identity, **extra_vars)

