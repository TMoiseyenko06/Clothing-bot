#!/usr/bin/env bash
# Run this on Vast.ai (or any remote GPU instance).
# Serves everything from a single port — no Vite dev server needed.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a; source "$ROOT/.env"; set +a
fi

PORT="${PORT:-8000}"

echo ">>> Installing PyTorch with CUDA (cu121)..."
pip install torch==2.3.0 torchvision==0.18.0 \
  --index-url https://download.pytorch.org/whl/cu121 -q

echo ">>> Installing backend dependencies..."
pip install -r "$ROOT/backend/requirements.txt" -q

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
