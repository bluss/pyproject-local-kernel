# Frequently Asked Questions

## How does it work?

The regular IPython kernel for Jupyter is launched like this:
`python -m ipykernel_launcher <arguments..>`

If you just prefix that command with `rye run`, `uv run`, `poetry run`,
`pdm run`, `hatch run`, etc, then you get a kernel invocation that executes in
the current pyproject's environment. That's basically the whole magic of this
package, it doesn't need to do more.

## Why do I have to install `ipykernel` manually?

The IPython kernel is the interpreter that executes everything in the notebook,
and it needs to be installed together with all the dependencies the notebook
wants to import. However only one installation of JupyterLab (or equivalent
notebook program) is necessary, and should be separate from the notebook.

For Uv, the default command is `uv run --with ipykernel` which creates an
overlay environment containing ipykernel if it wasn't already installed. This
makes it possible to skip ipykernel in the project dependencies if desired.

## Does Pyproject Local Kernel require Uv or Rye?

No, neither of them are strictly required to use. Any supported project manager
is enough, or even none for custom or vitualenv configurations.

For development of the project and running tests, Uv is required.

## How to setup for VSCodium or VS Code?

The [vscode-jupyter][] extension instructs that you must install `jupyter`
in a python environment to use the extension. Install `pyproject-local-kernel` in that
particular environment, and it will work. If doing this from scratch, you can
setup a new environment with both `jupyter` and `pyproject-local-kernel`.

It's possible you need to use the command *Python: Select Interpreter* to
select the environment.

[vscode-jupyter]: https://github.com/microsoft/vscode-jupyter

- The *jupyter* environment must install the `pyproject-local-kernel` package.
  (“server side”)
- The notebook projects install `ipykernel` and the notebook dependencies
  (“client side”)

**Note** that code natively supports just using a directory local virtualenv
for notebooks, such as Rye or Uv's `.venv` or similar. For this reason
`pyproject-local-kernel` does not matter so much in this case, it's
mainly useful for JupyterLab!

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

## Does Pyproject Local Kernel work with [Papermill][1]?

Yes it does.

Pyproject Local Kernel relies on jupyter's working directory: the working
directory is always the same as the notebook's location - and it will work as
long as you run papermill the same way, using its --cwd argument.

You can install papermill and pyproject-local-kernel in a separate environment,
and run each notebook in its own pyproject environment with its dependencies
this way.

[1]: https://papermill.readthedocs.io/en/latest/


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
