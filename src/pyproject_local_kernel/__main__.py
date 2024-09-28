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
import platform
import signal
import subprocess
import sys

from pyproject_local_kernel import MY_TOOL_NAME, ProjectKind
from pyproject_local_kernel import identify, find_pyproject_file_from


_logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, format=f"{MY_TOOL_NAME}: %(message)s")

    find_project = identify(Path.cwd())
    python_cmd = list(find_project.get_python_cmd(allow_fallback=True, allow_hatch_workaround=True))

    launched = False
    failure_to_start_msg = ""

    if python_cmd is not None:
        cmd = python_cmd + [
            "-m", "ipykernel_launcher",
            *sys.argv[1:],
        ]

        _logger.info("Starting kernel: %r", cmd)
        try:
            proc = subprocess.Popen(cmd)

            if platform.system() == 'Windows':
                forward_signals = set(signal.Signals) - {signal.CTRL_BREAK_EVENT, signal.CTRL_C_EVENT, signal.SIGTERM}
            else:
                forward_signals = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP, signal.SIGCHLD}

            def handle_signal(sig, _frame):
                _logger.debug("Forwarding signal to kernel: %r", sig)
                try:
                    proc.send_signal(sig)
                except ProcessLookupError as exc:
                    # process is already dead
                    _logger.error("Error when forwarding signal %r: %s", sig, exc)

            for sig in forward_signals:
                signal.signal(sig, handle_signal)

            exit_code = proc.wait()
            if exit_code != 0:
                _logger.error("kernel exited with error code: %r", exit_code)
            else:
                launched = True
        except (IOError, OSError) as exc:
            failure_to_start_msg = str(exc)
            _logger.error("kernel could not be started: %s", failure_to_start_msg)
        except Exception as exc:
            failure_to_start_msg = str(exc)
            _logger.exception("kernel could not be started: %s", failure_to_start_msg)
    if not launched:
        start_fallback_kernel(find_project.kind, failure_to_start_msg)


def start_fallback_kernel(project_kind: ProjectKind, failure_to_start_msg: str = ""):
    """
    Start a fallback kernel. Its purpose is

    1. Show a message that rye is not setup as expected in this environment
    2. Provide a regular ipython kernel which lets you run shell commands to fix rye!
    """
    has_pyproject = find_pyproject_file_from(Path.cwd()) is not None

    help_messages = []

    rye_init_messages = [
        "No pyproject.toml found - do you need to create a new project?",
        "",
        "Use a command such as one of these to start:",
        "!rye init --virtual",
        "!uv init",
        "!pdm init",
        "!poetry new .",
        "!hatch new",
        "",
    ]

    if not has_pyproject:
        help_messages += rye_init_messages

    if failure_to_start_msg:
        help_messages += ["Error: " + failure_to_start_msg]


    sync_kernel_env_messages = [
        f"Failed to start kernel! The detected project type is: {project_kind.name}",
        "Is the virtual environment created, and does it have ipykernel in the project?",
        "",
    ]

    if project_kind == ProjectKind.Rye:
        sync_kernel_env_messages += [
            "Run this:",
            "!rye add --sync ipykernel",
            "",
            "Then restart the kernel to try again.",
        ]
    elif project_kind == ProjectKind.Uv:
        sync_kernel_env_messages += [
            "Run this:",
            "!uv add ipykernel",
            "",
            "Then restart the kernel to try again.",
        ]
    else:
        sync_kernel_env_messages += [
            "Add ipykernel as a dependency in the project and sync the virtualenv."
            "",
            "Then restart the kernel to try again.",
        ]

    help_messages += sync_kernel_env_messages

    _logger.info("starting fallback kernel")
    for msg in help_messages:
        _logger.info(msg)

    import ipykernel.kernelapp
    import ipykernel.ipkernel
    from ipykernel.kernelapp import IPKernelApp

    class FallbackMessageKernel(ipykernel.ipkernel.IPythonKernel):
        def do_execute(self, *args, **kwargs):
            for msg in help_messages:
                print(msg, file=sys.stderr)
            return super().do_execute(*args, **kwargs)

    IPKernelApp.launch_instance(kernel_class=FallbackMessageKernel)


if __name__ == "__main__":
    main()
