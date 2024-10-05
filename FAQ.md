# Frequently Asked Questions

## How does it work?

The regular IPython kernel for Jupyter is launched like this:
`python -m ipykernel_launcher <arguments..>`

If you just prefix that command with `rye run`, `uv run`, `poetry run`,
`pdm run`, `hatch run`, etc, then you get a kernel invocation that executes in
the current pyproject's environment. That's basically the whole magic of this
package, it doesn't need to do more (well, if it only were *that* easy..)

To break it down:

- You install `jupyterlab` and `pyproject-local-kernel` together.
- Then you have projects defined in a `pyproject.toml` for each notebook project

## Why do I have to install `ipykernel` manually?

The IPython kernel is the interpreter that executes everything in the notebook,
and it needs to be installed together with all the dependencies the notebook
wants to import. However only one installation of JupyterLab (or equivalent
notebook program) is necessary, and should be separate from the notebook.

For Uv, the default command is `uv run --with ipykernel` which creates an
overlay environment containing ipykernel if it wasn't already installed. This
makes it possible to skip ipykernel in the project dependencies if desired.

## How can I debug my project?

In general it is a good idea to look at these variables, in a notebook,
to try to understand which python and which python environment it is using:

- `sys.prefix` - the path to the virtual environment
- `sys.executable`
- `sys.path`
- `sys.version_info`

## What is the benefit of the `use-venv` setting?

It is used for more flexibility. It means that pyproject local does not
depend on any particular project manager and can use any virtual environment.

And, if you for example compare the uv default configuration vs a `use-venv`
configuration, both in a uv-defined project, then they stack up like this:

**uv default**

* Runs `uv run --with ipykernel python`
* Installs `ipykernel` automatically
* Syncs dependencies automatically on every run

**`use-venv = ".venv"`**

* Runs `python` from the virtual environment directly which has less
  indirection and overhead
* Does not create or change the environment, only uses it as it is
* Requires `ipykernel` to be installed

## Does Pyproject Local Kernel work with Nbconvert and [Papermill][1]?

Yes it works, with both Nbconvert and Papermill.

Pyproject Local Kernel relies on jupyter's working directory: the working
directory is always the same as the notebook's location - and it will work as
long as you run papermill the same way, using its `--cwd` argument.

You can install papermill and pyproject-local-kernel in a separate environment,
and run each notebook in its own pyproject environment with its dependencies
this way.

[1]: https://papermill.readthedocs.io/en/latest/

## Does Pyproject Local Kernel require Uv or Rye?

No, neither of them are strictly required to use. Any supported project manager
is enough, or even none for custom or vitualenv configurations.

For development of the project and running tests, Uv is required.

## How to setup for VSCodium or VS Code?

**Note** that code natively supports using virtual environments in a local
directory directly. For this reason `pyproject-local-kernel` is almost always
unecessary with VSCodium or VS Code ("code").

Code does not launch the kernel in the same way that jupyterlab does
(jupyterlab uses `jupyter-client` and enables kernel provisioning), for this reason
`pyproject-local-kernel` is launched using a less reliable way when
using code, and this is a - for now - unsupported way to use this project.

However, it should more or less work. Here are some suggestions:

Install both `jupyter` and `pyproject-local-kernel` in a central python
environment that you choose. (The [vscode-jupyter][] extension instructs that
you should install `jupyter` and tell it where this installation is).

Then you need need to use the command *Python: Select Interpreter* to select
the environment where you installed `jupyter`.

When this is done, you can use *Select Kernel* → *Jupyter Kernel* → *Pyproject
Local* to use this project from code.

[vscode-jupyter]: https://github.com/microsoft/vscode-jupyter

The output panel has a *Jupyter* section with logs from the jupyter kernel,
which can help in debugging.


## Does it work with with Pipenv?

1. Add ipykernel to the environment packages
2. Configure the python run command in local pyproject file

```toml
[tool.pyproject-local-kernel]
python-cmd = ["env", "PIPENV_IGNORE_VIRTUALENVS=1", "pipenv", "run", "python"]
```


## How change environment variables for the kernel?

For example in Rye you can set environment variables for scripts, and you can
configure pyproject-local-kernel to use the script for its kernel invocation.

Here is an example (the name `kernelpython` is arbitrary).


```toml
[tool.pyproject-local-kernel]
python-cmd = ["rye", "run", "kernelpython"]

[tool.rye.scripts.kernelpython]
cmd = ["python"]

[tool.rye.scripts.kernelpython.env]
X=1
Y=2
```

Other project managers have similar features (PDM, at least).


## Isn't There a Less Complicated Way to Do It?

Yes, there kind of is a way.

If you install the following kernelspec, you can use `uv run` as
the environment manager for your notebooks. You don't hardcode a virtual environment path,
but you hardcode that you're using `uv run`.

This example does more or less the same as what `pyproject-local-kernel` does, but without
the indirections (and without the error handling).

```json

{
  "argv": ["uv", "run", "--with", "ipykernel", "python", "-m", "ipykernel_launcher", "-f", "{connection_file}"],
  "display_name": "Uv Run Ipykernel",
  "language": "python",
  "metadata": {
    "debugger": true
  }
}
```

## More questions about Uv

### Why is the python environment path weird?

If you run the following when using uv and pyproject local kernel:

```python
import sys
sys.prefix
```

and you see a prefix like this, or similar
`'~/.cache/uv/archive-v0/n2G3HHDzRZ7cjiFgGXIwC'` then uv is using an ephemeral
environment to run. It should work just fine, it means that `ipykernel` is not
installed in your base environment. If you want to fix this, use `uv add
ipykernel` and restart the kernel.

### Can I nest projects?

You can, but `pyproject-local-kernel` always looks at the closest
`pyproject.toml` only, not at the whole workspace.

If you want to “isolate” a `pyproject.toml` insert an empty
`[tool.uv.workspace]` in the `pyproject.toml`, that way it is not part of any
other workspace from directories above it.
