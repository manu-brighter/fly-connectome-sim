# Imported-proposal observation demo — 2026-11-07

The local experimental observation demo is accepted: real reel RGB, recorded
native motor output, an unchanged selected event plan and a newly exported,
playable film. It uses the authored `examples/event-options.json` proposal.
**Genuine LLM proposal/session acceptance remains externally blocked and open.**
No new native simulation, provider request or research gate ran for this export.

## Exact recording and film

The source is the existing [session workflow recording](2026-11-07-session-workflow.md)
at `runs/session-workflow-20261107/`. Its historical 38-member model identity is
`f3ef2ff605432fe549ada0aeb37384f3426df94be23d95049f2a180cc2d4197c`.
The current 39-member diagnostic source was not rerun or substituted for it.
Viewer source at `c2e9d1c27552c520873d83d1db8926e95ab6c3eb` rendered this film.
The separate film from the [November 3 session](2026-11-03-feed-event-session.md)
remains historical evidence, not this export.

The original session has 7 s of 5× sampled feed and 2 s of event cards, with
no state reset between phases. Final ticks 85000..90000 contain L6/R2 spikes,
one motor cell per side: 12/4 Hz, difference −8 Hz, `inspect_left` → Sunset House.
The original option, brief and programme are preserved in the bound plan.
Current `inspect-session` exited 0 with `complete`, matching that result;
this is artifact integrity verification, not native replay attestation.

The presentation folder `runs/final-demo-20261107/` retains exact copies of
`recording.json` and `plan.json`, the new `demo-30fps.webm`, `README.txt` and
`demo-manifest.json`. The original `receipt.json` and raw `run/` stay only in
the source bundle.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| recording.json | 13138511 | `b7887d75cc84db3d28ab341f265a78c16336abc9554798149ed7b28c38eb4983` |
| plan.json | 1077 | `824d82356164a315f3acb22b1f414add8074b9d9eda12404e6668c79a51279e1` |
| source-bundle receipt.json | 702 | `452b2da4ba66ecb77c6d698122b2abb3bdd8b45ebb9474559e8f11f3beab037a` |
| demo-30fps.webm | 3337541 | `c7254562e521fbfc33be13213a31817d518311e802ddcd6cdde4d39eed4db78f` |

The source receipt is not copied into the presentation folder. Its hash is
bound by the local `demo-manifest.json` bookkeeping file (SHA256
`fa0f3a365282ac2a0aff676512c07a265c31a6d2fd55704ca28fe61c155cba24`), which adds
no native-history or scientific authority.

## Actual acceptance checks

Windows Chrome 157 exported the actual loaded recording. PyAV decoded all
**360 VP9 frames, 900×900, 12.000 s, no audio**: 270 source frames plus 90 labelled
terminal-hold frames. PTS span 0..11.967 s at 33/34 ms intervals. Frame 209 is
the last feed frame; frame 210 starts cards at 7 s without an intermediate
hold. Frame 269 remains pending; frames 270..359 show the final selected plan
and labelled terminal sample. The 3 s presentation hold advances no simulation.
Decoded frames 0, 8, 92, 209, 210, 211, 269, 270 and 359 were retained for review.

Browser checks covered forward and reverse boundaries, pending/selected plan
download availability, replay playback and the completed export. The downloaded
plan equals the original plan structurally. The exported file was separately
played through all 12 s in Chrome: `ended=true`, current time 12 s and no media
error. This establishes this local Chrome/VP9 artifact, not all-browser,
mobile, accessibility or live-frame-pacing certification.

Existing viewer checks were repeated without source or dependency changes:

```powershell
npm --prefix viewer test
npm --prefix viewer run build
```

**97 tests passed, no skips, 31.5198 s; build exited 0.** Known warnings were
Node experimental TypeScript support, an 830.64 kB build chunk, browser
PCFSoftShadowMap fallback and a favicon 404. No export or playback failure
occurred. No backend/native suite or formal assay was repeated for this
documentation and rendering acceptance.

## Reopen or export again without simulation

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli inspect-session runs/session-workflow-20261107
npm --prefix viewer run dev
# Open the localhost URL printed by Vite.
# Open recording: runs/final-demo-20261107/recording.json
# Export video; retain the new download separately.
```

Existing exact bytes remain local and ignored, alongside audit/browser/playback
evidence under `.tools/final-demo/`. A fresh checkout lacks these media/run files.
The compact copied recording suffices for viewer playback; inspect the original
bundle with its raw `run/`. Rendering again does not require `run-session`.

## Scope closed and external prerequisite

The film labels recorded simulation, actual input/measured output, illustrative
fly/swipe motion and the terminal presentation hold. Geometry and motion are
not measured anatomy or validated behavior. The [separate diagnostic](2026-11-07-content-side-diagnostic.md)
supports sensitivity to its specific whole-image manipulation; neither it nor
this film establishes semantics, stable event preference, biological learning
or formal scientific support.

API preflight on November 7 found no `OPENAI_API_KEY` in process, user or machine
scope, and no explicit model/token/cost configuration was supplied. Zero provider
requests or API charges occurred. Genuine LLM acceptance requires local API
configuration, the explicit paid-request opt-in and a separately validated
provider proposal/session; secrets should remain outside chat. That task stays
open. The imported-proposal observation/demo scope is closed; the entire LLM v1
and the parked training/research track are not complete.
