#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DASHBOARD_DIR="$REPO_ROOT/dashboard"
OUT_DIR="$DASHBOARD_DIR/out"
STATIC_DIR="$REPO_ROOT/llmscope/static"

echo "==> Building Next.js dashboard..."
cd "$DASHBOARD_DIR"
npm ci --prefer-offline
npm run build

echo "==> Copying build output to llmscope/static/..."
rm -rf "$STATIC_DIR"
mkdir -p "$STATIC_DIR"
cp -r "$OUT_DIR/." "$STATIC_DIR/"

echo "==> Dashboard build complete: $STATIC_DIR"
