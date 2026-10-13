#!/usr/bin/env bash
# Start the MCP server (:8000) and the Alexa+ simulator (:8080) together.
set -e
PY="${PYTHON:-python3}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "▶ Starting MCP server on http://127.0.0.1:8000/mcp ..."
"$PY" "$HERE/server.py" --port 8000 &
SRV=$!

echo "▶ Starting Alexa+ simulator on http://127.0.0.1:8080 ..."
"$PY" "$HERE/simulator/simulator.py" --port 8080 --mcp http://127.0.0.1:8000/mcp/ &
SIM=$!

cleanup() { kill "$SRV" "$SIM" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo
echo "Open http://127.0.0.1:8080 in your browser. Ctrl+C to stop."
wait
