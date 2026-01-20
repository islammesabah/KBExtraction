#!/bin/bash

# Parse arguments.
MACHINE_NAME=$1 # Name of the machine to run on.
JOB_NAME=$2 # Name of the job.
NUM_NODES=$3 # Number of nodes to run on.
NUM_TASKS_PER_NODE=$4 # Number of tasks (i.e., workers or processes) per node.
NUM_GPUS_PER_TASK=$5 # Number of GPUs per task.
NUM_CPUS_PER_TASK=$6 # Number of CPUs per task.
MEM=$7 # Total RAM to request.
HOURS=$8 # Time to request in hours.

# User arguments.
shift 8 # This removes the first 8 arguments from the argument list so that $@ contains only user arguments.
ARGS=$@


echo -e "🤗 HF TOKEN: $HF_TOKEN"
echo -e "🤗 HF HOME: $HF_HOME"


# Load environment variables from .env file.
if [ -f .env ]; then
  echo "💡 Loaded .env file."
  source .env # this loads the .env file and exports its variables into the environment
else
  echo "🚨 Error: .env file not found!"
  exit 1
fi


# ---- Ensure we're using the container venv (/venv) ----
if [ -x /venv/bin/python ]; then
  export VIRTUAL_ENV=/venv
  export PATH="/venv/bin:${PATH}"
else
  echo "🚨 Error: /venv/bin/python not found. Are you running inside the kbdebugger.sqsh container?" >&2
  exit 1
fi

echo "🐍 $(python --version) @ $(which python)"
python -c "import sys; print('sys.executable:', sys.executable)"


# ---- Portable hnswlib install (wheelhouse-first, optional rebuild fallback) ----
# Put your wheelhouse on a shared path visible from all nodes:
# e.g. /netscratch/abuali/wheelhouse (recommended) or in the repo if it lives on /home.
WHEELHOUSE="${WHEELHOUSE:-/netscratch/abuali/wheelhouse}"

install_hnswlib_portably() {
  # 1) Prefer installing a prebuilt *portable* wheel you built earlier
  if [ -d "$WHEELHOUSE" ] && ls -1 "$WHEELHOUSE"/*.whl >/dev/null 2>&1; then
    echo "📦 Installing hnswlib from wheelhouse: $WHEELHOUSE"
    python -m pip install --no-index --no-deps --find-links="$WHEELHOUSE" --force-reinstall hnswlib >/dev/null
    python -c "import hnswlib; print('✅ hnswlib ok:', hnswlib.__file__)"
    return 0
  fi

  # 2) If no wheelhouse, try importing; if it fails, rebuild with generic CPU flags
  echo "⚠️ Wheelhouse missing/empty at: $WHEELHOUSE"
  echo "   Trying current hnswlib import (may SIGILL if it was built on a newer CPU)..."

  set +e
  python -c "import hnswlib; print('✅ hnswlib import ok')" >/dev/null 2>&1
  rc=$?
  set -e

  if [ "$rc" -ne 0 ]; then
    echo "🛠️ Rebuilding hnswlib with portable CPU flags (x86-64 generic)..."
    python -m pip uninstall -y hnswlib || true

    export CFLAGS="-O3 -march=x86-64 -mtune=generic"
    export CXXFLAGS="-O3 -march=x86-64 -mtune=generic"

    python -m pip install --no-binary=:all: --no-build-isolation hnswlib
    python -c "import hnswlib; print('✅ hnswlib rebuilt ok:', hnswlib.__file__)"
  fi
}

install_hnswlib_portably
# ---------------------------------------------------------------------------

# python main.py $MACHINE_NAME $JOB_NAME $NUM_NODES $NUM_TASKS_PER_NODE $NUM_GPUS_PER_TASK $NUM_CPUS_PER_TASK $MEM $HOURS $ARGS
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
python -m kbdebugger.main
