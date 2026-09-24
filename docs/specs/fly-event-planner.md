# Fly Connectome Sim — Product and Experiment Specification

**Status:** Approved direction, implementation in progress  
**Date:** 2026-09-16  
## Problem Statement

The project needs a short-form social media experiment in which a reconstructed
fruit-fly nervous system has a real, inspectable causal role. Existing viral
projects often show authentic-looking neural charts while the feed timing,
swipe gesture, reward and final action are scripted. That would undermine the
main joke here: an LLM proposes event ideas and the fly acts as the chaotic
board member that decides what survives.

The MaleCNS connectome supplies anatomy and inferred connection strengths. It
does not supply a complete living brain, semantic understanding, receptor
kinetics or a validated learning rule. The project must preserve that boundary
while still using the available neural graph as far as the evidence supports.

## Objective

Build a reproducible MaleCNS experiment that can observe spontaneous responses
or apply a defined dopamine-linked training protocol, record every input and
neural output, and replay the resulting decisions in a polished 3D event-planning
video.

## Product Narrative

The fly completes a "board internship":

1. It watches club reels on a virtual phone.
2. In observation mode, the system records spontaneous responses without an
   externally supplied reward pulse.
3. In training mode, selected visual stimuli are paired with a documented
   dopaminergic neuron stimulus.
4. A reward-free test checks whether the trained state responds differently to
   the same or related stimuli.
5. An LLM presents visual event options and receives only the fly adapter's
   recorded decisions. It may explain or continue the plan, but it cannot replace
   the chosen option.
6. A replay renders the phone, fly, event-planning table and synchronized neural
   telemetry at a smooth video frame rate.

Absurd event choices are allowed by default. Session constraints may later lock
budget, safety or venue rules if the generated plan is intended for a real event.

## Success Criteria

- [ ] The prepared graph contains exactly 166,700 retained cells and 25,582,938
      directed connections and is reproducibly derived from checksum-locked
      MaleCNS v1.0 inputs.
- [ ] A fixed RGB input reaches the mapped R1–R6 and R8 visual cells and produces
      deterministic telemetry from a restored checkpoint.
- [ ] `observe` and `train` are separate experiment modes with separate run
      directories and checkpoints.
- [ ] Training pairs only the declared stimulus with the declared PAM11 or PPL101
      input; the reward-free test contains no external reward pulse.
- [ ] The assay compares trained, untrained, frozen-plasticity and temporally
      unpaired controls from the same baseline checkpoint.
- [ ] A result is reported as learned behavior only if a predeclared behavioral
      metric changes reproducibly relative to controls. A weight change alone is
      insufficient.
- [ ] Every run stores provenance, seed, input hashes, model/build hashes,
      checkpoints, per-step telemetry and decisions.
- [ ] Replay is derived entirely from recorded run data and can play smoothly
      even if simulation ran slower than real time.
- [ ] Display labels distinguish DAN firing rate, external stimulation and
      plastic efficacy. They never claim dopamine concentration, receptor
      occupancy, pleasure, addiction or semantic understanding.

## Constraint Registry

### Hard Constraints

| ID | Constraint |
|---|---|
| H1 | The connectome simulation must causally influence behavior and event choices. |
| H2 | Both spontaneous observation and targeted training must be selectable experiments. |
| H3 | Comparable modes start from an identical baseline and keep separate state. |
| H4 | Smooth replay of real recorded measurements is sufficient; real-time simulation is not required. |
| H5 | The presentation includes a simple 3D fly plus synchronized technical telemetry. |
| H6 | MaleCNS source data, model assumptions and engineered adapters remain auditable. |

### Soft Constraints

| ID | Preference |
|---|---|
| S1 | Use dopaminergic mechanisms and identified circuits as far as available evidence supports. |
| S2 | Match the visual energy of the supplied DJ and doomscroll references. |
| S3 | Keep local operation practical on the Ryzen 9 5900X, RTX 3080 and 64 GB RAM desktop. |

### Boundaries

| ID | Excluded Claim or Scope |
|---|---|
| B1 | No claim that the simulation is a complete biological fly or conscious. |
| B2 | No claim that it understands reels, event concepts or language. |
| B3 | No receptor concentration or occupancy display until an explicit calibrated receptor model exists. |
| B4 | No public multi-user deployment in the first experiment milestone. |

## Technical Direction

### Numerical core

