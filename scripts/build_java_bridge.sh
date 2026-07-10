#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$ROOT/java-bridge/src/main/java"
BUILD_DIR="$ROOT/java-bridge/build/classes"
JAR_PATH="$ROOT/java-bridge/build/tarifmatcher-bridge.jar"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$(dirname "$JAR_PATH")"
javac -encoding UTF-8 -d "$BUILD_DIR" $(find "$SRC_DIR" -name '*.java' | sort)
jar --create --file "$JAR_PATH" --main-class ch.itignos.tarifmatcherbridge.BridgeApplication -C "$BUILD_DIR" .
echo "$JAR_PATH"
