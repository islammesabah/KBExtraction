podman run \
    --rm \
    --device nvidia.com/gpu=0 \
    --security-opt=label=disable \
    docker.io/nvidia/cuda:12.3.1-devel-ubuntu20.04 \
    nvidia-smi