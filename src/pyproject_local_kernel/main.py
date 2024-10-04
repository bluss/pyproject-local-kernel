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


import logging
from pathlib import Path
import os
import sys

from jupyter_client.provisioning.factory import KernelProvisionerFactory
import jupyter_client.kernelspec

from pyproject_local_kernel import MY_TOOL_NAME, ProjectKind, ENABLE_DEBUG_ENV
from pyproject_local_kernel import identify, find_pyproject_file_from
from pyproject_local_kernel.signal import KernelLifecycleHandler


_logger = logging.getLogger(__name__)


def _setup_logging():
    log_level = logging.DEBUG if os.environ.get(ENABLE_DEBUG_ENV, "") not in ("0", "") else logging.INFO
    logging.basicConfig(level=log_level, format=f"{MY_TOOL_NAME}: %(message)s")


async def async_main(prov) -> int:
    while True:
        try:
            ret = await prov.wait()
            return ret
        except KeyboardInterrupt:
            import signal
            await prov.send_signal(signal.SIGINT)


def main() -> int:
    _setup_logging()

    _logger.info("argv: %s", sys.argv)
    _logger.error("Unsupported: must use jupyter-client")

    raise SystemExit(1)
