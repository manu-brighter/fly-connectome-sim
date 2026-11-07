# Bounded visual-content and side diagnostic — 2026-11-07

The [pre-run protocol](../superpowers/specs/2026-11-07-content-side-diagnostic.md)
fixes two8s histories (real reels or explicit black RGB) and normal/swapped/black
2s probes restored from each history's complete checkpoint. Exactly28s native
advancement/504 observations, one engine, three checkpoints, no adaptive dwell,
external DAN, learning, threshold changes or retry. This is a descriptive local
diagnostic of the declared model, not the adaptive demonstration or an assay.

**Observed result:** this fixed visual manipulation changes the measured motor
readout. It does not establish a semantic or stable event preference. Under the
real-feed history both layouts end with `inspect_left`, selecting different
options when those options move. Under black history the normal cards defer,
while swapped cards end with `inspect_right`. This is one deterministic setup,
not independent replication or evidence about general reel preference.

## Native measurements

Each cell below is actual L/R spikes in one500ms window, with one DNa02 cell per
side. Per-cell Hz is therefore twice the displayed count. Probe windows retain
global time8..10s; only9.5..10s determines the final mapped choice.

| Feed history | Probe | 8–8.5s | 8.5–9s | 9–9.5s | 9.5–10s | Final action → option |
| --- | --- | --- | --- | --- | --- | --- |
| Real reels | Normal cards | 13/5 | 9/3 | 9/7 | 11/1 | left → Sunset House |
| Real reels | Swapped cards | 12/5 | 9/3 | 7/10 | 7/0 | left → Warehouse Techno |
| Real reels | Black | 4/2 | 3/8 | 3/4 | 5/5 | defer; no event selection |
| Black | Normal cards | 0/0 | 0/0 | 0/0 | 0/0 | defer |
| Black | Swapped cards | 1/0 | 4/4 | 19/3 | 1/8 | right → Sunset House |
| Black | Black | 0/0 | 0/0 | 0/0 | 0/0 | defer; no event selection |

All ten declared contrasts were retained. Real-versus-black feed counts differ
in12/16 windows; both feeds have0/0 in their first2s. The remaining real-feed
L/R500ms counts, in order, are6/4,7/9,4/0,9/3,10/0,23/5,4/3,12/3,11/5,10/2,8/3,5/6;
the black feed stays0/0. Real-minus-black differences span L0..23/R0..9 spikes.

After-effect under the common black probe differs in4/4 windows, including final
L+5/R+5 spikes (+10/+10Hz). This residual influence can include visual filtering
and neural adaptation; it does not isolate plastic memory. Within real history,
normal-minus-black and swapped-minus-black differ in4/4 windows, and
normal-minus-swapped in3/4. Within black history, normal-minus-black differs
in0/4 windows, while swapped-minus-black and normal-minus-swapped differ in4/4.
Real-versus-black history differs in4/4 windows for each identical card layout.
The final real-history normal-minus-swapped difference is L+4/R+1 spikes
(+8/+2Hz), even though both final adapter actions remain left.

These controls vary the whole image, including luminance/contrast/motion, and
relocate rendered cards while preserving physical LEFT/RIGHT labels. They do
not identify event meaning, biological learning, general preference or validated
motor behavior. The fixed8s feed is distinct from the historical adaptive7s demo.

## Implementation and checks

Only `experiment/content_diagnostic.py` and its test file add executable code.
They compose the existing decoder, native engine, complete-state restore,
renderer and motor-only adapter. Existing session/replay/CLI formats, numerical
core, schema and dependencies are unchanged. Plain JSON/JSONL diagnostic outputs
carry no sealed-artifact or native-replay authority.

