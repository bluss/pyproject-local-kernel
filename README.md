# Rye(ish) Jupyter Kernel

Use per-directory Rye projects to run Python Jupyter kernels. See the examples
directory for how to setup jupyterlab and notebook projects separately.

The intention is that instead of installing a myriad of jupyter kernelspecs,
one per project, instead have one "meta" kernel that enables the environment
for the project the notebook file resides in. This approach should be more
portable (usable to anyone who checks out your project structure from git) and
easier to use.

Project Status: Proof of Concept

* Rye: https://github.com/mitsuhiko/rye
* Poetry-kernel: https://github.com/pathbird/poetry-kernel
  See poetry-kernel for more documentation about the per-directory concept.

The name is currently Rye(ish) because it is not officially connected with Rye.

## User Experience

If the Rye kernel is used in a project where rye is not installed, or
the rye project does not have an ipykernel, then starting the kernel fails.

It starts a "fallback" kernel which that shows a message that rye is not setup
as expected in this environment, and provide a regular ipython kernel which
lets you run shell commands to fix rye!

```diff
- Failed to start Rye environment kernel - no ipykernel in rye project?
- Run these:
- !rye add ipykernel
- !rye sync
- 
- Then restart the kernel to try again.
```
