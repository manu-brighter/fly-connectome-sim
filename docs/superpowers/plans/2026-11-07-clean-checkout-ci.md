# Clean-checkout compatibility CI implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development for this bounded task. Routine technical execution and reviewed feature pushes are already authorized.

**Goal:** Exercise the real tiny C++ kernel, checkpoint continuation and local session workflow from an empty hosted Linux checkout, alongside viewer tests/build.

**Architecture:** Two independent Ubuntu 24.04 GitHub Actions jobs install locked Python/media dependencies or locked viewer dependencies. Neither job downloads MaleCNS, media, checkpoints or private notes. These are compatibility checks, not scientific qualification or binary-identical reproduction.

**Tech stack:** GitHub Actions, uv 0.12.15, Python 3.12.14, system C++17, Node 24.21.0.

**Spec:** The fresh-checkout and live TODO sections of `docs/cloud-handover.md`, existing dependency locks, and the requirements below define this slice.

## Global constraints

- Preserve every packaged Python/C++ source, schema, lock, dependency and existing test byte. Any platform defect requiring source changes is a separate reviewed scope decision.
- Keep the existing feature branch. No remote settings, PR, merge, deployment, authentication changes or paid API calls.
- Trigger on feature pushes, pull requests and manual dispatch. Use standard `ubuntu-24.04` runners only, read-only contents permission, full commit SHA action pins, no persisted checkout credentials, caches, secrets or uploads. Cancel superseded runs; bound each job to 15 minutes.
- Verify action pins against their official repositories. Initial verified releases: checkout v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`; setup-uv v10.3.3 `68559e99cc807c1eb7e9238fd43a15bba460eec2`; setup-node v7.1.0 `949feb2413d6458794dcd2491c4babbbce0c15c1`.
- Python job sets `FLY_CONNECTOME_SIM_DATA` to a fresh empty ignored `.tools/ci/runtime` directory before Python imports; clear opt-in fullgraph and Python path overrides. Install `uv sync --locked --extra test --extra media` with exact Python. Import `av` explicitly so media tests cannot silently disappear.
- Record tool/compiler/image versions and actual source identity from that checkout; Windows raw-byte model identity cannot label a Linux checkout. System compiler/image remain unpinned within Ubuntu 24.04.
- Local clean-checkout acceptance uses an ignored `git archive` export, its own virtualenv and empty data directory; outside toolchain/cache executables may be reused, never outside installed project packages or runtime data.
- Tracked evidence distinguishes local Windows results, actual hosted Linux results, skipped tests and untested fullgraph/macOS/hosted Windows/browser/live API/formal gates.

## Review focus

- Accidental real-data reliance: empty data root before imports; select only declared tiny/synthetic tests.
- False green through missing media/native tooling: explicit av import and compiler check, genuine native build/evolved checkpoint/session fixture.
- Untrusted PR execution: ordinary pull_request only, read-only token, no secrets, no credentials retained, no untrusted context interpolated into shell.
- Local package leakage: isolated environment and assert imported package location belongs to exported checkout.
- Overstated portability: hosted workflow outcome must be observed; compatibility is not native attestation or fullgraph qualification.

## Task 1: Two-job workflow and operator documentation

**Files:** create `.github/workflows/compatibility.yml`; update `README.md`, `docs/getting-started.md`, `docs/cloud-handover.md`; create `docs/experiments/2026-11-07-clean-checkout-ci.md`.

**Interfaces:** consumes existing locks and tests; produces two visible checks and documented local equivalents. No application interface changes.

- [x] Confirm baseline has no CI workflow and capture unchanged source/lock hashes. This configuration task reuses behavioral tests; do not add tests that merely restate YAML or claim a feature RED/GREEN cycle.
- [x] Implement the two jobs with the constraints above. Native job runs exactly:

  ```text
  pytest -q tests/test_native_build.py tests/test_checkpoint.py::test_evolved_emitted_checkpoint_replays_with_native_kernel tests/experiment/test_replay.py::test_native_qualification_context_maps_and_single_factory tests/experiment/test_session_workflow.py tests/experiment/test_recorder_limits.py tests/test_cli.py
  ```

  Viewer job uses `npm ci`, `npm test`, `npm run build` under `viewer/`, disables automatic package-manager cache. Record versions.
- [x] Independently review YAML/security/test selection; verify every action SHA and actual inputs. Apply material findings before push.
- [x] Run selected Python tests and viewer commands from an isolated clean export. Report command, count, elapsed time, skips and toolchain; verify application import belongs to export and no runtime data is used.
- [x] Update tracked report/handover with local evidence and clearly pending hosted acceptance. Inspect complete staged diff, hashes and size; commit/push explicitly to feature branch.
- [x] Observe the real hosted run, diagnose any failure before claiming Linux support, and update the tracked report/TODO with its exact tested commit, job outcome, versions and scope. Review and push a small evidence follow-up if needed, then pause with concise status.

Acceptance: first hosted run 42379675655 on `cfcda1de00520b8c8a267d509b178926c508f884`, 142 Python passes/1 Windows-only skip; 97 viewer passes/build 0. See the tracked report for exact tools, durations and review scope. Evidence follow-up is a documentation-only checkpoint.

## Boundaries after this slice

MaleCNS/fullgraph tests remain opt-in and absent from CI; the general full suite includes data-dependent cases. Formal assay/C1/source-freeze and live API acceptance stay parked. No live browser or video-encoding acceptance is established by Node tests/build.
