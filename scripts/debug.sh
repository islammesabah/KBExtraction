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



# Use the container venv (this image already has /venv and PATH set)
# IMPORTANT: do NOT activate ./ .venv here, because that points to your old netscratch venv.
# # Activate venv (./.venv symlinks to /netscratch/.../KBExtract)
# # source ./.venv/bin/activate
if [ -x /venv/bin/python ]; then
  export VIRTUAL_ENV=/venv
  export PATH="/venv/bin:${PATH}"
else
  echo "🚨 Error: /venv/bin/python not found. Are you running inside the kbdebugger.sqsh container?" >&2
  exit 1
fi


echo "🐍 $(python --version) @ $(which python)"


# # ------------------ Portable hnswlib install (wheelhouse) ------------------
# # Goal: avoid SIGILL when SLURM places you on a different CPU node.
# # One-time: build a portable wheel into ./.wheelhouse (see scripts/build_portable_wheels.sh).
# # Every run: reinstall from wheelhouse quickly and deterministically.

# WHEELHOUSE="${WHEELHOUSE:-/netscratch/abuali/wheelhouse}"
# NUMPY_PIN="${NUMPY_PIN:-1.26.4}"

# install_hnswlib_from_wheelhouse() {
#   if [ -d "$WHEELHOUSE" ] && ls -1 "$WHEELHOUSE"/hnswlib-*.whl >/dev/null 2>&1; then
#     echo "📦 Installing hnswlib from wheelhouse: $WHEELHOUSE (no deps)"
#     python -m pip install --no-index --no-deps --find-links="$WHEELHOUSE" --force-reinstall hnswlib >/dev/null
#     python -m pip install --force-reinstall "numpy==${NUMPY_PIN}" >/dev/null || true
#     python -c "import hnswlib, numpy as np; print('✅ hnswlib:', hnswlib.__file__); print('✅ numpy:', np.__version__)"
#   else
#     echo "⚠️ Wheelhouse missing/empty at: $WHEELHOUSE"
#     echo "   Build once with: python -m pip wheel --no-build-isolation --no-binary=:all: --no-deps -w $WHEELHOUSE hnswlib"
#   fi
# }

# install_hnswlib_from_wheelhouse
# # --------------------------------------------------------------------------


# print which venv got activated (great for debugging)
python -c "import sys; print('sys.executable:', sys.executable)"

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
exec python -m debugpy --listen 0.0.0.0:$PORT --wait-for-client -m kbdebugger.main "$@"
