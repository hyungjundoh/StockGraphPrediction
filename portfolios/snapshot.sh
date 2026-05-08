#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/main.json"
[ -f "$SRC" ] || { echo "No main.json to snapshot"; exit 1; }
mkdir -p "$HERE/history"
TS="$(date +%Y-%m-%d_%H%M%S)"
DST="$HERE/history/main_$TS.json"
cp "$SRC" "$DST"
echo "Snapshotted: $DST"
