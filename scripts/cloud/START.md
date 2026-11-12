# Start skill: Fly Exchange Linux development

Work from the checked-out `fly-connectome-sim` repository. Read `AGENTS.md` and
`docs/codex-cloud.md`. Verify the branch is `feat/connectome-experiment-core`,
origin is `https://github.com/manu-brighter/fly-connectome-sim.git`, and inspect
status/HEAD before editing. Preserve uncommitted work.

Source `scripts/cloud/env.sh` in each new command shell. Confirm Python 3.12.14,
uv 0.12.15, Node 24.21.0 and npm 11.19.0. If missing, run
`bash scripts/cloud/setup.sh`. If prepared data is needed but absent, explicitly
run `bash scripts/cloud/data.sh --download-and-prepare`; this prepares data only.
Check data with `.venv/bin/python -m fly_connectome_sim.data verify-prepared`.

For synthetic price-board UI work, run `bash scripts/cloud/start.sh market` in
the foreground (default loopback 127.0.0.1:8765 and persistent ignored database
`.tools/cloud/market/state.sqlite3`). Keep opening role links private. Start is
paused; claim primary, await ACK/presence, then explicitly resume. Stop with
Ctrl+C and verify owned process/listener ended. Do not delete ownership locks.
Use a disposable DB for tests: `bash scripts/cloud/start.sh market PORT DB_PATH`.

For viewer development, run `bash scripts/cloud/start.sh viewer` (loopback 5173).
Use an existing authenticated cloud preview/desktop if offered; localhost on
the phone does not access the VM. Do not create a public tunnel or deployment.

Run the CI-equivalent groups with `bash scripts/cloud/check.sh all`, or select
`native`, `market_buffers`, `market_price`, `viewer`. This uses fresh isolated
data-free exports and retains logs under `.tools/cloud/logs/`. Report actual
passes/failures and skips. No automatic fullgraph runs. Native image/live service
is Windows-only; do not weaken gates or substitute a simulator. Keep assay parked.

Resume this same task across devices; new tasks have separate files. Commit and
push reviewed first-party work only to the feature branch. Do not assume a
Default task survives two weeks of inactivity or that scripts publish a cloud
environment. Environment Save draft/Publish is a separate product action.
