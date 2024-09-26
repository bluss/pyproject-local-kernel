import contextlib
from pathlib import Path
import subprocess
import shutil
import sys
import typing as t


def is_relative_to(this: Path, other: Path):
    "Path.is_relative_to polyfill for py 3.8"
    if sys.version_info >= (3, 9):
        return this.is_relative_to(other)
    return other == this or other in this.parents


def run(argv: t.Union[str, t.List[str]], quiet=False, **kwargs) -> subprocess.CompletedProcess:
    """
    run external command and return completed process
    """
    if isinstance(argv, str):
        argv = argv.split()
    if not quiet:
        print(">", " ".join(argv))
    ret = subprocess.run(argv, **kwargs)
    try:
        assert ret.returncode == 0
    except AssertionError:
        if ret.stdout is not None:
            print(ret.stdout)
        if ret.stderr is not None:
            print(ret.stderr)
        raise
    return ret


@contextlib.contextmanager
def save_restore_file(filename: Path, tmp_path: Path, if_exists=True):
    """Save filename, then restore it after the context ends"""
    if filename.exists():
        dest = tmp_path / filename.name
        shutil.copyfile(filename, dest)
        try:
            yield
        finally:
            shutil.copyfile(dest, filename)
    else:
        yield
