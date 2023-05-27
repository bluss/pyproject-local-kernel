import os
import shutil
import sys
from glob import glob

# Ironically, we can't use Poetry as the build system since it doesn't have
# support for running arbitrary install scripts
# TODO: ^^^that might not actually be true
from setuptools import setup

current_dir = os.path.abspath(os.path.dirname(__file__))
setup_args = dict()

# Package the kernel.json file
# Note: this was adapted from the ipython/ipykernel setup.py script
# https://github.com/ipython/ipykernel/blob/abefee4c935ee79d3821dfda02f1511f55d4c996/setup.py#L95
# (Modified BSD License)
if any(a.startswith(("bdist", "install")) for a in sys.argv):
    sys.path.insert(0, current_dir)

    spec_dir = os.path.join(current_dir, "data_kernelspec")
    if os.path.exists(spec_dir):
        shutil.rmtree(spec_dir)
    os.mkdir(spec_dir)
    from ryeish_kernel.kernelspec import _write_kernelspec
    _write_kernelspec(spec_dir)

    setup_args["data_files"] = [
        # Extract the kernel.json file relative to the installation root
        # (i.e., the virtual environment or system Python installation).
        (
            os.path.join("share", "jupyter", "kernels", "ryeish-kernel"),
            glob(os.path.join(spec_dir, "*")),
        ),
    ]

with open(os.path.join(current_dir, "README.md")) as fp:
    README = fp.read()

setup(
    name="ryeish-kernel",
    version="0.2.0",

    # Package metadata
    author="Ulrik Sverdrup",
    author_email="bluss@example.com",
    url="https://github.com/bluss/ryeish-kernel",
    license="MIT",
    description="Python Jupyter kernel using Rye for dependency management",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords=["Interactive", "Interpreter", "Shell", "Web"],
    classifiers=[
        "Framework :: Jupyter",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],

    # Actual code stuff
    packages=["ryeish_kernel"],
    python_requires=">=3.8",
    install_requires=[
        "jupyter-client >= 7.0, < 9",
    ],
    **setup_args,
)
