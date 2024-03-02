# Pyproject Local Jupyter Kernel

- Use per-directory python projects to run Python Jupyter kernels - separate
  dependencies for every notebook, as needed!

- Use Rye, PDM, Poetry, or similar project setups to define and run IPython
  kernels and dependencies for Jupyter notebooks.

The intention is that instead of installing a myriad of jupyter kernelspecs,
one per project, instead have one "meta" kernel that enables the environment
for the project the notebook file resides in. This approach should be more
portable (usable to anyone who checks out your project structure from git) and
easier to use.

Supports

- Rye
- Poetry
- Hatch
- Pdm
- Custom configurations possible for other projects
- Reads the pyproject.toml file to figure out which kind of project it is.

## Quick Start

1. Install pyproject-local-kernel in your jupyterlab environment and restart
   jupyterlab
2. Create a new directory and notebook, select the **Pyproject Local** kernel
   for the notebook
3. Run (Example for Rye)
  
   * `!rye init --virtual`
   * `!rye add --sync ipykernel`

4. Restart the kernel and you are good to go. Use `!rye add` to add further
   dependencies.

- See the examples directory for how to setup jupyterlab and notebook projects
  separately. JupyterLab and the notebook are installed in separate environments.


## Project Status

Status: Proof of Concept

* Rye: https://github.com/mitsuhiko/rye
* Poetry-kernel: https://github.com/pathbird/poetry-kernel
  See poetry-kernel for more documentation about the per-directory concept.

The name is currently Rye(ish) because it is not officially connected with Rye.

## User Experience

If the Rye kernel is used in a project where rye is not installed, or
the rye project does not have an ipykernel, then starting the kernel fails.

It starts a "fallback" kernel which that shows a message that rye is not setup
as expected in this environment, and provide a regular ipython kernel which
lets you run shell commands to fix rye!

```diff
! Failed to start Rye environment kernel - no ipykernel in rye project?
! Run this:
! !rye add --sync ipykernel
! 
! Then restart the kernel to try again.
```
