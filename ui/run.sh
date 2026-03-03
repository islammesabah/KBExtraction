#!/bin/bash
set -euo pipefail

# Always run from repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Ensure venv exists; bootstrap if needed
if [ ! -d "venv" ]; then
  echo "ℹ️  venv/ not found. Running ./setup.sh first..."
  ./setup.sh
fi

# Activate venv
# shellcheck disable=SC1091
source venv/bin/activate

# Make kbdebugger importable
export PYTHONPATH="${REPO_ROOT}/src"

echo "🚀 Server is up and running on PORT http://localhost:5002"

# Run Flask entrypoint
exec python -m ui.app
