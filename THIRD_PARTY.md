# Third-party sources and provenance

The numerical files in `src/fly_connectome_sim/neural/` are adapted from
[`nftechie/stonkfly`](https://github.com/nftechie/stonkfly) commit
`78ef3e05ab0fa086032098558d893667068944a0`, itself derived from DOOMFLY.
They were imported through the audited Fly/Wirehead revision
[`fcefe9441f80e25aab713411ebced53f5e5ea172`](https://github.com/mattyhempstead/fly-wirehead/commit/fcefe9441f80e25aab713411ebced53f5e5ea172).
The original MIT notice is preserved at `licenses/stonkfly-MIT.txt`.

Local adaptations:

- renamed the data environment variable to `FLY_CONNECTOME_SIM_DATA`;
- added a platform-aware, provenance-recording Windows/Unix build adapter;
- the project-owned engine and experiment protocols live outside this directory.

The released MaleCNS v1.0 data is distributed separately under CC BY 4.0 by
the [MaleCNS collaboration](https://male-cns.janelia.org/download/). Raw data is
downloaded into ignored local storage and is not redistributed by this repository.

The wiring data and adapted physiology do not establish accurate receptor
kinetics, subjective experience, attention, addiction or semantic understanding.
