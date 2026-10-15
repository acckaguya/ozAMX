# V4 large-workspace page alignment and THP hint screen

Dataset: `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z` (completed 2026-10-14T12:29:11Z; wait for exclusive global perf lock: 229.7s).
This is a four-configuration, three-repetition screen. It reports observations for a later matched run and does not establish a winner.

## Implementation and verification

Only the isolated page-layout source tree changed. Allocations with logical payloads below 2 MiB retain 64-byte alignment. For logical payloads at least 2 MiB, `posix_memalign` uses the configured 4 KiB or 2 MiB alignment and the original logical byte count; exact-size pool keys, cache accounting, and `std::free` remain unchanged. With the hint enabled, the allocator calls `madvise(pointer, floor(bytes/4096)*4096, MADV_HUGEPAGE)`. The pointer is page-aligned and the advised range stays inside the allocation. A failed hint is recorded and does not change allocation/API behavior. Larger allocator alignment can add allocator-internal padding/fragmentation; this is not an RSS measurement and is not included in the logical pool byte cap.

The benchmark driver is shared by the V3 controls and all candidates. Candidate workspace addresses and `/proc/self/smaps` VMA `AnonHugePages` values are dumped once, after all five workloads and timed calls finish. The independent probe reports its own hint return count/errno and the mapping containing its large allocation. A successful `madvise` return is advisory acceptance only; actual `AnonHugePages` is reported separately. V3's frozen library has no candidate allocator snapshot hook, so its post-run marker is unavailable by design. These observations do not measure global traffic or identify a hardware bottleneck.

Assembly is unchanged byte-for-byte from the isolated base (`src/kernels.S` SHA-256 `94af3cf4345b2383100e4d8d883be57b084ec68d12e056f80c4a8bb77bc9bd68`). The experiment-specific source identity is [`PAGE_LAYOUT_SOURCE_SNAPSHOT.json`](../bench/8454h/roofline_v4/page_layout_src/PAGE_LAYOUT_SOURCE_SNAPSHOT.json); the prior `SOURCE_ORIGIN.json` is retained only as base provenance. CMake identities record both page knobs, assembly/core/allocator/driver hashes, and the oneMKL runtime hash. Checkpoints include alignment and hint in their source ID.

