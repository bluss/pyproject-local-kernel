#!/bin/sh

## For the sake of the example, how to run jupyterlab here

set -ex

uv run jupyter-lab --notebook-dir=.. "$@"
