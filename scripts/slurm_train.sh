#!/bin/bash

# Load environment variables from .env file.
if [ -f .env ]; then
  source .env
else
  echo "Error: .env file not found!"
  exit 1
fi

# Parse arguments.
# SLURM arguments.
MACHINE_NAME=$1 # Name of the machine to run on.
JOB_NAME=$2 # Name of the job.
NUM_NODES=$3 # Number of nodes to run on.
NUM_TASKS_PER_NODE=$4 # Number of tasks to run 
NUM_GPUS_PER_TASK=$5 # Number of GPUs per task.
NUM_CPUS_PER_TASK=$6 # Number of CPUs per task.
MEM=$7 # Total RAM to request.
HOURS=$8 # Time to request in hours.

# User arguments.
shift 8
ARGS=$@

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
echo -e "Working directory: $WORKDIR"

# Set the docker container to use.
CONTAINER="/netscratch/enroot/nvcr.io_nvidia_pytorch_${NVIDIA_CONTAINER_VERSION}-py3.sqsh"
echo "Container: $CONTAINER"

# Print the job details.
echo -e "Requesting $NUM_NODES nodes, $NUM_TASKS_PER_NODE tasks per node, $NUM_GPUS_PER_TASK GPUs per task, $NUM_CPUS_PER_TASK CPUs per task, $MEM memory per task on $MACHINE_NAME for $HOURS hours"
echo -e "Requested Total GPUs: $TOTAL_GPUS"
echo -e "Requested Total CPUs: $TOTAL_CPUS"
echo -e "Requested Total MEM: $((NUM_NODES * MEM_IN_GB))GB"
echo -e "Requested for TIME : $HOURS hours"
echo -e "\e[34mJob Name: $JOB_NAME\e[0m"


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
bash scripts/install.sh scripts/run.sh $MACHINE_NAME $JOB_NAME $NUM_NODES $NUM_TASKS_PER_NODE $NUM_GPUS_PER_TASK $NUM_CPUS_PER_TASK $MEM $HOURS $ARGS
