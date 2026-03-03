#!/bin/bash
set -euo pipefail

echo "🔧 Setting up KBExtraction (local venv + locked deps)..."

# Always run from repo root, even if executed from elsewhere
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Check for Python
if ! command -v python3 &> /dev/null; then
  echo "❌ Python 3 is required but not found."
  exit 1
fi

# Create venv if missing
if [ ! -d "venv" ]; then
  echo "🐍 Creating virtual environment in ./venv ..."
  python3 -m venv venv
else
  echo "✅ Virtual environment already exists."
fi

# Activate venv
# shellcheck disable=SC1091
source venv/bin/activate

echo "⬆️  Upgrading pip tooling..."
python -m pip install --upgrade pip setuptools wheel

# Install deps from lock for reproducibility
if [ ! -f "requirements.lock.txt" ]; then
  echo "❌ requirements.lock.txt not found. Cannot do reproducible install."
  echo "   (Expected file at: $REPO_ROOT/requirements.lock.txt)"
  exit 1
fi

# Ensure pip can resolve torch==...+cpu and torchvision==...+cpu
cat > "$VIRTUAL_ENV/pip.conf" <<'EOF'
[global]
extra-index-url = https://download.pytorch.org/whl/cpu
EOF

echo "📦 Installing dependencies from requirements.lock.txt ..."
if [ -f "constraints.txt" ]; then
  echo "🔒 Using constraints.txt ..."
  python -m pip install -r requirements.lock.txt -c constraints.txt
else
  python -m pip install -r requirements.lock.txt
fi

python -c "import torch; print('torch:', torch.__version__); print('cuda available:', torch.cuda.is_available())"


echo "✅ Setup complete."
echo "👉 Run locally with: ./ui/run.sh"
