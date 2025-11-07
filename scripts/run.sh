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

# Load environment variables from .env file.
if [ -f .env ]; then
  echo "💡 Loaded .env file."
  source .env # this loads the .env file and exports its variables into the environment
else
  echo "🚨 Error: .env file not found!"
  exit 1
fi

echo -e "🤗 HF TOKEN: $HF_TOKEN"
echo -e "🤗 HF HOME: $HF_HOME"

# export HF_TOKEN=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

# Activate the virtual environment.
source ./.venv/bin/activate # Because ./.venv now symlinks to /netscratch/abuali/envs/KBExtract
# # fallback in case the symlink didn't work
# source "$VENV_DIR/bin/activate"
echo -e "🐍 Using $(python --version) ($(which python))"

# python main.py $MACHINE_NAME $JOB_NAME $NUM_NODES $NUM_TASKS_PER_NODE $NUM_GPUS_PER_TASK $NUM_CPUS_PER_TASK $MEM $HOURS $ARGS
python -m src.main
