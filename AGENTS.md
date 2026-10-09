# Working on Fly Connectome Sim

Read `README.md`, `docs/cloud-handover.md` and the current assay plan before
continuing. The handover is the tracked continuation record; private local
`.superpowers/` notes are not required and are unavailable in a cloud checkout.

## Scope and scientific integrity

- Preserve the existing Python/C++ core, provenance locks and upstream MIT notice.
  Do not build a second simulator or weaken checks to obtain a positive result.
- Primary endpoint: MBON11 response under the declared PPL101-modulated
  KC-to-MBON11 model. PAM11/MBON07 is exploratory and cannot rescue a failed gate.
  Do not claim consciousness, semantic understanding, dopamine concentration,
  receptor activity, biological learning or validated motor behavior.
- Advance every scheduled interval, including black frames. `stimulus=None`
  requires explicit black RGB `uint8`; individual observations are at most 500 ms.
  Reward-free tests/retention have no external DAN, `learning=False` and normal
  passive decay. Preserve association reference versus training-end clocks.
- Artifact integrity is not native replay attestation or scientific support.
  Report negative/inconclusive results honestly. Do not fabricate configuration,
  provenance, checkpoints, verification modes or successful gates.
- Any packaged `.py`/`.cpp` change invalidates existing formal qualification,
  frozen configuration and confirmation evidence. Finish source-bearing tasks
  before the formal source-freeze gate. Viewer/LLM work remains gated by the plan.

## Implementation and review

- Match existing structure/style; avoid unnecessary abstractions. Use UTF-8 and
  trailing commas. Preserve unrelated edits. Implement features/fixes test-first;
  record actual test commands/results, skips and unavailable dependencies.
- Delegate bounded implementation/fixes to Sol when available. Use Astra for
  difficult scientific, architectural and integrity reviews when available;
  do not spend that tier on routine edits. If unavailable, state the limitation
  before substituting for a required review. Never claim an interrupted review
  passed. Reviewers must independently evaluate evidence, not trust summaries.
- Ask only for real product decisions, new authority or irreversible actions.
  Technical continuation, relevant tests, reviewed commits and feature pushes
  are authorized. Do not create a PR, merge, deploy or rename remote resources
  without a separate request. Keep user-facing updates short and in German.

## Git

- Work on `feat/connectome-experiment-core`, remote `origin`. Verify the checkout
  and tracking before writing; never push `main`, `master` or `develop`, including
  via a refspec. Push explicitly: `git push -u origin feat/connectome-experiment-core`.
  Never force-push or discard existing work.
- Commit messages are English, with no attribution signatures:

  ```text
  <type> / <title> : Short description

  - What changed
  - Why it matters
  ```

  Types: `feat`, `fix`, `chore`, `refactor`, `hotfix`, `tryout`.
- Stage explicit first-party paths, inspect the complete staged diff and size.
  Never commit raw/downloaded data, `data/malecns-v1.0/runtime/`, `.tools/`,
  `.venv/`, `.superpowers/`, `.ai/`, egg-info, runs/checkpoints/benchmarks,
  private chats or reference images. Do not force-add ignored files for handover.
- Update the tracked handover/current TODO status at a reviewed checkpoint.
  Pause with a concise result after the next sensible commit/push unless asked
  to continue further.
