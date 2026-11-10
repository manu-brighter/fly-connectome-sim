# Local synthetic price board — prospective design

Status: **prospectively accepted after independent review**. This
document authorizes no implementation by itself and reports no new passing
tests. The controller publishes the accepted design/plan with the accepted
performance result before product implementation. Latest accepted local result
checkpoint is `6c7685c`, one commit after published source `70a73b1`.

## Purpose and boundary

Implement Stage C of the [market plan](../plans/2026-11-09-live-drink-market.md#stage-c--price-service-and-local-test-board):
one durable local price authority, synthetic proposal fixtures and a separate
browser board. The [handover](../../cloud-handover.md) accepts this continuation
after the bounded performance result. No neural worker, measurement-clock
adapter, uploads, provider request, training, public deployment, POS integration
or scientific qualification is included. Staff adoption remains manual in the
broader product; these are explicitly **not sale prices**.

Technical choices here belong to the implementation under the existing
autonomous authorization: Python 3.12 stdlib SQLite/HTTP, plain TypeScript/DOM,
existing Vite 8.3.5/Node >=24 build. No dependencies, setuptools configuration or
neural-package sources change. Preserve every existing replay parser, index
entry, ten-second limit, source lock, historical helper and completed artifact.

## Files and responsibility

- `market/__init__.py`: identifies the separate repository-local Python module.
- `market/price_service.py`: config/types, single authority lock, SQLite ledger,
  clock, ownership, presence, safety fence and all state transitions. An internal
  OS ownership helper may live in `market/ownership.py` with this same owner.
- `market/fixtures.py`: exact synthetic scenario parsing; authority stamps all
  source/session/sequence/clock fields transactionally.
- `market/local_server.py`: bounded loopback HTTP and explicit built asset map.
- `scripts/run-market-price-service.py`: thin CLI invoking that adapter.
- `market/web/{protocol,state,render,main}.ts` and `market/web/style.css`: typed
  wire validation, client state, DOM rendering and browser orchestration.
- `viewer/market.html`, `viewer/src/market-entry.ts`, `viewer/vite.config.ts` and
  `viewer/tsconfig.json`: separate HTML entry using existing dependencies.
- `examples/market-synthetic.json`: labelled immutable twenty-drink fixture.
- `tests/market/`: Python domain, adapter and process tests; board tests remain
  `viewer/tests/market-*.test.mjs` and use existing Node 24 direct TS imports.

## Exact value and wire conventions

JSON objects reject unknown and missing required fields. Integers exclude
booleans. Versions/generation/sequence are integers in `[0, 9007199254740991]`;
sequence begins at 1, overflow fails closed. Money is integer Rappen in
`[1, 1000000]`. IDs match ASCII `[A-Za-z0-9_-]{1,64}`, UUIDs use canonical
lowercase 36-character spelling, digests are 64 lowercase hex characters.
Names contain 1–80 Unicode code points, <=320 UTF-8 bytes and no control
characters. UTC strings use RFC3339 UTC with `Z`; they are labels, never clocks.
Nullable fields are present as JSON `null`. Arrays preserve configuration order.

`MarketConfig = {schema: "market-config-v1", drinks: DrinkConfig[]}` has 10–20
unique drinks. `DrinkConfig = {id: string, name: string, minimum_rappen: int,
maximum_rappen: int, grid_rappen: int, initial_rappen: int}`. Require
`minimum_rappen <= initial_rappen <= maximum_rappen`, endpoints and initial
amount divisible by `grid_rappen`. `config_id` is SHA256 of canonical UTF-8 JSON
(sorted object keys, compact separators, no NaN, `ensure_ascii=False`). Freeze
the exact configuration for a database; mismatch refuses reopening. The example
uses `drink-00`…`drink-19`, names `Testgetränk 01`…`Testgetränk 20`,
minimum/initial 400, maximum 700, grid 50. This is no real event menu.

The shared Python types below are immutable dataclasses; DTOs serialize to the
exact named fields. TypeScript mirrors the JSON shapes without nanosecond fields.

```text
ClockSample(monotonic_ns: int, utc: datetime)
Clock.sample() -> ClockSample
Clock.describe() -> dict[str, str | int | bool]
FixtureScenario(fixture_id: Literal["synthetic-price-v1"], drink_id: str,
                target_rappen: int, expected_drink_version: int)
Proposal(schema: Literal["market-proposal-v1"], event_id: str, request_id: str,
         source_kind: Literal["synthetic_fixture"], source_session: str,
         sequence: int, generation: int, config_id: str,
         readout_version: Literal["synthetic-price-v1"], incarnation: str,
         drink_id: str, target_rappen: int, expected_drink_version: int,
         created_ns: int, model_interval_ms: tuple[int, int] | None,
         recorded_utc: str)
```

Event/source/incarnation IDs are UUIDs; request IDs follow the ASCII ID rule.
`created_ns` is a nonnegative signed SQLite 64-bit integer, internal only.
`model_interval_ms`, when supplied by tests, has ordered JSON-safe nonnegative
endpoints; the production fixture uses `None`. It never establishes freshness.
Digest every Proposal field using the same canonicalization, tuple as JSON array.

Exact public DTOs (`int`/`string` here mean the bounded JSON forms above):

```text
Fault = null | "clock" | "storage" | "capacity" | "overload"
PrimaryState = "unclaimed" | "awaiting_ack" | "present" | "absent"
Challenge = {id: UUID, incarnation: UUID, session_id: UUID, revision: int,
             expires_in_ms: int}
PriceRow = {id: string, name: string, minimum_rappen: int, maximum_rappen: int,
            grid_rappen: int, initial_rappen: int, current_rappen: int,
            drink_version: int, last_activation_id: UUID|null,
            recorded_utc: string|null, remaining_lock_ms: int,
            estimated_eligible_utc: string|null, recovery_lock: boolean}
Snapshot = {schema: "market-snapshot-v1", incarnation: UUID, revision: int,
            price_version: int, config_id: digest, generation: int,
            paused: boolean, fault: Fault, primary_state: PrimaryState,
            server_utc: string, rows: PriceRow[], challenge: Challenge|null}
ProposalResult = {event_id: UUID, request_id: string,
                  status: "activated"|"no_change"|"rejected", reason: string,
                  activation_id: UUID|null, terminal_revision: int,
                  terminal_price_version: int, drink_version: int|null,
                  current_rappen: int|null}
PauseReply = {paused: true, durable: boolean, fault: Fault, revision: int,
              audit_recorded: boolean}
ControlResult = {command_id: string, status: "accepted"|"rejected",
                 reason: string, terminal_revision: int}
ResumeReply = {result: ControlResult, snapshot: Snapshot,
               superseding_reason: null|"operator_pause"|"overload"}
ClaimReply = {session_id: UUID, primary_token: string, snapshot: Snapshot}
AckReply = {accepted: boolean, reason: string, snapshot: Snapshot}
ApiError = {error: string}
```

`reason` is a closed enum: successful ProposalResult reasons are `activated` and
`no_change`; terminal rejections are `clock`, `storage`, `capacity`, `overload`,
`wrong_config`, `wrong_source`, `wrong_incarnation`, `wrong_generation`,
`reordered`, `future_proposal`, `expired`, `unknown_drink`, `stale_drink_version`,
`paused`, `board_absent`, `out_of_range`, `off_grid`, `cooldown`.
Internal validation failures raise `MarketError("invalid_request")` without
ledger writes; duplicate changed payload raises `idempotency_conflict` without
sequence consumption. Unknown drink uses result `drink_version=null`,
`current_rappen=null`; every result for a known drink has its actual integer
version/current amount. No synthetic default price enters a board row.
Resume reasons are `resumed`, `clock`, `storage`, `capacity`, `board_absent`,
`superseded`; an already unpaused healthy resume returns `resumed` without a
transition. ACK reasons are `acknowledged`, `unknown_session`, `invalid_challenge`,
`expired_challenge`, `stale_revision`. Other MarketError codes are `not_found`,
`unauthorized`, `wrong_incarnation`, `primary_busy`, `superseded`, `claim_capacity`, `ownership`,
`config_mismatch`, `clock`, `storage`, `capacity`. Failed durable storage cannot
invent a terminal result: raise `storage`, preserving the in-memory pause latch.

## Authority contract and persistence

```text
open_authority(config: MarketConfig, db_path: Path,
               clock: Clock | None = None) -> PriceAuthority
PriceAuthority.close() -> None
PriceAuthority.snapshot(primary_session: str | None = None) -> Snapshot
PriceAuthority.run_fixture(request_id: str, scenario: FixtureScenario) -> ProposalResult
PriceAuthority.submit_synthetic(proposal: Proposal) -> ProposalResult
PriceAuthority.get_event(event_id: str) -> ProposalResult
PriceAuthority.request_safety_pause(reason: Literal["operator_pause", "overload"]) -> int
PriceAuthority.capture_safety_epoch() -> int
PriceAuthority.pause(*, safety_epoch: int | None = None) -> PauseReply
PriceAuthority.resume(request_id: str, *, ingress_epoch: int) -> ResumeReply
PriceAuthority.claim_primary(incarnation: str, request_id: str) -> ClaimReply
PriceAuthority.resolve_primary_token(token: str) -> str | None
PriceAuthority.ack_primary(session_id: str, challenge: str) -> AckReply
PriceAuthority.maintain() -> None
```

`primary_session` is an already authenticated session ID, not an arbitrary client
declaration. The adapter resolves bearer tokens against the authority's current
session credentials using `resolve_primary_token`; replaced credentials cannot
remain in an adapter cache. Resolve under the authority lock with constant-time
comparison and return only the current session ID or None. Snapshot/ACK recheck
current session while holding that same authority lock, so replacement between
resolution and use cannot issue a challenge or renew the retired session.
Snapshot supplied a retired/unknown session raises `unauthorized`.
All price, presence, source,
version, ledger and DB operations share **one authority lock** and explicit
transactions. One separate short safety-epoch lock protects ingress only; never
hold it while waiting for the authority lock. No transport lease-check/activate
gap is permitted. `submit_synthetic` is fixture/test-only, never an HTTP route.

Use `sqlite3.connect(..., autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL,
isolation_level=None, check_same_thread=False)` and explicit SQL
`BEGIN IMMEDIATE`, `COMMIT`, `ROLLBACK`. Set foreign keys, `synchronous=FULL`,
`busy_timeout=1000`, `journal_mode=DELETE`, `cache_spill=OFF`,
`page_size=4096`, `max_page_count=16384`; forbid WAL/ATTACH. Constrain tables
`market`, `drinks`, `activations`, `proposal_results`, `source_state`,
`fixture_requests`, `control_results` with CHECK/UNIQUE/FK declarations. Fixed
tables have one market/source and <=20 drinks. Activations record old/new amounts,
proposal/config/readout/session/incarnation identity, UTC record time and
`cooldown_policy="postcommit-1800s-restart-full-v1"`.

The sum of append-only fixture_requests/proposal_results/activations/control_results
is capped at 10,000 rows. Fixture operations use only the first 9,000; reserve
1,000 for controls. Reserve the candidate's worst-case rows before any write.
Never evict deduplication history. DB <=64 MiB, rollback journal <=72 MiB,
combined <=136 MiB; check existing files and the installed SQLite journal-envelope
assumptions (one transaction, one preimage per page plus headers/checksums).
`journal_size_limit` alone is not a transient quota. Faults latch activation off.

Hold an exclusive stdlib Windows `msvcrt.locking` / POSIX `fcntl.flock` lock on
`<database filename>.owner.lock` for the process lifetime, before DB opening.
Process death releases ownership. Do not unlink locks or trust PID files. A
second authority fails, even on another port. Refuse broken/existing incompatible
DBs instead of silently initializing replacement state.

Startup persists pause, advances generation/revision, creates a new incarnation
and source session, clears transient primary/challenge/claim state and retains
all durable prices, versions, outcomes and IDs. Initial prices create no ledger
activation or cooldown. `revision` changes for actual price/control/presence
transitions; `price_version` changes only on activation. Countdown/UTC ticks do
not change either. Terminal revisions in stored results never become current
snapshot substitutes. No timer, retry or elapsed cooldown activates anything.

## Clock, transaction order and safety priority

Default Clock uses `time.perf_counter_ns()` and UTC datetime. On startup require
`get_clock_info('perf_counter')` monotonic, nonadjustable and resolution <=1 ms;
record its implementation/resolution in local startup diagnostics without tokens.
Backward, unavailable, non-integer or invalid clock reads latch `clock`, fence
sessions and forbid activation. No UTC repair or subtraction across incarnations.
UTC jumps do not change eligibility. OS monotonic correctness is a trust
assumption; detection is not independent clock attestation.

A changed drink gets an in-memory deadline **after COMMIT returns**, while still
holding the authority lock: fresh sample +1,800,000,000,000 ns. Only then may any
operation observe it. Eligibility is `now >= deadline`; remaining milliseconds
round upward. Every previously activated drink receives a complete fresh
1800-second recovery lock at every restart, regardless of UTC/downtime. Never
changed drinks remain eligible. Mark `recovery_lock`; clear it on the next actual
activation. An eligible drink has remaining 0 and eligible estimate null.
Postcommit clock failure preserves the activation but stops acceptance; recovery
applies. The transaction's UTC label is not a measured storage-completion instant.

For a new proposal: bounded validation, authority lock, BEGIN IMMEDIATE,
synchronize expiry/safety, fixture/event idempotency lookup, fault check,
config/source/incarnation/generation checks, sequence, age, drink/version,
operator pause, board present, range/grid, equal-price no-op, cooldown. The first
failure is final. Age must be `0 <= now-created_ns < 5000000000`; equality expires.
Valid current-source sequences above high-water are consumed for terminal
outcomes after identity checks, including age/version/pause/range/cooldown
rejections. Gaps are allowed. Old session/malformed/conflicting messages cannot
advance current high-water. Reordered messages are terminal and cannot lower it.

Duplicate same event/digest returns original before current freshness/generation
checks. Fixture request/digest is looked up **before generating** an event; a
retry across restart returns the same original outcome. Changed scenario conflicts.
Creation of event/session/sequence/time and request→event→terminal result mapping
commits atomically with any activation. Rollback accepts no request. Never send
terminal success before durable commit.

Before COMMIT, refresh clock and expiry; recheck fault/generation, age, pause,
presence and cooldown. Roll tentative activation back to a savepoint on failure,
then commit only rejection/consumed sequence/request mapping **and any recognized
presence-loss generation/revision transition**. Reapply that transition exactly
once if the savepoint rollback removed it. The in-memory fence survives storage
failure. Assert durable absent state/generation in tests. A slow COMMIT can cross
a lease or later pause: keep its durable activation, anchor cooldown, then fence
subsequent work. Lost responses cannot undo prices. Same-drink attempts serialize;
different drinks have no global cooldown.

Actual pause/resume, restart and present→absent advance acceptance generation.
Pause is idempotent, takes no request ID, and never requires ledger room: persist
the fixed paused flag; audit only when room exists. On storage failure return
`paused=true,durable=false,fault="storage"`. Capacity cannot be cleared by resume.
Resume requires healthy storage, fresh board and durable ID/result; no proposal
from before the transition can execute afterward.

Authenticated pause ingress and overload immediately increment a short safety
epoch and latch pause. Resume captures epoch at authenticated ingress; compare
under authority lock and before COMMIT. Clear latch only by atomic compare-and-clear
of that same epoch **after COMMIT**. A newer safety event prevents an older resume
clearing it, including while COMMIT is blocked. Reconcile newer latch into durable
pause/generation before another activation. Persist the immutable ControlResult;
ResumeReply adds a **fresh** snapshot and superseding reason on every retry.
Historical acceptance is never represented as a guarantee of current unpaused
state. An overload latch can clear only through a newer explicit healthy resume.

## Primary presence

States: unclaimed → awaiting_ack → present → absent. An authenticated new claim
is accepted only while unclaimed/absent. Awaiting_ack expires at claim+5 seconds,
equality expired; becoming absent here does not fence. Replacement revokes the
previous token/challenge, issues a new session/token and awaiting_ack deadline.
Present→absent alone increments generation/revision and invalidates pending
proposals/challenge once; repeated absent polls do nothing. The current absent
session may rejoin with a newly rendered valid challenge. Replacement makes old
tokens unusable. Keep <=64 accepted claim request IDs per incarnation without
eviction: current retry returns its session; retired retry is `superseded`;
claim 65 is `claim_capacity`. Reject old incarnation before history replay.

Primary snapshots replace the single outstanding challenge, bound to current
incarnation/session/revision, lifetime 5 seconds. Read-only snapshots have
challenge null and cannot replace it. ACK synchronizes expiry **first**, validates
the existing challenge/revision, then transitions awaiting_ack/absent→present,
increments revision once, consumes challenge and returns post-transition snapshot
without another challenge. Self-caused revision does not invalidate this ACK.
Present→present renews without revision increment. Changes before ACK reject it.
Presence deadline is valid ACK sample+5 seconds, equality expired; issuing or
sending a snapshot never renews it. Synchronize expiry on every operation and
100 ms maintenance tick; reconnect before the next tick cannot evade fencing.

## Loopback transport and asset boundary

`create_server(authority: PriceAuthority, host: str, port: int,
assets_dir: Path) -> LocalMarketServer`; `serve_forever()`, `shutdown()`,
`server_close()` provide bounded lifetime and ownership cleanup. Read-only
properties `operator_url: str` and `view_url: str` provide the two opening URLs
to CLI output and local tests. `market.fixtures.load_config(path: Path) ->
MarketConfig` parses the exact configuration schema. The CLI is
`.venv/Scripts/python.exe scripts/run-market-price-service.py --config examples/market-synthetic.json --db .tools/market-local/state.sqlite3 --host 127.0.0.1 --port 8765 --assets viewer/dist`.
Use `.venv/bin/python` on Linux. Reject every host except `127.0.0.1`; port is
1–65535. Print two local opening URLs: `/market.html#operator=<capability>` and
`/market.html#view=<capability>`, distinct 32-byte `secrets.token_urlsafe` tokens.
These URLs are explicit local operator output; never include them in request
logs, reports or committed docs. Primary token is a third distinct capability.
JS consumes/removes fragment once and retains credentials in memory only.
No cookies, browser snapshot persistence, CORS or external content.

Exact Host is `127.0.0.1:<port>`; supplied Origin must equal
`http://127.0.0.1:<port>`, mandatory on every POST including CLI automation.
Bearer read capability permits GET snapshot/result; primary bearer permits those
GETs with challenge and primary ACK; operator bearer permits GETs and
claim/pause/resume/fixture. Operator GET has challenge null. Claim carries the
session token to its operator browser; read-only clients never receive it.

| Method/path | Exact JSON body | Success |
| --- | --- | --- |
| GET `/api/snapshot` | none | Snapshot |
| GET `/api/events/<event_id>` | none | ProposalResult |
| POST `/api/primary/claim` | `{incarnation, request_id}` | ClaimReply |
| POST `/api/primary/ack` | `{session_id, challenge}` (challenge ID) | AckReply |
| POST `/api/pause` | `{}` | PauseReply |
| POST `/api/resume` | `{request_id}` | ResumeReply |
| POST `/api/fixtures` | `{request_id, scenario}` | ProposalResult |

All success/domain terminal replies use HTTP 200, including rejected proposals,
rejected resume and rejected ACK; errors use ApiError. Exact HTTP error mapping:
400 invalid_request/invalid_http; 401 unauthorized; 403 forbidden_origin or
forbidden_host; 404 not_found; 405 method_not_allowed; 408 request_timeout;
409 idempotency_conflict/wrong_incarnation/primary_busy/superseded;
411 length_required; 413 body_too_large; 415 unsupported_media_type;
431 headers_too_large; 503 clock/storage/capacity/claim_capacity.
Malformed protocol errors and socket closures never become terminal ledger rows.

Eight handlers maximum, body <=8192 bytes, JSON response <=65536 bytes,
socket I/O timeout 2 seconds, total request-read deadline 5 seconds. Reject
duplicate/ambiguous Content-Length, any Transfer-Encoding, non-UTF8/non-JSON,
duplicate JSON keys, invalid constants, unknown keys, and >16384 header bytes or
>64 header fields; request line <=2048 bytes. Close on framing errors; never
stream bodies. Saturation closes excess sockets **and immediately latches
effective pause**; no ninth/reserved pause handler or guarantee that every HTTP
pause request succeeds. Draining does not resume. Maintenance persists safety
pause when the authority lock becomes available.

Serve `/market.html` and only manifest-reachable market JS/CSS/assets via an
explicit startup map. Do not expose replay index, Vite manifest, source maps,
directory listing, symlinks, traversal, raw runs or arbitrary files. Reject
query-bearing API/static URLs. JSON/static responses use `Cache-Control: no-store`,
`X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and CSP
`default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'`.
Never log request bodies, Authorization or fragments.

## Browser board

Separate Vite entry: `viewer/src/market-entry.ts` imports
`../../market/web/main.ts`; keep `index.html` entry and existing base unchanged.
Vite config uses verified `build.rolldownOptions.input` for both HTML entries,
`build.manifest=true`, explicit dev filesystem access limited to viewer and
market/web; extend tsconfig include to `../market/web`. Verify actual manifest
output paths before wiring authority assets. No replay/science-parser imports.

One serial primary loop: GET full snapshot → validate → render with textContent
→ ACK → accept/render returned snapshot → next poll after 1000 ms. A read-only
view polls without ACK. Stop ACK when hidden/disconnected; immediately display
`Letzter bekannter Stand — aktuell unbekannt`. Independently expire local display
freshness after 5000 ms via browser monotonic time. Abort/invalidate older requests
with a connection generation; reject old-generation/incarnation or lower-revision
responses. `disconnect` increments the connection generation; accepting a new
incarnation also increments it, invalidating every older pending operator/ACK
response, and clears old session/challenge state. A fresh full snapshot can
establish that new incarnation. Do not compare revision numbers across incarnations.
No stored snapshots between reloads. Unknown before first successful snapshot;
retain full dated last-known rows afterward. Clock countdowns estimate eligibility
only and cannot activate/change prices or renew presence. Separate the last
fixture outcome from current rows; a historical activated result cannot overwrite
a newer snapshot. Operator controls claim, pause, resume and submit exact fixture;
new request IDs per deliberate action, same ID for an uncertain-response retry.

Visual direction: existing lab-blue identity, paper `#E7EFF4`, ink `#172B3A`,
board `#15384B`, focus `#2456D6`, increase `#98512C`, decrease `#23676A`.
Bahnschrift/Aptos/Segoe UI local stack, tabular CHF amounts, names 18–22 px,
prices clamp 28–44 px, supporting text 14–16 px. Wide 16:9 uses two aligned
semantic lists, <=10 rows each; narrow screens one list. Text/arrows supplement
colors, visible keyboard focus, reduced-motion respecting brief activation
highlight. One connection/pause banner, quiet versions/change/eligibility labels,
collapsible operator section. Permanent copy: `Lokaler Testbetrieb`,
`Testvorschläge, keine Verkaufspreise.` and
`Synthetischer lokaler Test — keine Verkaufspreise / keine Neuronendaten`.
Recovery rows show `Sicherheitswartezeit nach Neustart`. No decorative neural
graphs, fake measurements or claim of simultaneous physical display/POS updates.

## Evidence and execution boundary

The [four-task plan](../plans/2026-11-10-local-price-board.md) assigns fresh Sol
implementers and independent Astra review at each meaningful gate. Controller
owns real-browser verification, final closure/handover, Git and publication.
Workers do not mutate Git. Prospective docs must be accepted/pushed before
implementation. Actual test logs retain failures/skips/unavailable dependencies;
interrupted reviews are not acceptance. Source-bearing tasks may use local
reviewed commits before one final source push/CI to avoid cancellation churn.

Use injected clock tests for the 30-minute and five-second boundaries; no real
30-minute sleep. Real SQLite/process restart, ownership death, finite local HTTP
checks, actual browser interaction and preserved complete CI suites establish
their own limited claims. Capture unchanged neural package `model_fingerprint()`
and SHA256 manifest of all preexisting tracked files under `src/`, `scripts/`,
`tests/`, `viewer/src/`, `viewer/tests/`, plus `pyproject.toml`, `uv.lock`,
`viewer/package.json`, `viewer/package-lock.json`, `viewer/index.html`,
`THIRD_PARTY.md` and `licenses/stonkfly-MIT.txt` before and after work. This
protected baseline excludes the explicitly planned docs/CI/tsconfig edits and
new files. Compare historical artifact manifests without rewriting artifacts.
No test here establishes a 12-hour soak, event throughput, neural integration or
public readiness. Existing separate research qualifications stay unchanged.
