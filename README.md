
# Pyproject Local Jupyter Kernel

<p class="web_hidden">

[Website][] - [PyPI][] [![PyPI - Python Version](https://img.shields.io/pypi/v/pyproject-local-kernel)][PyPi]

</p>

Separate dependencies for Jupyter notebooks in separate projects.

Use python project managers to define dependencies:
  use one of Uv, Rye, PDM, Poetry, Hatch (and so on).

[Website]: https://bluss.github.io/pyproject-local-kernel/
[PyPi]: https://pypi.org/project/pyproject-local-kernel/

Instead of installing a myriad of jupyter kernelspecs, one per project, with
this solution there is only one "meta" kernel that enables the environment for
the project the notebook file resides in. This approach should be more
portable, usable to anyone who checks out your project structure from git, and
easier to use.

Pyproject Local supports the following systems, and reads `pyproject.toml` to
figure out which kind of project it is:

Uv <br>
Rye <br>
Poetry <br>
Hatch <br>
PDM <br>

A custom command or direct use of virtual environment can also be configured.

## Quick Start (JupyterLab)

1. Install pyproject-local-kernel in your jupyterlab environment and restart
   jupyterlab
2. Create a new directory and notebook
3. Select the **Pyproject Local** kernel for the notebook
4. Run these shell commands in the notebook to setup the new project:<br>
   
  (Example for Uv:)

  `!uv init && uv add ipykernel`

  (Example for Rye:)

  `!rye init --virtual && rye add ipykernel`


Now restart the kernel and you are good to go. Use more `add` commands to add
further dependencies.

See the examples directory for how to setup jupyterlab and notebook projects
separately. JupyterLab and the notebook are installed in separate environments.


Do you want to use pyproject-local-kernel in other environments, like
**VSCodium or VS Code**, or maybe using Pipenv? See our [FAQ][] for more
information.

[FAQ]: FAQ.md

## User Experience

If the Pyproject Local kernel is used in a project where Uv (or the relevant
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

Configuration is optional and is read from `pyproject.toml`. Only the
`pyproject.toml` closest to the notebook is read. Defaults are based on
“sniffing” the `pyproject.toml` to detect which project manager is in use.

### `python-cmd`

The key `tool.pyproject-local-kernel.python-cmd` should be a command that runs
python from the environment you want to use for the project.

If this is set then it overrides the default command.

**Default:** *Depends on project manager*<br>
**Type:** `list[str] | str`<br>
**Example:**

```toml
[tool.pyproject-local-kernel]
python-cmd = ["uv", "run", "--with", "ipykernel", "python"]
```

### `use-venv`

Path to virtual environment that should be used, relative to the
`pyproject.toml` file. Can also be an absolute path.

If this is set then it overrides the default command.

**Default:** Not set<br>
**Type:** `str`<br>
**Example:**

```toml
[tool.pyproject-local-kernel]
use-venv = ".venv"
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

- The command used is `uv run --with ipykernel python` which means that it ensures
  `ipykernel` is used even if it's not already in the project(!). However, note that
  it uses an ephemeral virtual environment for ipykernel in that case. Add
  ipykernel to the project to avoid this.

### PDM

- PDM is detected if pyproject.toml contains `tool.pdm`

### Hatch

- Hatch is detected if pyproject.toml contains `tool.hatch.envs`

- By default it calls out to `hatch env find`, to find the default virtualenv,
  and runs from there. `hatch run` should not be used directly because
  it's not compatible with how kernel interrupts work (as of this writing).

- It's best to create the hatch project, add ipykernel as dependency and sync
  dependencies in a terminal before starting (it does not work so well with
  shell commands in a notebook).

## Project Status

Additional interest and maintainer help is welcomed.

## Links

* <https://github.com/mitsuhiko/rye>
* <https://github.com/astral-sh/uv>
* <https://github.com/goerz/python-localvenv-kernel>
* <https://github.com/pathbird/poetry-kernel>
