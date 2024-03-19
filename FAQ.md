# Frequently asked questions

## Why do I have to install `ipykernel` manually?

The IPython kernel runs as part of the same process as all your other Python
code. This means we can't install our own version of it outside of your project.

## How do use with Pipenv?

1. Add ipykernel to the environment packages
2. Configure the python run command in local pyproject file

```toml
[tool.pyproject-local-kernel]
python-cmd = ["env", "PIPENV_IGNORE_VIRTUALENVS=1", "pipenv", "run", "python"]
```


## How change environment variables for the kernel

For example in Rye you can set environment variables for scripts, and you can
configure pyproject-local-kernel to use the script for its kernel invocation.

Here is an example (the name `kernelpython` is arbitrary).


```toml
[tool.pyproject-local-kernel]
python-cmd = ["rye", "run", "kernelpython"]

[tool.rye.scripts.kernelpython]
cmd = ["rye", "run", "python"]

[tool.rye.scripts.kernelpython.env]
X=1
Y=2
```

## Does Pyproject Local Kernel work with [Papermill][1]?

Yes it does.

Pyproject Local Kernel relies on jupyter's working directory: the working
directory is always the same as the notebook's location - and it will work as
long as you run papermill the same way, using its --cwd argument.

You can install papermill and pyproject-local-kernel in a separate environment,
and run each notebook in its own pyproject environment with its dependencies
this way.

[1]: https://papermill.readthedocs.io/en/latest/
