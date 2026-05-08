#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LATEST="$(ls -t "$HERE"/history/main_*.json 2>/dev/null | head -1 || true)"
[ -n "$LATEST" ] || { echo "No snapshots yet. Run ./portfolios/snapshot.sh first."; exit 1; }
echo "Comparing: $LATEST  →  $HERE/main.json"
echo ""
diff -u "$LATEST" "$HERE/main.json" || true
