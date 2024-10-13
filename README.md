
# Pyproject Local Jupyter Kernel

<p class="web_hidden">

[Website][] - [PyPI][] [![PyPI - Python Version](https://img.shields.io/pypi/v/pyproject-local-kernel)][PyPi]

</p>

Separate dependencies for Jupyter notebooks - each notebook
project can have its own dependencies!

[Website]: https://bluss.github.io/pyproject-local-kernel/
[PyPi]: https://pypi.org/project/pyproject-local-kernel/

Instead of installing a myriad of Jupyter kernelspecs, one per project, with
this solution there is only one [kernel provisioner][kp] that enables the
environment for the project the notebook file resides in. This approach should
be more portable, usable to anyone who checks out your project structure from
git, and easier to use.

Pyproject Local supports **Uv, Poetry, Hatch, Rye, and PDM**
and reads `pyproject.toml` to figure out which kind of project it is.
Or it can use a custom command or a bare virtual environment directly.

[kp]: https://jupyter-client.readthedocs.io/en/latest/provisioning.html

![screenshot of notebook launcher](https://raw.githubusercontent.com/bluss/pyproject-local-kernel/main/docs/images/pyproject-local.png)

## Quick Start (JupyterLab)

1. Install pyproject-local-kernel in your Jupyterlab environment and restart
   Jupyterlab
2. Create a new directory for the notebook project
3. Create a new notebook and select the **Pyproject Local** kernel
4. In the *“fallback”* environment that appears - because it is an empty
   project - create a new project.

  (Example for Uv:)

  `!uv init && uv add ipykernel`

5. Use the restart button in JupyterLab to restart the kernel after these changes.
6. Dependencies will quickly sync and you are good to go!
7. Use more `add` commands to add further dependencies.


See the examples directory for how to setup Jupyterlab and notebook projects
separately. JupyterLab and the notebook are installed in separate environments.


Do you want to use pyproject-local-kernel in other environments, like with
papermill, **VSCodium or VS Code**, or or other ways? See our [FAQ][] for more
information.

[FAQ]: FAQ.md

## User Experience

If started in an empty directory or where a project is not correctly set up,
the Pyproject Local will fail to start normally, but it will start a fallback
kernel so that you can fix the project.

It will show a message like this - with some details about the error.

```diff
! Error: Could not find `ipykernel` in environment.
! Add `ipykernel` as a dependency in your project and update the virtual environment.
! The detected project type is: Unknown
!
! This is a fallback - pyproject-local-kernel failed to start.
! The purpose of the fallback is to let you run shell commands to fix the
! environment - when you are done, restart the kernel and try again!
```

Remember that you can also use Jupyterlab's embedded terminal to help setting
up a project.

***If `pyproject.toml` is Missing***

If the Pyproject Local kernel is selected in a project where there is no `pyproject.toml`,
then starting the kernel fails. On first run it should show an error message in JupyterLab.

If this happens, create a new `pyproject.toml` with the editor or use
one of the project init commands to create a new project.

***If the `ipykernel` is Missing***

The notebook project needs to install `ipykernel` as a dependency.

Edit the `pyproject.toml` to include `ipykernel` in dependencies:

```toml
dependencies = [
    "ipykernel>=6.29",
    # .. more dependencies
]
```

sync the changes to the project using sync command for the project
manager you use, then restart the Pyproject local kernel in Jupyterlab.

## Configuration

Configuration is optional and is read from `pyproject.toml`. Only the
`pyproject.toml` closest to the notebook is read. Defaults are based on
“sniffing” the `pyproject.toml` to detect which project manager is in use.

### `python-cmd`

The key `tool.pyproject-local-kernel.python-cmd` should be a command that runs
python from the environment you want to use for the project.

If this is set then it overrides the default command. There is further
explanation in [the FAQ](FAQ.md#how-does-the-python-cmd-configuration-work).

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

If this is set then it overrides the default command - the virtualenv is used
directly without invoking any project manager. Remember to explicitly install
or sync required dependencies.

**Default:** Not set<br>
**Type:** `str`<br>
**Example:**

```toml
[tool.pyproject-local-kernel]
use-venv = ".venv"
```

### `sanity-check`

If `true`, then run a check for `ipykernel` being installed in the project
before starting the kernel process.

**Default:** true<br>
**Type:** `bool`<br>
**Example:**

```toml
[tool.pyproject-local-kernel]
sanity-check = true
```


### `PyprojectKernelProvisioner`

The kernel provisioner is configurable in the same way as other Jupyter
objects, with the following settings. They can be set in your
`jupyter_lab_config.py` settings file.
When possible, prefer to use settings in `pyproject.toml` instead, to keep them
close to the project.

```python
#------------------------------------------------------------------------------
# PyprojectKernelProvisioner(LocalProvisioner) configuration
#------------------------------------------------------------------------------
## Enable sanity check for 'ipykernel' package in environment
#  Default: True
# c.PyprojectKernelProvisioner.sanity_check = True

## Default setting for use-venv for projects using the 'use-venv' kernel
#  Default: '.venv'
# c.PyprojectKernelProvisioner.use_venv = '.venv'
```


## About Particular Project Managers

The project manager command, be it rye, uv, pdm, etc needs to be
available on the path where Jupyterlab runs. Either install the project
manager in the Jupyterlab environment, or install the project manager
user-wide (using something like pipx, uv tool, rye tools, brew, or
other method to install it.)

***Uv***

- Uv is detected if the pyproject.toml contains `tool.uv`. It is also the
  default fallback if no project manager is detected from a pyproject file.

- The command used is `uv run --with ipykernel python` which means that it ensures
  `ipykernel` is used even if it's not already in the project(!). However, note that
  it uses an [ephemeral virtual environment][eph] for ipykernel in that case.
  Add ipykernel to the project to avoid this.

[eph]: https://docs.astral.sh/uv/reference/cli/

***Rye***

- Rye is detected if the pyproject.toml contains `tool.rye.managed = true`
  which Rye sets by default for its new projects.

***PDM***

- PDM is detected if pyproject.toml contains `tool.pdm`

***Hatch***

- Hatch is detected if pyproject.toml contains `tool.hatch.envs`

- By default it calls out to `hatch env find`, to find the default virtualenv,
  and runs from there. `hatch run` should not be used directly because
  it's not compatible with how kernel interrupts work (as of this writing).

- It's best to create the hatch project, add ipykernel as dependency and sync
  dependencies in a terminal before starting (it does not work so well with
  shell commands in a notebook).

***Poetry***

- Poetry is detected if pyproject.toml contains `tool.poetry.name`

- Some commands are interactive by default and don't work in a notebook,
  but they have an `-n` switch to make them non-interactive.

## Project Status

Additional interest and maintainer help is welcomed.

## Links

* <https://github.com/astral-sh/uv>
* <https://github.com/renan-r-santos/pixi-kernel>
* <https://github.com/goerz/python-localvenv-kernel>
* <https://github.com/pathbird/poetry-kernel>

## License

`pyproject-local-kernel` is open source. See the LICENSE.md file in the source
distribution for more information.
