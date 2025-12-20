#!/bin/bash

# Load environment variables from .env file.
if [ -f .env ]; then
  source .env
  echo "💡 Loaded .env file."
else
  echo "🚨 Error: .env file not found!"
  exit 1
fi

# Parse arguments.
# SLURM arguments.
MACHINE_NAME=$1         # Name of the machine to run on. (e.g., 'batch' or 'H100-DSA')
JOB_NAME=$2             # Name of the job. (e.g., 'my_experiment', 'serialize_magic_brush')
NUM_NODES=$3            # Number of nodes (i.e., physical machines) to run on.
NUM_TASKS_PER_NODE=$4   # Number of tasks to run (i.e., workers or processes) per node.
NUM_GPUS_PER_TASK=$5    # Number of GPUs per task.
NUM_CPUS_PER_TASK=$6    # Number of CPUs per task.
MEM=$7                  # Total RAM (in GB) to request.
HOURS=$8                # Time to request in hours.

# User arguments.
shift 8 # This removes the first 8 arguments from the argument list so that $@ contains only user arguments.
ARGS=$@

# ALL MACHINES is an option to run on all available machines. (CAUTION: This will use all available resources on the cluster!)
ALL_MACHINES="batch,RTX3090,V100-32GB,RTXA6000,RTXA6000-AV,L40S,L40S-AV,A100-40GB,A100-80GB,A100-RP,A100-PCI,H100,H100-RP,H100-PCI,H200"

if [[ "$MACHINE_NAME" == "all" ]]; then
  MACHINE_NAME=$ALL_MACHINES
  echo "Using all machines: $MACHINE_NAME"
fi


# Normalize memory input to handle 'G', 'GB', and no suffix cases
if [[ $MEM == *GB ]]; then
    MEM="${MEM%GB}G"  # Remove 'GB' and replace with 'G'
elif [[ $MEM != *G ]]; then
    MEM="${MEM}G"  # Append 'G' if no suffix is present
fi

# Calculate total resources.
TOTAL_GPUS=$((NUM_NODES * NUM_TASKS_PER_NODE * NUM_GPUS_PER_TASK))
TOTAL_CPUS=$((NUM_NODES * NUM_TASKS_PER_NODE * NUM_CPUS_PER_TASK))
MEM_IN_GB=$(echo $MEM | tr -d 'G')


# Set working directory to where this was executed from.
WORKDIR=$(pwd)
# WORKDIR=$(dirname "$(pwd)")   # if you always run from inside scripts/
echo -e "📂 Working directory: $WORKDIR"

# Set the docker container to use.
# CONTAINER="/netscratch/enroot/nvcr.io_nvidia_pytorch_${NVIDIA_CONTAINER_VERSION}-py3.sqsh"
CONTAINER="/netscratch/abuali/containers/images/kbdebugger.sqsh"

echo "🚢 Container: $CONTAINER"

# Print the job details.
echo -e "🛒 Requesting $NUM_NODES nodes, $NUM_TASKS_PER_NODE tasks per node, $NUM_GPUS_PER_TASK GPUs per task, $NUM_CPUS_PER_TASK CPUs per task, $MEM memory per task on $MACHINE_NAME for $HOURS hours"
echo -e "🚌 Requested Total GPUs: $TOTAL_GPUS"
echo -e "🚗 Requested Total CPUs: $TOTAL_CPUS"
echo -e "🚚 Requested Total MEM: $((NUM_NODES * MEM_IN_GB))GB"
echo -e "⌛ Requested for TIME: $HOURS hours"
echo -e "🏷️  \e[34mJob Name: $JOB_NAME\e[0m"


# Run the job.
srun -K \
-p $MACHINE_NAME \
--job-name $JOB_NAME \
--nodes $NUM_NODES \
--mem "$MEM" \
--ntasks-per-node $NUM_TASKS_PER_NODE \
--gpus-per-task $NUM_GPUS_PER_TASK \
--cpus-per-task $NUM_CPUS_PER_TASK \
--container-image $CONTAINER \
--container-mounts /home:/home,/netscratch:/netscratch,/ds:/ds \
--container-workdir $WORKDIR \
--export "NCCL_SOCKET_IFNAME=bond,NCCL_IB_HCA=mlx5,TERM=linux" \
--time="$HOURS:00:00" \
--immediate=3600 \
--pty \
/bin/bash