#!/usr/bin/env bash
# Wrapper launcher for macOS / Linux
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure wake-lock on Android Termux
if command -v termux-wake-lock &> /dev/null; then
    termux-wake-lock
    trap 'termux-wake-unlock' EXIT
fi

# Fallback to python3 or python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[!] Python is not found. Please install Python 3."
    exit 1
fi

exec $PYTHON_CMD "$SCRIPT_DIR/netbench.py" "$@"
