# 8454H tuning search results

## Scope and reproducibility

Search study fingerprint: `c0eafaa4c07f9445406dea2d62abc81d982da40aeae5b34f26c2ea1f4dbc0663` (runner v2). No production source or CMake files were modified during the search. Every variant passed CTest and the strict 100-case native gate (0 bitwise mismatches, 0 padding failures). The runner serialized build, correctness, and benchmark work with `/tmp/ozamx-perf.lock`, on CPUs 0–63 with 64 OpenMP threads, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, and `OMP_DYNAMIC=FALSE`.

The final stage used three interleaved passes, one warmup and seven fixed-input repetitions per configuration, across N=256/1024/4096/8192, FP32, and FP64 slice budgets 6/10/15/21. The holdout used N=512/2048 with the same budgets. Comparisons below use the median `wall_s`, including dispatch and teardown; component `total_s` is also recorded in the raw CSV and metrics JSON. All per-repetition results, checksums, and rusage deltas remain under `bench/8454h/search/runs/c0eafaa4c07f9445/`; stage rankings are in `bench/8454h/search/selection_final_c0eafaa4c07f9445.json`.

## Selected configuration

The paired final comparison selected `OZAMX_PREP_GRAIN=16384` plus `OZAMX_TILELOAD_HINT=1` (`refine_04`), with other settings at defaults (cache block 128, minimum compute work 8, load schedule 0, loop order 0, M/N order 0). Its geometric mean speedup over default was 1.254x across 20 measured configurations. An independent holdout gave 1.194x across ten configurations.

| Input | Final paired speedup range | Holdout speedup |
|---|---:|---:|
| FP32 N=256 | 1.55x | — |
| FP32 N=512 | — | 1.39x |
| FP32 N=1024 | 3.08x | — |
| FP32 N=2048 | — | 1.12x |
| FP32 N=4096 | 1.01x | — |
| FP32 N=8192 | 0.99x | — |
| FP64 N=256, p6/p10/p15/p21 | 1.57/1.56/1.57/1.57x | — |
| FP64 N=512, p6/p10/p15/p21 | — | 1.44/1.40/1.42/1.34x |
| FP64 N=1024, p6/p10/p15/p21 | 1.31/1.22/1.42/1.16x | — |
| FP64 N=2048, p6/p10/p15/p21 | — | 1.00/1.02/0.97/1.01x |
| FP64 N=4096, p6/p10/p15/p21 | 0.98/1.05/1.04/1.05x | — |
| FP64 N=8192, p6/p10/p15/p21 | 1.05/1.00/1.02/1.04x | — |

The improvement is concentrated in small matrices; medium and large inputs are generally near neutral, with a few percent movement. The second finalist, `OZAMX_PREP_GRAIN=16384` plus `OZAMX_MIN_COMPUTE_WORK=1`, was rejected: it regressed FP32 N=256 to 0.19x and FP64 N=256 to 0.36–0.43x, and also regressed FP64 N=4096 to 0.79–0.98x. It did improve N=1024, which was not enough to offset those losses.

Scout's apparent large-input `prep16k` advantage was not robust in the larger paired test. For FP64 N=4096 p21, scout default repetitions were 173.27/176.42/217.83 ms, while `prep16k` was 98.16/97.63/105.72 ms. The final paired result for the selected `prep16k+T1` was only about 1.05x for p21 and 0.98x for p6. One default scout repetition also had 85,182 minor faults, 1,232 voluntary context switches, and 1.685 s of system CPU time, versus 49,158 faults, 36 switches, and 0.540 s for the third `prep16k` repetition. This confirms the initial scout was affected by system noise and should not be used as a large-shape estimate. For FP32 N=1024, by contrast, default scout wall was 2.18/2.20/1.89 ms and `prep16k` was 0.74/0.65/0.65 ms; the final paired medians remained 2.094 vs 0.681 ms.

## Workspace pool cap

The separate N=8192 pool comparison alternated three 5-repetition passes between the default 1 GiB cap and a 4 GiB cap. At 4 GiB, FP64 p6 wall fell from 610.07 to 319.66 ms (1.91x), and p21 fell from 1295.61 to 814.16 ms (1.59x). Median minor faults fell from 524,331 to 0 at p6, and from 917,516 to 65,536 at p21; system CPU time also fell from 6.50 to 0.034 s at p6 and from 11.31 to 0.63 s at p21. User CPU time was similar between caps. This supports retaining more workspaces for repeated large calls, but the results are specific to the tested N=8192 p6/p21 sequence; the 4 GiB memory-retention tradeoff should be considered separately from the tuning winner.

`perf_event_open` cycles counters were unavailable (`EACCES`, errno 13; host `perf_event_paranoid=4`), so no hardware-counter claims are made. `max_rss_kib` in the CSV is the process cumulative high-water mark, not per-call memory usage. Raw rusage fields are recorded for diagnosing faults and context switches, not used as the primary objective.


## Run and artifact audit

For this source fingerprint, all expected 50 stage/pass jobs are present: scout 16, refine 13, final 9, holdout 6, and pool 6. They comprise 30 distinct variant labels (27 distinct compile-time definition sets across scout/refine, plus the separate 1 GiB and 4 GiB runtime cache-cap profiles). The runner ledger contains 53 `started` and 51 `completed` events because interrupted jobs were retried; the two interrupted final attempts were later completed, and every final artifact passed the runner's fingerprint and raw-CSV hash checks.

The 50 completed jobs each have one CTest pass, one 100-case strict gate summary, and one nonempty benchmark CSV. Each gate compares six baseline/optimized and thread-count combinations; every comparison reports zero bitwise mismatches and zero padding failures. The CSVs contain 2,292 measured repetitions total: scout 288, refine 234, final 1,260, holdout 420, and pool 90.

The manual deep-experiment CSVs listed in [DEEP_EXPERIMENT_INDEX.json](../bench/8454h/search/DEEP_EXPERIMENT_INDEX.json) were audited read-only. Paired CSVs have identical precision/size/budget/rep keys, seeds, and checksums; every rep row has `wall_s >= total_s`, and the split/pack/compute phase sum matches `total_s`. All CSVs in the current snapshot are nonempty, newline-terminated, and have complete contiguous rep IDs. The parent confirmed the four bounded-commit passes are complete; each archived CSV contains the same six configurations × seven reps. The candidate remains unadopted because its measured gain was unstable. The index uses source/binary hashes only where the pre-existing `experiment_metadata.json` explicitly records them; missing hashes and validation evidence remain marked absent.


The exact study source snapshot is archived in `bench/8454h/search/source_base/`. Its manifest verifies all 17 lineage-listed source files against the original study hashes (source fingerprint `d53e356393fd464727e12d7863c64b63098f5108e1b7f18410ecb45c57ad9c66`). The snapshot was reconstructed from the matching v2 candidate tree and benchmark/gate sources, then `v2_candidate.patch` was reverse-applied only inside the snapshot. A separate disposable copy had the patch reapplied and reproduced the candidate `gemm.cpp` and `preprocess.hpp` hashes exactly. No build or CPU test was run during this archival step.
