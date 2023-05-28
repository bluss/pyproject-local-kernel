# Rye(ish) Jupyter Kernel

Use per-directory Rye projects to run Python Jupyter kernels. See the examples
directory for how to setup jupyterlab and notebook projects separately.

The intention is that instead of installing a myriad of jupyter kernels, one
per project, instead have one "meta" kernel that enables the environment for
the project the notebook file resides in. This approach should be more portable
(usable to anyone who checks out your project structure from git) and easier to
use.

Project Status: Proof of Concept

* Rye: https://github.com/mitsuhiko/rye
* Poetry-kernel: https://github.com/pathbird/poetry-kernel
  See poetry-kernel for more documentation about the per-directory concept.

The name is currently Rye(ish) because it is not officially connected with Rye.

