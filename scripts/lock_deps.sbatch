#!/bin/bash
#SBATCH --job-name=lock-deps
#SBATCH -p batch
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH -o /home/abuali/projects/KBExtraction/lockdeps-%j.out
#SBATCH -e /home/abuali/projects/KBExtraction/lockdeps-%j.err

set -euo pipefail

cd /home/abuali/projects/KBExtraction

# Use a clean venv just for pip-tools so we don't fight system-site-packages
python -m venv .lockenv
source .lockenv/bin/activate
python -m pip install -U pip setuptools wheel pip-tools

# Compile with logging to a file in the project dir
python -m piptools compile requirements.in \
  --resolver=backtracking \
  --output-file requirements.lock.txt \
  --upgrade \
  --index-url https://pypi.org/simple \
  2>&1 | tee pip_compile.log

echo "✅ Wrote requirements.lock.txt"
ls -lh requirements.lock.txt
