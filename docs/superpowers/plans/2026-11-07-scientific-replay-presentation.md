# Scientific replay presentation repair — 2026-11-07

Status: implemented and reviewed. The [result](../../experiments/2026-11-07-scientific-presentation.md)
records final source/data checks, tests and actual film acceptance.

The user reopened presentation acceptance after seeing the tablet intersect the
fly and the absence of the scientific visual layer from the supplied references.
Reuse the exact November 7 session recording and bound plan; do not run another
simulation or alter the motor decision. The prior film remains historical.

## Bounded implementation

1. **Sol: scene and interaction.** Add regression checks for a separate safe
   tablet composition, gaze, both card contact targets and full limb paths.
   Cut to that composition at the recorded phase boundary. A deterministic
   presentation clock drives one reach/contact/retract during the existing
   terminal hold, only after a selected decision; defer never taps. Interactive
   playback, seek, reduced motion and export must agree on recorded time.
2. **Astra: anatomy contract and design.** Specify a source-bound, optional
   static soma-position sidecar joined to the actual modeled cell IDs. Retain
   missing-position counts and source identity. The recording provides seven
   population bins, not per-neuron activity or spatial synapse locations.
3. **Sol: scientific canvas panel.** Test and implement bounded offline sidecar
   generation/loading and a canvas panel containing static source anatomy and
   clearly separate measured population traces. Include it in video export.
   No fabricated neuron spikes, synapse flashes, anatomical axes or units.
   Keep derived data ignored; preserve recording bytes and core source.
4. **Parent: acceptance.** Run relevant tests/build, open the actual recording
   and sidecar, inspect transition/contact/retraction and narrow/reduced-motion
   states, then export and decode/play the actual film. Compare the recording
   and downloaded plan with the originals. Record concrete results and limits.
5. **Astra: independent review.** Review the implementation, source joins,
   scientific labels, actual geometry and decoded film evidence. Resolve
   findings, update the handover, inspect/stage explicit first-party files,
   commit and push the existing feature branch. No PR or deployment.

## Completion boundary

The presentation fix does not establish biological behavior or scientific
qualification. Genuine LLM proposal/session acceptance remains separately open
for API configuration. Individual-neuron and synaptic activity need a new
recording contract and remain outside this repair.
