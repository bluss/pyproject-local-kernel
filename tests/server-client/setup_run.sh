#!/bin/bash

set -ex

directory=$(dirname "$0")
cd "$directory"

RYE=${RYE:-rye}

SPROJ=server/pyproject.toml
CPROJ=client/pyproject.toml

# use uv as a workaround for relative paths on windows

if [ -n "$IS_WINDOWS" ]; then
    UV=$HOME/.rye/uv/*/uv
    (cd server; $UV venv; $UV pip install -r pyproject.toml)
    (cd client; $UV venv; $UV pip install -r pyproject.toml)
else
    $RYE sync --pyproject $SPROJ
    $RYE sync --pyproject $CPROJ
fi
$RYE run --pyproject $SPROJ jupytext --to ipynb client/notebook.py

# Now execute the notebook
$RYE run --pyproject $SPROJ papermill --cwd client client/notebook.ipynb client/notebook_out.ipynb
