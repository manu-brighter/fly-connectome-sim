#!/usr/bin/env bash
# Reproduce the four compatibility.yml jobs with fresh source exports/environments.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
cd "$FLY_CLOUD_ROOT"
selection=${1:-all}
if (( $# > 1 )); then echo 'Usage: check.sh [all|native|market_buffers|market_price|viewer]' >&2; exit 2; fi
case "$selection" in
    all) jobs=(native market_buffers market_price viewer) ;;
    native|market_buffers|market_price|viewer) jobs=("$selection") ;;
    *) echo 'Usage: check.sh [all|native|market_buffers|market_price|viewer]' >&2; exit 2 ;;
esac
command -v timeout >/dev/null || { echo 'GNU timeout is required for the 15-minute job bounds.' >&2; exit 1; }
[[ "$(uv --version)" =~ ^uv\ 0\.12\.15([[:space:]]|$) ]]
[[ "$(node --version)" == v24.21.0 ]]
[[ "$(npm --version)" == 11.19.0 ]]
mkdir -p "$FLY_CLOUD_TOOLS/logs"
run=$(mktemp -d "$FLY_CLOUD_TOOLS/logs/check-$(date -u +%Y%m%dT%H%M%SZ).XXXXXX")
work=$(mktemp -d "$FLY_CLOUD_TOOLS/check.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
# Include current first-party edits; exclude .tools, runtime, dependencies and all
# other ignored artifacts. Keep one snapshot so every job tests identical bytes.
git ls-files --cached --others --exclude-standard -z > "$run/files.list"
tar --null -T "$run/files.list" -cf "$work/source.tar"
sha256sum "$work/source.tar" > "$run/source.sha256"
git rev-parse HEAD > "$run/checkout.txt"
git status --short >> "$run/checkout.txt"

cloud_check_job() {
    local job=$1 directory=$2
    cd "$directory"
    unset VIRTUAL_ENV
    export UV_PROJECT_ENVIRONMENT="$directory/.venv"
    export UV_NO_CACHE=true UV_PYTHON_DOWNLOADS=never
    export FLY_CONNECTOME_SIM_FULL_TEST='' FLY_CONNECTOME_SIM_CXX='' PYTHONPATH='' PYTHONHOME=''
    export FLY_CONNECTOME_SIM_DATA="$directory/.tools/ci/runtime"
    if [[ "$job" == market_price ]]; then
        export FLY_CONNECTOME_SIM_DATA="$directory/.tools/ci/market-price/runtime"
    fi
    mkdir -p "$(dirname "$FLY_CONNECTOME_SIM_DATA")"
    mkdir "$FLY_CONNECTOME_SIM_DATA"
    cat /etc/os-release
    uname -a
    uv --version
    if [[ "$job" == viewer ]]; then
        node --version
        npm --version
        cd viewer
        npm ci
        npm test
        # The package build includes tsc --noEmit, then the Vite production build.
        npm run build
        return
    fi
    if [[ "$job" != market_price ]]; then
        command -v c++
        c++ --version
        uv sync --locked --extra test --extra media --python 3.12.14
    else
        uv sync --locked --extra test --python 3.12.14
    fi
    if [[ "$job" == market_price ]]; then
        uv run --no-sync python - <<'PY'
import json
import os
from pathlib import Path
import sqlite3
import sys
from market.price_service import SystemClock

runtime = Path(os.environ['FLY_CONNECTOME_SIM_DATA']).resolve()
assert runtime.is_dir() and not any(runtime.iterdir()), runtime
assert not any(name == 'fly_connectome_sim' or name.startswith('fly_connectome_sim.') for name in sys.modules)
print(sys.version)
print(f'Python executable: {sys.executable}')
print(f'SQLite: {sqlite3.sqlite_version}')
print(f'Empty runtime: {runtime}')
print(json.dumps(SystemClock().describe(), sort_keys=True))
PY
        uv run --no-sync python -m pytest -q -ra tests/market
        return
    fi
    uv run --no-sync python - <<'PY'
import json
import os
from pathlib import Path
import sys

runtime = Path(os.environ['FLY_CONNECTOME_SIM_DATA']).resolve()
assert runtime.is_dir() and not any(runtime.iterdir()), runtime
import av
import fly_connectome_sim
from fly_connectome_sim.neural.checkpoint import model_fingerprint
from fly_connectome_sim.neural.common import DATA

package = Path(fly_connectome_sim.__file__).resolve()
assert package == (Path.cwd() / 'src/fly_connectome_sim/__init__.py').resolve(), package
assert DATA == runtime, DATA
print(sys.version)
print(f'Python executable: {sys.executable}')
print(f'Package: {package}')
print(f'PyAV: {av.__version__}')
print(f'Empty runtime: {runtime}')
print(json.dumps(model_fingerprint(), sort_keys=True))
PY
    if [[ "$job" == market_buffers ]]; then
        uv run --no-sync pytest -q -ra \
            tests/test_market_live_buffers.py \
            tests/test_live_buffer_performance.py \
            tests/test_live_buffer_supervisor.py
    else
        # Keep this exact selection in sync with compatibility.yml's native job.
        uv run --no-sync pytest -q -ra \
            tests/test_export_anatomy.py \
            tests/test_market_feasibility.py \
            tests/test_market_motor_readout.py \
            tests/test_market_continuous_drive.py \
            tests/test_market_motor_readout_v2.py \
            tests/test_continuous_motor_probe.py \
            tests/test_drive_input_comparison.py \
            tests/test_population_excursion_screen.py \
            tests/test_continuous_motor_supervisor.py \
            tests/test_drive_input_supervisor.py \
            tests/test_market_response_diagnostic.py \
            tests/test_response_structure.py \
            tests/test_market_response_supervisor.py \
            tests/experiment/test_cell_activity.py \
            tests/test_native_build.py \
            tests/test_checkpoint.py::test_evolved_emitted_checkpoint_replays_with_native_kernel \
            tests/experiment/test_replay.py::test_native_qualification_context_maps_and_single_factory \
            tests/experiment/test_session_workflow.py \
            tests/experiment/test_event_proposals.py \
            tests/experiment/test_event_followup.py \
            tests/experiment/test_recorder_limits.py \
            tests/test_cli.py
    fi
}
export -f cloud_check_job
result=0
for job in "${jobs[@]}"; do
    directory="$work/$job"
    mkdir "$directory"
    tar -xf "$work/source.tar" -C "$directory"
    printf 'Running %s; log: %s/%s.log\n' "$job" "$run" "$job"
    if timeout --signal=TERM --kill-after=30s 15m bash -c 'set -euo pipefail; cloud_check_job "$@"' _ "$job" "$directory" 2>&1 | tee "$run/$job.log"; then
        printf '%s PASS\n' "$job" | tee -a "$run/summary.txt"
    else
        code=${PIPESTATUS[0]}
        printf '%s FAIL (exit %s; 124 means 15-minute timeout)\n' "$job" "$code" | tee -a "$run/summary.txt"
        result=1
    fi
    rm -rf -- "$directory"
done
printf 'Logs retained at %s\n' "$run"
exit "$result"
