#!/bin/bash

set -ex

directory=$(dirname "$0")
cd "$directory"

RYE=${RYE:-rye}

SPROJ=server/pyproject.toml
CPROJ=client/pyproject.toml

$RYE sync --pyproject $SPROJ
$RYE sync --pyproject $CPROJ
$RYE run --pyproject $SPROJ jupytext --to ipynb client/notebook.py

# Now execute the notebook
$RYE run --pyproject $SPROJ papermill --cwd client client/notebook.ipynb client/notebook_out.ipynb
