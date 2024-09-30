"""
Forward signals to the kernel process.

We fit into a hierarchy of processes like this:

- JupyterLab
- Uses `jupyter-client`
  - Starts `pyproject_local_kernel`
  - Uses `jupyter-client`
    - Starts project kernel `uv run python -m ipykernel_launcher ...`
      - Starts `ipykernel`

`jupyter-client` to child interrupts use SIGINT on posix platforms. On windows it uses an interrupt event handle by some other mechanism that
`jupyter-client` and `ipykernel` agree upon. When the kernel is launched, the launcher sets the environment variable `JPY_INTERRUPT_EVENT` for the
child with an integer handle for the interrupt event.

We handle one interrupt channel from jupyterlab to us and one from us to the `ipykernel`.
"""

import logging
import os
import queue
import signal
import subprocess
import sys


from pyproject_local_kernel.jpy_vars import JpyVars
from pyproject_local_kernel.parentpoller import ParentPollerWindows

_logger = logging.getLogger(__name__)


def is_windows():
    return sys.platform == "win32"


class ForwardKernelSignals:
    def __init__(self, jpy_vars: JpyVars):
        "Setup - before process is launched"
        self.process = None
        self.process_group_id: int = 0
        self.started = False
        self.queue: "queue.Queue[int]" = queue.Queue()
        self.poller = None

        if is_windows():
            self.interrupt_handle = jpy_vars.interrupt_event
        else:
            self.interrupt_handle = 0
        if is_windows():
            forward_signals = set(signal.Signals) - {signal.CTRL_BREAK_EVENT, signal.CTRL_C_EVENT, signal.SIGTERM}
        else:
            forward_signals = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP, signal.SIGCHLD}

        for sig in forward_signals:
            signal.signal(sig, self.handle_signal)

    def handle_signal(self, sig: int, _frame=None, from_queue=False):
        "Signal callback"
        if not self.started and not from_queue:
            _logger.debug("Kernel process not yet started, queue signal: %s", sig)
            self.queue.put_nowait(sig)
        elif self.process is not None:
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
                _logger.debug("fallback to process.send_signal(%d)", sig)
                self.process.send_signal(sig)
            except ProcessLookupError as exc:
                # process is already dead
                _logger.error("Error when forwarding signal %r: %s", sig, exc)
        else:
            _logger.error("No process!")

    def _windows_interrupt_callback(self):
        # will be called on the poller thread, but that should be ok
        self.handle_signal(int(signal.SIGINT))

    def process_exists(self, proc: subprocess.Popen):
        "Call when process exists (has started) but not marked as started yet"
        self.process = proc
        if hasattr(os, "getpgid"):
            try:
                self.process_group_id = os.getpgid(proc.pid)
            except ProcessLookupError as exc:
                _logger.error("Error on getting process group id: %s", exc)
                self.process_group_id = 0

        if self.interrupt_handle and is_windows():
            self.poller = ParentPollerWindows(self.interrupt_handle,
                                              interrupt_callback=self._windows_interrupt_callback)
            self.poller.start()
            _logger.debug("Started %s", type(self.poller).__name__)

    def process_started(self, proc: subprocess.Popen):
        "Called when process is considered to be properly started"
        if proc is not self.process:
            raise ValueError("Wrong process value or process_exists not called")

        while not self.queue.empty():
            _logger.debug("Processing signal from queue")
            self.handle_signal(self.queue.get(timeout=0.1), from_queue=True)

        _logger.debug("marking kernel process as started")
        self.started = True
