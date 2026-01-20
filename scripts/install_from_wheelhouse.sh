#!/usr/bin/env bash
set -euo pipefail

WHEELHOUSE="${WHEELHOUSE:-$(pwd)/.wheelhouse}"

python -m pip install --no-index --find-links="$WHEELHOUSE" --force-reinstall hnswlib
python -c"import hnswlib; print('✅ hnswlib ok:', hnswlib.__file__)"

echo"✅ Installed hnswlib from wheelhouse: $WHEELHOUSE"

# **How you use it:**

# 1. On *any* node where building works (ideally the *oldest CPU* you might get):
#     `bash scripts/build_portable_wheels.sh`
    
# 2. Later, on any node/container:
#     `bash scripts/install_from_wheelhouse.sh`
    
# Because you built a wheel with generic CPU flags, it should be portable across nodes.