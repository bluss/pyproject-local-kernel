
from pathlib import Path
import sys


def is_relative_to(this: Path, other: Path):
    "Path.is_relative_to polyfill for py 3.8"
    if sys.version_info >= (3, 9):
        return this.is_relative_to(other)
    return other == this or other in this.parents
