# Local Price Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and independently verify Stage C's durable, loopback-only synthetic
price service and separately loadable browser board.

**Architecture:** One Python authority owns SQLite, clock, presence, safety epoch
and proposal decisions. A bounded local HTTP adapter exposes synthetic fixtures
and full snapshots to a separate TypeScript/DOM entry built with existing Vite.

**Tech Stack:** Python 3.12 stdlib sqlite3/http.server, pytest already installed;
Node >=24 direct node:test, TypeScript 7.0.2 and Vite 8.3.5 already locked.

**Spec:** [Exact design and contracts](../specs/2026-11-10-local-price-board-design.md).

**Status:** Prospectively accepted at `b05ce33`; Task 1 implementation is now
independently accepted. Tasks 2–4 remain pending. The user already authorized
autonomous sequential
execution with Sol implementation/Astra review; no new approval loop is added.
Controller must accept and push these docs with accepted result `6c7685c` before
product code. Parent/root controls acceptance, publication and closure.

## Global Constraints

- All exact names, types, reason enums, endpoint/DTO shapes and values are fixed
  by the spec; no alternatives or deferred API decisions.
- New Python code is under repository-local `market/` with `__init__.py`, outside
  `src/fly_connectome_sim/`; no setuptools/package/dependency/lockfile changes.
- Preserve old Python/C++, source/provenance locks, helpers, observations, replay
  index/base/ten-second limits and all current CI tests. No native acquisition,
  provider spend, Stage D/public upload, live worker, deployment or scientific gate.
- Prices are integer Rappen, full range jumps permitted, each changed drink locks
  for 1,800,000 ms from a **postcommit** clock sample. Fresh synthetic proposals
  and primary presence expire at 5000 ms, equality expired. Deadlines are distinct;
  all service durations use the same authority clock.
- One authority lock owns domain/store/presence; only the ingress safety epoch
  uses a second short lock. Newer pause/overload must defeat older resumes.
- Eight HTTP handlers, 8192-byte bodies, 65536-byte JSON responses, 2-second I/O
  timeout, 5-second read deadline; excess connections close and latch pause.
- 10,000 append-only rows total, fixture ceiling 9,000; DB64 MiB/journal72 MiB,
  combined136 MiB. Claim history64/incarnation without eviction.
- Fresh bounded Sol worker per task, independent Astra evidence review before
  progression. Tell each worker they are not alone and must preserve others'
  changes. Workers cannot mutate Git. Controller may group local reviewed source
  commits before final source push/CI; never push protected branches or create PR.
- TDD: write assertions first, run red, implement, run green; retain actual
  commands/output/skips/failures. No real30-minute sleeps or invented review pass.

## Review Focus

- A presence loss detected after tentative activation survives savepoint rollback
  as a durable absent state/generation fence (Task1).
- A later authenticated pause or overload while an older resume commits remains
  effective; only a newer explicit resume clears it (Tasks1/2).
- An absent replacement claim revokes old token/challenge; retired retries and
  claim65 cannot restore or evict accepted ownership history (Tasks1/2).
- A lost commit/HTTP response preserves activation and exact terminal retry,
  including across process death before postcommit anchoring (Tasks1/4).
- A hidden/restarted/disconnected browser cannot refresh presence, overwrite a
  newer incarnation or display a candidate as current price (Tasks3/4).

---

## Before Task1: controller checkpoint

- [x] Independently review both prospective documents against the accepted StageC
  scope and architecture; fix findings without claiming the review already passed.
- [x] Verify branch/tracking `feat/connectome-experiment-core` / origin. Publish
  accepted docs with already accepted result; explicit push only
  `git push -u origin feat/connectome-experiment-core`. No implementation first.
- [x] Record the spec's exact protected preexisting tracked file SHA256 manifest and neural
  `model_fingerprint()` in ignored `.tools/market-local-20261110/`; preserve the
  historical artifact/source manifest from the accepted performance result.
  Record installed Python/SQLite/Node/Vite paths and versions without installing.
