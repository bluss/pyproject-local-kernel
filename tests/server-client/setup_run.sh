#!/bin/bash

set -ex

directory=$(dirname "$0")
cd "$directory"

RYE=${RYE:-rye}

SPROJ=server/pyproject.toml
CPROJ=client-rye/pyproject.toml

$RYE sync --pyproject $SPROJ
$RYE sync --pyproject $CPROJ
(cd client-uv; uv sync)

for nbdir in client-rye client-uv ; do
    # convert to ipynb
    cp -v ./notebook.py $nbdir/
    $RYE run --pyproject $SPROJ jupytext --to ipynb $nbdir/notebook.py
    # execute the notebook
    $RYE run --pyproject $SPROJ papermill --cwd $nbdir $nbdir/notebook.ipynb $nbdir/notebook_out.ipynb
done

