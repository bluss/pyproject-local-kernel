# Changelog

## 0.9.1

- Call `hatch env find` using `--no-color` for robustness (#27)
- Support a command string for `python-cmd` configuration (#28)
- Better test setup for jupyter using pytest (#27)

## 0.9.0

- Check configuration value types strictly and warn on unknown configuration
- Examples in the repository now use Uv

## 0.8.1

- Fix problem trying to forward SIGCHLD to kernel, which was maybe specific to
  Python 3.8 (and not-windows) (#24)

## 0.8.0

- Change how `hatch` projects are run: detect the (default) virtual env path
  and run python from there. User has to ensure virtualenv dependencies are
  synchronized. (#23)

## 0.7.2

- Published documentation to a new website using mkdocs
- Copyedited documentation

## 0.7.1

- Use Uv as first fallback if no explicit project manager can be identified
  from the pyproject if `uv` is in the command path. Use Rye as the second
  fallback in the same way.

## 0.7.0

- Use `uv run` for uv projects. Requires uv 0.2.29 or later.
  Uses `uv run --with ipykernel` which means it will run as
  before if ipykernel is already installed, or run in an overlay
  environment (ipykernel + base pyproject) if not.
- Include kernel start failure messages in user visible text in more cases such
  as “command not found”.

## 0.6.0

- Support configuration `use-venv` for setting a name of a virtualenv to use
- Support Uv (in a basic way, by assuming `use-venv=".venv"` for uv)

## 0.5.5

- Fix ProjectDetection.path which should hold the path to the pyproject file
- Added trusted publishing (for PyPI) workflow on github

## 0.5.4

- Enable debugging for the Pyproject Local kernel (just like the regular
ipykernel)
- More extensive tests, on linux and windows, including notebook execution

## 0.5.3

- Add tests. Moved main logic to module to facilitate.
- Update readme

## 0.5.2

- Use tomllib for newer Python, and tomli as fallback
- Catch all exceptions when starting the kernel, so that the fallback can be
started in most situations.
- More detailed error messages in the fallback

## 0.5.1

- Cleaned up unnecessary log output
- Set repo URL in package

## 0.5.0

- Changed name to pyproject-local-kernel (previously ryeish-kernel)
- Now supports Rye, PDM, Poetry, Hatch and custom configuration
