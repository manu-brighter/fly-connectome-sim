# Matched-state image-response diagnostic

Status: prospective protocol for the approved live-market continuation. No new
fullgraph observation has run under this protocol. Source, supervisor and frozen
manifest review precede one bounded acquisition. This is not the parked learning
assay or an event-market qualification.

## Question and interpretation

Do fixed visual inputs produce reproducible differences in the recorded KC
cohort and DNa02 readouts from the same complete model state? The
[historical screen](../../experiments/2026-11-09-market-kc-screen.md) found strong
absolute-count dominance and sampled recruitment near two seconds. It does not
establish a universal latency or show that all useful input differences are absent.

This diagnostic measures input-dependent counts, not beverage semantics, learning,
twenty independent channels, a price policy, real-time capacity or twelve-hour
operation. A null means no difference detected in the declared windows under
these conditions, not that longer or other observations can never respond.

## Fixed inputs and timeline

RGB frames are exactly 64×64×3 `uint8`. White is `(255,255,255)` and black
`(0,0,0)`. Coordinates use row first, column second, zero-based. No resizing,
randomness, external image files, compression or learned preprocessing.

| ID | Definition |
| --- | --- |
| black | All pixels black |
| A | Columns 0–31 white, columns 32–63 black |
| B | Columns 0–31 black, columns 32–63 white |
| C | Rows 0–31 white, rows 32–63 black |
| D | Rows 0–31 black, rows 32–63 white |

A–D have identical whole-frame RGB and linear-luminance averages. Retinal sample
locations can produce different receptor-level brightness: do not claim receptor
drive is matched. A/B and C/D are spatial comparisons; each against black combines
spatial and brightness changes.

One fresh `FlyEngine.from_prepared_graph()`; initialize a passive observer before
any advance. Advance black for exactly 2,000 ms in four 500-ms observations, then
save a complete common checkpoint. Black is neither a reset nor a proven settled
baseline; normal lamina bias, neural state and passive decay remain active.

Restore that same complete checkpoint before **every** arm, then advance its
unchanged frame for 4,000 ms in eight 500-ms observations:

| Order | Arm ID | Frame |
| ---: | --- | --- |
| 1 | control-1 | black |
| 2 | vertical-left | A |
| 3 | vertical-right | B |
| 4 | vertical-left-repeat | A |
| 5 | control-2 | black |
| 6 | horizontal-top | C |
| 7 | horizontal-bottom | D |
| 8 | horizontal-top-repeat | C |

Total actual advancement: **2 + 8×4 = 34 model seconds**, 68 observe calls,
3,400 original 10-ms bins. Prefix model time is 0–2 s; every arm covers 2–6 s.
These are branched continuations, not one continuous event session. Do not sum
their final timestamps or call the last arm clock the executed-duration total.

All observations explicitly use `learning=False`, `stimulation=None`, default
normal passive decay, `pathway_detail=False`, `qualification_detail=False`.
No external DAN input, deliberate weight edits/freezing, model shortcuts or
core-source edits. Normal declared passive dynamics remain unchanged.

## State and readout binding

- Existing `brain.checkpoint`, `brain.restore` and
  `brain.checkpoint_state_sha256` preserve/check the full state, including visual
  filters, queues, adaptation, traces/memory and weights. Check the common file
  hash and restored live complete-state hash before every arm. Clock must be
  exactly 2,000 ms, and engine identity must remain the same.
- Reuse `cell_activity.build_header(identity, runtime_directory)` once to obtain
  the source-bound existing cohort and static provenance. Select its KC members
  by source-ID order: first 220 ranks modulo 20 → twenty groups of eleven.
  Remaining KC cells are explicitly excluded from this derived grouping.
  Freeze header, IDs, indices, membership and hashes before the first advance.
  Fail if the required cohort is unavailable; do not pick active replacements.
- Keep the existing at-most-256-cell passive observer configured once. Its
  observation counter continues across restores; do not reset private fields.
  Buffer at most the 50 native callback bins for one 500-ms observation, then
  write them with their arm/observation identity and clear the buffer.
- Record both DNa02 population counts from ordinary telemetry. Do not use the
  old normalized `evidence_strength` as confidence or an independent price signal.
- Reuse the sealed `RunRecorder` schema with explicit checkpoint-bound fork
  events. Three checkpoint files suffice: initial `brain-before.npz`, shared
  `black-prefix.npz`, terminal `brain-after.npz` in the final arm. Record actual
  parent sequence/name/hash and common complete-state hash for each fork.
