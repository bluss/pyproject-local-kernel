from __future__ import annotations

import logging
from pathlib import Path
import os
import subprocess
import time
import typing as t

from jupyter_client import KernelConnectionInfo
from jupyter_client.kernelspec import KernelSpec
from jupyter_client.provisioning.local_provisioner import LocalProvisioner
from traitlets import Bool, List, Unicode

from pyproject_local_kernel import ProjectDetection, ProjectKind, identify, MY_TOOL_NAME, ENABLE_DEBUG_ENV
from pyproject_local_kernel.configdata import Config


_SCRIPT_CHECK_HAS_KERNEL = """import importlib.util; assert importlib.util.find_spec("ipykernel")"""

_MESSAGE_GENERIC = """Could not start project - no pyproject.toml or malformed pyproject.toml?"""

_MESSAGE_NO_PYPROJECT = _MESSAGE_GENERIC

_MESSAGE_NO_IPYKERNEL = """Could not find `ipykernel` in environment
Use `uv add ipykernel` or other command to install ipykernel into the environment."""


class PyprojectKernelProvisioner(LocalProvisioner):
    use_venv: Unicode = Unicode(default_value=None, config=True, allow_none=True)
    python_kernel_args = List[str](config=True, allow_none=False)
    sanity_check = Bool(config=True)

    def _log_info(self, message, *args):
        self.__log(logging.INFO, message, *args)

    def _log_debug(self, message, *args):
        debug_enable = os.environ.get(ENABLE_DEBUG_ENV, "") not in ("0", "")
        level = logging.INFO if debug_enable else logging.DEBUG
        self.__log(level, message, *args)

    def __log(self, level: int, message: str, *args: t.Any):
        logger = t.cast(logging.Logger, self.log)
        logger.log(level, MY_TOOL_NAME + ": " + message, *args)

    async def pre_launch(self, **kwargs) -> t.Dict[str, t.Any]:
        """prepare kernel launch"""
        # can raise an exception here and JupyterLab will show the message
        # in a modal.
        kernel_spec = t.cast(KernelSpec, self.kernel_spec)
        self._log_debug("kernel_id=%r", self.kernel_id)
        self._log_debug("connection_info=%r", self.connection_info)
        self._log_debug("config=%r", self.config)
        self._log_debug("spec=%r", kernel_spec.to_dict())
        cwd = Path(kwargs.get("cwd", Path.cwd()))
        self._log_debug("cwd=%s", cwd)

        spec_config = Config(use_venv=self.use_venv)

        if not self.python_kernel_args:
            raise RuntimeError("pyproject_local_kernel metadata missing from kernelspec")

        find_project = identify(cwd)
        self._log_debug("Found project %s in %s", find_project.kind, find_project.path)
        find_project.config = find_project.config.merge_with(spec_config)
        self._log_debug("pyproject config=%r", find_project.config)

        if find_project.path is None:
            raise RuntimeError(_MESSAGE_NO_PYPROJECT)

        python_cmd = find_project.get_python_cmd(allow_fallback=True, allow_hatch_workaround=True)

        if python_cmd is None:
            if find_project.kind == ProjectKind.InvalidData:
                raise RuntimeError("\n".join([_MESSAGE_GENERIC, f"Reason: {find_project.error_context}"]))
            else:
                raise RuntimeError("No python cmd - unknown project\n" + _MESSAGE_NO_PYPROJECT)

        # convert path to string and update kernel spec argv
        python_cmd = list(map(str, python_cmd))
        kernel_spec.argv[:] = python_cmd + self.python_kernel_args

        if self.sanity_check:
            self._python_environment_sanity_check(find_project, python_cmd, cwd, kwargs)

        self._log_debug("launching kernel from process pid=%d", os.getpid())
        return await super().pre_launch(**kwargs)

    def _python_environment_sanity_check(self, project: ProjectDetection, python_cmd: list[str], cwd: Path, kwargs: dict):
        # skip sanity for uv because it will install ipykernel
        uv_cmd = t.cast(list, ProjectKind.Uv.python_cmd())
        if not project.config.use_venv and python_cmd[:len(uv_cmd)] == uv_cmd:
            return

        st = time.time()
        try:
            sanity_cmd = python_cmd + ["-c", _SCRIPT_CHECK_HAS_KERNEL]
            self._log_debug("Running sanity check: %r", sanity_cmd)
            try:
                subprocess.run(sanity_cmd, check=True, cwd=cwd, env=kwargs.get("env"))
            except (subprocess.CalledProcessError, OSError) as exc:
                self.__log(logging.ERROR, "failed sanity check: %s", exc)
                raise RuntimeError(_MESSAGE_NO_IPYKERNEL)
        finally:
            self._log_debug("used %.3f s on sanity check", (time.time() - st))

    async def send_signal(self, signum: int) -> None:
        self._log_debug("send signal=%r", signum)
        await super().send_signal(signum)

    async def terminate(self, restart: bool = False) -> None:
        self._log_debug("terminate")
        await super().terminate(restart=restart)

    async def cleanup(self, restart: bool = False) -> None:
        self._log_debug("cleanup")
        await super().cleanup(restart=restart)

    async def launch_kernel(self, cmd: t.List[str], **kwargs: t.Any) -> KernelConnectionInfo:
        self._log_info("Launching %r", cmd)
        try:
            return await super().launch_kernel(cmd, **kwargs)
        except OSError as exc:
            raise RuntimeError(f"Could not start kernel: {exc}") from exc
