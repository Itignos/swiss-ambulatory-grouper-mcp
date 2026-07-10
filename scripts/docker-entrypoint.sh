#!/usr/bin/env bash
set -euo pipefail

JAVA_BRIDGE_JAR=${JAVA_BRIDGE_JAR:-/app/java-bridge/tarifmatcher-bridge.jar}
BRIDGE_PORT=${BRIDGE_PORT:-8080}
export TARIFMATCHER_BASE_URL=${TARIFMATCHER_BASE_URL:-http://127.0.0.1:${BRIDGE_PORT}}

java ${JAVA_TOOL_OPTIONS:-} -Dfile.encoding=UTF-8 -jar "$JAVA_BRIDGE_JAR" &
JAVA_PID=$!

python -m swiss_ambulatory_grouper_mcp.mcp_server &
PY_PID=$!

terminate() {
  kill "$JAVA_PID" "$PY_PID" 2>/dev/null || true
}
trap terminate TERM INT

wait -n "$JAVA_PID" "$PY_PID"
STATUS=$?
terminate
wait "$JAVA_PID" "$PY_PID" 2>/dev/null || true
exit "$STATUS"
