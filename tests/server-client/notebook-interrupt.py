# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.6
#   kernelspec:
#     display_name: Pyproject Local
#     language: python
#     name: pyproject_local_kernel
# ---

# %%
import sys

# %%
sys.executable

# %%
sys.version_info

# %%
# let's calculate something slow
acc = 0
for x in range(1000_000_000_000):
    acc += x
print(acc)