- [x] Confirm local Python3.12 explicit transaction mode/PRAGMA behavior and
  `perf_counter` information. Runtime notes already checked Python3.12.14,
  SQLite3.53.1 and explicit BEGIN/ROLLBACK; this is not application verification.
  Inspect installed stdlib HTTP deadline/header hooks and ownership APIs before
  implementing their bounds. Vite8.3.5 uses `build.rolldownOptions`, not the
  deprecated alias. No network/API call is required for implementation preflight.

### Task1: Complete authority, SQLite, clocks, ownership and presence

**Files:** create `market/__init__.py`, `market/price_service.py`,
`market/ownership.py`, `tests/market/conftest.py`,
`tests/market/test_price_service.py`, `tests/market/test_price_clock.py`,
`tests/market/test_price_presence.py`, `tests/market/test_price_storage.py`.

**Interfaces:** Produce every Python dataclass/DTO, `MarketError(code: str)`,
`open_authority(config: MarketConfig, db_path: Path, clock: Clock | None = None)`
and all `PriceAuthority` signatures in the spec. This includes atomic
`run_fixture`, internal `submit_synthetic`, claim/ACK, snapshot, safety ingress,
pause/resume and maintenance, so transport never owns state logic. `close()` is
idempotent and releases DB/OS ownership; context-manager support is allowed but
not consumed by later tasks. Tests provide `FakeClock.sample/describe`, explicit
proposal constructors and `make_present` helpers only in conftest.

- [x] Write failing `test_price_service.py` config/price/terminal tests. Fix
  these assertions by name: `test_full_jump` gives activated400→700 and version1;
  `test_exact_cooldown` uses fresh events at+1,799,999ms (`cooldown`) and
  +1,800,000ms (`activated`); `test_independent_drinks` activates drink01 while00
  is locked; `test_no_change_preserves_anchor` asserts unchanged price_version,
  activation count and deadline; `test_expiry_alone_does_nothing` advances fake
  time and asserts no new activation. Refresh presence with fresh ACKs in boundary
  tests; an expired board must not accidentally mask cooldown assertions.
- [x] Add failing `test_sequence_age_and_reasons`: exact ages -1ns,0,
  4,999,999,999ns,5,000,000,000ns; current-source seq3 consumes high-water,
  seq2 rejects reordered, gaps accepted, old session/generation/config/unknown
  drink/stale drink version/range/off-grid reject with exact first-failure reason.
  Retrying rejected/activated/no_change same digest returns byte-equivalent
  ProposalResult after time, pause and restart; changed digest conflicts without
  advancing high-water. Validate bool money, duplicate IDs, unknown config fields,
  bounds/encoding/names and counters at JSON-safe exhaustion.
- [x] Add failing `test_price_clock.py`: `test_postcommit_anchor_includes_latency`
  delays COMMIT with fake elapsed time and asserts full1800s remains afterward;
  `test_clock_fault_after_commit_preserves_price`, `test_backward_clock_fences`,
  `test_invalid_clock_samples`, `test_utc_jumps_do_not_unlock`,
  `test_repeated_restart_full_lock`. Assert untouched drinks start eligible,
  every previously changed drink starts recovery lock, UTC estimates only label,
  and ceil(remaining_ns/1e6) never rounds toward early eligibility.
- [x] Add failing `test_price_presence.py`: claim→rendered snapshot→ACK is present
  with one revision increment and no ACK loop; read-only polling never replaces
  challenge; revision change rejects old ACK; expiry equality fences once before
  reconnect even without maintenance; no snapshot issuance renews lease.
  `test_awaiting_ack_timeout_and_replacement` expires exactly5000ms without
  generation fence, replaces token/challenge, rejects retired ID superseded;
  `test_claim_history_bound` accepts64 replacements, rejects65 claim_capacity,
  retains current retry/ACK and rejects stale-incarnation retry before history.
