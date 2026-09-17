# Connectome Experiment Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible Windows-capable MaleCNS A/B experiment that records enough provenance and telemetry for later replay.

**Architecture:** A vendored, attributed numerical core prepares checksum-locked
MaleCNS inputs and advances the full graph through a native C++ kernel. A small
project-owned experiment package owns protocols, decision adapters and append-only
run artifacts. Presentation code consumes the run artifacts later and stays out
of the numerical path.

**Tech Stack:** Python 3.12, NumPy, pandas, PyArrow, Pillow, C++17 via Zig C++, pytest.

**Spec:** `docs/specs/fly-event-planner.md`

## Global Constraints

- Keep the exact MaleCNS v1.0 source hashes and prepared graph locks.
- Preserve the MIT notice and upstream provenance for adapted numerical files.
- Do not label DAN activity as dopamine concentration or receptor activity.
- Keep observation, training and controls in separate run directories.
- Tests must fail for the intended missing behavior before implementation.
- Raw connectome inputs, prepared arrays, checkpoints and run artifacts remain outside Git.

---

### Task 1: Repository and deterministic toolchain

**Files:**
- Modify: `.gitignore`
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `README.md`

**Interfaces:**
- Produces: `uv run pytest`, local Python 3.12, documented raw-data path.

- [ ] Initialize the local Git repository on `main` and add the GitHub remote without pushing.
- [x] Pin Python and runtime/test dependencies in `pyproject.toml`.
- [x] Document setup, data provenance and the current experiment milestone.
- [x] Verify dependency installation and the test invocation.

### Task 2: Attributed MaleCNS numerical core

**Files:**
- Create: `src/jogge_fly_brain/neural/*.py`
- Create: `src/jogge_fly_brain/neural/kernel.cpp`
- Create: `src/jogge_fly_brain/neural/*.json`
- Create: `src/jogge_fly_brain/data.py`
- Create: `licenses/stonkfly-MIT.txt`
- Create: `THIRD_PARTY.md`
- Test: `tests/test_native_build.py`
- Test: `tests/test_data_sources.py`

**Interfaces:**
- Produces: `prepare()`, `verify()`, `MemoryBrain`, `VisualMemoryBrain`.

- [x] Write a failing source-data test that resolves the three official files by manifest and verifies their SHA-256 hashes.
- [x] Vendor the audited MIT-derived numerical files and provenance records, renaming the data environment variable to `JOGGE_FLY_DATA`.
- [x] Write a failing native-build test requiring a loadable platform library with an exported `memory_advance` symbol.
- [x] Implement the platform build adapter: Zig C++ and `.dll` on Windows; conventional C++ and `.so`/`.dylib` elsewhere.
- [x] Run focused tests, prepare the full graph and execute upstream array verification.

### Task 3: Project-owned engine telemetry

**Files:**
- Create: `src/jogge_fly_brain/engine.py`
- Test: `tests/test_engine_contract.py`
- Test: `tests/test_full_graph.py`

**Interfaces:**
- Produces: `FlyEngine.observe(frame, duration_ms, stimulation=None, learning=False)` returning typed telemetry for DAN, KC, MBON and motor groups.

- [x] Write failing unit tests for input validation and telemetry shape using a small test double at the neural boundary.
- [x] Implement the engine without automatic per-frame reward.
- [x] Add explicit PAM11/PPL101 stimulation parameters and separate MBON07/MBON11 rates.
- [x] Write and run an opt-in full-graph determinism test from a restored checkpoint.

### Task 4: A/B protocol and leakage-resistant adapter

**Files:**
- Create: `src/jogge_fly_brain/experiment/protocol.py`
- Create: `src/jogge_fly_brain/experiment/adapter.py`
- Create: `src/jogge_fly_brain/experiment/stimuli.py`
- Test: `tests/experiment/test_protocol.py`
- Test: `tests/experiment/test_adapter.py`

**Interfaces:**
- Produces: `ProtocolSchedule`, `PreferenceAdapter`, deterministic A/B stimulus frames.

- [x] Write a failing adapter test showing that only neural telemetry affects the signed preference score and action.
- [x] Implement a versioned adapter using declared MBON and lateral motor fields.
- [x] Write failing schedule tests for baseline, pairing, reward-free test, reversal and controls.
- [x] Implement schedules with explicit simulated timestamps and seed.

### Task 5: Append-only run artifact and replay contract

**Files:**
- Create: `src/jogge_fly_brain/experiment/recorder.py`
- Create: `src/jogge_fly_brain/schemas/run.schema.json`
- Create: `src/jogge_fly_brain/cli.py`
- Test: `tests/experiment/test_recorder.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `run.json`, `events.jsonl`, `brain-before.npz`, `brain-after.npz`; CLI commands `prepare`, `assay`, `verify-run`.

- [ ] Write failing tests proving an event stream is append-only, ordered and hash-verifiable.
- [ ] Implement atomic metadata/checkpoint writes and append-only event records.
- [ ] Implement CLI mode selection and independent run-directory enforcement.
- [ ] Run a short synthetic assay and verify the complete artifact.

### Task 6: Full learning assay and honest result report

**Files:**
- Create: `src/jogge_fly_brain/experiment/analysis.py`
- Create: `configs/assay.synthetic.json`
- Test: `tests/experiment/test_analysis.py`
- Output: `runs/synthetic-*/report.json` (ignored)

**Interfaces:**
- Produces: effect estimates for trained, frozen, no-DAN and unpaired conditions, without asserting success in advance.

- [ ] Write failing analysis tests with hand-checked synthetic event streams.
- [ ] Implement predeclared metrics and control comparisons.
- [ ] Execute the full graph assay with fixed schedules and record compute time.
- [ ] Classify the result as supported, unsupported or inconclusive using declared thresholds.
- [ ] Update the product spec with measured feasibility and limitations.

### Task 7: Replay viewer milestone

**Files:**
- Create: `viewer/` web application
- Test: viewer contract and sampled-frame synchronization tests

**Interfaces:**
- Consumes: verified run artifacts only.
- Produces: smooth portrait replay with 3D fly, phone, neural overlay and experiment labels.

- [ ] Design the viewer from the supplied references after the experiment schema stabilizes.
- [ ] Render the fly and scene with lightweight Three.js geometry.
- [ ] Drive every technical chart and decision from recorded events.
- [ ] Clearly label stimulation, DAN firing, efficacy and any choreographed motion.
- [ ] Capture a 9:16 replay suitable for editing in DaVinci Resolve.

### Task 8: LLM event-planning loop

**Files:**
- Create: provider-independent planner module, schemas and mock provider
- Test: schema, immutable decision and fallback tests

**Interfaces:**
- Consumes: immutable fly decisions.
- Produces: validated event option rounds and final plan.

- [ ] Add only after the synthetic assay and replay path are stable.
- [ ] Enforce structured options and immutable selected choices.
- [ ] Use local deterministic fixtures as the default demo provider.
- [ ] Add an API-backed provider without coupling it to the neural engine.

## Self-review

The plan covers every hard constraint in the product spec. Scientific uncertainty
is isolated in Task 6 rather than hidden behind UI work. Viewer and LLM tasks are
kept after the run schema because both consume verified artifacts and should not
shape the experiment result.
