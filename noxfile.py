"""
Nox is the task runner for the project.
Run ./nox -l to list available tasks, extra arguments after -- are passed to the task.
"""

import glob
import os
import sys

import nox

nox.options.default_venv_backend = "none"
nox.options.reuse_venv = True
nox.options.sessions = []

python_versions = [
    "3.8",
    "3.9",
    "3.10",
    "3.11",
    "3.12",
]
python_short = ["py" + p.replace(".", "") for p in python_versions]

def _pytest(session: nox.Session, *args, python=None):
    py_args = ("-p", python) if python is not None else ()
    session.run("uv", "run", "--isolated", *py_args, "pytest", *args, external=True)

@nox.session()
def test(session: nox.Session):
    "Run pytest unit tests. With extra args, run pytest with those args."
    pytest_args = session.posargs
    if not pytest_args:
        _pytest(session, "-m", "unit")
    else:
        _pytest(session, *pytest_args)


@nox.session(tags=["ci-linux", "ci-windows"])
@nox.parametrize("py", python_versions, ids=python_short)
def tests(session: nox.Session, py: str):
    "Run pytest unit tests"
    _pytest(session, "-m", "unit", *session.posargs, python=py)


@nox.session(tags=[])
def jupyter(session: nox.Session):
    "Run pytest integration tests with jupyter kernel"
    _pytest(session, "-s", "-m", "jupyter", *session.posargs)


@nox.session(tags=["ci-linux", "ci-windows"])
def jupyter_all_python(session: nox.Session):
    "Run pytest integration tests with jupyter kernel"
    use_python = python_versions if sys.platform != "win32" else python_versions[-2:]
    pytest_args = ["--use-python", " ".join(use_python)]
    pytest_args += session.posargs
    _pytest(session, "-s", "-m", "jupyter", *pytest_args)


@nox.session(tags=["ci-linux"])
def build(session: nox.Session):
    "Build the package to wheel"
    session.run("uv", "build", external=True)


@nox.session(name="build-test", tags=["ci-linux"])
def build_test(session: nox.Session):
    "Test the built wheel"
    for wheel in glob.glob("dist/pyproject_local_kernel*.whl"):
        session.run("uvx", "--refresh-package", "pyproject-local-kernel", "--with", wheel, "pytest", "-k", "unit")


@nox.session(name="docs-serve")
def docs_serve(session: nox.Session):
    "serve the website locally using mkdocs"
    # spawn to avoid problems with Ctrl-c
    args = "uv run --project ./tools/mkdocs-tool mkdocs serve".split()
    args += session.posargs
    os.execvp(args[0], args)


@nox.session(tags=["check"])
def check(session: nox.Session):
    "lint check; extra args are passed to ruff"
    session.run("uvx", "ruff@0.6.8", "check", "--output-format=concise", *session.posargs)
