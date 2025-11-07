srun \
  --time=04:00:00 --immediate=3600 \
  --mem=50000 \
  --gpus=1 \
  -p V100-16GB \
  --container-mounts="`pwd`":"`pwd`" \
  --container-image=/netscratch/enroot/nvcr.io_nvidia_pytorch_24.11-py3.sqsh \
  --container-mounts=/netscratch/$USER:/netscratch/$USER,/ds:/ds:ro,"`pwd`":"`pwd`" \
  --container-save=/netscratch/$USER/containers/trustifai.sqsh \
  --container-workdir="`pwd`" \
  --pty /bin/bash 

# pip freeze | grep -v file:// > Cluster/requirements.txt