- [x] Add failing `test_savepoint_retains_presence_fence`: inject expiry between
  tentative activation and final check; assert rejected result, no activation,
  durable absent state, generation/revision increment exactly once, consumed
  sequence and immutable request mapping after reopen. Inject persistence failure
  separately and assert in-memory activation fence remains latched.
- [x] Add failing safety tests with threading barriers:
  `test_later_pause_defeats_resume_before_commit` and
  `test_later_pause_defeats_resume_during_commit` capture old ingress_epoch,
  block resume, request newer safety pause, release; assert snapshot.paused true,
  newer generation before subsequent activation, ResumeReply preserves historical
  result plus superseding_reason and only a newly captured resume can clear.
  Also assert repeated pause changes neither revision nor generation once reconciled.
- [x] Add failing `test_price_storage.py`: explicit rollback leaves no accepted
  request/event mapping; fixture worst-case row reservation enforces9000 limit;
  control reserve reaches10000 without eviction; full-ledger pause still works
  with audit_recorded false; failed durable pause returns durable false and
  storage latch. Validate64MiB page cap, refusal of oversize existing DB/journal,
  bounded journal envelope, SQLite-full failure, malformed/incompatible DB and
  exact reopen config. Two authority objects cannot own one DB on different ports.
- [x] Run red: `.venv/Scripts/python.exe -m pytest -q tests/market/test_price_service.py tests/market/test_price_clock.py tests/market/test_price_presence.py tests/market/test_price_storage.py`.
  Record actual missing-implementation/assertion failures; no skip replacing red.
- [x] Implement minimal complete spec behavior. Keep all transaction/clock/presence
  state in authority. Use real SQLite tests with injectable clock and monkeypatch
  private `_commit_transaction() -> None` /
  `_anchor_committed_activation(drink_id: str) -> None` only as deterministic
  commit barriers; production hooks have no external control route. Reapply
  detected presence transitions after savepoint rollback. Pause ingress epoch
  must remain available while a long authority operation holds its lock.
- [x] Run the same command green, inspect all failures/skips, and inspect SQL
  constraints/PRAGMA results on actual runtime. Controller obtains independent
  Astra review of source and evidence; fix findings with red/green regression.
  Controller alone creates the reviewed local Task1 checkpoint, explicit paths.

### Task2: Synthetic factory, bounded local HTTP and CLI

**Files:** create `market/fixtures.py`, `market/local_server.py`,
`scripts/run-market-price-service.py`, `examples/market-synthetic.json`,
`tests/market/test_price_fixtures.py`, `tests/market/test_price_http.py`.

**Interfaces:** consume Task1's complete authority/types, no SQL in adapter.
Produce `parse_scenario(payload: object) -> FixtureScenario`,
`load_config(path: Path) -> MarketConfig`,
`create_server(authority: PriceAuthority, host: str, port: int, assets_dir: Path)
-> LocalMarketServer`, and CLI `main(argv: list[str] | None = None) -> int`.
Server provides `serve_forever/shutdown/server_close`, `operator_url: str`,
`view_url: str`, explicit bounded static map and capabilities. Both parser
functions live in `market/fixtures.py`. Use the spec's seven exact API paths/bodies/response shapes
and HTTP mapping. Task1 generates Proposal only within `run_fixture` transaction.

- [ ] Write failing `test_price_fixtures.py`: exact20-row example and strict
  four-field scenario parser; same request/digest yields original event/outcome
  after restart; changed scenario conflicts; factory rollback creates no accepted
  mapping; client cannot provide source/clock/sequence/model fields. Assert real
  synthetic labels and no raw-proposal endpoint.
- [ ] Write failing `test_price_http.py` with actual loopback sockets and temporary
  built-asset fixtures: exact Host/Origin/bearer role matrix; read-only no claim
  or challenge; primary cannot operator-resume; wrong-incarnation claim409,
  superseded retry409 and claim_capacity503; immutable terminal responses200;
  JSON/field/status errors per spec; single-event lookup only and404 unknown.
  Verify no mutations occur on malformed/auth/framing failures.
