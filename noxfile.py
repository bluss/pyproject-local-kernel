import nox


nox.needs_version = ">=2024.3.2"
nox.options.default_venv_backend = "uv"

# Not using nox python parametrization: because it doesn't fetch the
# requested version automatically.

python_versions = [
    "3.8",
    "3.9",
    "3.10",
    "3.11",
    "3.12",
]
python_ids = ["py" + ver.replace(".", "") for ver in python_versions]


@nox.session(reuse_venv=True)
@nox.parametrize("py", python_versions, ids=python_ids)
def tests(session: nox.Session, py: str):
    session.run("uv", "run", "-q", "--with", "pytest", "-p", py, "pytest", "-v")


@nox.session(reuse_venv=True)
@nox.parametrize("py", python_versions, ids=python_ids)
def server_client(session: nox.Session, py: str):
    session.run("bash", "./tests/server-client/setup_run.sh", env=dict(PYVERSION=py))
