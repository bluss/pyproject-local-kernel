[![PyPI - Python Version](https://img.shields.io/pypi/v/pyproject-local-kernel)][pypi]

[pypi]: https://pypi.org/project/pyproject-local-kernel/


# Pyproject Local Jupyter Kernel

- Use per-directory python projects to run Python Jupyter kernels
- Separate dependencies for notebooks in separate projects
- Use Rye, PDM, Poetry, Hatch, or similar project setups to define and run
  IPython kernels with dependencies for Jupyter notebooks.

Instead of installing a myriad of jupyter kernelspecs, one per project, instead
have one "meta" kernel that enables the environment for the project the
notebook file resides in. This approach should be more portable, usable to
anyone who checks out your project structure from git, and easier to use.

Pyproject Local supports the following systems, and reads pyproject.toml to
figure out which kind of project it is:

- Rye
- Poetry
- Hatch
- Pdm
- Custom configuration (for other setups)

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


## User Experience

If the Pyproject Local kernel is used in a project where rye (or the relevant
pyproject manager) is not installed, or the project does not have an ipykernel
in the environment, then starting the kernel fails.

In that case a fallback kernel is started which that shows a message that it is
not setup as expected in this environment. This is a regular ipython kernel which
allows you to run shell commands and hopefully fix the configuration of the project.

It will give you some hints in the Jupyter notebook interface about the next
steps to get it working. Example below is for Rye.

```diff
! Failed to start kernel! The detected project type is: Rye
! Is the virtual environment created, and does it have ipykernel in the project?
!
! Run this:
! !rye add --sync ipykernel
!
! Then restart the kernel to try again.
```

## Configuration

By default python from the local pyproject is run (using rye run, poetry run, etc.).
A custom command can be configured in `pyproject.toml` - the pyproject file closest
to the notebook is used (and no other means of configuration are supported).

The key `tool.pyproject-local-kernel.python-cmd` should be a command that runs
python in the virtual environment you want to use for the project.

```toml
[tool.pyproject-local-kernel]
python-cmd = ["my", "custom", "python"]
```

## Project Status

Status: Working proof of concept, published to PyPI. Additional interest and
maintainer help is welcomed.

See also:

* Rye: https://github.com/mitsuhiko/rye
* https://github.com/goerz/python-localvenv-kernel
* Poetry-kernel: https://github.com/pathbird/poetry-kernel
