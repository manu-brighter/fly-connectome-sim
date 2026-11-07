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

The viewer commands `npm ci`, `npm test`, `npm run build` exited 0:
97 tests passed, zero skipped, test duration 25.401s. Vite retained its existing
bundle-size warning (830.64kB main JS). No real browser or encoded-video
acceptance was performed in this slice.

The exact native selection is recorded in the workflow and local commands:
143 tests passed, zero skipped, in 85.90s (86.528s command wall time), exit 0.
The evolved native checkpoint test verifies an active state, exact restoration and
identical continuation; the genuine session fixture uses a generated MPEG4
and four-neuron native graph. Mutated/resealed count fixtures are declared
test cases and do not constitute measured MaleCNS outcomes.

The Windows archive's 38-member raw-byte model identity is
`8bc237a7a592ab023d23a980034e4c5dc9441dd84b35b6d056bca60fea355e59`.
The existing Windows working-tree raw-byte identity remains
`f3ef2ff605432fe549ada0aeb37384f3426df94be23d95049f2a180cc2d4197c`.
The archive retained Windows CRLF conversion under `core.autocrlf=true`; the
working tree has mixed LF/CRLF files. The initial report labelled the archive
as Git/LF; hosted comparison corrected that assumption. No source files were
rewritten and no formal source-freeze gate was performed. All 77 captured
source/test/schema/dependency-lock paths remained byte-identical locally.

## Hosted acceptance

The first actual [GitHub run 42379675655](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42379675655)
completed successfully on commit
`cfcda1de00520b8c8a267d509b178926c508f884`, push event, at
2026-11-07T14:02:55Z. No rerun or workflow/source correction was required.

| Job | Actual result | Job duration |
| --- | --- | --- |
| [Tiny native/session 128424446628](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42379675655/job/128424446628) | 142 passed, 1 skipped in 29.63s | 40s |
| [Viewer 128424446946](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42379675655/job/128424446946) | 97 passed, 0 skipped in 29.183s; build exit 0 | 44s |

The sole Python skip is the existing Windows-junction case at
`tests/experiment/test_session_workflow.py:388`, explicitly inapplicable on
Linux. Media/native tests executed; the Windows isolated run covered that
junction case. The viewer's retained bundle-size warning is not a build failure.

Both jobs used image `ubuntu24 20261101.360.1`, Ubuntu 24.04 x64. Native compiler:
`c++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`; uv 0.12.15;
Python 3.12.14 (Clang 22.1.3-built distribution); PyAV 19.0.2. Viewer:
Node 24.21.0/npm 11.19.0. The workflow's package-location, empty runtime and
effective data-root assertions passed. Hosted source model identity was
`26b0f88127be9bd3d0732161519e23d34c0e8f9ef436ff0d773f558c447ea3e0`.
All 38 hosted member hashes match their exact `git show` blob bytes at the tested
commit. All 38 archive member hashes match those hosted/blob hashes after CRLF
to LF normalization in memory. The archive, hosted checkout and Windows working
tree identities are therefore recorded separately; no identity is relabelled
across them. This establishes this tiny-native/session compatibility selection
on that hosted environment,
not cross-platform numerical equivalence or fullgraph execution.

Run metadata and full logs were read through the authenticated CLI and retained
locally under ignored `.tools/ci-clean-20261107/`; the linked GitHub run is the
tracked continuation reference. Local evidence is not a cloud prerequisite.

Configuration lint: official actionlint 1.7.12, archive checksum verified against
its release manifest, exited 0 with no diagnostics. ShellCheck was unavailable.
`git diff --check` passed. Existing tests provide behavioral acceptance; no
YAML-mirroring tests or configuration RED/GREEN cycle is claimed.
Independent configuration/security review closed with zero Critical, Important
or Minor findings; it verified action metadata, trust/isolation boundaries and
the genuine native fixture selection. It did not execute the tests or establish
hosted Linux acceptance.
The final evidence review independently checked retained run/logs, first-attempt
metadata, all 77 frozen paths, all 38 hosted/Git member hashes and the three
source identities; it also closed with zero Critical, Important or Minor findings.

## Remaining boundaries

Fullgraph/data-dependent general pytest, hosted Windows, macOS, actual browser
or encoding, broader filesystem/resource hardening, live model API acceptance,
formal assay/C1, native-history attestation and scientific gates remain
separate. No learning, content-understanding or content-causality conclusion
follows from these checks.
