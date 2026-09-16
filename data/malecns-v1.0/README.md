# MaleCNS v1.0 source data

Official source: https://male-cns.janelia.org/download/

The dataset is produced by FlyEM (HHMI Janelia), the University of Cambridge,
the MRC Laboratory of Molecular Biology, and Google Research. See the official
project page for publication credits and the CC BY licence.

This directory contains the initial simulation inputs: curated cell annotations,
predicted neurotransmitters, and the segment-to-segment connection table.
The raw tables include segments; selecting the simulated neuronal graph is a
separate import step. Physiology and learning rules are not supplied by these files.

Download or verify the files using Node.js:

```powershell
node scripts/download-connectome.mjs
```

`manifest.json` records the official object generations, byte sizes and MD5 hashes
returned by Google Cloud Storage over HTTPS. The downloader verifies each file
before promoting its `.part` download, prints a SHA-256 hash, and verifies existing
files instead of overwriting them. Interrupted partial files are retained for
inspection. Raw data and partial downloads are excluded from Git.

All three files were downloaded and verified on 2026-09-15 (1,109,008,094 bytes
in total). The SHA-256 fields in the manifest were calculated locally from those
verified downloads; the downloader's upstream integrity check uses the recorded MD5.
