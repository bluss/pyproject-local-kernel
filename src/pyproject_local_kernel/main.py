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
import signal
import sys
import uuid

from jupyter_client import KernelProvisionerBase  # type: ignore
from jupyter_client.provisioning.factory import KernelProvisionerFactory
import jupyter_client.kernelspec

from pyproject_local_kernel import MY_TOOL_NAME, ENABLE_DEBUG_ENV


_logger = logging.getLogger(__name__)


def _setup_logging():
    log_level = logging.DEBUG if os.environ.get(ENABLE_DEBUG_ENV, "") not in ("0", "") else logging.INFO
    logging.basicConfig(level=log_level, format=f"{MY_TOOL_NAME} %(levelname)-7s: %(message)s")


async def async_kernel_start(prov: KernelProvisionerBase, args: argparse.Namespace, extra_args: list[str]):
    await prov.pre_launch()

    def expand(arg: str):
        "expand variables in argument"
        if '{connection_file}' in arg and args.connection_file:
            arg = arg.format(connection_file=args.connection_file)
        return arg

    cmd = [expand(arg) for arg in prov.kernel_spec.argv] + extra_args

    kernel_connect_info = await prov.launch_kernel(cmd)
    _logger.debug("info=%r", kernel_connect_info)


async def async_kernel_loop(prov: KernelProvisionerBase, args: argparse.Namespace) -> int:
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
    _logger.warning("Unsupported: direct launch of %s - but will attempt to work with this", MY_TOOL_NAME)
    _logger.warning("Must use jupyter-client to launch kernel with kernel provisioning")

    parser = argparse.ArgumentParser()
    parser.add_argument("--use-venv", action="store_true")
    parser.add_argument("-f", type=str, dest="connection_file")
    parser.add_argument("--test-interrupt", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--test-quit", action="store_true", help=argparse.SUPPRESS)

    args, extra_args = parser.parse_known_args()
    _logger.debug("args=%r rest=%r", args, extra_args)
    kernel_spec_name = "pyproject_local_kernel" if not args.use_venv else "pyproject_local_kernel_use_venv"

    try:
        kernel_spec = jupyter_client.kernelspec.get_kernel_spec(kernel_spec_name)
    except KeyError:
        _logger.error("Could not find kernel spec %r", kernel_spec_name)
        return 1
    prov = KernelProvisionerFactory().create_provisioner_instance(str(uuid.uuid4()), kernel_spec, parent=None)
    _logger.debug("provisioner=%s", prov)

    asyncio.run(async_kernel_start(prov, args, extra_args))

    # KeyboardInterrupt will work on windows, signal handler does not
    while True:
        try:
            return asyncio.run(async_kernel_loop(prov, args))
        except KeyboardInterrupt:
            asyncio.run(prov.send_signal(signal.SIGINT))
