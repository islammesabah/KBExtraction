#!/usr/bin/env bash
set -euo pipefail

# Build wheels into a local wheelhouse that you can reuse on any node
WHEELHOUSE="${WHEELHOUSE:-$(pwd)/.wheelhouse}"
mkdir -p"$WHEELHOUSE"

# Conservative CPU flags so wheels run on older CPUs too
export CFLAGS="${CFLAGS:- -O3 -march=x86-64 -mtune=generic}"
export CXXFLAGS="${CXXFLAGS:- -O3 -march=x86-64 -mtune=generic}"

# Avoid build isolation (HPC indexes often block fetching build deps)
python -m pip wheel --no-build-isolation --no-binary=:all: -w"$WHEELHOUSE" hnswlib

echo"✅ Built wheels in: $WHEELHOUSE"
ls -lh"$WHEELHOUSE"

