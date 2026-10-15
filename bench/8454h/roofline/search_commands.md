# Reproduction commands for saved roofline-guided searches

These commands are reconstructed from the preserved CSV schemas, benchmark driver, CMake caches, and pass filenames. The original shell transcript was not stored alongside the CSVs, so this file records a reproducible invocation template, not a claim to byte-for-byte recover the original wrapper. Per-variant source, static library, binary, CMake cache, CSV, and SHA-256 evidence are in each search's `metadata.json`; every timed row, including outliers, is in `summary.json` and the original CSV.

The saved searches ran on the 8454H using logical CPUs 0–63, 64 OpenMP workers, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, `OMP_DYNAMIC=FALSE`, and `OZAMX_WORKSPACE_CACHE_BYTES=2147483648`. The candidate CMake configurations are captured verbatim as `OZAMX_*` values in the metadata. The following command form shows the parsed benchmark arguments:

```bash
flock -x /tmp/ozamx-perf.lock taskset --cpu-list 0-63 \
  env OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE \
      OZAMX_WORKSPACE_CACHE_BYTES=2147483648 \
  /tmp/<candidate-root>/<build-dir>/ozamx_optimization_benchmark \
      --sizes <sizes> --precision all --threads 64 --budgets <budgets> --reps <repetitions> \
      --output bench/8454h/roofline/search_<family>/<pass>.csv
```

Use the variant-to-build mappings from metadata. Frozen processes use `/tmp/ozamx-production-final/ozamx_optimization_benchmark` and its frozen library. Variant families are:

| Search | Sizes | Budgets | Repetitions | Candidate build directories |
|---|---|---|---:|---|
| pad | 1024,4096,8192 | 6,21 | 5 | `/tmp/ozamx-roof-pad-batch/build-{p1b1,p2b1,p3b1,p1b2}` |
| THP | 1024,4096,8192 | 6,21 | 5 | `/tmp/ozamx-roof-thp/build-h1`; frozen controls use frozen binary/library |
| rectangular | 1024,4096,8192 | 6,21 | 5 | `/tmp/ozamx-roof-rect/build-{n256p1,n512p1,n256p0,n256p1b2}` |
| adaptive | 1024,2048,4096,8192 | 6,10,15,21 | 7 | `/tmp/ozamx-roof-adaptive/build` |

The controls are ordered as `pass0`, `pass2`, and `pass4` (adaptive/THP) or `pass0`, `pass5`, and `pass8` (pad/rect), interleaved with candidates as shown by `process_order` in each metadata file. THP's `probe_hint0.json` and `probe_hint1.json` preserve the `smaps` evidence. They report 0 KiB versus 497,664 KiB `AnonHugePages` during the probe samples; the latter verifies huge-page backing in that probe and does not imply a benchmark-wide speedup.

All summaries use only `record == "rep"` for timed statistics. They report the median of each process's repetitions and preserve all raw repetitions; outliers are flagged but never removed. Summary CSV rows (`summary_*`) and warmups remain in the raw CSV but are not mixed into timed medians.
