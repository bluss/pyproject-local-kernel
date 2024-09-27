import contextlib
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
import shutil
import sys
import threading
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
    assert ret.returncode == 0
    return ret


@dataclass
class Popen:
    stdout: str
    stderr: str
    returncode: int


def popen_capture(args: str, stream_to_stdout=True, popen_kwargs=None):
    """
    Run a subprocess using Popen, stream stdout, stderr to stdout/stderr, but also capture them.
    """
    argv = shlex.split(args)
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", **(popen_kwargs or {}))

    stdout = []
    stderr = []

    def reader(from_file, to, collect_in: list):
        for line in from_file:
            to.write(line)
            collect_in.append(line)


    t1 = threading.Thread(target=reader, args=(proc.stdout, sys.stdout, stdout))
    t2 = threading.Thread(target=reader, args=(proc.stderr, sys.stderr, stderr))

    t1.start()
    t2.start()

    ret = proc.wait()
    t1.join(timeout=1)
    t2.join(timeout=1)

    return Popen(stdout="".join(stdout), stderr="".join(stderr), returncode=ret)


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