System THP state was not modified. The official Linux kernel THP manual was saved at [`third_party/manuals/linux-transhuge.html`](../third_party/manuals/linux-transhuge.html), SHA-256 `9210d85532f46083a1d410b574cbc02ac63f1228479ea1cba7e8792bd3b91a25`; [official online manual](https://docs.kernel.org/admin-guide/mm/transhuge.html). It describes MADV_HUGEPAGE as a range-level hint and transparent promotion as conditional. This experiment neither changed sysfs nor NUMA settings.

| Candidate | Large allocation alignment | MADV_HUGEPAGE | Direct probe result | Probe calls / success / failure / errno | Benchmark calls / success / failure / errno | Probe VMA AnonHugePages | Benchmark cached buffers with AnonHugePages > 0 | Max reported VMA AnonHugePages |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| a4k_hint0 | 4096 B | 0 | pass | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 KiB | 0/13 | 0 KiB |
| a4k_hint1 | 4096 B | 1 | pass | 1 / 1 / 0 / 0 | 14 / 14 / 0 / 0 | 6144 KiB | 13/13 | 522240 KiB |
| a2m_hint0 | 2097152 B | 0 | pass | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 KiB | 0/13 | 0 KiB |
| a2m_hint1 | 2097152 B | 1 | pass | 1 / 1 / 0 / 0 | 14 / 14 / 0 / 0 | 8192 KiB | 13/13 | 524288 KiB |

The per-process smaps dump is linked from each candidate's `records/<candidate>/allocator_smaps.json`. Each value covers the VMA containing the cached allocation pointer, which may include allocator mapping overhead. Values from multiple pointers can refer to the same VMA; counts/sums must not be interpreted as unique resident bytes.

## Numerical and timing protocol

The immutable V3 library SHA-256 is `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`; the oneMKL runtime SHA-256 is `b2ff0e31d7cd18c91813d8f6500f37665597d89de22649d90687aa6bf7bd2c0f`. All builds use mode 0, FP64 batch 2, CBM 128, automatic CBN, 64-byte wide-row padding, tileloaddt1, BK=256, and FP32 late32 off. Inputs use uniform generation with seed base 260904 (N=8192 seed 269096), 64 threads on cpuset `0-63`, OMP places `cores`, bind `close`, and MKL GNU threading. Each candidate has 3 CTests, the full 20-case byte/semantic gate, a separate allocation probe, and N=8192 five-workload measurements with 3 repetitions. Frozen V3 controls bracket the candidates with 7 repetitions each. Full API wall is primary; profile phases and the MKL GEMM-only reference remain separate.

Gate evidence:

- `a4k_hint0`: 20/20 output-byte/semantic cases passed; gate `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint0_full.json` (SHA `8ed86424dd42912787d2178c636c879c2f10a6c9649903e9081f21ea2561b962`).
- `a4k_hint1`: 20/20 output-byte/semantic cases passed; gate `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint1_full.json` (SHA `b497e86e994e34606efea76426ed21ad6722ac67ad5997f5b5b1f395c2d715dc`).
- `a2m_hint0`: 20/20 output-byte/semantic cases passed; gate `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint0_full.json` (SHA `767079506b47b039e088c0beec23989e8016c877c5141de43223a926e3877fe5`).
- `a2m_hint1`: 20/20 output-byte/semantic cases passed; gate `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint1_full.json` (SHA `4efa6cc3a6e0ea4789a62c8dda2b306082dd0a4c8c2a9020d9c9d9ea5f749796`).

CTest evidence:

- `a4k_hint0`: 3/3 passed; log `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a4k_hint0_ctest.log`.
- `a4k_hint1`: 3/3 passed; log `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a4k_hint1_ctest.log`.
- `a2m_hint0`: 3/3 passed; log `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a2m_hint0_ctest.log`.
- `a2m_hint1`: 3/3 passed; log `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/logs/a2m_hint1_ctest.log`.

## Per-workload raw timings

All times below are milliseconds. `API [3]` and `compute+recon [3]` list the preserved per-repetition raw samples in their original order. `Δ API` compares the candidate mean to the midpoint of the initial/final V3 API means; `V3 drift` is final versus initial V3. Positive deltas mean slower. Three samples are descriptive only.

| Workload | Candidate | API raw [3] | Δ API vs V3 midpoint | V3 drift | Compute+recon raw [3] | Δ compute vs V3 midpoint | Split / pack / profile-total means | MKL GEMM mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| FP32 | a4k_hint0 | `[154.614, 183.626, 206.193]` | -27.01% | +102.32% | `[142.777, 172.222, 195.184]` | -27.73% | 11.409 / 0.001 / 181.471 | 149.096 |
| FP32 | a4k_hint1 | `[160.653, 148.824, 183.368]` | -33.93% | +102.32% | `[147.489, 136.529, 170.800]` | -35.57% | 12.667 / 0.000 / 164.273 | 151.855 |
| FP32 | a2m_hint0 | `[235.603, 221.081, 171.234]` | -15.82% | +102.32% | `[223.677, 209.438, 159.502]` | -16.05% | 11.759 / 0.000 / 209.298 | 153.762 |
| FP32 | a2m_hint1 | `[279.759, 278.603, 279.279]` | +12.30% | +102.32% | `[265.831, 264.167, 265.313]` | +12.66% | 14.100 / 0.000 / 279.204 | 146.826 |
| FP64 p6 | a4k_hint0 | `[253.666, 275.600, 321.501]` | -16.67% | +75.99% | `[212.071, 233.197, 280.022]` | -17.47% | 41.818 / 0.000 / 283.582 | 296.713 |
| FP64 p6 | a4k_hint1 | `[252.199, 222.891, 219.992]` | -31.92% | +75.99% | `[208.325, 180.475, 177.812]` | -35.53% | 42.815 / 0.001 / 231.687 | 293.018 |
| FP64 p6 | a2m_hint0 | `[312.001, 304.063, 225.741]` | -17.55% | +75.99% | `[270.199, 262.128, 184.034]` | -18.49% | 41.807 / 0.000 / 280.594 | 293.269 |
| FP64 p6 | a2m_hint1 | `[402.661, 403.154, 391.251]` | +17.25% | +75.99% | `[353.384, 355.929, 345.419]` | +20.01% | 47.436 / 0.000 / 399.014 | 297.784 |
| FP64 p10 | a4k_hint0 | `[315.860, 333.940, 375.488]` | -31.18% | +65.35% | `[272.668, 290.739, 332.180]` | -33.87% | 43.227 / 0.000 / 341.756 | 297.711 |
| FP64 p10 | a4k_hint1 | `[327.636, 344.849, 310.263]` | -34.03% | +65.35% | `[279.810, 300.818, 265.789]` | -37.50% | 45.436 / 0.000 / 327.575 | 342.432 |
| FP64 p10 | a2m_hint0 | `[333.625, 378.310, 348.232]` | -28.83% | +65.35% | `[290.416, 335.236, 305.094]` | -31.28% | 43.134 / 0.000 / 353.382 | 291.687 |
| FP64 p10 | a2m_hint1 | `[623.116, 554.685, 574.575]` | +17.63% | +65.35% | `[576.324, 491.525, 529.712]` | +17.96% | 51.598 / 0.000 / 584.118 | 302.917 |
| FP64 p15 | a4k_hint0 | `[469.263, 471.307, 486.347]` | -28.45% | +82.77% | `[395.373, 426.904, 441.992]` | -31.23% | 54.208 / 0.000 / 475.632 | 300.782 |
| FP64 p15 | a4k_hint1 | `[613.573, 472.439, 459.600]` | -22.50% | +82.77% | `[568.623, 427.353, 412.031]` | -23.41% | 45.861 / 0.000 / 515.197 | 302.332 |
| FP64 p15 | a2m_hint0 | `[462.374, 701.668, 532.390]` | -14.93% | +82.77% | `[417.799, 657.258, 487.356]` | -15.01% | 44.665 / 0.000 / 565.470 | 304.388 |
| FP64 p15 | a2m_hint1 | `[820.007, 823.454, 819.745]` | +23.51% | +82.77% | `[769.998, 752.709, 770.469]` | +24.74% | 56.667 / 0.001 / 821.060 | 316.352 |
| FP64 p21 | a4k_hint0 | `[605.490, 602.390, 597.348]` | -28.04% | +68.93% | `[558.118, 548.921, 551.181]` | -29.11% | 48.996 / 0.000 / 601.736 | 311.872 |
| FP64 p21 | a4k_hint1 | `[559.857, 542.407, 661.977]` | -29.67% | +68.93% | `[512.577, 494.195, 615.563]` | -30.64% | 47.294 / 0.000 / 588.073 | 305.651 |
| FP64 p21 | a2m_hint0 | `[565.486, 600.448, 588.500]` | -30.06% | +68.93% | `[518.285, 550.898, 542.191]` | -31.11% | 47.679 / 0.001 / 584.804 | 307.469 |
| FP64 p21 | a2m_hint1 | `[1415.118, 1397.754, 1102.952]` | +56.10% | +68.93% | `[1363.801, 1344.148, 1047.819]` | +60.56% | 53.343 / 0.001 / 1305.266 | 396.450 |

Frozen-control API wall means (ms), initial → final, and drift:

- FP32: 164.486 → 332.792 (+102.32%).
- FP64 p6: 246.623 → 434.024 (+75.99%).
- FP64 p10: 374.281 → 618.860 (+65.35%).
- FP64 p15: 470.176 → 859.340 (+82.77%).
- FP64 p21: 621.874 → 1050.536 (+68.93%).

The bracketing V3 control moved substantially: absolute drift ranged from 65.35% to 102.32% across the five workloads. Candidates ran sequentially in the stated order rather than interleaved, so candidate-versus-midpoint deltas are strongly exposed to shared-host drift and are descriptive only. The table retains the raw triples for later review; the matched follow-up should make any performance comparison.

## Artifact paths and limits

Candidate libraries:

- `a4k_hint0`: [`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint0/libozamx.a`](../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint0/libozamx.a) — SHA-256 `71749f8581951a37354584b895f62fa2a2ad0d728c6d7f9f0a5adbac9fd7dc0d`; build identity `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint0/build_identity.json`.
- `a4k_hint1`: [`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/libozamx.a`](../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/libozamx.a) — SHA-256 `dbec090534a1c920ebc533e4a5394c1a0a7b83582526ea1d7362f9f43face1af`; build identity `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/build_identity.json`.
- `a2m_hint0`: [`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint0/libozamx.a`](../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint0/libozamx.a) — SHA-256 `2fc1c0aade9fd1089adf7808bfe01f109aa0d8a558f49a11e39217d621751a8d`; build identity `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint0/build_identity.json`.
- `a2m_hint1`: [`bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/libozamx.a`](../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/libozamx.a) — SHA-256 `91ce6bdf48976cc5f9a60db6b15f7861547099060341fc9a57bc6652aa9fbfd4`; build identity `bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/build_identity.json`.

V3 matched follow-up should use these exact paths and library hashes. No candidate is declared a winner from this three-repetition screen. `madvise` success and VMA `AnonHugePages` are reported independently; even a rise in huge-page backing does not establish that address translation limited GEMM. No PMU evidence or whole-system traffic attribution was collected. The run preserves every build log, gate, probe, benchmark CSV/checkpoint, metadata record, and post-run smaps snapshot under the dataset directory.
