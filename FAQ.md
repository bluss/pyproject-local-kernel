# Frequently Asked Questions


## How does it work?

The regular IPython kernel for Jupyter is launched like this:
`python -m ipykernel_launcher -f <connection_file>`

If you just prefix that command with `rye run`, `uv run`, `poetry run`,
`pdm run`, `hatch run`, etc, then you get a kernel invocation that executes in
the current pyproject's environment. That's basically the whole magic of this
package, it doesn't need to do more (well, if it only were *that* easy..)

It uses [Kernel Provisioning][kp] in `jupyter-client` to launch the right
command depending on project configuration.

[kp]: https://jupyter-client.readthedocs.io/en/latest/provisioning.html

## How do I install it?

To break it down:

- You install `jupyterlab` and `pyproject-local-kernel` together.
- Then you have projects defined by `pyproject.toml` for each notebook
  or collection of notebooks. They install `ipykernel` and packages
  you want to use in the notebook.

See also [`example/`][ex] in the git repository.

[ex]: https://github.com/bluss/pyproject-local-kernel/tree/main/example


## Why do I have to install `ipykernel` manually?

The IPython kernel is the interpreter that executes everything in the notebook,
and it needs to be installed together with all the dependencies the notebook
wants to import. However only one installation of JupyterLab (or equivalent
notebook program) is necessary, and should be separate from the notebook.

For Uv, the default command is `uv run --with ipykernel` which creates an
overlay environment containing ipykernel if it wasn't already installed. This
makes it possible to skip ipykernel in the project dependencies if desired.


## How can I see which Python environment I am using?

In general it is a good idea to look at these variables in a notebook
to understand which Python version and Python environment it is using:

```python
sys.prefix
sys.executable
sys.path
sys.version_info
```

You can also start JupyterLab with debug logs, and look for
`pyproject-local-kernel` debug info in the output.


## What is the benefit of the `use-venv` setting?

It is used for more flexibility. It means that pyproject local does not
depend on any particular project manager and can use any virtual environment.

And, if you for example compare the uv default configuration vs a `use-venv`
configuration, both in a uv-defined project, then they stack up like this:

**Uv default**

* Runs `uv run --with ipykernel python`
* Installs `ipykernel` automatically
* Syncs dependencies automatically on every start/restart

**`use-venv = ".venv"`**

* Runs `python` from the virtual environment directly which has less
  indirection and overhead
* Does not create or change the environment, only uses it as it is
* Requires `ipykernel` to be installed


## Does Pyproject Local Kernel work with Nbconvert and [Papermill][1]?

Yes it works, with both Nbconvert and Papermill.

Pyproject Local Kernel relies on Jupyter's working directory convention: the
working directory is always the same as the notebook's location - and it will
work as long as you run Papermill the same way, using its `--cwd` argument.

You can install Papermill and pyproject-local-kernel in a separate environment,
and run each notebook in its own pyproject environment with its dependencies
this way.

[1]: https://papermill.readthedocs.io/en/latest/


## Does it work with Conda?

Conda environments are supported only by using the `use-venv` setting in
`pyproject.toml`, where it needs to point to the location of the installed
environment as an absolute path, or a path relative to the the `pyproject.toml`
file.

```toml
[tool.pyproject-local-kernel]
use-venv = ".venv"
```


## How to setup for VSCodium or VS Code?

**Note** that code natively supports using virtual environments in a local
directory directly. For this reason `pyproject-local-kernel` is almost always
unecessary with VSCodium or VS Code ("code").

Code does not launch the kernel in the same way that Jupyterlab does
(Jupyterlab uses `jupyter-client` and enables kernel provisioning), for this reason
`pyproject-local-kernel` is launched using a less reliable way when
using code, and this is a - for now - unsupported way to use this project.

However, it should more or less work. Here are some suggestions:

Install both `jupyter` and `pyproject-local-kernel` in a central Python
environment that you choose. (The [vscode-jupyter][] extension instructs that
you should install `jupyter` and tell it where this installation is).

