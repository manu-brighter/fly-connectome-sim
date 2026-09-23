# Associative Plasticity Assay Pivot

**Status:** Approved direction; implementation plan pending

**Date:** 2026-09-24

**Supersedes:** The scientific interpretation and milestone order of Tasks 5–6
in `docs/superpowers/plans/2026-09-16-connectome-experiment-core.md`. Existing
integrity, checkpoint, telemetry and protocol primitives remain inputs.

## Decision

The first scientific milestone is a model-specific demonstration of persistent,
stimulus-specific and causally attributable associative plasticity. It is not a
left/right preference, learned behavior or event-choice claim.

Motor activity and event decisions remain product goals, but become a separate
downstream validation stage. The replay may show measured MBON and motor
activity, provided its labels do not imply a validated behavioral mapping.

## Why the direction changes

The current `PreferenceAdapter` combines a global MBON07-minus-MBON11 term with
a DNa02 right-minus-left term. The MBON term has no established lateral meaning,
so it can select `inspect_right` without rightward motor evidence. That is not a
defensible behavioral endpoint.

The current A/B images also change pattern, color and screen side together. A
response difference therefore cannot be assigned to stimulus identity. Finally,
the current `reversal` schedule starts from baseline with the opposite pairing;
it is reciprocal acquisition, not reversal learning in one continuing state.

The candidate plasticity rule is explicitly an unvalidated adaptation. Equal
one-second KC and DAN traces can make some synchronous rate combinations cancel,
so timing and pathway observability must be measured before a confirmatory assay
is frozen.

## Claim boundary

If all gates pass, the strongest permitted statement is:

> In this declared MaleCNS-constrained spiking model, the specified visual and
> PPL101 stimulation protocol produced a change in MBON11 response that remained
> after the declared retention interval, followed the paired stimulus identity,
> exceeded matched controls and depended on the model's plastic state.

The result does not establish biological learning, valence, semantic
understanding, dopamine concentration, receptor activity, consciousness or a
validated motor decision. Repeated deterministic runs demonstrate computational
reproducibility, not biological replication.

## Primary candidate and extensions

The first candidate is the project-defined PPL101-modulated KC-to-MBON11
plasticity compartment. Local MaleCNS annotations and related literature support
the cell-type pairing, but the project's RGB projection, contact-fraction gains
and application of the rate rule remain model hypotheses.

PAM11-to-MBON07 remains a predeclared exploratory extension. PAM11/alpha1 is
associated with appetitive long-term-memory circuitry in the literature, but
that does not validate this reconstruction, stimulation method or learning rule.
It must not be substituted post hoc if the primary assay fails.

## Milestone 1: exploratory qualification

Qualification runs are explicitly exploratory and use separate seeds and
stimulus families from the later confirmatory run.

### Visual-path observability

For every candidate stimulus, record the causal chain:

1. input hash and exact RGB geometry;
2. mapped visual-cell drive;
3. KC response in the declared measurement window;
4. candidate MBON response;
5. DNa02 activity as secondary telemetry only.

A stimulus family qualifies only if A and B both drive the upstream pathway,
responses are numerically stable after checkpoint restore, and the selected MBON
has measurable dynamic range without external DAN stimulation.

### Timing-rule characterization

Run a bounded, predeclared grid over CS/DAN onset offset, duration and neutral
gap. Record KC/DAN traces, candidate-edge efficacy changes, saturation and
post-pairing MBON responses. This characterizes the implemented equation; it is
not evidence for learning.

Select one timing configuration before confirmatory data exist. If no tested
configuration produces a stable candidate effect without saturation, report the
mechanism as unsupported and stop the confirmatory assay rather than expanding
the grid until a positive result appears.

### Retention and washout

Qualification selects a fixed retention interval of at least 10 seconds. In a
matched frozen-plasticity run, acute stimulation and recurrent-network effects
must fall below the predeclared effect floor by that time; ten KC/DAN trace time
constants alone do not prove washout.

Run reward-free tests at the selected interval `T` and at `T + 60 s`, each from
a separate copy of the same training-end checkpoint. During retention and test,
use no external DAN pulse, set `learning=False`, and retain normal passive memory
decay. Report only the duration actually demonstrated; do not generalize it to
long-term memory.

### Runtime qualification

Benchmark simulated time, wall time, event volume and checkpoint size on the
full graph. These measurements set chunk sizes and recorder flush behavior. They
must not change the scientific endpoint.

## Stimulus and schedule design

Stimulus identity, screen side, color/luminance assignment, presentation order
and paired identity are independent declared factors. The generator must support
them independently instead of encoding all factors in `A` and `B`.

- For the first assay, use controlled A/B patterns at the same image location
  with fixed chromatic composition and documented receptor-drive statistics.
- Balance A/B order and paired identity across schedules. If side becomes a
  factor, cross training side with test side and qualify receptor and KC responses
  separately; do not assume side-invariant recognition.
- Reserve a separate held-out stimulus family and seeds for confirmation.
- Pass a neutral black RGB frame during every `stimulus=None` interval, including
  the temporally unpaired DAN pulse.
- Simulate every scheduled gap in chunks of at most 500 ms so neural state and
  trace decay follow simulated time.

Rename the current `reversal` condition to `reciprocal_pairing`. A future true
reversal condition must first acquire one contingency, continue from that learned
state, switch the contingency, and measure the transition without restoring the
baseline checkpoint between phases.

