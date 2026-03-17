#!/bin/bash
set -euo pipefail

echo "🚀 Deploying to Hugging Face Space..."

# Resolve paths
DEV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HF_ROOT="${DEV_ROOT}/../kbdebugger-demo-hf"

# Check HF repo exists
if [ ! -d "$HF_ROOT/.git" ]; then
  echo "❌ HF repo not found at: $HF_ROOT"
  echo "   Clone it first:"
  echo "   git clone https://huggingface.co/spaces/faris-abuali/kbdebugger-demo kbdebugger-demo-hf"
  exit 1
fi

# Sync files (exclude binaries and unnecessary dirs)
echo "📂 Syncing files..."
rsync -av --delete \
  --exclude ".git/" \
  --exclude "venv/" \
  --exclude "__pycache__/" \
  --exclude ".pytest_cache/" \
  --exclude "logs/" \
  --exclude ".env" \
  --exclude "docs/" \
  --exclude "data/" \
  --exclude "notebooks/" \
  --exclude "ui/static/img/" \
  --exclude "README.md" \
  "$DEV_ROOT/" "$HF_ROOT/"

# Commit and push
cd "$HF_ROOT"

echo "📝 Committing changes..."
git add -A
git commit -m "Deploy $(date -Iseconds)" || echo "No changes to commit."

echo "📤 Pushing to Hugging Face..."

# Try the safe force first (protects against overwriting unexpected remote updates)
if git push --force-with-lease; then
  echo "✅ Pushed with --force-with-lease."
else
  echo "⚠️  --force-with-lease failed (likely remote moved and local didn't fetch)."
  echo "   Falling back to plain --force for deploy mirror..."
  git push --force
  echo "✅ Pushed with --force."
fi

echo "✅ Deployment complete."