- There are exactly 79 events: three checkpoints, four prefix observations,
  eight forks and 64 arm observations. Preserve every native bin and explicit
  black interval. New cell-bin fields are schema extensions, not new attestation.
- Bind state evidence in the sealed raw stream: prefix checkpoint event
  `complete_state_sha256`; each fork's `complete_state_sha256` from the actual
  restored live state; each arm's last observe event
  `complete_state_sha256_after` from the actual final live state. Recorder
  metadata is fixed before execution; do not retroactively add unknown end hashes
  there or rely on unbound receipt fields. Summaries derive them from raw events.

## Predeclared analysis

The **primary** window is the last 500 ms of each arm (relative 3.5–4.0 s;
absolute model time 5.5–6.0 s). All eight completed half-second windows are a
predeclared **secondary** time course. Earlier responses may be reported as such,
but cannot replace a null primary result.

For each window retain the twenty group count vector, whole-KC and both motor
counts; compute signed DNa02 difference from counts and declared group sizes.
Report A−B, C−D, each image minus its block's black control, and differences
between control-1/control-2, A/A-repeat and C/C-repeat. Repeated arms must have
identical scientific outputs and final complete-state hashes; timing fields and
monotonic observer indices need not be identical. A mismatch invalidates the
comparison and is not evidence of learning or variability.

Repeat equality uses an explicit projection: per-observation model clocks,
durations, stimulus RGB hash, learning/stimulation flags, group rates and original
bin clocks/counts, cell-bin clocks/indices/counts and final complete-state hash.
Exclude arm/branch IDs, global event sequence, monotonic observation index,
compute/kernel timing and event/scientific-chain hashes. Cell identities and
group declarations must match their common frozen header independently. Whole
events and whole hash chains are not expected to be equal across branches.

There is **no adaptive calibration** in this diagnostic: no fitted scales,
regrouping, threshold search, changing windows or price mapping. The second image
pair is a separately predeclared check, not a claim of statistical independence.
Record exact count differences, including zeros. No p-values or population-level
generalisations from deterministic repetitions.

An effect confined to a common rise across all groups does not establish useful
selection among drinks. Black subtraction is an experimental comparison from a
matched state, not a live adapter with access to a counterfactual future.

## Resource and process bounds

- One controller acquisition after review; no automatic repeat after failure.
  Investigate and review any failed launch before deciding the next bounded step.
- **900 s wall deadline**, **4 GiB native Python process peak resident memory**,
  **256 MiB total new output plus supervisor evidence/logs**.
- Poll at most every 2 seconds; include startup/header construction and restore
  peaks. State actual platform memory semantics and sampling limits. These are
  stop thresholds, not a guarantee against every sub-poll disk overshoot.
- The first supported host supervisor is Windows/PowerShell 7. A virtualenv
  executable can forward to a second Python process. Before engine construction,
  identify and hold the actual worker process by PID, creation time, executable
  and descent from the launched process. Start hidden. Assign the launcher and
  actual worker to an owned Windows Job Object with `KILL_ON_JOB_CLOSE` and no
  breakaway flags before releasing the worker. Any failed identity or assignment
  check aborts without release. Terminate the job on deadline, overrun, monitor
  failure or cancellation; wait for all owned processes to terminate.
- The fixed PowerShell frontend delegates Win32 ownership to the Python helper.
  Before worker release, the helper confirms its actual owner PID/start identity,
  holds the exact PowerShell parent handle and starts a parent-death watchdog.
  Frontend cancellation signals the owner explicitly, waits boundedly and kills
  that actual owner if needed. Hold a temporary candidate and independently
  validate its identity and OS ancestry to the launched helper before promoting
  it into any cleanup target; failed candidates are never killed. Parent death
  also terminates and drains the job.
  The owner's job handle is non-inheritable so abrupt owner death triggers
  kill-on-close. A venv launcher PID alone is insufficient for either direction.
- Cancellation uses a preallocated, counted fixed-size signal and a synchronized
  terminal cutoff after the owned job is empty. Observe cancellation through
  that cutoff. Later frontend cancellation cannot grow the counted signal or
  change an already finalized outcome. Verify both sides of this boundary;
  stopping the watchdog before final accounting is insufficient.
