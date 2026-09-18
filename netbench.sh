#!/bin/bash
# Wrapper launcher for macOS / Linux
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ensure wake-lock on Android Termux
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    trap 'termux-wake-unlock' EXIT
fi

# Fallback to python3 or python
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[!] Python 3 is required. Please install python3."
    exit 1
fi

exec "$PYTHON_CMD" "$SCRIPT_DIR/netbench.py" "$@"