#!/usr/bin/env bash
# Launch the Expense Splitter app and open it in the browser.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet pypdf >/dev/null 2>&1 || true
(python3 -m src.server) &
SERVER_PID=$!
sleep 1
open http://localhost:8000 || true
wait $SERVER_PID
