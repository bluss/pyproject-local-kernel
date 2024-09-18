#!/bin/bash

set -ex

directory=$(dirname "$0")
cd "$directory"

UV=${UV:-uv}
PYVERSION=${PYVERSION:-3.12}
UPDATE_ON=3.12
VERBOSE=-q

if [[ $PYVERSION == "$UPDATE_ON" ]] ; then
    UPDATE=-U
else
    UPDATE=
fi

directories=(server client-rye client-uv)

for dir in ${directories[@]} ; do
    (cd "$dir";
        cp uv.lock uv.lock.orig;
        $UV python pin "$PYVERSION";
        $UV sync --reinstall-package pyproject-local-kernel $VERBOSE $UPDATE ;
    )
done

SERVER_PY=$(uv python find server/.venv)

# ensure client-hatch is synced
(cd client-hatch;
    hatch env run -- python -c "";
)

for nbdir in client-rye client-uv client-hatch ; do
    # convert to ipynb
    cp -v ./notebook.py $nbdir/
    "$SERVER_PY" -m jupytext --to ipynb $nbdir/notebook.py
    # execute the notebook
    # check for problems in the log and exit with error in that case
    "$SERVER_PY" -m papermill --cwd $nbdir $nbdir/notebook.ipynb $nbdir/notebook_out.ipynb 2>&1 | \
        awk 'BEGIN {status = 0} /Failed to start kernel|Traceback/ {status = 1} 1; END {exit(status)}'
done

for dir in ${directories[@]} ; do
    (cd "$dir";
        mv -f uv.lock.orig uv.lock;
    )
done
