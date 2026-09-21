#!/bin/sh
# Start the template generator and open it in a browser.
cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo "No .venv found. Run: python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

PORT="${PORT:-8765}"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Either open http://127.0.0.1:$PORT"
  echo "or stop the other process, or run: PORT=8766 ./run.sh"
  exit 1
fi

( sleep 1.5; open "http://127.0.0.1:$PORT" 2>/dev/null ) &
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
