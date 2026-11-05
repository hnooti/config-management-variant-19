#!/bin/sh
set -eu
app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$app_dir${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m src "$@"
