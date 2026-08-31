#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/src/gui/modern_app.py" "$@"
