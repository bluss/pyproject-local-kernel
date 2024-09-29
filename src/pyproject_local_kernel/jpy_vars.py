from dataclasses import dataclass, field
import logging
import sys
import os


_logger = logging.getLogger(__name__)


@dataclass
class JpyVars:
    """
    Variables set by jupyter-client when launching kernel
    JPY_PARENT_PID: process id of parent process
    JPY_INTERRUPT_EVENT: interrupt event handle (windows only)
    """

    parent_pid: int = field(init=False)
    interrupt_event: int = field(init=False)

    def __post_init__(self):
        def int_parse_from_text(text):
            if text:
                try:
                    value = int(text)
                    if value > 0:
                        return value
                except ValueError:
                    pass
            return 0

        def int_from_env(name):
            "read integer from environment variable and validate > 0"
            text = os.environ.get(name)
            result = int_parse_from_text(text)
            _logger.debug("Read %s=%r, result=%r", name, text, result)
            return result

        self.parent_pid = int_from_env("JPY_PARENT_PID")
        self.interrupt_event = int_from_env("JPY_INTERRUPT_EVENT") if sys.platform == "win32" else 0
