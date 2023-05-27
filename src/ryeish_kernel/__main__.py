import platform
import signal
import subprocess
import sys
from pathlib import Path

RUN_CMD = ["rye", "run"]


def main():
    # Try to find pyproject.toml file
    # We do this so that we can spit out a better, more informative error
    # message if there is no pyproject.toml file present.
    if find_pyproject_file() is None:
        print(
            "\n" +
            "!" * 80 + "\n" +
            "!! Cannot start Rye kernel:\n"
            "!!     expected pyproject.toml in notebook directory\n" +
            "!!     (or any parent directory)\n" +
            "!! Do you need to run `rye init`?\n" +
            "!" * 80 + "\n",
            file=sys.stderr,
            sep="\n",
        )
        raise RuntimeError("Cannot start Rye kernel: couldn't find pyproject.toml")

    cmd = RUN_CMD + [
        "python", "-m", "ipykernel_launcher",
        *sys.argv[1:],
    ]
    proc = subprocess.Popen(cmd)

    if platform.system() == 'Windows':
        forward_signals = set(signal.Signals) - {signal.CTRL_BREAK_EVENT, signal.CTRL_C_EVENT, signal.SIGTERM}
    else:
        forward_signals = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP}

    def handle_signal(sig, _frame):
        proc.send_signal(sig)

    for sig in forward_signals:
        signal.signal(sig, handle_signal)

    exit_code = proc.wait()
    if exit_code == 0:
        print("ipykernel_launcher exited", file=sys.stderr)
    else:
        print("ipykernel_launcher exited with error code:", exit_code, file=sys.stderr)


def find_pyproject_file():
    cwd = Path().resolve()
    candidate_dirs = [cwd, *cwd.parents]
    for dirs in candidate_dirs:
        pyproject_file = dirs / "pyproject.toml"
        if pyproject_file.exists():
            return pyproject_file
    return None


if __name__ == "__main__":
    main()
