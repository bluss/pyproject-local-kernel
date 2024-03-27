# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
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
# You'll need to sync the project (download dependencies) before
# it can execute properly.  
# In this example, it's using rye, so you'd run rye sync and restart the kernel if needed.

# %%
# !rye sync

# %%
import sys
sys.executable, sys.version_info

# %%
import numpy as np
np.__version__

# %%
