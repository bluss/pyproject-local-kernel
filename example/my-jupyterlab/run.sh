#!/bin/sh

## For the sake of the example, how to run jupyterlab here

set -ex

rye run jupyter lab --notebook-dir=..