Sol recorded11 behavioral RED failures against a stub before implementation,
then11 passing tests. Later strengthened pixel/factory/raw-count/boundary
assertions passed on their first run; no separate RED cycle is claimed for those.
An initial default pytest temporary-directory ACL error was resolved with a
new scoped directory. No dependencies were missing. Controller's final check:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/experiment/test_content_diagnostic.py tests/experiment/test_adapter.py tests/experiment/test_event_cards.py tests/experiment/test_video_observation.py tests/experiment/test_feed_event_session.py -q -rs -p no:cacheprovider --basetemp=.tools/content-diagnostic/pytest-final
```

**204 passed, no skips,172.86s**, exit0. These are focused tiny-native/media
checks, not the entire assay suite or fullgraph qualification. Astra reviewed
the protocol against actual engine/visual/checkpoint/adapter code, then the
implementation/tests/logs and local supervisor/audit. Both reviews had no
remaining findings; the latter independently rehashed all93 pinned files.
The reviewer did not repeat tests or native execution.

## One attempt, raw audit and supervision correction

The single attempt completed with521 raw events,504 observations and3120 native
bins:28s cumulative advancement, at most10s along each trajectory. Module wall
time was183.240s; launcher supervision completed in185.396s. Final output was
35,441,647 bytes. Both launcher and native child exited0, with no termination
reason, no repeated native run and no changed input/threshold.

The initial Windows supervisor monitored the venv launcher's RSS, not its child
interpreter; its4,317,184-byte peak is **not** the workload measurement. The
controller detected this during the run and added a host-side watcher after
124.438s, checking the exact native PID, parent and executable before monitoring
it. The native OS peak working set, which includes earlier process history, was
880,824,320 bytes (840MiB), below4GiB. Thirty2s samples covered the remainder;
the last live sample was at182.923s, and process exit was observed at184.951s.
No final post-exit RSS sample was obtained. This is a disclosed supervision
correction, not a claim of uninterrupted original protocol compliance or hard
OS resource enforcement. Wall/output monitoring remained active throughout.

The controller's separate audit redecoded both original videos, re-rendered
both layouts, checked all actual input hashes/PTS, complete event order/global
clocks, reward-free flags and population-normalized native counts. It rebuilt
all56 motor windows, strict1Hz actions, mapped options and ten contrasts without
using the diagnostic reducer. It independently loaded all three checkpoint
files and recomputed their complete state hashes, compared every restore, and
confirmed all93 frozen files unchanged. The audit passed; terminal hashes are
recorded evidence, not independently replayed native states. No engine was
constructed or native observation repeated for this audit.

Astra's final evidence review independently reconstructed all56 windows from
the raw JSONL, checked clocks/actions/mappings, artifact/checkpoint hashes and
all93 pinned files, and confirmed the reported results and204-test log. It
accepted the scoped claims and disclosed supervision deviation without further
findings. No test or native execution was repeated by the reviewer.

Local artifacts: `runs/content-diagnostic-20261107/{manifest.json,events.jsonl,summary.json,checkpoints/}`.
The corresponding SHA256 values are:

- Manifest: `13bf9a98fdda0321b964d3329b7a93fc6a5f861af2f00fbc961efe697fc972f2`.
- Events: `fa027c1f84ee89aa69ef9cc76ba2224b59e9daccf1854b083b86e112ed84d356`.
- Summary: `aea605489f7cca1d24cb520ac29497f974ba248f58e8b8d46c90c6beaebb2203`.

## Source and invocation

Diagnostic source pins are not a formal production source freeze. Current
Windows working-copy model identity (39 Python/C++ members):
`804899ab8b828365ffb8065094b84aa3eb78330da85b79dd62465435e2cfb1b4`.
New packaged source invalidates any earlier formal identities/evidence; no
formal fullgraph qualification or confirmation is established.

The local freeze manifest contains raw-byte SHA256 values:

```json
{
  "protocol_sha256": "4ea3511e9c2c381707a7b07ace2d1b6ffc184197bfcd520bcd3e868d1a8db139",
  "model_sha256": "804899ab8b828365ffb8065094b84aa3eb78330da85b79dd62465435e2cfb1b4",
  "implementation_sha256": "e9a0657a634f0e770cf8dcd529c8428cac1c4b527014bf5e7a1da7cb07b26455"
}
```

The actual single child command, with external supervision:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.experiment.content_diagnostic --playlist .tools/reels-source/playlist.json --proposal examples/event-options.json --protocol docs/superpowers/specs/2026-11-07-content-side-diagnostic.md --freeze-manifest .tools/content-diagnostic/freeze.json --output-dir runs/content-diagnostic-20261107
```

The supervisor polls every2s and terminates its child after an observed900s
wall,4GiB RSS or256MiB new-output breach; these are monitored thresholds with
possible polling overshoot, not OS hard limits. The module itself does not
enforce resource caps. No automatic retry is permitted. Use a new output path;
source pins from another byte layout must not be relabelled as these bytes.
To prepare new pins, hash the protocol/module raw bytes and obtain
`model_fingerprint()['sha256']` from `fly_connectome_sim.neural.checkpoint`;
record and review the new declaration before a separately authorized run.

Local-only raw files, media, checkpoints, freeze/audit/test logs and supervision
receipt remain ignored. A fresh checkout can run the tiny-native tests, but
cannot reproduce this local observation without the locked graph and media.
