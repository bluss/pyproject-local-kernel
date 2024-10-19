from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from pathlib import Path
import shlex
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
    assert ret.returncode == 0
    return ret


@dataclass
class PopenResult:
    stdout: str
    stderr: str
    returncode: int


def popen_capture(args: str, popen_kwargs=None, launch_callback=None, timeout=None) -> PopenResult:
    """
    Run a subprocess using Popen, stream stdout, stderr to stdout/stderr, but also capture them.
    """
    print(">", args)
    async def async_process():
        argv = shlex.split(args)
        proc = await asyncio.create_subprocess_exec(argv[0], *argv[1:],
                                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                    **(popen_kwargs or {}))

        if launch_callback:
            launch_callback(proc)

        return await asyncio.gather(
            asyncio.wait_for(proc.wait(), timeout=timeout),
            _areadlines("stdout", proc.stdout),  # type: ignore
            _areadlines("stderr", proc.stderr),  # type: ignore
        )

    ret, stdout, stderr = asyncio.run(async_process())

    return PopenResult(stdout="".join(stdout), stderr="".join(stderr), returncode=ret)


async def _areadlines(name: str, fp: asyncio.StreamReader) -> list[str]:
    "async read and echo all lines of a file"
    result = []
    while True:
        ret = (await fp.readline()).decode("utf-8", errors="replace")
        if ret == "":
            break
        print(name, ": ", ret, sep="", end="")
        result.append(ret)
    return result


@contextlib.contextmanager
def save_restore_file(filename: Path, tmp_path: Path, if_exists=True):
    """Save filename, then restore it after the context ends"""
    filename = filename.absolute()
    if filename.exists():
        dest = tmp_path / filename.name
        shutil.copyfile(filename, dest)
        try:
            yield
        finally:
            shutil.copyfile(dest, filename)
    else:
        yield
