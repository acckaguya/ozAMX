# Fingerprint-exact source snapshot

This directory contains the exact source and validation-driver files fingerprinted by study `c0eafaa4c07f9445406dea2d62abc81d982da40aeae5b34f26c2ea1f4dbc0663` (source fingerprint `d53e356393fd464727e12d7863c64b63098f5108e1b7f18410ecb45c57ad9c66`). The matching root files and the reversed `ideas/v2_candidate.patch` were verified file-by-file against the source hashes in the run ledger. See `manifest.json` for the full hash list and provenance.

No build output, compiled library, binary, or vendor tree is included. The temporary candidate tree was not modified.

To replay an individual manual idea patch, make a fresh copy of this snapshot and apply the corresponding patch from the sibling `../ideas/` directory. Each archived `*.patch` was checked to apply directly to this snapshot. To reconstruct the later combined v2 candidate instead, copy the snapshot and apply `../ideas/v2_candidate.patch` in the copy. The archive step performed patch-application checks only; it did not rebuild or run a benchmark.

Example (from the repository root):

```sh
cp -a bench/8454h/search/source_base /tmp/ozamx-replay
cd /tmp/ozamx-replay
git apply /home/caiweili/ozAMX/bench/8454h/search/ideas/direct_pack.patch
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

Use a new copy for every patch. Do not apply an idea patch on top of another idea unless its notes specify that sequence.
