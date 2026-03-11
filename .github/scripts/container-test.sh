#!/bin/bash
# Verify the container image starts and responds to MCP requests.

set -euo pipefail

IMAGE="$1"
if [ -z "$IMAGE" ]; then
  echo "Usage: $0 <image>"
  exit 1
fi

if ! podman image exists "$IMAGE"; then
  echo "FAIL: image not found"
  exit 1
fi

REQUEST='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"capabilities":{},"clientInfo":{"name":"test","version":"1.0"},"protocolVersion":"2025-11-25"}}'
OUTFILE=$(mktemp)
PIPE=$(mktemp -u)
mkfifo "$PIPE"

podman run --rm -i "$IMAGE" < "$PIPE" > "$OUTFILE" &
PID=$!

sleep 2
echo "$REQUEST" > "$PIPE"
sleep 5

kill "$PID" || true
wait "$PID" || true
rm -f "$PIPE"

if grep -q '"Release Assistant MCP"' "$OUTFILE"; then
  echo "PASS"
  rm -f "$OUTFILE"
else
  echo "FAIL"
  cat "$OUTFILE"
  rm -f "$OUTFILE"
  exit 1
fi