Use the MIT-derived numerical core audited at `fly-wirehead` commit
`fcefe9441f80e25aab713411ebced53f5e5ea172`, retaining its provenance files and
original MIT notice. Keep the connectome importer, visual projection, C++17 LIF
kernel, circuit identification, checkpoints and candidate KC→MBON rule.

Add a platform build adapter so the native kernel builds as a Windows DLL using
the project-local Zig C++ compiler and as a shared object with a conventional
Unix C++ compiler. Do not alter numerical equations as part of that port.

### Experiment modes

`observe` supplies visual input without a project-defined reward pulse. It may
record native network dynamics. Any habituation feature must be declared and
tested separately because it is itself a form of learning.

`train` follows a fixed protocol:

1. Establish baseline responses to stimuli A and B.
2. Pair A with a declared DAN stimulus; present B without it.
3. Restore the same schedule without reward and measure both responses.
4. Repeat with A/B positions or identities reversed.
5. Run frozen, no-DAN and temporally unpaired controls from the same baseline.

The first stimuli are synthetic, controlled visual patterns. Club reels are
introduced only after the synthetic assay demonstrates that the implemented
mechanism can affect the behavioral readout.

### Behavioral adapter

The first adapter is predeclared and frozen before training. It uses identified
MBON07/MBON11 activity and lateral motor evidence to produce a signed preference
score, confidence and one of three actions: inspect left, inspect right or defer.
It does not read labels, reward flags or event metadata. Later adapters may add
watch/scroll behavior but must pass the same leakage rules.

### Replay contract

Each run produces an append-only JSON Lines event stream plus immutable metadata.
Events use simulated timestamps and include input hashes, spike summaries, DAN,
KC and MBON rates, efficacy summaries, adapter values and chosen action. The
renderer consumes this stream; it never queries a live model during replay.

### Event planner boundary

The LLM emits strictly validated option objects containing label, visual prompt
and constraints. A separate renderer turns options into visual stimuli. After
the fly adapter chooses, the selection is appended to the session log and passed
back to the LLM as immutable context. The LLM can comment and propose the next
round but cannot revise a recorded choice.

## Evidence and Assumption Corrections

| Original assumption | Corrected understanding |
|---|---|
| More dopamine detail automatically means more biological accuracy. | DAN spikes, release, concentration, receptor binding and intracellular effects are separate quantities; each added layer needs parameters and validation. |
| The connectome includes a ready-to-run learning brain. | It supplies anatomy and annotations. Physiology, stimuli, learning and action mappings are model choices. |
| Existing wirehead visuals show learned scrolling. | The audited reference advances its feed on a timer and choreographs the swipe; its tests prove stimulation, weight changes and replay, not preference learning. |
| MaleCNS was released with the September paper. | MaleCNS v1.0 was released on 2026-06-08; the paper was published on 2026-09-03. |

## Validation Gates

1. **Data gate:** upstream hashes and prepared-array locks pass.
2. **Kernel gate:** a restored checkpoint produces identical spike and adapter
   hashes on repeated execution on the same build.
3. **Mechanism gate:** stimulation changes the declared DAN activity and plastic
   weights while a frozen run does not.
4. **Behavior gate:** reward-free post-training behavior differs from matched
   controls over multiple predefined seeds/schedules.
5. **Replay gate:** rendered values match the recorded stream at sampled frames.

If the behavior gate fails, the result is reported as a negative experiment.
The video may still show the attempt, but it must not claim learning.

## Research Sources

- MaleCNS v1.0 data: https://male-cns.janelia.org/download/
- Whole-brain LIF model and limitations: https://pmc.ncbi.nlm.nih.gov/articles/PMC11446845/
- Dopamine receptor and timing effects: https://pmc.ncbi.nlm.nih.gov/articles/PMC9012144/
- Local dopamine release regulation: https://pmc.ncbi.nlm.nih.gov/articles/PMC5262376/
- Connectome-constrained learning model: https://pmc.ncbi.nlm.nih.gov/articles/PMC11525173/
- Audited reference implementation: https://github.com/mattyhempstead/fly-wirehead/commit/fcefe9441f80e25aab713411ebced53f5e5ea172

## Interview Record

- The requested concept combines reel viewing, dopamine-linked learning, LLM
  event proposals and a simple 3D social-video presentation.
- The user selected both observation and training as switchable experiments.
- Precomputation plus smooth replay is accepted.
- Hardware was taken from the user's maintained gear profile: Ryzen 9 5900X,
  RTX 3080, 64 GB RAM.
- The user authorized continued work without further questions until a material
  decision or blocker requires input.
