# Scientific replay presentation repair — 2026-11-07

The user reopened the [previous film's](2026-11-07-final-demo.md) presentation
acceptance: the wide event tablet intersected the fly, there was no selected-card
tap, and the scientific visual layer from the supplied references was missing.
This repair uses the [bounded presentation contract](../superpowers/specs/2026-11-07-scientific-replay-presentation.md).

## Source and scope

The recording and plan remain exact copies of the existing
`runs/session-workflow-20261107/` bundle. Its historical native model fingerprint
is `f3ef2ff605432fe549ada0aeb37384f3426df94be23d95049f2a180cc2d4197c`.
It records 7 s of feed and 2 s of cards; final-window counts L6/R2 give
12/4 Hz and select Sunset House. The illustrative gesture cannot change that
decision. No native simulation or provider request is needed for this repair.

The original files remain:

| Artifact | SHA256 |
| --- | --- |
| recording.json | `b7887d75cc84db3d28ab341f265a78c16336abc9554798149ed7b28c38eb4983` |
| plan.json | `824d82356164a315f3acb22b1f414add8074b9d9eda12404e6668c79a51279e1` |

The static anatomy source is the locked MaleCNS v1.0 annotation table, joined
by body ID to the locked 166,700 model IDs. It contains soma positions for
139,662 of those cells; 27,038 lack positions. The display uses at most 12,000
deterministically sampled real points, with no invented missing positions,
anatomical axes, synapse locations or individual-neuron activity.

Seven separate population traces use recorded integer counts, population sizes
and actual bin durations. Their values are model output, not biological
measurements. Source anatomy and simulated activity remain visibly distinct.

The generated `runs/scientific-demo-20261107/anatomy.json` is 417,084 bytes,
SHA256 `de3d7914c64d8a37b3cf5355c352a351cf7bde3c87092d24a516bac75eacf589`.
A second generation produced identical bytes. An independent direct join of
the locked annotations and graph IDs verified every displayed model index,
body ID and XYZ coordinate, the deterministic sample and all coverage counts.
Its source annotation SHA256 is
`2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`;
the existing graph-ID SHA256 is
`6b6b40c3bddf84b1281ef0b18db06927c2bf61c5f4cb32a4219ec9b7839dc2e5`.

## Acceptance record

The replacement film is `runs/scientific-demo-20261107/demo-30fps.webm`,
2,864,019 bytes, SHA256
`82482c28d1a89fb2096ed7fe3fc4d01a98bb93d3d51922e7b4604263b54d7f5f`.
Chrome 157 exported the actual loaded recording and anatomy. PyAV decoded every
frame: **360 VP9 frames, 900×900, 12.000 s, no audio**, PTS 0..11.967 s at
33/34 ms spacing. Frame 210 cuts from phone to the separate safe tablet scene
at 7 s; frame 270 starts the sole 3 s presentation hold at recorded time 9 s.
Reach, contact and retraction occur only within that hold; no source time,
input, activity bin or plan changes. Frames through the transition and the
gesture were inspected separately from the older film.

The new file also played through all 12 s in Chrome: `ended=true`, no media
error, 900×900. The downloaded plan matches the original structurally; the
presentation copies of recording/plan remain byte-identical to the source.
No source receipt is copied or relabelled as a new simulation receipt.

Browser checks covered pending/selected and reverse boundaries, wrong-recording
anatomy rejection with usable replay, clearing anatomy on recording reload,
export-time load guards, paused gesture, selected-side highlight and source time
fixed at 9 s. Reduced motion produced identical raw canvas pixels across two
samples of the running hold. An earlier element-screenshot byte comparison was
not equal and is not used as evidence of pixel identity. The 390px viewport
stacks anatomy and activity with readable labels and separates plan, scene and
captions; this is a bounded responsive check, not mobile-browser certification.
Right-choice/defer rendering uses explicitly labelled synthetic presentation
fixtures, not additional claimed native outcomes.

The geometry regression checks use actual meshes, joint/tube radii and both
gesture paths. Initial checks reproduced the original intersection; subsequent
review caught overextended limbs and a right-arm thorax collision. The final
implementation uses the nearer mirrored foreleg, constant original segment
lengths, grounded feet and separate tablet-facing placement. The film clearly
labels illustrative motion; this is not a reconstructed motor trajectory.

Actual final commands:

```powershell
npm --prefix viewer test
npm --prefix viewer run build
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_export_anatomy.py -q
```

**114 viewer tests passed, no skips, 37.782 s; build exited 0.**
**10 generator tests passed, no skips** (parent run 0.99 s; worker's final run
1.14 s). The new synthetic generator tests are included in the existing
clean-checkout workflow. Known non-failing notices: experimental Node TypeScript
support, an 844.26 kB build chunk, PCFSoftShadowMap fallback, npm update notice,
and a denied pytest cache write in the parent's sandbox run. No dependency,
packaged Python/C++ core, recording schema or native engine change was made;
the native/research suites were not repeated for this presentation repair.

Independent final source/frame review found no open blocker. It independently
decoded the new WebM, compared all 15 extracted review frames and checked the
source snapshots, real source join, raw bin arithmetic and playback evidence.
This is presentation acceptance, not scientific qualification or LLM acceptance.
Local checks and source snapshots live
under `.tools/scientific-presentation/`; all media, anatomy and raw evidence stay
ignored. Reproduce without simulation:

```powershell
npm --prefix viewer run dev
# Open recording: runs/scientific-demo-20261107/recording.json
# Open anatomy: runs/scientific-demo-20261107/anatomy.json
# Export video, or play the existing demo-30fps.webm directly.
```

A fresh checkout lacks these local data/media files. The generator and optional
loading workflow are documented in [Getting started](../getting-started.md#optional-scientific-replay-anatomy).

## Limits

The compact recording contains group bins, not per-neuron spike timing or
synaptic events. Dynamic individual-neuron/synapse displays require a separate
recording contract. Neither the point cloud nor the illustrative fly motion
establishes biological learning, semantic event preference or validated motor
behavior. Scientific qualification and genuine LLM/API acceptance remain open
on their separately documented tracks.