## Endpoint and controls

For one candidate MBON and a frozen response window, define:

```text
delta = (post_CS_plus - post_CS_minus) - (pre_CS_plus - pre_CS_minus)
```

The expected sign, response window, aggregation, exclusions and minimum relevant
effect are frozen after qualification and before held-out runs. The confirmatory
comparison is the trained delta against matched frozen-plasticity,
no-external-DAN and temporally unpaired deltas. Report all condition values, not
only a pass/fail label.

The delta alone is not evidence of stimulus specificity: a global response gain
can change it whenever pre-training A and B responses differ. Qualification must
show distinguishable A/B activity patterns among the KCs that actually innervate
MBON11. Reciprocal pairing must move the effect with the paired identity, with
results reported per identity rather than only pooled. Add either an unpaired
third test stimulus or a frozen test against a global-scaling explanation.

The minimum relevant effect is calibrated from numerical resolution, pathway
dynamic range and exploratory control spread. It is not selected from the
held-out result. Deterministic schedule variants test robustness to declared
identity/side/order factors; they are not independent biological samples and do
not justify population-statistical language.

## Causal memory interventions

Association alone is insufficient. Treat the candidate memory state atomically
as its candidate-edge `memory_u`, `memory_w`, and
`weight = baseline_plastic * (1 + memory_w)`. From identical post-training state
copies, create declared intervention branches:

- **Necessity:** restore all three candidate memory components to their matched
  baseline values while preserving neuronal state, traces and simulated time,
  then rerun the reward-free test.
- **Sufficiency:** transplant all three trained candidate memory components into
  a time- and exposure-matched untrained state, then rerun the same test.
- **Sham intervention:** write back the unchanged state through the same path to
  detect intervention machinery effects.

The primary effect should disappear under the necessity intervention and appear
with the sufficiency intervention in the model. If state separation cannot be
implemented without contaminating other variables, report the limitation and do
not use the phrase "caused by memory state".

## Motor and event-choice stage

MBON plasticity does not automatically validate an action. After the primary
assay, test visual and intervention effects on left and right DNa02 populations
as a separate endpoint. A lateral action may use only predeclared lateral motor
evidence until an MBON-to-motor mapping is independently justified.

The current `confidence` field is only normalized evidence magnitude. Rename it
to `evidence_strength` before public artifacts; it is not statistical confidence.
Keep the existing adapter version readable for old artifacts, but do not use it
as the primary assay outcome.

## Run-artifact requirements

The recorder schema is frozen only after qualification establishes the required
fields. Each run must still be append-only and contain:

- source, build, graph, model, parameter, group and engine identities;
- protocol/stimulus versions, counterbalance factors, seeds and exact input
  hashes;
- simulated timestamps, neutral-gap chunks and all external stimulation;
- raw window/bin spike counts and rates used to derive the endpoint;
- candidate plastic-state summaries, saturation, retention timing and atomic
  intervention declarations;
- checkpoints before training, after training and for each intervention branch;
- exact analysis version, frozen threshold and result classification.

`compute_seconds` is operational telemetry and excluded from deterministic event
hash equality. Replay consumes only verified artifacts and must distinguish
measured values from engineered derived values.

## Gates and milestone order

1. **Integrity:** source/runtime locks, native identity and checkpoint restore
   pass.
2. **Pathway:** visual-to-KC-to-candidate-MBON observability passes.
3. **Mechanism:** a predeclared timing configuration changes candidate plastic
   state without saturation; the frozen-plasticity control does not. The
   `no_external_dan` condition records any effect driven by endogenous DAN
   activity and is not assumed to be a zero-plasticity control.
4. **Recorder pilot:** the qualified short assay round-trips through an
   append-only verified artifact.
5. **Confirmation:** the held-out primary delta exceeds the frozen effect floor,
   controls and causal interventions behave as declared.
6. **Motor:** a separate lateral-motor endpoint is validated or explicitly
   reported unsupported.
7. **Presentation:** viewer and LLM integration consume immutable recorded
   results only.

Failure at a gate is a valid negative result. Later gates must not relabel it as
success.

## Implementation consequences

- Do not implement the original Task 6 behavioral report as written.
- Split the next work into qualification, recorder pilot, frozen analysis and
  confirmatory execution.
- Revise protocol/stimulus terminology before recording durable artifacts.
- Rename `no_dan` to `no_external_dan`. For the initial compartment assay,
  freeze secondary MBON07 plasticity or explicitly measure and report its
  contribution.
- Keep Core Tasks 1–4 and hardening work; they provide the deterministic and
  provenance foundation this design requires.
- Regenerate and verify the ignored runtime manifest before assay execution so
  its corrected DNa02 description matches the current code.

## Sources

- PAM-alpha1/MBON-alpha1 appetitive long-term-memory circuit:
  https://elifesciences.org/articles/10719
- PPL1/MBON timing-dependent plasticity model underlying the adapted rule:
  https://www.nature.com/articles/s41586-024-07819-w
- Visual conditioning evidence involving the related DAN/MBON pair:
  https://elifesciences.org/articles/4580
- Whole-brain LIF modelling assumptions and validation limits:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10187186/
- MaleCNS v1.0 source data: https://male-cns.janelia.org/download/
