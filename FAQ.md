# Frequently asked questions

## How does it work?

The regular IPython kernel for Jupyter is launched like this:
`python -m ipykernel_launcher <arguments..>`

If you just prefix that command with `rye run`, `poetry run`, `pdm run` etc,
then you get a kernel invocation that executes in the current pyproject's
environment. That's basically the whole magic of this package, it doesn't
need to do more.

## Why do I have to install `ipykernel` manually?

The IPython kernel is the interpreter that executes everything in the notebook,
and it needs to be installed together with all the dependencies the notebook
wants to import. The kernel and Jupyter however communicate over IPC and
can be installed completely separately.

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
