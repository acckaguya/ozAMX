# V4 padding and tile-load layout screen

This six-variant follow-up holds the strongest screened geometry fixed at batch 2, CBM=256, CBN=256, BK=256, and late FP32 validation enabled. It varies only C-row padding (0/64/128 bytes) and the AMX tile-load hint (`tileloadd`/`tileloaddt1`). Each candidate ran the N=8192 FP32 and FP64 p6/p10/p15/p21 workloads for three timed repetitions.

## Validation and artifacts

All six variants have five 37-column CSV rows, three raw API-wall samples per row, complete three-repetition checkpoints whose call-wall vectors match the CSV, matching per-build library/source/MKL identities, three passing CTests, and a passing six-case quick byte gate. This phase did not run the full 20-case gate for every variant. The p0/h1 candidate was selected for an additional full gate because its screen profile was the closest alternative to the p64/h1 control; it passed all 20 cases against the immutable V3 release.

| Padding | Tile-load hint | FP32 API mean | FP64 p6 | FP64 p10 | FP64 p15 | FP64 p21 | Geometric mean time ratio vs p64/h1 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 B | `tileloadd` | 0.137271 s | 0.225072 s | 0.328217 s | 0.438484 s | 0.584015 s | 1.072× |
| 0 B | `tileloaddt1` | 0.128003 s | 0.218239 s | 0.323378 s | 0.408120 s | 0.535495 s | 1.014× |
| 64 B | `tileloadd` | 0.142543 s | 0.214670 s | 0.340338 s | 0.454552 s | 0.579497 s | 1.083× |
| 64 B | `tileloaddt1` | 0.142901 s | 0.201618 s | 0.285675 s | 0.415202 s | 0.537974 s | 1.000× |
| 128 B | `tileloadd` | 0.136238 s | 0.224293 s | 0.322779 s | 0.456663 s | 0.545653 s | 1.060× |
| 128 B | `tileloaddt1` | 0.134931 s | 0.204774 s | 0.302709 s | 0.475705 s | 0.536774 s | 1.030× |

The time ratio is the geometric mean of the five per-workload API-mean ratios against the p64/h1 row in this same run; values above 1 are slower. The p0/h1 variant is mixed: it improves the FP32, p15, and p21 means by about 10.4%, 1.7%, and 0.5%, while p6 and p10 are about 8.2% and 13.2% slower. Its five-workload geometric mean is 1.014×, so it does not displace p64/h1. The other variants are 3.0–8.3% slower by this same descriptive measure.

The phase profiles support the mixed result. For p0/h1 versus p64/h1, FP32 compute/reconstruction is 0.1160 s versus 0.1311 s, while FP64 p10 is 0.2799 s versus 0.2418 s; p21 is effectively tied at 0.4894 s versus 0.4897 s. The full phase means and all raw API and phase samples are in the machine-readable [`layout_analysis.json`](../bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/layout_analysis.json); the original CSVs, checkpoints, logs, gates, builds, and identities remain alongside it.

These are screening measurements. The layout runner inserted no frozen-V3 timing brackets, and the same-run p64/h1 row is an internal candidate control rather than a V3 control. The preceding geometry screen showed material V3 movement across its own bracket controls. Small layout differences therefore do not establish a stable improvement. No padding or hint variant is promoted from this screen. The p64/h1 and p0/h1 candidate libraries are available at:

- Default layout: [`libozamx.a`](../bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/builds/layout_b2_m256_n256_p64_h1_l1__mode3_b2_m256_n256_p64_h1_l1/libozamx.a)
- Screen alternative, full 20-case gate passed: [`libozamx.a`](../bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/builds/layout_b2_m256_n256_p0_h1_l1__mode3_b2_m256_n256_p0_h1_l1/libozamx.a)

## Cost-model audit

The active-tile estimate in [`8454H_V4_COST_MODEL.md`](8454H_V4_COST_MODEL.md) is consistent with the implementation for its stated p21/default-padding examples. `budget_depth()` maps p6/p10/p15/p21 to stored FP64 slice depths 3/4/5/6. The packed A/B tile bytes are `2 × depth × BK × (CBM + CBN)`, the private FP64 block uses `8 × CBM × (CBN + pad_bytes/8)`, and the batched FP32 product scratch uses `4096 × batch` bytes. With BK=256, batch=2, and 64-byte row padding, these sum to 1424 KiB for CBM=128/CBN=256/p21, 2072 KiB for CBM=256/CBN=256/p21, 3352 KiB for CBM=256/CBN=512/p21, and 1304 KiB for CBM=256/CBN=256/p6. The current CPU cache sysfs entry reports a 2048 KiB per-core L2.

Those are per-worker active-array estimates, not measured residency or miss counts. The workspace pool's 2 GiB setting limits retained thread-local workspace; it is not an RSS ceiling. The calculation excludes other live arrays and cache mapping effects, as the cost-model note states. The frozen V3 library still hashes to `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`.

## Interrupted launch records

Two incomplete launch directories are retained as evidence. The first launch's output directory was moved while its process could still be active; its partial record reports `benchmark error: cannot write checkpoint`. The duplicate launch was stopped before it completed its first screen. These artifacts are not included in the six-candidate analysis:

- [`layout_b2_m256_n256_20261014_interrupted_transport`](../bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_interrupted_transport/)
- [`layout_b2_m256_n256_20261014`](../bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014/)

The complete retry is [`layout_b2_m256_n256_20261014_retry2`](../bench/8454h/roofline_v4/search_runs/layout_b2_m256_n256_20261014_retry2/).