- Monitor the actual worker's `PeakWorkingSetSize` through its held process
  handle, including startup and restore. Job commit-memory limits are not RSS
  limits; do not report them as such. Account separately for owned children.
- The existing native builder always executes a compiler version probe, even
  with a matching cache. Readiness binds the cache DLL/metadata, native source
  and resolved compiler executable/hash/exact version command. Before engine
  construction install a runner-local process-start guard allowing only that
  version probe. Reject compile commands and other process starts; never bypass
  the core cache validation or fall back to a new build. The probe inherits the
  job and its timeout. This guard controls a known code path, not a general sandbox.
- Prepared output and supervisor evidence have distinct new directories under
  this workspace. Reject undeclared existing or execution artifacts, unsafe links,
  ancestor/descendant overlap and nonempty undeclared contents. Count all new
  bytes there, including prepared manifest and logs; exclude unrelated old runs.
  After preflight, bind the child's `TMP`/`TEMP` to new counted evidence scratch
  space so private audit/checkpoint copies cannot evade the output threshold.
- Partial output is preserved with failure status. A completion receipt is written
  only after all observations, sealed record and offline semantic audit succeed.
  The diagnostic producer writes `receipt.json`; the supervisor consumes that
  actual contract. Exit 0 or a receipt alone is not scientific acceptance.

## Preparation, verification and acceptance

Prepare mode performs no engine construction or native execution. It freezes
the above constants, frame hashes, group-selection algorithm, package/script
identities and budgets in a new protocol manifest. Run mode requires its exact
expected hash. Native identity/cohort are bound before advancing, without using
activity to choose them. Unexpected package/source/protocol changes reject the run.

Exact preparation state: diagnostic `prepare` creates a new output directory
containing **only `protocol.json`**. Supervisor `Prepare` requires that state,
creates a new evidence directory containing **only `readiness.json`**, and does
not launch native work. Readiness binds canonical directories, prepared-protocol
hash, resolved Python/entrypoint identities, supervisor hash and fixed limits.
Supervisor `Run` requires both expected file hashes and exactly these two
directory inventories; it rechecks all bound values and current source identities.
Any prior log, raw run, partial result or completion artifact rejects reuse.
Execution logs and `run/` may be created only after that validation. These rules
permit prepared inputs, but never make a failed output directory resumable.

The native CLI additionally requires `--supervision-directory`,
`--expected-readiness-sha256` and `--start-token`. After validated Run preflight,
the supervisor creates a fresh token and starts the monotonic deadline before
launch. The runner exclusively publishes `worker-ready.json` in the evidence
directory with actual PID, token, protocol hash and readiness hash, then waits
at most 30 seconds for `release.json`. The supervisor writes release only after
identity/job assignment and the first resource sample; release binds the same
PID, token and both hashes. Missing, malformed or mismatched release prevents
engine construction. Handshake time and bytes count against the normal limits.
Test-only injected engines remain independent of Windows; production cannot use
that injection through the CLI. The external supervision helper and supervisor
source identities are bound before launch too.

Host smoke evidence must include virtualenv forwarding, missing/wrong release,
job-assignment failure, a hanging version child, denied compile commands, each
resource/monitor stop condition and cancellation of the whole owned job. Exercise
frontend cancellation while it remains alive, forced frontend death, forced
actual owner death and cancellation before/just after worker release, including
a hanging grandchild. Measure detection/cleanup latency; no instantaneous-stop
claim. Neither a receipt nor a normal `finally` test proves abrupt-exit cleanup.
Windows API semantics follow [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
and [process memory counters](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters).

Offline inspection consumes a capped private snapshot and the existing verifier:
2-MiB manifest, 1-MiB event line, 64-MiB events, at most 79 events and three
checkpoints of at most 64 MiB each. Validate protocol/frame bindings, complete
arm ordering, state/fork routes, observation/bin clocks and counts, cell/native
alignment, cohort/group arithmetic and all 34 seconds of actual advancement.
Only this checked source can generate a summary. Verification stays
`integrity-only`; no invented native replay qualification.

Before acquisition: failing-then-passing synthetic regressions, bounded existing
tiny-native interface coverage, independent source/protocol review and a real
non-neural child-monitoring smoke test on the host. After acquisition: independent
review of raw bindings, repeated arms, declared comparisons, resource evidence,
unchanged historical artifacts and package fingerprint. Publish honest positive,
negative, invalid or inconclusive results; none alone qualifies the market.
