# Isolated Image Decoding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Convert one bounded JPEG/PNG into the exact canonical image in an owned,
short-lived process, preserving D1's original decode deadline.

**Status:** Both tasks and complete local integration independently accepted after
effective PNG-depth and terminal cleanup/EOF corrections. Final decoder suite225
passed/four Windows privilege skips; full Market540 passed/five privilege skips.
Publication and all four source CI jobs remain pending.
The [exact D2 contract](../specs/2026-11-10-image-decoding-design.md) governs both tasks.

**Architecture:** A private portable transform/protocol worker and a Windows parent
owner. Reuse unchanged process/Job primitives; only the bounded process-creation
and pipe adapter is new. No HTTP, D1 wiring or simulation is part of this slice.

**Tech stack:** Existing Python3.12.14, Pillow12.3.0, NumPy2.4.6 and pytest; existing
public market clock and ownership primitives. No new dependency or framework.

## Global Constraints

- Exact public DTO/API, enum strings, byte/pixel/time/resource bounds and wire
  framing follow the versioned spec. Do not create a second lifecycle or queue.
- Preserve D1, price authority/HTTP/board, packaged core, frozen scripts, replay,
  old artifacts, dependencies and existing workflow jobs. Root alone owns docs/Git.
- Source scope is only market/image_decode.py, market/image_decode_windows.py,
  scripts/market-image-decode-worker.py and corresponding tests/market files.
- No production in-process Pillow fallback; parent validates bytes/metadata and
  returned RGB/digest. No URL, arbitrary executable/path, provider call or server.
- Deadline remains accepted_ns+10s, including successful cleanup; equality fails.
  Sampled memory/poll thresholds are supervision, not an OS security sandbox.
- Child creation must atomically associate the kill-on-close Job and use an exact
  inherited-handle allowlist. No fallback to the parent-crash assignment gap.
  Verify membership directly; WindowsJob.assign must not repair a missing binding.
  The isolated child uses -B alongside -I -S to prevent bytecode writes.
- Genuine Windows lifecycle evidence is separate from portable Linux pixel tests.
  Private fixtures exercise harmless child failures; never kill unrelated processes.
- Sol implements sequentially, independent Astra checks spec compliance and quality.
  Workers are not alone and must preserve concurrent edits. No worker child agents,
  Git changes, real images from users, native simulation or API work.
- Test-first with meaningful RED/GREEN; use .venv/Scripts/python.exe -m pytest,
  a fresh task-local --basetemp and -p no:cacheprovider. Retain actual logs, exits,
  skips and infrastructure errors. Do not use blocked pytest.exe or weaken tests.
- Reviewed local task commits may be grouped into one explicit feature push;
  all existing CI jobs must finish successfully before D2 completion is claimed.

## Task 1 — Exact canonical transform and child protocol

Ownership: scripts/market-image-decode-worker.py and
tests/market/test_image_decode_worker.py only. Root owns evidence/status docs.

Consume the fixed generated request/input files, strict framing and exact
market-rgb64/v1 transform from the spec. Produce one bounded success/rejection
message with exact image identity; no raw exception/metadata output or extra files.
The request schema is market-image-decode/v1; both response variants use
market-image-decode-result/v1. Text-limit units and EXIF-only handling follow
the corrected spec rather than inferred Pillow mode/metadata behavior.

- [x] Root captures reviewed spec/plan and unchanged-source/artifact identities.
- [x] Write failing portable behavioral tests: JPEG/PNG/MIME, dimensions/pixels,
  modes/frame count, malformed/truncated data, PNG text bounds, all orientations,
  alpha/palette/grayscale, odd padding/rounding/upscaling and exact canonical hash.
  Check strict request keys/types, source hash, one-message lengths and no metadata.
  Include RGB16/RGBA16 PNG source depth, XMP-only/conflicting orientation, repeated
  and uncompressed/multibyte text, and the exact response schema/rejection reasons.
- [x] Implement only the private worker and deterministic transform. Verify/load
  against the same bounded immutable input and strip metadata by raw RGB output.
- [x] Run focused green tests; record initial RED and any fixture/infrastructure
  corrections separately. No test result claims a native input or real admission.
- [x] Independent Astra reviews actual source/evidence and the exact pixel/protocol
  contract. Resolve findings with regressions, then root records the local checkpoint.

## Task 2 — Windows ownership, bounded pipes and cleanup

Ownership: market/image_decode.py, market/image_decode_windows.py and
tests/market/test_image_decode.py / test_image_decode_windows.py. Task1 files may
change only for a reviewed integration defect with a regression; preserve its API.

Consume Task1's fixed files/wire message and unchanged Clock/SystemClock,
DatabaseOwnership, WindowsJob and WindowsProcess. Produce the exact immutable
DecodedImage only after all identity, process, pipe, deadline and cleanup checks.

- [x] Write failing parent protocol/timing/capacity tests and actual harmless
  Windows child ownership tests before adding the adapter/controller.
- [x] Implement verified startup-only primitive import, atomically assigned Job
  creation, exact executable/handle identity, bounded pipe polling and scratch
  ownership. Reject unsupported platforms/configurations without an unsafe fallback.
- [x] Verify normal decode, timeout/cancel/flood/crash, memory/poll failure, clock
  failure, failed cleanup and stale/foreign/reparse paths. Exercise actual parent
  death including launch; prove zero owned survivors and an unrelated sentinel
  survives. Distinguish synthetic monitor tests from measured OS lifecycle evidence.
  Assert absent creation-time membership never calls AssignProcessToJobObject;
  cover cancel-during-cleanup, final deadline equality, post-cleanup clock failure,
  interrupt plus cleanup failure, repeated close/decode-after-close and retained
  ownership on unconfirmed teardown. Check bytecode suppression using an isolated
  trusted package fixture with absent/stale caches, not the real environment.
  Cover closed-before-busy/fault precedence, idempotent successful close and
  cleanup retry through retained exact handles only, without process discovery.
- [x] Prove a late result cannot renew D1's accepted-time deadline or escape after
  failed cleanup. Busy calls retain no extra payload; a faulted instance cannot
  silently recover. Record actual resource peaks and private-file cleanup limits.
- [x] Run focused and complete tests/market under the appropriate Windows host
  permissions; preserve honest platform skips. No HTTP/browser/native run is needed.
- [x] Independent Astra reviews full D2 source/evidence, including trusted import,
  frame digest consistency, parent death, clock/timeout/cleanup precedence and
  preserving all prior sources. Fix actionable issues with meaningful regressions.
- [ ] Root records reviewed evidence in handover/plan/result docs, verifies the
  complete staged diff and preservation manifest, commits explicit first-party
  paths and pushes only feat/connectome-experiment-core. Await every CI job.

## Completion boundary and next work

This completes a local decoder component, not guest uploads, moderation, native
handoff, sustained load or public readiness. HTTP intake/preview/approval must later
wire D1 and this decoder without restarting acceptance clocks or displaying raw
uploads. Native ownership/telemetry, genuine price admission and the scientific
display remain distinct later integrations. No sale-price or deployment authority
follows from either portable pixel tests or Windows cleanup tests.
