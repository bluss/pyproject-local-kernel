"""
Forward signals to the kernel process.

We fit into a hierarchy of processes like this:

- JupyterLab
- Uses `jupyter-client`
  - Starts `pyproject_local_kernel`
  - Uses `jupyter-client`
    - Starts project kernel `uv run python -m ipykernel_launcher ...`
      - Starts `ipykernel`

`jupyter-client` to child interrupts use SIGINT on posix platforms. On windows it uses
an interrupt event handle by some other mechanism that `jupyter-client` and `ipykernel`
agree on. When the kernel is launched, the launcher sets the environment variable
`JPY_INTERRUPT_EVENT` for the child with an integer handle for the interrupt event.

We handle one interrupt channel from jupyterlab to us and one from us to the
`ipykernel`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import time

import jupyter_client


from pyproject_local_kernel.jpy_vars import JpyVars
from pyproject_local_kernel.parentpoller import ParentPollerUnix, ParentPollerWindows

_logger = logging.getLogger(__name__)


def is_windows():
    return sys.platform == "win32"


class SignalQueue:
    """
    Signal callback registrar, batches callbacks in a queue before the process has started
    """
    def __init__(self, signal_callback):
        self.started = False
        self.queue: queue.Queue[int] = queue.Queue()
        self.signal_callback = signal_callback

        if is_windows():
            forward_signals = set(signal.Signals) - {signal.CTRL_BREAK_EVENT, signal.CTRL_C_EVENT, signal.SIGTERM}
        else:
            forward_signals = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP, signal.SIGCHLD}

        for sig in forward_signals:
            signal.signal(sig, self._signal_callback)

    def start(self):
        while not self.queue.empty():
            _logger.debug("Processing signal from queue")
            self._signal_callback(self.queue.get(timeout=0.1), from_queue=True)
        self.started = True


    def _signal_callback(self, sig: int, frame=None, from_queue=False):
        if self.started or from_queue:
            self.signal_callback(sig)
        else:
            _logger.debug("Kernel process not yet started, queue signal: %s", sig)
            self.queue.put_nowait(sig)


class KernelLifecycleHandler:
    @classmethod
    def run(cls, kernel_cmd: list[str | Path]) -> int:
        """
        Run the kernel, block until it has finished.

        kernel_cmd should be a commandline that runs ipykernel_launcher.

        Return exit code.
        Raises exceptions from problems with kernel starting: OSError or other exceptions.
        """
        # read jupyter-client variables from upstream launcher
        # set up the signal handler
        kernel_handler = cls(JpyVars())
        # launch the kernel
        return kernel_handler.run_kernel(kernel_cmd)

    def __init__(self, jpy_vars: JpyVars):
        self.process = None
        self.process_group_id: int = 0
        self.poller = None

        self.parent_handle = jpy_vars.parent_pid
        if is_windows():
            self.interrupt_handle = jpy_vars.interrupt_event
        else:
            self.interrupt_handle = 0

        self.signal_queue = SignalQueue(self._signal_callback)

    def run_kernel(self, kernel_cmd: list[str | Path]) -> int:
        _logger.info("Starting kernel: %r", kernel_cmd)
        proc = jupyter_client.launch_kernel(kernel_cmd, independent=False)  # type: ignore
        _logger.debug("Kernel started with pid=%s.", proc.pid)

        # give the process some time to start. We are just a guardian/parent process now,
        # and the kernel loses no time here.
        self.process_setup(proc)
        time.sleep(0.5)
        self.process_started(proc)

        exit_code = proc.wait()
        if exit_code != 0:
            _logger.error("kernel exited with error code: %r", exit_code)
        return exit_code

    def process_setup(self, proc: subprocess.Popen):
        "Call when process exists (has started) but not marked as started yet"
        self.process = proc
        if hasattr(os, "getpgid") and not is_windows():
            try:
                self.process_group_id = os.getpgid(proc.pid)
            except (ProcessLookupError, OSError) as exc:
                _logger.error("Error on getting process group id: %s", exc)
                self.process_group_id = 0

        if self.interrupt_handle and is_windows():
            self.poller = ParentPollerWindows(self.interrupt_handle,
                                              self.parent_handle,
                                              interrupt_callback=self._windows_interrupt_callback,
                                              parent_callback=self._parent_exited_callback)
            self.poller.start()
        elif self.parent_handle:
            self.poller = ParentPollerUnix(self.parent_handle, parent_callback=self._parent_exited_callback)
            self.poller.start()
        if self.poller is not None:
            _logger.debug("Started %s", type(self.poller).__name__)

    def process_started(self, proc: subprocess.Popen):
        "Called when process is considered to be properly started"
        if proc is not self.process:
            raise ValueError("Wrong process value or process_setup not called")

        self.signal_queue.start()
        _logger.debug("marking kernel process as started")

    def _signal_callback(self, sig: int):
        if self.process is None:
            _logger.error("received signal - have no process")
            return

        _logger.debug("Forwarding signal to kernel: %r", sig)
        try:
            if sig == signal.SIGINT and is_windows():
                from jupyter_client.win_interrupt import send_interrupt

                _logger.debug("win32 send interrupt event")
                # win32_interrupt_event set by launcher_kernel
                send_interrupt(self.process.win32_interrupt_event)  # type: ignore
                return
            if self.process_group_id:
                _logger.debug("posix killpg(%r, %r)", self.process_group_id, sig)
                os.killpg(self.process_group_id, sig)
                return
            _logger.debug("process.send_signal(%d)", sig)
            self.process.send_signal(sig)
        except ProcessLookupError as exc:
            # process is already dead
            _logger.error("Error when forwarding signal %r: %s", sig, exc)

    def _parent_exited_callback(self):
        if self.process is not None:
            # windows doesn't support SIGTERM, but subprocess send_signal handles the necessary 
            # difference for us.
            self._signal_callback(int(signal.SIGTERM))
            self.process = None
        self._fast_exit()

    def _fast_exit(self):
        for handler in _logger.handlers:
            handler.flush()
        os._exit(1)

    def _windows_interrupt_callback(self):
        # will be called on the poller thread, but that should be ok
        self._signal_callback(int(signal.SIGINT))
