# Changelog

## 0.12.1

- Update how configuration types are displayed in errors (#60)

- Pin Python 3.12 for the examples (#62)

- Minor fixes to fallback kernel mode (#62)

- Clarify error message when project section is missing from `pyproject.toml`
  (#62)


## 0.12.0

- Show more specific error if we fail to run sanity check (#55)

- Add project config `sanity-check` (#55)

- Accept both underscore and hyphen in project configuration (#55)

- Sharpen the public/private API distinction even if this is not a library;
  only the main function and the kernel provisioner are public API now. (#57)

## 0.11.3

- Set `PYPROJECT_LOCAL_KERNEL_SANITY_CHECK` in the environment when running the
  sanity check. (#51)

- Log working directory setting when starting kernel process. (#51)

- If `pyproject.toml` has no project section, do not identify it as belonging
  to a project manager that requires the project section. (#52)

## 0.11.2

- Enable the binary path in the virtual environment for use-venv
  and hatch configurations (#48)

- Launch fallback kernel using `python -m`. (#49)

- Test using Python 3.13. (#45)

## 0.11.1

- Add another kernelspec **Pyproject Local (use-venv)** which defaults to the
  `use-venv` setting, using the virtual environment directly.
  (#43 and cb90a2064576d8e58645ad9577a7653a94780065).

- `PyprojectKernelProvisioner` is now configurable like other “jupyter objects”
  using the same config system. However, `pyproject.toml` configuration
  should be preferred. (#43)

- When preparing to start the kernel, only errors from known checks
  are caught and passed off to the starting fallback kernel.
  (aaed1da1069de41df4ce493582ad98ccd6bc7d48)

## 0.11.0

- Use [local kernel provisioning][lkp] to launch the kernel. This is
  a more standard way to do it, with less overhead and less compatibility
  issues. (#39)
- Improved fallback mode on errors and documentation around this
- License update again, more or less reverting what was done in v0.10.0,
  because the relevant code has been removed. (#39)
- The package now installs an executable `pyproject_local_kernel` that is
  used interally (#39)
- This one goes to eleven, it really does

[lkp]: https://jupyter-client.readthedocs.io/en/latest/provisioning.html

## 0.10.1

- If there is no `pyproject.toml` at all, show an error message to the user
  instead of throwing an exception. Fixes a regression. (#34)
- Fix running tests in sdist (#33)

## 0.10.0

- Support interrupting the kernel on windows (#30, #32)
- Now uses `jupyter-client` to launch the kernel process (#30)
- License was updated after we copied one file from ipykernel,
  now a combination of MIT and BSD 3-clause.

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
