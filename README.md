# Jogge di Fly Brain

A reproducible experiment in which an LLM proposes event ideas and a simulated
fruit-fly connectome influences which ideas survive.

The project uses the released MaleCNS v1.0 wiring graph. It does not claim to
simulate a complete living fly, consciousness, dopamine concentration, receptor
occupancy or semantic understanding. Physiology, learning and action mappings
are explicit model choices and are tested against controls.

## Current milestone

The first milestone is a controlled A/B learning assay:

1. present two synthetic visual stimuli;
2. pair one stimulus with an explicit dopaminergic-neuron input;
3. test both without reward;
4. compare trained, untrained, frozen and temporally unpaired runs;
5. store an immutable event stream for later 3D replay.

Product scope and evidence rules are defined in
[`docs/specs/fly-event-planner.md`](docs/specs/fly-event-planner.md).

### WIP status — 2026-09-16

- MaleCNS v1.0 sources are checksum-locked and the prepared graph verifies at
  166,700 cells and 25,582,938 directed edges.
- The attributed numerical core builds as a Windows DLL through the
  project-local Zig toolchain.
- `FlyEngine` exposes explicit PAM11/PPL101 stimulation and measured KC,
  MBON07, MBON11 and DNa02 telemetry.
- A full-graph test produces identical neural output after a complete reset.
- Next: freeze the A/B protocol and preference adapter, then run trained and
  matched control assays. No learning result is claimed yet.

## Data

The three required MaleCNS files are downloaded from the
[official HHMI Janelia release](https://male-cns.janelia.org/download/) into
`data/malecns-v1.0/`. Raw and prepared data stay outside Git. The local manifest
records source generations and checksums.

```powershell
node scripts/download-connectome.mjs
```

## Local tools

Development is pinned to Python 3.12. Project-local `uv` and Zig installations
may live under `.tools/`; that directory is ignored. No global Python or compiler
installation is required.

```powershell
.tools\uv\uv.exe sync --cache-dir .tools\uv-cache --extra test --python .tools\python\cpython-3.12.14-windows-x86_64-none\python.exe
.tools\uv\uv.exe run --cache-dir .tools\uv-cache pytest
$env:JOGGE_FLY_FULL_TEST='1'
.tools\uv\uv.exe run --cache-dir .tools\uv-cache pytest tests\test_full_graph_engine.py
```

The last command is opt-in because it loads and advances the complete graph.
Local chat notes and visual references remain outside Git.

## Provenance

The numerical core is adapted from MIT-licensed Stonkfly/DOOMFLY work through a
checksum-pinned Fly/Wirehead revision. Its notice and exact revisions are kept in
`THIRD_PARTY.md` and `licenses/`. MaleCNS data is distributed separately under
CC BY 4.0; see the official project page for attribution and citation details.
