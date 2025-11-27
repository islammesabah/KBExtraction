#!/usr/bin/env bash
set -euo pipefail # Exit on error, undefined variable, or error in a pipeline

# 0. Load .env
# Load environment variables from .env file.
if [ -f .env ]; then
  set -a; # automatically export all variables 
  source .env;  # load .env file
  set +a # stop automatically exporting variables
  echo "💡 Loaded .env file."
else
  echo "🚨 Error: .env file not found!" >&2
  # >&2 redirects the output to stderr
  exit 1
fi

# 1. Prepare dirs
mkdir -p "$(dirname "$VENV_DIR")" "$PIP_CACHE_DIR" "$HF_HOME" "$TRANSFORMERS_CACHE"
es0-
# 2. Create venv on /netscratch if missing, reusing container site-packages (torch lives there)
# Install core dependencies, that are sometimes missing from the base image.
if [ -d "$VENV_DIR" ]; then
    # VENV FOUND
    echo -e "💡 Found existing virtual environment at $VENV_DIR | Using $(python --version) ($(which python))"
else
    # NO VENV FOUND, CREATE A NEW ONE
    # 1. Update the image and install the required packages.
    echo -e "🐳 Updating image..."
    apt update
    apt-get update
    apt-get install ffmpeg libsm6 libxext6  -y
    apt install software-properties-common -y
    
    # 2. Create a virtual environment using Python 3.12
    echo -e "💡 [install] Creating virtual environment at $VENV_DIR (Python ${PYTHON_VERSION}) with system site packages"
    # apt install python${PYTHON_VERSION}-venv -y
    # python${PYTHON_VERSION} -m venv venv
    
    # # Prefer builtin venv; fall back if PYTHON_VERSION isn't available as python3.x
    # ( command -v "python${PYTHON_VERSION}" >/dev/null 2>&1 && \
    #     "python${PYTHON_VERSION}" -m venv --system-site-packages "$VENV_DIR" ) \
    #   || python3 -m venv --system-site-packages "$VENV_DIR"

    ## Prefer builtin venv; fall back if PYTHON_VERSION isn't available as python3.x
    # ( command -v "python${PYTHON_VERSION}" >/dev/null 2>&1 && "python${PYTHON_VERSION}" -m venv "$VENV_DIR" ) \
    #   || python3 -m venv "$VENV_DIR"

    # Prefer builtin venv; fall back if PYTHON_VERSION isn't available as python3.x
    apt install python${PYTHON_VERSION}-venv -y
    python${PYTHON_VERSION} -m venv --system-site-packages "$VENV_DIR" \
      || python3 -m venv --system-site-packages "$VENV_DIR"
    # --system-site-packages allows your venv to “see” the container’s preinstalled torch (and other global libs) without re-installing them:
fi

# ⛓️🏷️ 3. Optional symlink so our run.sh file can 'source ./venv/bin/activate'
ln -sfn "$VENV_DIR" .venv

# 4. Activate the virtual environment and install (excluding torch; container provides it)
source "$VENV_DIR/bin/activate"
echo -e "🐍 Using $(python --version) ($(which python))"

# export the following dirs to keep $HOME clean and installs fast.
# export means make the contents of these dirs available to subprocesses
export PIP_CACHE_DIR HF_HOME TRANSFORMERS_CACHE

echo -e "🐍💡 Installing required packages 📍 in $(which python)"
python -m pip install --upgrade pip setuptools wheel
# python -m pip install --upgrade pip
# python -m pip install --upgrade setuptools
# python -m pip install -U wheel
# python -m pip install packaging

if [ -f requirements.txt ]; then
  echo "💡 Installing requirements.txt into $(which python)"
  python -m pip install -r requirements.txt
else
  echo "⚠️ No requirements.txt found; skipping."
fi

# Flash Attention (optional)
# python -m pip install flash-attn==2.5.7 # Install this version of flash-attn as it is torch headless compatible, we upgrade to latest version later (look at the top of the script)
# python -m pip install flash-attn==2.5.8 --no-build-isolation

echo "🐍 Python: $(python --version) 📍 at $(which python)"

# Quick sanity
python - <<'PY' # this means "read the following lines until PY and run them with python"
import torch, sys
print("🕯️ Torch:", torch.__version__, "| CUDA available?", torch.cuda.is_available())
print("🕯️ Torch CUDA:", getattr(torch.version, "cuda", None))
PY

# # Run the training.
# start=`date +%s`
# SCRIPT=$1
# shift 1
# ARGS=$@
# bash $SCRIPT $ARGS
# end=`date +%s`
# echo -e "Job took $((end-start)) seconds."

# # Deactivate the virtual environment.
# deactivate