- [ ] Add boundary cases8192/8193-byte body,65536-byte response cap, duplicate
  JSON keys/Content-Length, transfer encoding, missing length, header16KiB/64-field
  and request-line2048 bounds, slow headers/body total5s and socket2s timeout.
  Tests use bounded <=6s socket waits, not arbitrary sleeps. Validate path/query,
  symlink/traversal rejection, manifest allowlist, no replay/manifest/source map
  access, no-store/CSP/security headers and absence of credentials/body in logs.
- [ ] Add `test_eight_handlers_overload_latches_pause`: hold all8 handlers at
  read barriers, open ninth, assert socket closes, price unchanged and immediate
  effective pause without ninth handler. Drain; assert it stays paused. Add
  `test_overload_defeats_older_resume_during_commit` using Task1 barriers and
  actual HTTP ingress; only a fresh authenticated resume restores eligibility.
  Do not assert a successful pause HTTP reply while slots are saturated.
- [ ] Add actual HTTP lease/restart/lost-response tests: current replacement
  invalidates old bearer/challenge, read-only poll cannot steal challenge,
  missed heartbeat fences before next maintenance, GET never renews, successful
  commit with dropped response retries same fixture ID without another change.
- [ ] Run red: `.venv/Scripts/python.exe -m pytest -q tests/market/test_price_fixtures.py tests/market/test_price_http.py`.
- [ ] Implement parser/adapter/CLI. Capture resume safety epoch at authenticated
  ingress and request pause/overload latch immediately; all long state work calls
  authority. Maintenance cadence100ms. Validate CLI host/port/assets before
  starting, acquire authority ownership, and close gracefully on Ctrl+C/failure.
  Parse actual Vite manifest-reachable market entry only; tests' tiny asset tree
  exercises the same loader used later by actual dist.
- [ ] Run green: `.venv/Scripts/python.exe -m pytest -q tests/market`.
  Independently review transport/storage/safety interactions with Astra before
  controller's explicit-path local checkpoint. Record runtime/deadline limitations.

### Task3: Standalone TypeScript/DOM board and existing Vite build

**Files:** create `market/web/protocol.ts`, `market/web/state.ts`,
`market/web/render.ts`, `market/web/main.ts`, `market/web/style.css`,
`viewer/market.html`, `viewer/src/market-entry.ts`, `viewer/vite.config.ts`,
`viewer/tests/market-protocol.test.mjs`, `viewer/tests/market-state.test.mjs`,
`viewer/tests/market-render.test.mjs`; modify `viewer/tsconfig.json` include only.

**Interfaces:** protocol exports the exact spec DTO TypeScript types and
`parseSnapshot(value: unknown): Snapshot`, `parseProposalResult(value: unknown):
ProposalResult`, `parseResumeReply(value: unknown): ResumeReply` throwing Error
on invalid wire data. `state.ts` exports `BoardState` with
`snapshot: Snapshot|null`, `connectionGeneration: number`,
`receivedAtMs: number|null`, `unknown: boolean`,
`primarySession: {session_id: string; primary_token: string}|null`;
`createState(): BoardState`, `disconnect(state: BoardState): BoardState`,
`applySnapshot(state: BoardState, snapshot: Snapshot, receivedAtMs: number,
connectionGeneration: number): BoardState`,
`isFresh(state: BoardState, nowMs: number): boolean`.
`renderBoard(root: HTMLElement, state: BoardState, nowMs: number): void` uses
textContent and semantic DOM. `startBoard(root: HTMLElement): () => void` owns
fetch/visibility/poll timers, credentials and operator event handlers; return
function aborts and removes them. Main invokes startBoard on the dedicated root.

