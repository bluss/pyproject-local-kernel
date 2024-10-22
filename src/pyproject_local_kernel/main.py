# Copyright 2023-2024 Ulrik Sverdrup "bluss"
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

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path
import signal
import sys
import uuid

from jupyter_client import KernelProvisionerBase  # type: ignore
from jupyter_client.provisioning import KernelProvisionerFactory as KPF  # type: ignore
import jupyter_client.kernelspec

from pyproject_local_kernel._identify import KERNEL_SPECS, MY_TOOL_NAME, ENABLE_DEBUG_ENV
from pyproject_local_kernel._identify import ProjectKind, find_pyproject_file_from, identify


_logger = logging.getLogger(__name__)


def _setup_logging():
    log_level = logging.DEBUG if os.environ.get(ENABLE_DEBUG_ENV, "") not in ("0", "") else logging.INFO
    logging.basicConfig(level=log_level, format=f"{MY_TOOL_NAME} %(levelname)-7s: %(message)s")


async def _async_kernel_start(prov: KernelProvisionerBase, args: argparse.Namespace, extra_args: list[str]):
    kernel_kws = await prov.pre_launch()

    def expand(arg: str):
        "expand variables in argument"
        if '{connection_file}' in arg and args.connection_file:
            arg = arg.format(connection_file=args.connection_file)
        return arg

    cmd = kernel_kws.pop("cmd", None)
    cmd = [expand(arg) for arg in cmd] + extra_args

    kernel_connect_info = await prov.launch_kernel(cmd, **kernel_kws)
    _logger.debug("info=%r", kernel_connect_info)


async def _async_kernel_loop(prov: KernelProvisionerBase, args: argparse.Namespace) -> int:
    async def sigterm():
        _logger.debug("sigterm in async loop")
        await prov.terminate()

    async def sigint():
        _logger.debug("sigint in async loop")
        await prov.send_signal(signal.SIGINT)

    loop = asyncio.get_event_loop()

    try:
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(sigterm()))
    except NotImplementedError:
        pass  # windows

    if args.test_interrupt:
        loop.call_later(3, lambda : asyncio.ensure_future(sigint()))
    if args.test_quit:
        loop.call_later(5, lambda : asyncio.ensure_future(sigterm()))

    ret = await prov.wait()
    return ret if ret is not None else 1


def main() -> int:
    _setup_logging()
    _logger.debug("Started with argv=%s", sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", type=str, dest="connection_file")
    parser.add_argument("--use-venv", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--test-interrupt", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--test-quit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fallback-kernel", default=None, type=str, help=argparse.SUPPRESS)

    args, extra_args = parser.parse_known_args()
    _logger.debug("args=%r rest=%r", args, extra_args)

    if args.fallback_kernel is not None:
        return _start_fallback_kernel(args, failure_to_start_msg=args.fallback_kernel)

    _logger.warning("Unsupported: direct launch of %s - but will attempt to work with this", MY_TOOL_NAME)
    _logger.warning("Must use jupyter-client to launch kernel with kernel provisioning")

    spec_name = KERNEL_SPECS[1] if args.use_venv else KERNEL_SPECS[0]
    try:
        kernel_spec = jupyter_client.kernelspec.get_kernel_spec(spec_name)
    except KeyError:
        _logger.error("Could not find kernel spec %r", spec_name)
        return 1
    prov = KPF.instance().create_provisioner_instance(str(uuid.uuid4()), kernel_spec, parent=None)
    _logger.debug("provisioner=%s", prov)

    asyncio.run(_async_kernel_start(prov, args, extra_args))

    # KeyboardInterrupt will work on windows, signal handler does not
    while True:
        try:
            return asyncio.run(_async_kernel_loop(prov, args))
        except KeyboardInterrupt:
            asyncio.run(prov.send_signal(signal.SIGINT))


def _start_fallback_kernel(args: argparse.Namespace, failure_to_start_msg: str):
    """
    Start a fallback kernel - for the purpose having a good interface for the user
    to fix their environment.
    """
    pyproject_file = find_pyproject_file_from(Path.cwd())

    try:
        project = identify(pyproject_file)
    except Exception:
        project = None

    project_kind = project and project.kind

    help_messages = []

    if failure_to_start_msg:
        help_messages += ["Error: " + failure_to_start_msg]

    python_major_version = ".".join(map(str, sys.version_info[:2]))
    init_messages = [
        "Do you need to create a new project?",
        "",
        "Use a command like one of these to start:",
        "" "!uv init && uv add ipykernel",
        f"!pdm init --python {python_major_version} -n && pdm add ipykernel",
        "!poetry init -n && poetry add ipykernel",
        "",
        "Some project managers work better in a terminal than in a notebook",
        "in that case, set up your project separately.",
    ]

    if pyproject_file is None:
        help_messages += init_messages

    if project_kind is not None:
        help_messages += [f"The detected project type is: {project_kind.name}"]

    help_messages += [""]
    if project_kind == ProjectKind.Rye:
        help_messages += [
            "Run this:",
            "!rye add --sync ipykernel",
        ]
    elif project_kind == ProjectKind.Uv:
        help_messages += [
            "Run this:",
            "!uv add ipykernel",
        ]
    elif project_kind is not None and project_kind.python_cmd() is not None:
        help_messages += [
            "Add ipykernel as a dependency in the project and sync the virtual environment.",
            "",
            "Then restart the kernel to try again.",
        ]

    message_explainer = [
        "",
        f"This is a fallback - {MY_TOOL_NAME} failed to start.",
        "The purpose of the fallback is to let you run shell commands to fix the",
        "environment - when you are done, restart the kernel and try again!",
    ]

    help_messages += message_explainer

    _logger.info("starting fallback kernel")
    for msg in help_messages:
        _logger.info(msg)

    try:
        import ipykernel.ipkernel
        from ipykernel.kernelapp import IPKernelApp
    except ImportError:
        _logger.error("Fallback kernel requires `ipykernel` to be installed")
        return 1

    class FallbackMessageKernel(ipykernel.ipkernel.IPythonKernel):
        def do_execute(self, *args, **kwargs):
            for msg in help_messages:
                print(msg, file=sys.stderr)
            return super().do_execute(*args, **kwargs)

    argv = _ipykernel_argv(args)
    _logger.debug("IPKernelApp launch argv=%r", argv)

    IPKernelApp.launch_instance(argv, kernel_class=FallbackMessageKernel)
    return 0


def _ipykernel_argv(args: argparse.Namespace) -> list[str]:
    argv = []
    if args.connection_file:
        argv += ["-f", args.connection_file]
    return argv
