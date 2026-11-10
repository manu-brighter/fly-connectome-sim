# Local synthetic price board — bounded software result, 2026-11-10

Status: All four tasks and the complete local implementation/evidence are
independently accepted. Feature publication and actual new-source Linux CI remain
pending. This is a synthetic local price-service demonstration,
not sale prices, neural integration, training or scientific qualification.

The [accepted design](../superpowers/specs/2026-11-10-local-price-board-design.md)
and [implementation plan](../superpowers/plans/2026-11-10-local-price-board.md)
define the exact contract. Follow the [operator instructions](../getting-started.md#local-synthetic-drink-price-board)
to build and open it. The authority lives separately under `market/`; the existing
Python/C++ package, dependencies, provenance locks and replay entry remain intact.

## What the bounded implementation establishes

One OS-owned SQLite authority records integer-Rappen prices, immutable fixture
request/results and activations atomically. A full-range CHF4.00→7.00 jump is
allowed. Every actual change locks only that drink for at least1800 seconds from
a fresh postcommit monotonic sample. No-change, countdown expiry or retry cannot
activate a price. Restart retains prices/versions/results, starts paused with a
new incarnation and opening capabilities, and assigns every previously activated
drink a full fresh30-minute recovery lock. Unchanged drinks start eligible.

Primary presence requires a rendered current snapshot followed by its ACK;
five-second equality is expired. Explicit pause and HTTP overload fence later
acceptance, including older in-flight resume operations. Eight handlers, bounded
request/response sizes and finite socket deadlines are exercised locally. The
board retains dated last-known prices when unknown; these are not confirmation
of current server state. Staff adoption and physical display/POS synchronization
are outside this local technical test.

## Executed evidence and platform separation

| Evidence | Actual result | Scope |
| --- | --- | --- |
| Task1 final authority/clock/presence/storage suite |95 passed,0 skipped,8.24s on Windows |Real SQLite, injected clocks and deterministic transaction/safety barriers; independently accepted after fixes |
| Task2 final complete Market suite |177 passed,1 skipped,27.14s on Windows |Actual finite loopback HTTP, framing/deadlines, overload and transport races; independent source/evidence acceptance |
| Task3 final market viewer tests |23 passed,0 skipped |Independent focused execution plus original activation-cue regression/reproduction |
| Task3 final complete viewer suite |270 passed,0 skipped,57368.7891ms |Controller host run on corrected source;247 existing cases plus23 market cases |
| Task3 build |Exit0 |Both HTML entries retained; market-only manifest graph served; existing replay chunk-size warning retained |
| Task4 final process-only suite |4 passed,0 skipped,2.20s on Windows |Real CLI child processes, ownership/release, crash after COMMIT before anchor, lost HTTP result then restart |
| Task4 complete Market suite |181 passed,1 skipped,29.85s on Windows |All seven price test files, including the four new process cases |
| New Ubuntu24.04 `market_price` job |Configured; not yet executed/accepted |POSIX ownership and Linux symlink assertions remain pending actual source CI |

The Windows skip is `test_symlink_assets_rejected`: creating the test symlink
fails with WinError1314 because this account lacks the privilege. Rejection code
and assertions remain unchanged; no skip stands in for Linux execution. These
results do not relabel earlier failures or skips: Task3's earlier complete run
reported267 passes/1 skip; the final approved host run includes the formerly
skipped dangling-output-link case and all270 pass.

Local price runtime identity: Python3.12.14, SQLite3.53.1 and
`QueryPerformanceCounter()`, monotonic=true, adjustable=false,100ns resolution.
This records the installed clock assumption, not independent clock attestation.

### Real process boundaries

The process tests invoke the actual CLI script with temporary configuration-bound
databases, tiny valid manifest assets, bounded loopback ports and pipes. A child
import guard rejects any `fly_connectome_sim` import; no fixture invokes that
package or a simulator. Every child reports its real PID and executable before
being used. Tests launch the base interpreter directly because Windows venv
`python.exe` is a redirector: an actual diagnostic reported wrapperPID4440 versus
interpreterPID30212. Killing only the wrapper did not establish owner death;
the initially failing test was corrected to target the verified actual child.
No production source, assertion or lock policy was changed for this correction.

Normal CLI shutdown is exercised by a test-only stdin helper injecting
`KeyboardInterrupt` into the real running main loop, then observing exit0 and
reopening the same DB. This is not a physical-console Ctrl+C experiment. Abrupt
shutdown kills only the verified owned interpreter, waits for its termination,
and reopens without deleting/replacing `.owner.lock`. A second live authority on
a different port fails `ownership`. A separately running sentinel survives both
targeted shutdowns; it is then stopped explicitly. All subprocess cleanup has a
shared bound below15 seconds, and a final read-only process inventory found no
remaining interpreter with this test's unique bootstrap/path.

The crash test blocks a child at `_anchor_committed_activation`, after a real
SQLite COMMIT and before any cooldown deadline exists. An independent connection
reads the durable activation and exact result while the child remains blocked.
After killing it, reopening retains the exact price/version/activation/result,
starts paused with a different incarnation and rejects a new change during the
full recovery lock. The exact1,800,000ms assertion uses a frozen test clock after
reopening; the acquisition/COMMIT/crash are real process events. No real30-minute
wait or public clock-override API is used.

The lost-response test sends a real fixture HTTP request without reading its
response. A separate snapshot and SQLite read establish that it committed.
After stopping/restarting the CLI with the same database and newly printed
opening capability, retrying the same request ID/payload returns the field-identical
original result/event. Fixture/result/activation counts remain exactly1/1/1 and
price_version stays1, even though the new authority is paused. This is durable
idempotency, not transparent reconnection using old browser credentials.

### Actual browser observations

The controller used Chromium157 on Windows against the actual immutable Vite
build and fresh bounded local authorities. Claim→render/ACK→resume and all20
individual synthetic selections completed at price_version20, each row CHF7.00.
Actual cooldown rejection, no_change, durable pause, read-only absence of controls,
fragment removal, keyboard focus retention and same-server network recovery
were observed. After six seconds offline, the board retained last-known rows,
marked unknown and disabled all five operator buttons; reconnect restored a full
snapshot. A process restart instead requires its newly printed URL.

Two real layout failures were corrected and retained in the evidence: initial
1920×1080 rows overflowed, then compact all-active rows overflowed because each
repeated a full absolute eligibility timestamp. The final build retains estimated
countdowns/recovery copy and dated overall status. With20 ordinary cooldown rows,
1920×1080 body height is1054px;1280×720 is717px. At390×844, one295px column scrolls
normally with document width375px and no horizontal overflow. Recovery labels,
long names or expanded controls may legitimately increase vertical scrolling.

Measured board text/background contrast is10.623:1 for that color pair; this is
not a complete accessibility audit. Reduced-motion emulation reported animation
none, with the activation direction still visible. Exact1200ms cue retention,
stable row identity and expiry are deterministic render-test/reproduction proofs;
browser timing began before the fresh price snapshot and cannot establish that
duration. Switching headless tabs left both visible, so actual hidden-tab behavior
and real desktop zoom remain unverified; focused unit tests cover hidden-event
abort/no-ACK/late-response rejection. The only incidental pre-shutdown console
error was favicon404. All three bounded servers exited0 and owned tabs closed.

## Preservation, CI and remaining closure

The controller's Task3 staged check found all159 protected original source/helper/
test/dependency files and the41-member native model fingerprint unchanged. Seven
historical native-artifact hashes were unchanged. The controller separately ran
the existing read-only performance `inspect` command successfully, without an
engine, runtime acquisition or rewritten artifacts. Those are controller
preservation checks, not new neural runs by this process-test task. Final Task4
reconciliation confirms263 of270 original tracked files unchanged; the seven
intentional changes are documentation, CI and the viewer include. All64 frozen
helpers,41 packaged source members and seven historical artifacts remain identical.
The offline inspection's decoded result equals the retained summary exactly.

The new independent15-minute Ubuntu24.04 job reuses pinned checkout/setup-uv and
Python3.12.14, installs the locked test extra, records SQLite/clock identity and
runs exactly `uv run --no-sync python -m pytest -q tests/market`. An exact
newline-normalized comparison confirms that all preexisting native/buffer job
text and the viewer job remain unchanged. The viewer's existing `npm test`
discovers market tests and builds both entries. Final independent local review
accepted the complete implementation/evidence, reran all four process cases
(4 passed in2.15s), and verified all27 prior task source hashes,159 protected
original files, seven artifacts and complete old CI command texts. No Linux
success or final source CI link/SHA is claimed before those checks occur.

No MaleCNS acquisition, provider spend, sales/public event, deployment, soak/load,
neural-market integration, biological learning or scientific qualification is
established. The separate research track remains parked.
