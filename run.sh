#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Kova ==="

# Check for API key
if ! grep -q "ANTHROPIC_API_KEY=sk-" "$SCRIPT_DIR/.env" 2>/dev/null; then
  echo "⚠  Add your Anthropic API key to .env before starting."
  echo "   ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

# Create/update Python venv
if [ ! -f "$SCRIPT_DIR/backend/.venv/bin/python3" ]; then
  echo "📦 Creating Python virtual environment..."
  python3 -m venv "$SCRIPT_DIR/backend/.venv"
fi
if ! "$SCRIPT_DIR/backend/.venv/bin/python3" -c "import fastapi" 2>/dev/null; then
  echo "📦 Installing Python dependencies..."
  "$SCRIPT_DIR/backend/.venv/bin/pip" install -r "$SCRIPT_DIR/backend/requirements.txt" -q
fi

# Install frontend deps if needed
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
  echo "📦 Installing frontend dependencies..."
  cd "$SCRIPT_DIR/frontend" && npm install --cache /tmp/npm-cache -q
fi

echo "🚀 Starting backend on http://127.0.0.1:8000"
cd "$SCRIPT_DIR/backend"
.venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "🚀 Starting frontend on http://localhost:5173"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

sleep 2
echo ""
echo "✅ Kova is running!"
echo "   Open: http://localhost:5173"
echo "   Press Ctrl+C to stop"
echo ""

# Open browser
open "http://localhost:5173" 2>/dev/null || true

# Cleanup on exit
trap "echo ''; echo 'Stopping Kova...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait $BACKEND_PID $FRONTEND_PID