Then you need need to use the command *Python: Select Interpreter* to select
the environment where you installed `jupyter`.

When this is done, you can use *Select Kernel* → *Jupyter Kernel* → *Pyproject
Local* to use this project from code.

[vscode-jupyter]: https://github.com/microsoft/vscode-jupyter

The output panel has a *Jupyter* section with logs from the Jupyter kernel,
which can help in debugging.


## Does it work with with Pipenv?

1. Add ipykernel to the environment packages
2. Configure the Python run command in local pyproject file

```toml
[tool.pyproject-local-kernel]
python-cmd = ["env", "PIPENV_IGNORE_VIRTUALENVS=1", "pipenv", "run", "python"]
```


## Does Pyproject Local Kernel require Uv or Rye?

No, neither of them are strictly required to use. Any supported project manager
is enough, or even none for custom or vitualenv configurations.

For development of the project and running tests, Uv is required.


## How does the `python-cmd` configuration work?

`python-cmd` should be a command-line that runs Python, in the environment that
should be used for the notebook.

For example, for a regular virtual environment, the python command would be
`.venv/bin/python` or `.venv\Scripts\python.exe`.

The python command should take arguments and will be run with arguments to start
the IPython kernel. It can also be used with different arguments to run a sanity check
script, checking if `ipykernel` is installed. [^1]

Example 1: `python-cmd` is a script in the same directory as `pyproject.toml`
and when invoked with arguments, it will run python in the desired environment.

```toml
[tool.pyproject-local-kernel]
python-cmd = "./runpy"
```

Example 2: a shell is invoked to be able to use shell constructs like `&&`
directly, and care is taken so that it still uses the extra command line
arguments. Of course, using any such script is less portable than just using a
project or virtual environment configuration directly.

```toml
[tool.pyproject-local-kernel]
python-cmd = ["bash", "-c", 'uv sync && X=1 .venv/bin/python -I "$@" && echo done', "--"]
```

[^1]: The variable `PYPROJECT_LOCAL_KERNEL_SANITY_CHECK` is set in the environment when
running the sanity check.


## Isn't There a Less Complicated Way to Do It?

Yes, there kind of is a way.

If you install the following kernelspec, you can use `uv run` as
the environment manager for your notebooks. You don't hardcode a virtual environment path,
but you hardcode that you're using `uv run`.

This example does more or less the same as what `pyproject-local-kernel` does, but without
the error handling and configurability:

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

If you have such a `.json` file, `jupyter kernelspec install --user` can help you install it.

## More questions about Uv

### Can I start `pyproject-local-kernel` with `uvx`?

Yes, you can launch a full Jupyterlab environment using:

```console
uvx --with pyproject-local-kernel --from jupyterlab jupyter-lab
```

However it is often good to use a project or environment manager to define the
Jupyter environment with your chosen dependencies, so that you can use a lock
file and have other benefits of a proper project.

### Can I use a different version of Python for the notebook?

Yes, the Python version can be pinned separately per notebook project.
It doesn't need to be the same as the Jupyterlab Python version.

### Why is the Python environment path weird?

If you look at `sys.prefix` when using **uv** and pyproject local kernel,
and you see a prefix like this or similar:
`'~/.cache/uv/archive-v0/n2G3HHDzRZ7cjiFgGXIwC'`, then `uv run` is using an
[ephemeral environment][eph] to run the kernel.<br>
It should work just fine in most cases, but it means that `ipykernel` is not
installed in your base environment. If you want to fix this,
use `uv add ipykernel` and restart the kernel.

[eph]: https://docs.astral.sh/uv/reference/cli/

### Can I nest projects?

You can, but `pyproject-local-kernel` always looks at the closest
`pyproject.toml` only, not at the whole workspace.

If you want to “isolate” a `pyproject.toml` insert an empty
`[tool.uv.workspace]` in the `pyproject.toml`, that way it is not part of any
other workspace from directories above it.