- [ ] Write failing Node tests, direct imports from `../../market/web/*.ts`:
  strict DTO numeric/enums/schema limits; unknown before data; fresh at4999ms,
  unknown at5000; lower revision and old connectionGeneration ignored; new
  connection full snapshot establishes new incarnation, increments the connection
  generation and clears primary session; every older operator/ACK response is ignored.
  `test_hidden_and_disconnect_stop_ack` uses injected browser/fetch test doubles
  around startBoard; assert one in-flight serial poll/render/ACK, no hidden ACK,
  resume/visibility full reload and ignored late aborted responses.
- [ ] Add DOM tests via small explicit DOM test double (no dependency install):
  escaped hostile drink names remain literal, all20 prices visible in configured
  order, monetary400 rendersCHF4.00, recovery/eligibility copy, no zero placeholders,
  no candidate-as-active row, historical result doesn't replace newer snapshot,
  accepted resume with superseding pause remains visibly paused. Tokens are
  fragment-only, removed immediately, never storage/query/log content; read-only
  mode has no operator secrets/controls. Unknown mutation result keeps same
  request ID for retry, deliberate new action receives a fresh ID.
- [ ] Run red from viewer: `node --test tests/market-*.test.mjs`.
- [ ] Implement the exact interfaces and visual direction from the spec. Keep
  browser clocks only for local freshness/countdowns, never authority decisions.
  Handle ACK's self-transition snapshot without an ACK loop. Disable hidden/
  disconnected writes, retain dated last-known prices and explicit unknown label.
  Vite multi-entry retains index/base; manifest and narrow fs.allow use verified
  local Vite API. No package.json/lock changes or replay parser imports.
- [ ] Run green from viewer: `node --test tests/market-*.test.mjs`, `npm test`,
  `npm run build`. Inspect actual generated market.html/manifest asset graph;
  with Python adapter serve only that market graph. Record complete old viewer
  test counts/skips and retain existing import/replay behavior.
- [ ] Controller opens actual built board locally and checks20-row wide/narrow,
  keyboard/contrast/reduced motion, claim→render/ACK→resume→fixture400→700,
  no_change/rejection feedback, hide/disconnect/reconnect and read-only view.
  Record browser/version and actual observed result; this browser check belongs
  to controller, never an unsupported claim by a worker. Astra reviews source,
  tests and actual evidence before controller's explicit-path local checkpoint.

### Task4: Cross-process recovery, CI, operator docs and closure

**Files:** create `tests/market/test_price_process.py`,
`docs/experiments/2026-11-10-local-price-board.md`; modify
`.github/workflows/compatibility.yml`, `docs/getting-started.md`,
`docs/cloud-handover.md` and `README.md` only for actual accepted status/commands.
Controller owns final handover/README acceptance and publication.

**Interfaces:** consume prior server/CLI/domain/board unchanged. Tests launch
`scripts/run-market-price-service.py` with bounded temporary DB/assets/ports and
process pipes; no synthetic clock override becomes a public CLI/HTTP option.
Test helper child processes may import authority and barriers directly for
deterministic crash timing. Subprocesses have explicit <=15s cleanup deadlines
and owned-process termination; do not kill unrelated processes.

- [ ] Write failing subprocess tests: two live authorities same DB/different
  port reject ownership on Windows/POSIX; normal stop releases; killed owner
  releases without lock deletion; exact prices/versions/results persist. Kill
  child after real COMMIT before anchor, reopen, assert activation durable,
  startup paused/new incarnation and full recovery cooldown. Lost HTTP result
  followed by restart/same request ID returns original result, not a fresh event.
  Assert fixtures cannot import/execute native package and unrelated PIDs survive.
- [ ] Run red `.venv/Scripts/python.exe -m pytest -q tests/market/test_price_process.py`;
  implement only necessary integration fixes and tests. Green the same command
  plus `.venv/Scripts/python.exe -m pytest -q tests/market`. Record actual Windows
  ownership evidence; POSIX equivalent runs in CI, never label unrun platform passed.
