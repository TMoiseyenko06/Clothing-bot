#!/usr/bin/env bash
# Run this on Vast.ai (or any remote GPU instance).
# Serves everything from a single port — no Vite dev server needed.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a; source "$ROOT/.env"; set +a
fi

PORT="${PORT:-6006}"

# Install Node.js if missing (Vast.ai instances don't include it)
if ! command -v npm &>/dev/null; then
  echo ">>> Installing Node.js..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

# Only install torch if CUDA isn't already available
# Vast.ai PyTorch templates ship with a newer torch — don't downgrade it
python -c "import torch; assert torch.cuda.is_available(), 'no cuda'" 2>/dev/null \
  && echo ">>> PyTorch with CUDA already present ($(python -c 'import torch; print(torch.__version__)'))" \
  || { echo ">>> Installing PyTorch with CUDA (cu121)..."; \
       pip install torch torchvision \
         --index-url https://download.pytorch.org/whl/cu121 -q; }

# transformer_engine is pre-installed on some Vast.ai images but compiled against
# a different torch ABI — it breaks transformers imports and we don't use it
pip uninstall -y transformer-engine 2>/dev/null || true

echo ">>> Installing backend dependencies..."
pip install -r "$ROOT/backend/requirements.txt" -q --root-user-action=ignore

echo ">>> Installing frontend dependencies..."
cd "$ROOT/frontend"
npm install --silent

echo ">>> Building frontend..."
npm run build

echo ""
echo "============================================"
echo "  Server starting on http://0.0.0.0:$PORT"
echo "  Open http://<instance-ip>:$PORT"
echo ""
echo "  First run: DeepFashion index builds in"
echo "  background (~5-15 min). Check /api/logs."
echo "============================================"
echo ""

cd "$ROOT/backend"
FRONTEND_DIST="$ROOT/frontend/dist" \
  uvicorn main:app --host 0.0.0.0 --port "$PORT"
