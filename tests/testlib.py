from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
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


def popen_capture(args: str, popen_kwargs=None) -> PopenResult:
    """
    Run a subprocess using Popen, stream stdout, stderr to stdout/stderr, but also capture them.
    """
    argv = shlex.split(args)
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", **(popen_kwargs or {}))

    ret, stdout, stderr = asyncio.run(_read_process_outputs(proc))

    return PopenResult(stdout="".join(stdout), stderr="".join(stderr), returncode=ret)


async def _read_process_outputs(proc: subprocess.Popen[str]) -> t.Tuple[int, list[str], list[str]]:
    loop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=3) as thread_pool:
        return await asyncio.gather(
            # wait for process end, stdout and stderr
            loop.run_in_executor(thread_pool, proc.wait),
            _areadlines(thread_pool, "stdout", proc.stdout),  # type: ignore
            _areadlines(thread_pool, "stderr", proc.stderr),  # type: ignore
        )


async def _areadlines(thread_pool: ThreadPoolExecutor, name: str, f: t.IO[str]) -> list[str]:
    "async read and echo all lines of a file"
    loop = asyncio.get_running_loop()
    result = []
    while True:
        # readline is blocking, so run it in the pool
        ret = await loop.run_in_executor(thread_pool, f.readline)
        if ret == "":
            break
        print(name, ": ", ret, sep="", end="")
        result.append(ret)
    return result


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
