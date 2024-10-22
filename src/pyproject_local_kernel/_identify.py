# Copyright 2023-2024 Ulrik Sverdrup "bluss"

"""
Parse/Identify pyproject.toml
"""

from __future__ import annotations

import dataclasses
import enum
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
import typing as t

try:
    import tomllib as tomli  # pyright: ignore[reportMissingImports]
except ImportError:
    import tomli as tomli    # pyright: ignore[reportMissingImports]


from pyproject_local_kernel._configdata import Config


_logger = logging.getLogger(__name__)

MY_TOOL_NAME = "pyproject-local-kernel"  # name of tool section in pyproject.toml for this tool
ENABLE_DEBUG_ENV = "PYPROJECT_LOCAL_KERNEL_DEBUG"
KERNEL_SPEC_NAME = "pyproject_local_kernel"
KERNEL_SPECS = [KERNEL_SPEC_NAME, KERNEL_SPEC_NAME + "_use_venv"]


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

    def python_cmd(self) -> list[str] | None:
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


@dataclasses.dataclass
class ProjectDetection:
    # pyproject.toml file path
    path: Path | None
    kind: ProjectKind
    config: Config = dataclasses.field(default_factory=Config)
    error_context: str | None = None

    def get_python_cmd(self, allow_fallback=True, allow_hatch_workaround=False) -> t.Sequence[Path | str] | None:
        penv = self.resolve(allow_fallback, allow_hatch_workaround)
        return penv and penv.python_cmd

    def resolve(self, allow_fallback=True, allow_hatch_workaround=False) -> PythonEnvironment | None:
        """
        allow_hatch_workaround: call out to `hatch env find`
        """
        # hatch quirk
        use_venv = self.config.use_venv
        if self.kind == ProjectKind.Hatch and allow_hatch_workaround:
            assert self.path is not None
            if hatch_env := get_hatch_venv(self.path):
                use_venv = hatch_env

        # configuration: use-venv
        if use_venv is not None:
            assert self.path is not None
            cmd = [self.path.parent / get_venv_bin_python(Path(use_venv))]
            # virtualenv PATH
            venv_bin_dir = cmd[0].parent
            return PythonEnvironment(cmd, venv_bin_dir)

        # configuration: python-cmd
        python_cmd = self.config.python_cmd
        if python_cmd is not None:
            return PythonEnvironment(python_cmd)

        # project detection
        result = self.kind.python_cmd()

        if result is not None:
            return PythonEnvironment(result)

        if (allow_fallback and
            self.kind not in (ProjectKind.NoProject, ProjectKind.InvalidData)):
            if fallback := self._fallback_project_kind().python_cmd():
                return PythonEnvironment(fallback)
        return None


    @classmethod
    def _fallback_project_kind(cls) -> ProjectKind:
        if shutil.which("uv") is not None:
            return ProjectKind.Uv
        if shutil.which("rye") is not None:
            return ProjectKind.Rye
        return ProjectKind.Unknown


@dataclasses.dataclass
class PythonEnvironment:
    "A project's python environment"
    python_cmd: t.Sequence[str | Path]
    venv_bin_dir: Path | None = None

    def update_environment(self, env: dict[str, t.Any]):
        "Update environment variables in dict env"
        if self.venv_bin_dir is None:
            return
        path_env = env.get("PATH", os.defpath)
        path_entries = path_env.split(os.pathsep)
        if not path_entries or path_entries[0] != self.venv_bin_dir:
            env["PATH"] = os.pathsep.join([str(self.venv_bin_dir), *path_entries])


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


def has_dotkey(data, dotkey):
    return get_dotkey(data, dotkey, None) is not None


def is_rye(data: dict):
    return has_project_table(data) and get_dotkey(data, 'tool.rye.managed', False) is True


def is_poetry(data: dict):
    return bool(get_dotkey(data, 'tool.poetry.name', ""))


def is_pdm(data: dict):
    return has_project_table(data) and get_dotkey(data, 'tool.pdm', None) is not None


def is_hatch(data: dict):
    return has_project_table(data) and (get_dotkey(data, 'tool.hatch.version', None) is not None or
            get_dotkey(data, 'tool.hatch.envs', None) is not None)

def is_uv(data: dict):
    return has_project_table(data) and get_dotkey(data, 'tool.uv', None) is not None


def has_project_table(data: dict):
    # we can't check for just project.version because it can be dynamic
    return has_dotkey(data, "project.name") and (
        has_dotkey(data, "project.version") or
        has_dotkey(data, "project.dynamic"))


IDENTIFY_FUNCTIONS = {
    ProjectKind.Rye: is_rye,
    ProjectKind.Pdm: is_pdm,
    ProjectKind.Poetry: is_poetry,
    ProjectKind.Hatch: is_hatch,
    ProjectKind.Uv: is_uv,
}


def _identify_toml(data) -> t.Tuple[ProjectKind, t.Optional[Config], t.Optional[str]]:
    if not isinstance(data, dict):
        return ProjectKind.InvalidData, None, "Could not read pyproject.toml"
    try:
        config = Config.from_dict(get_dotkey(data, f"tool.{MY_TOOL_NAME}", {}))
    except TypeError as exc:
        error_message = f"Error on reading pyproject.toml: {exc}"
        _logger.warning(error_message)
        return ProjectKind.InvalidData, None, error_message
    if config.python_cmd is not None:
        return ProjectKind.CustomConfiguration, config, None
    if config.use_venv is not None:
        return ProjectKind.UseVenv, config, None
    for kind, func in IDENTIFY_FUNCTIONS.items():
        if func(data):
            return kind, config, None
    if not has_project_table(data):
        return ProjectKind.InvalidData, None, "No valid project table or configuration"
    return ProjectKind.Unknown, config, None


def identify(file):
    pyproj = find_pyproject_file_from(file)
    extra_vars = {}
    if pyproj is None:
        identity = ProjectKind.NoProject
    else:
        try:
            with open(pyproj, "rb") as tf:
                toml_structure = tomli.load(tf)
                identity, config, error_context = _identify_toml(toml_structure)
                if config:
                    extra_vars['config'] = config
                if error_context:
                    extra_vars['error_context'] = error_context
        except (IOError, tomli.TOMLDecodeError) as exc:
            print("Error: ", exc, file=sys.stderr)
            kind = ProjectKind.InvalidData
            return ProjectDetection(pyproj, kind, error_context=str(exc))

    return ProjectDetection(pyproj, identity, **extra_vars)


def get_venv_bin_python(base_venv: Path) -> Path:
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
        proc = subprocess.run(["hatch", "--no-color", "env", "find"],
                              cwd=pyproject_toml.parent,
                              timeout=3, capture_output=True, check=True, encoding="utf-8")
        return proc.stdout.strip()
    except OSError as exc:
        _logger.exception("Error calling hatch: %s", exc)
        return None
