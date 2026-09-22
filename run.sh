#!/bin/sh
# Build the static site and serve it locally, exactly as GitHub Pages will.
#
# There is no application server any more: the page carries its own Python.
# It does need to be served over http, though - `file://` blocks the module
# and wheel fetches PyScript relies on.
cd "$(dirname "$0")" || exit 1

PORT="${PORT:-8765}"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Either open http://127.0.0.1:$PORT"
  echo "or stop the other process, or run: PORT=8766 ./run.sh"
  exit 1
fi

( sleep 1.5; open "http://127.0.0.1:$PORT" 2>/dev/null ) &
exec python3 tools/build_site.py _site --serve --port "$PORT"
