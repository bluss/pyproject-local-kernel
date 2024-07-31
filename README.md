[Website][] - [PyPI][] [![PyPI - Python Version](https://img.shields.io/pypi/v/pyproject-local-kernel)][PyPi]
{ .doc_hidden }

[Website]: https://bluss.github.io/pyproject-local-kernel/
[PyPi]: https://pypi.org/project/pyproject-local-kernel/


# Pyproject Local Jupyter Kernel

- Use per-directory python projects to run Python Jupyter kernels
- Separate dependencies for notebooks in separate projects
- Use Rye, Uv, PDM, Poetry, Hatch, or similar project/environment managers to
  define and run IPython kernels with dependencies for Jupyter notebooks.

Instead of installing a myriad of jupyter kernelspecs, one per project, instead
have one "meta" kernel that enables the environment for the project the
notebook file resides in. This approach should be more portable, usable to
anyone who checks out your project structure from git, and easier to use.

Pyproject Local supports the following systems, and reads pyproject.toml to
figure out which kind of project it is:

- Rye
- Uv
- Poetry
- Hatch
- Pdm
- Custom command (for other setups)
- Use venv at path (for other setups)

## Quick Start (JupyterLab)

1. Install pyproject-local-kernel in your jupyterlab environment and restart
   jupyterlab
2. Create a new directory and notebook
3. Select the **Pyproject Local** kernel for the notebook
4. Run these to setup the new project:

  (Example for Rye)

   * `!rye init --virtual`
   * `!rye add --sync ipykernel`

  (Example for Uv)

   * `!uv init`
   * `!uv add "ipykernel>=6"`

5. Restart the kernel and you are good to go. Use more `add` commands to add
   further dependencies.

- See the examples directory for how to setup jupyterlab and notebook projects
  separately. JupyterLab and the notebook are installed in separate environments.


Do you want to use pyproject-local-kernel in other environments, like
**VSCodium or VS Code**, or maybe using Pipenv? See our [FAQ][] for more
information.

[FAQ]: FAQ.md

## User Experience

If the Pyproject Local kernel is used in a project where Rye (or the relevant
project manager) is not installed, or the project does not have an ipykernel
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

Only one of the custom command and virtualenv path configurations can be used
at a time.

### Virtualenv Path

The key `tool.pyproject-local-kernel.use-venv` can be a path to a virtualenv,
relative to the pyproject.toml file, which should be used.

```toml
[tool.pyproject-local-kernel]
use-venv = ".venv"
```

### Custom Command

By default python from the local pyproject is run (using rye run, poetry run,
etc.). A custom command can be configured in `pyproject.toml` - the pyproject
file closest to the notebook is used (and no other means of configuration are
supported).

The key `tool.pyproject-local-kernel.python-cmd` should be a command that runs
python in the virtual environment you want to use for the project.

```toml
[tool.pyproject-local-kernel]
python-cmd = ["my", "custom", "python"]
```

## About Particular Project Managers

The project manager command, be it rye, uv, pdm, etc needs to be
available on the path where jupyterlab runs. Either install the project
manager in the jupyterlab environment, or install the project manager
user-wide (using something like pipx, rye tools, uv tool, brew, or
other method to install it.)

### Rye

- Rye is detected if the pyproject.toml contains `tool.rye.managed = true`
  which Rye sets by default for its new projects.

### Uv

- Uv is detected if the pyproject.toml contains `tool.uv`. It is also the
  default fallback if no project manager is detected from a pyproject file.

- pyproject-local-kernel requires uv 0.2.29 or later

- Uses `uv run` which is a preview feature (could break on future uv changes)

- The command used is `uv run --with ipykernel python` which means that it ensures
  `ipykernel` is used even if it's not already in the project(!). However, note that
  it uses an ephemeral virtual environment for ipykernel in that case. Add
  ipykernel to the project to avoid this.

## Project Status

Status: Working proof of concept, published to PyPI. Additional interest and
maintainer help is welcomed.

See also:

* https://github.com/mitsuhiko/rye
* https://github.com/astral-sh/uv
* https://github.com/goerz/python-localvenv-kernel
* https://github.com/pathbird/poetry-kernel
