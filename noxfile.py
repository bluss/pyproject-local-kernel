"""
Nox is the task runner for the project.
"""

import glob
import os

import nox

nox.options.default_venv_backend = "none"
nox.options.reuse_venv = True

python_versions = [
    "3.8",
    "3.9",
    "3.10",
    "3.11",
    "3.12",
]
python_short = ["py" + p.replace(".", "") for p in python_versions]


@nox.session()
def test(session: nox.Session):
    "Run pytest unit tests"
    tests(session, py=python_versions[-1])


@nox.session()
@nox.parametrize("py", python_versions, ids=python_short)
def tests(session: nox.Session, py: str):
    "Run pytest unit tests"
    pytest_args = session.posargs
    session.run("uv", "run", "--isolated", "-p", py, "pytest", "-k", "identify", *pytest_args, external=True)


@nox.session(tags=["jupyter"])
@nox.parametrize("py", python_versions, ids=python_short)
def jupyter(session: nox.Session, py):
    "Run pytest integration tests with jupyter kernel"
    pytest_args = session.posargs
    session.run("uv", "run", "--isolated", "-p", py, "pytest", "-s", "-k", "jupyter", *pytest_args, external=True)


@nox.session()
def build(session: nox.Session):
    "Build the package to wheel"
    session.run("uv", "build", external=True)


@nox.session(name="build-test")
def build_test(session: nox.Session):
    "Test the built wheel"
    for wheel in glob.glob("dist/pyproject_local_kernel*.whl"):
        session.run("uvx", "--refresh-package", "pyproject-local-kernel", "--with", wheel, "pytest", "-k", "identify")


@nox.session(name="docs-serve", default=False)
def docs_serve(session: nox.Session):
    "serve the website locally using mkdocs"
    # spawn to avoid problems with Ctrl-c
    args = "uv run --project ./tools/mkdocs-tool mkdocs serve".split()
    args += session.posargs
    os.execvp(args[0], args)
