#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==================================================="
echo "  Codebase Intelligence - Web Dashboard Launcher"
echo "==================================================="

# Determine python executable
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON_EXE="$DIR/.venv/bin/python"
else
    PYTHON_EXE="python3"
fi

# Target repository (default to demo_project)
TARGET_REPO="${1:-demo_project}"

echo "[*] Indexing repository: $TARGET_REPO"
"$PYTHON_EXE" "$DIR/cli.py" index "$TARGET_REPO"

echo ""
echo "[*] Starting web dashboard at http://127.0.0.1:5050 ..."
"$PYTHON_EXE" "$DIR/demo_dashboard/server.py"
