# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.3
#   kernelspec:
#     display_name: Pyproject Local
#     language: python
#     name: pyproject_local_kernel
# ---

# %% [markdown]
# This is a notebook using the Pyproject Local kernel.
#
# That means - it looks at the closest pyproject.toml and runs the python kernel in the environment defined by the project.
#
# In this example, it's using uv through `uv run`, so it should sync the required dependencies
# automatically on first run of the notebook.

# %%
import sys
sys.executable, sys.version_info

# %%
import numpy as np
np.__version__

# %% [markdown]
# If you use other project managers such as for example rye you might need to run `rye sync` or similar to sync
# the notebook before starting. This can be run directly in the notebook, and *then* you restart the kernel in the jupyterlab interface.

# %% [raw]
# !rye sync
