srun \
  --time=04:00:00 --immediate=3600 \
  --mem=50000 \
  --gpus=1 \
  -p batch \
  --container-mounts="`pwd`":"`pwd`" \
  --container-image=/netscratch/$USER/containers/trustifai.sqsh \
  --container-mounts=/netscratch/$USER:/netscratch/$USER,/ds:/ds:ro,"`pwd`":"`pwd`" \
  --container-workdir="`pwd`" \
  --pty /bin/bash 


# -p could be V100-16GB or batch 