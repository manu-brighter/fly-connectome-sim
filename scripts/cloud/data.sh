#!/usr/bin/env bash
# Optional locked data preparation only; never starts a simulation or test suite.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
cd "$FLY_CLOUD_ROOT"
if [[ "${1:-}" != --download-and-prepare || $# != 1 ]]; then
    echo 'Usage: data.sh --download-and-prepare' >&2
    echo 'Downloads approximately 1.1 GB and prepares the full locked graph; no simulation.' >&2
    exit 2
fi
[[ -x .venv/bin/python ]] || { echo 'Run scripts/cloud/setup.sh first.' >&2; exit 1; }
export FLY_CONNECTOME_SIM_DATA="$FLY_CLOUD_ROOT/data/malecns-v1.0/runtime"
export FLY_CONNECTOME_SIM_FULL_TEST=''
export PYTHONPATH='' PYTHONHOME=''
.venv/bin/python - <<'PY'
from pathlib import Path
import shutil

minimum = 8 * 1024**3
free = shutil.disk_usage('.').free
available = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
# A cgroup quota can be lower than the host's MemAvailable (Codex Cloud/Docker).
for root in (Path('/sys/fs/cgroup'), Path('/sys/fs/cgroup/memory')):
    for limit_name, used_name in (('memory.max', 'memory.current'), ('memory.limit_in_bytes', 'memory.usage_in_bytes')):
        limit, used = root / limit_name, root / used_name
        if limit.is_file() and used.is_file() and limit.read_text().strip() != 'max':
            available = min(available, max(0, int(limit.read_text()) - int(used.read_text())))
print(f'Preflight: {free / 1024**3:.2f} GiB disk free; {available / 1024**3:.2f} GiB memory available', flush=True)
if free < minimum or available < minimum:
    raise SystemExit('Data preparation requires at least 8 GiB free disk and 8 GiB available memory. This is a cautious minimum, not a capacity guarantee.')
PY
node scripts/download-connectome.mjs
.venv/bin/python -m fly_connectome_sim.data verify-sources data/malecns-v1.0
.venv/bin/python -m fly_connectome_sim.data stage data/malecns-v1.0
.venv/bin/python -m fly_connectome_sim.neural.connectome malecns_v1
.venv/bin/python -m fly_connectome_sim.neural.prepare
.venv/bin/python -m fly_connectome_sim.data verify-prepared
