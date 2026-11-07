# Clean-checkout compatibility — 2026-11-07

## Scope

The [workflow](../../.github/workflows/compatibility.yml) checks a data-free
checkout using two standard Ubuntu 24.04 jobs: real tiny native/session tests,
and viewer tests/build. See the [plan](../superpowers/plans/2026-11-07-clean-checkout-ci.md)
and [local commands](../getting-started.md#clean-checkout-compatibility).

This is a compatibility check, not binary-identical reproduction or formal
qualification. No MaleCNS files, Instagram media, historical run, checkpoint,
private working note or paid API access is required. Dependencies and tool
distributions are downloaded. The system C++ compiler and runner image remain
unpinned within Ubuntu 24.04; each job records its versions.

## Local isolated export

`git archive` exported commit `b0ea3c14449e664267af3c680de8e3e2cde85033`
to ignored `.tools/ci-clean-20261107/checkout`. It has its own new virtualenv
and node_modules, installed from unchanged `uv.lock` and viewer lock. Existing
uv, Python, Zig and Node executables/caches were reused only as toolchains;
the imported project package was asserted to reside inside that export.
`FLY_CONNECTOME_SIM_DATA` was set before imports to the export's fresh empty
`.tools/ci/runtime`; tests populate only local generated tiny fixtures/cache.

The initial sandboxed editable-package build failed with Windows access denied;
the same locked sync passed on the host. No lock or application code was changed
to bypass it. Local versions: Windows, Python 3.12.14, uv 0.12.15, Zig 0.16.0,
PyAV 19.0.2, pytest 9.1.1, Node 24.21.0/npm 11.19.0.

The viewer commands `npm ci`, `npm test`, `npm run build` exited0:
97 tests passed, zero skipped, test duration25.401s. Vite retained its existing
bundle-size warning (830.64kB main JS). No real browser or encoded-video
acceptance was performed in this slice.

The exact native selection is recorded in the workflow and local commands:
143 tests passed, zero skipped, in85.90s (86.528s command wall time), exit0.
The evolved native
checkpoint test verifies an active state, exact checkpoint restoration and
identical continuation; the genuine session fixture uses a generated MPEG4
and four-neuron native graph. Mutated/resealed count fixtures are declared
test cases and do not constitute measured MaleCNS outcomes.

The exported Git/LF38-member model identity is
`8bc237a7a592ab023d23a980034e4c5dc9441dd84b35b6d056bca60fea355e59`.
The existing Windows working-tree raw-byte identity remains
`f3ef2ff605432fe549ada0aeb37384f3426df94be23d95049f2a180cc2d4197c`.
This is the existing Git/working-tree line-ending distinction; no source
normalization or formal source-freeze gate was performed. All77 captured
source/test/schema/dependency-lock paths remained byte-identical locally.

## Hosted acceptance

Pending first reviewed workflow push. A local Windows pass must not be reported
as Linux execution. The follow-up record must identify the exact tested commit,
run/jobs, versions, counts and skips before claiming hosted acceptance.
The existing Windows-junction test intentionally skips on non-Windows platforms;
that skip must remain visible in the hosted result.

Configuration lint: official actionlint1.7.12, archive checksum verified against
its release manifest, exited0 with no diagnostics. ShellCheck was unavailable.
`git diff --check` passed. Existing tests provide behavioral acceptance; no
YAML-mirroring tests or configuration RED/GREEN cycle is claimed.
Independent configuration/security review closed with zero Critical, Important
or Minor findings; it verified action metadata, trust/isolation boundaries and
the genuine native fixture selection. It did not execute the tests or establish
hosted Linux acceptance.

## Remaining boundaries

Fullgraph/data-dependent general pytest, hosted Windows, macOS, actual browser
or encoding, broader filesystem/resource hardening, live model API acceptance,
formal assay/C1, native-history attestation and scientific gates remain
separate. No learning, content-understanding or content-causality conclusion
follows from these checks.
