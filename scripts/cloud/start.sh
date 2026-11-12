#!/usr/bin/env bash
# Foreground loopback services; Ctrl+C stops the selected service.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
cd "$FLY_CLOUD_ROOT"
mode=${1:-market}
if (( $# )); then shift; fi
case "$mode" in
    market)
        if (( $# > 2 )); then echo 'Usage: start.sh [market [PORT [DATABASE]]]' >&2; exit 2; fi
        port=${1:-8765}
        database=${2:-$FLY_CLOUD_TOOLS/market/state.sqlite3}
        [[ -x .venv/bin/python && -f viewer/dist/market.html ]] || { echo 'Run scripts/cloud/setup.sh first.' >&2; exit 1; }
        exec .venv/bin/python scripts/run-market-price-service.py --config examples/market-synthetic.json --db "$database" --host 127.0.0.1 --port "$port" --assets viewer/dist
        ;;
    viewer)
        if (( $# > 1 )); then echo 'Usage: start.sh viewer [PORT]' >&2; exit 2; fi
        exec npm --prefix viewer run dev -- --host 127.0.0.1 --port "${1:-5173}" --strictPort
        ;;
    *) echo 'Usage: start.sh [market [PORT [DATABASE]] | viewer [PORT]]' >&2; exit 2 ;;
esac