- [ ] Add a separate15-minute Ubuntu24.04 `market_price` CI job reusing existing
  pinned checkout/setup-uv/Python3.12.14 and locked test environment. Exact new
  command `uv run --no-sync python -m pytest -q tests/market` includes all seven test files;
  record Python/SQLite/clock identity, run without MaleCNS data/provider credentials.
  Existing native and market_buffers job commands remain byte-for-byte unchanged;
  existing viewer `npm test` discovers market-*.test.mjs and builds both entries.
  Preserve all prior CI paths: native's export-anatomy, market-feasibility,
  market-motor-readout, continuous-drive, motor-readout-v2, continuous-motor-probe,
  drive-input-comparison, population-excursion-screen, both motor/drive supervisors,
  market-response-diagnostic, response-structure, response-supervisor, cell-activity,
  native-build, named checkpoint/replay tests, session-workflow, event-proposals,
  event-followup, recorder-limits and CLI; market_buffers' live-buffers,
  live-buffer-performance and live-buffer-supervisor. No exclusions or weakened gates.
- [ ] Document exact operator commands from spec: viewer `npm run build`; CLI
  `--config examples/market-synthetic.json --db .tools/market-local/state.sqlite3
  --host 127.0.0.1 --port 8765 --assets viewer/dist`; local opening fragments,
  primary claim/ACK, explicit resume, fixture/retry, pause, restart recovery and
  Ctrl+C stop. Explain lost commit visibility, safety pause under overload,
  full30-minute restart lock and last-known unknown board. Do not commit real
  capabilities, DBs, generated assets/screenshots or raw artifacts.
- [ ] Controller runs actual bounded synthetic local workflow and complete
  relevant regressions, preserves outputs under `.tools/market-local-20261110/`,
  compares the spec's protected original source/helper/lock SHA256 manifest and
  `model_fingerprint()` unchanged, and independently verifies old artifacts
  without rewriting them. Experimental report distinguishes fake-clock proofs,
  actual process/HTTP/browser observations and unavailable checks; no soak/load,
  neural integration, sales/public-event or science claim.
- [ ] Obtain final independent Astra review of complete source/evidence/diff,
  repair actionable findings with regression tests, and controller inspects full
  staged diff/size with explicit first-party paths only. Create reviewed source
  checkpoint and explicit feature push; await final CI jobs to terminal outcome,
  recording actual run link/SHA/counts/skips/failures. Do not claim cancelled or
  unavailable CI passed. Grouped source push avoids canceling preceding task runs.
- [ ] Controller updates handover/current TODO/report at reviewed checkpoint with
  actual browser/Windows/Linux CI evidence and limitations, commits/pushes docs
  as appropriate. Under the user's ongoing authorization, continue to the next
  separately specified technical stage after its evidence gate; do not infer
  permission for PR, merge, deployment or additional acquisition from this stage.

## Plan self-check

Task 1 is independently accepted after one review correction round: 95 tests
passed without skips in 8.24 s on Windows. Public-method regressions now preserve
the capacity fence across immediate restart and later clock/storage failures;
closed proposal methods return the domain error. Independent re-review verified
late capacity after tentative activation and failed fence persistence too. Linux,
HTTP and browser checks remain for their later tasks. The CI command uses the
same `python -m pytest` entry as local verification, making the repository-local
`market/` import explicit without changing package installation or test coverage.

Spec coverage maps authority/clock/presence/safety/store to Task1, fixture/HTTP
bounds to Task2, board/build to Task3 and process/CI/docs to Task4. Later tasks
consume the exact spec DTOs and Task1 methods; they cannot add competing clock,
presence or proposal-admission logic. All five Review Focus items have explicit
tests. Independent prospective review accepted the design and plan after correcting
the shared-clock wording. Implementation checkboxes remain open; no implementation
or test success is inferred.
