#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a; source "$ROOT/.env"; set +a
fi

echo ">>> Installing PyTorch with CUDA support..."
pip install torch==2.3.0 torchvision==0.18.0 \
  --index-url https://download.pytorch.org/whl/cu121 -q

echo ">>> Installing backend dependencies..."
cd "$ROOT/backend"
pip install -r requirements.txt -q

echo ">>> Installing frontend dependencies..."
cd "$ROOT/frontend"
npm install --silent

echo ""
echo "Backend  → http://localhost:8000"
echo "Frontend → http://localhost:5173"
echo ""
echo "First run: DeepFashion index will build in the background (~5-15 min)."
echo "Press Ctrl+C to stop."
echo ""

cd "$ROOT/backend"
uvicorn main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

cleanup() {
  echo ""
  echo "Stopping..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
}
trap cleanup INT TERM

wait "$BACKEND_PID" "$FRONTEND_PID"
