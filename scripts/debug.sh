#!/usr/bin/env bash
set -euo pipefail

# Load environment variables from .env file.
if [ -f .env ]; then
  echo "💡 Loaded .env file."
  source .env # this loads the .env file and exports its variables into the environment
else
  echo "🚨 Error: .env file not found!"
  exit 1
fi


# Choose a port (default 5678) or pass DEBUG_PORT=xxxx
# Parse KEY=VALUE args
for arg in "$@"; do
  case $arg in
    PORT=*)
      DEBUG_PORT="${arg#PORT=}"
      shift
      ;;
  esac
done
PORT="${DEBUG_PORT:-5678}"

# Activate venv (./.venv symlinks to /netscratch/.../KBExtract)
source ./.venv/bin/activate
echo "🐍 $(python --version) @ $(which python)"
echo "🪲🐞 Debugger will listen on 0.0.0.0:${PORT}"

# Make src/ visible as a top-level package root
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"

# -------- portable port check (no 'ss' dependency) ----------
if ! python - "$PORT" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(("0.0.0.0", port))
    # free immediately; we just wanted the test
    s.close()
    sys.exit(0)
except OSError:
    sys.exit(1)
PY
then
  echo "⚠️ Port ${PORT} appears to be in use."
  # Best-effort diagnostics if tools are present
  if command -v lsof >/dev/null 2>&1; then
    echo "🔎 lsof on :${PORT}:"
    lsof -i TCP:${PORT} || true
  elif command -v fuser >/dev/null 2>&1; then
    echo "🔎 fuser on :${PORT}:"
    fuser -v -n tcp ${PORT} || true
  else
    echo "ℹ️ Install lsof/fuser for more details, or pick another port."
  fi
  echo "👉 Use a free port: DEBUG_PORT=5690 $0"
  exit 1
fi
# -----------------------------------------------------------

# # If the port is busy, show owner and exit nicely
# if ss -ltnp | grep -q ":${PORT} "; then
#   echo "⚠️ Port ${PORT} is already in use:"
#   ss -ltnp | grep ":${PORT} " || true
#   echo "👉 Set DEBUG_PORT to a free port, e.g.: DEBUG_PORT=5690 $0"
#   exit 1
# fi

# Start debugpy and wait for VS Code to attach
# Tip: 0.0.0.0 makes it reachable from the login node for tunneling
# exec python -m debugpy --listen 0.0.0.0:$PORT --wait-for-client -m kbdebugger.main "$@"
exec python -m debugpy --listen 0.0.0.0:$PORT --wait-for-client -m kbdebugger.extractor_main "$@"
