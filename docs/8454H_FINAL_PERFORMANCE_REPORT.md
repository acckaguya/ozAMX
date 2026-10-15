# 8454H final production performance report

> **Historical V2 report:** this report preserves the completed V2 measurements and their original interpretation. V2 remains immutable in [`v2_release`](../bench/8454h/versions/v2_release/README.md). Current production is V3; see the [V3 Roofline results and matched recheck](8454H_ROOFLINE_RESULTS.md) and [V3 model](8454H_ROOFLINE_MODEL.md).

**V2 status:** completed against the frozen production library at `/tmp/ozamx-production-final/libozamx.a`; source ID `mkl-wall-production-final-20261013`. The full raw CSV, all 20 checkpoints, source/library/driver hashes and run protocol are archived under [`bench/8454h/mkl_production`](../bench/8454h/mkl_production/README.md).

The release review bundle is [`v2_release`](../bench/8454h/versions/v2_release/README.md); it supplements the immutable [`v2` source snapshot](../bench/8454h/versions/v2/README.md). A new roofline-guided search has been initialized in [`8454H_ROOFLINE_SEARCH_LOG.md`](8454H_ROOFLINE_SEARCH_LOG.md); no new roofline measurements are included in this report.

## Frozen production configuration

The measured production source instantiates eager and late64 FP64 paths separately; K≥4096 selects late64, while smaller K keeps eager checks. Large aligned matrices use the fused path. The bounded-commit combination, late32, and pending-pipeline variants were not adopted. The selected build uses the final CMake/header defaults, including `OZAMX_PREP_GRAIN=16384`, `OZAMX_TILELOAD_HINT=1`, and a 2 GiB workspace-cache cap. The complete source SHA set and all CMake options are in [`provenance.json`](../bench/8454h/mkl_production/provenance.json).

The frozen production source passed fresh CMake build, OpenMP ON/OFF CTest, native audit, 100-case bitwise equivalence at 1/4/64 threads, cache-on/off comparisons, irregular long-K transactional probes and alias checks. Full evidence is in [V2_VALIDATION.md](../bench/8454h/V2_VALIDATION.md); the [standalone source snapshot](../bench/8454h/versions/v2/README.md) rebuilds to the exact production-library hash. The experiment linked the exact fresh static library whose hash is recorded in provenance. Final source and binary identities are:

- `src/gemm.cpp`: `8a5d27440c604df9304b75769e3c048a6748789aab6ee8fed3a5c3446335a85b`
- `src/preprocess.hpp`: `df36a028fbbeec62bcacc5a0a50194f917285d20fd9cf231abd4c28d4013ee31`
- `libozamx.a`: `ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251`
- benchmark binary: `266a2dfff5f6ffe03978ea9b1e98600e0ccc8bdca9c48447e021e5ed18bec461`

## Measurement protocol

The run used the dual-socket Xeon Platinum 8454H host (2×32 physical cores, 128 logical CPUs, two NUMA nodes, 165 MiB aggregate LLC; frequency was not pinned and the governor was `powersave`). It held `flock -x /tmp/ozamx-perf.lock` across driver compilation and measurement. It used CPUs 0–63, 64 OpenMP threads, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, `OMP_DYNAMIC=FALSE`, GNU-threaded oneMKL 2026.1, and `OZAMX_WORKSPACE_CACHE_BYTES=2147483648`. The CMake library build was the reported warning-free final Release build with `-O3`, `-mamx-tile`, `-mamx-bf16`, `-fopenmp`, and GEMM-specific `-march=sapphirerapids -ffp-contract=off`; build compile commands and options are hashed in provenance. The separately compiled wall driver emitted nonfatal existing warnings for compact parser indentation and an unused helper; this does not reflect warnings from the production CMake library. The matrix covers N=256, 1024, 4096, 8192; FP32 p6 and FP64 p6/p10/p15/p21; uniform inputs in [-1,1], base seed 260904 with resolved seed `260904 + N`; one first-call warmup and five timed repetitions per configuration. All 20 configurations completed with status `ok`; each has five raw wall/profile samples and a checkpoint.

ozAMX API wall encloses the full profiled call, including dispatch and teardown. The phase/profile total is recorded separately. The oneMKL timer covers GEMM only, so `production wall / MKL GEMM` is an explicitly asymmetric timing ratio, not an end-to-end application comparison. The full table includes v1 wall means/SD, production wall means/SD, v1/production ratios, split/pack/compute/profile phase means, MKL GEMM means, error metrics, and checksums: [production comparison](../bench/8454h/mkl_production/production_comparison.md). Raw repetitions and full CSV fields are in [full_production.csv](../bench/8454h/mkl_production/full_production.csv).

## Results

Compared with frozen v1, final production whole-call wall was faster in 19 of 20 configurations; ratios range from 0.995× to 4.498× when expressed as v1 wall divided by production wall. The one near-tie/regression is FP32 p6 at N=4096 (23.956 ± 5.234 ms final vs 23.837 ± 4.815 ms v1). N=8192 FP32 p6 measured 195.997 ± 19.962 ms vs 311.058 ± 6.137 ms v1. N=8192 FP64 p6 measured 261.761 ± 9.228 ms vs 589.681 ± 14.884 ms v1; p21 measured 632.018 ± 16.404 ms vs 1294.021 ± 18.654 ms v1.

Against oneMKL GEMM-only means, final N=8192 FP32 p6 whole-call wall was 1.379× MKL GEMM time; FP64 p6 was 0.822×, while FP64 p21 was 2.008×. Do not interpret these as matched end-to-end costs: the ozAMX side includes full API dispatch/teardown and MKL does not. Maximum relative error against MKL was `eF_mkl=3.97e-7` (FP32 p6, N=8192); maximum scaled error was `2.36e-7` (FP32 p6, N=256). The detailed table and CSV preserve every checksum and per-config error.

## Full 20-configuration table

Fresh production library SHA-256: `ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251`. All 20 configurations completed with five timed repetitions, one first-call warmup, and `ok` status. Frozen-v1 wall values come from `mkl_v1/full_cmake.csv` with the same configuration, resolved seed, distribution, thread count and API-wall scope. API wall encloses the full ozAMX profiled call including dispatch/teardown; oneMKL timing covers GEMM only.

The phase cell gives `mean ± population SD` in milliseconds for split / pack / compute / profile total. The v1/prod column is v1 API-wall mean divided by final production API-wall mean; prod/MKL compares full API wall with MKL GEMM-only time. Raw phase and wall samples, all errors and checksums are preserved in `full_production.csv`.

| Type | N | Budget | v1 wall mean ± SD (ms) | Production API wall mean ± SD (ms) | v1/prod | Split / pack / compute / profile total means ± SD (ms) | MKL GEMM (ms) | prod wall / MKL | eF vs MKL | scaled error | checksum |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fp32 | 256 | p6 | 0.642 ± 0.142 | 0.445 ± 0.105 | 1.444× | 0.159 ± 0.063 / 0.074 ± 0.003 / 0.210 ± 0.040 / 0.443 ± 0.105 | 0.058 | 7.640× | 3.121e-07 | 2.357e-07 | 712.682745 |
| fp64 | 256 | p6 | 1.303 ± 0.075 | 0.910 ± 0.069 | 1.432× | 0.560 ± 0.027 / 0.067 ± 0.002 / 0.279 ± 0.041 / 0.906 ± 0.064 | 0.106 | 8.578× | 8.492e-08 | 2.979e-08 | 712.683028 |
| fp64 | 256 | p10 | 1.396 ± 0.024 | 0.943 ± 0.011 | 1.481× | 0.592 ± 0.013 / 0.087 ± 0.002 / 0.262 ± 0.011 / 0.941 ± 0.011 | 0.102 | 9.204× | 3.615e-10 | 1.339e-10 | 712.683149 |
| fp64 | 256 | p15 | 1.552 ± 0.060 | 1.091 ± 0.098 | 1.423× | 0.630 ± 0.047 / 0.155 ± 0.091 / 0.304 ± 0.010 / 1.089 ± 0.099 | 0.104 | 10.484× | 1.526e-12 | 5.320e-13 | 712.683149 |
| fp64 | 256 | p21 | 1.668 ± 0.049 | 1.113 ± 0.014 | 1.499× | 0.622 ± 0.010 / 0.137 ± 0.011 / 0.351 ± 0.016 / 1.111 ± 0.014 | 0.108 | 10.300× | 6.387e-15 | 2.292e-15 | 712.683149 |
| fp32 | 1024 | p6 | 2.853 ± 1.281 | 0.634 ± 0.031 | 4.498× | 0.277 ± 0.013 / 0.000 ± 0.000 / 0.356 ± 0.025 / 0.633 ± 0.030 | 0.477 | 1.329× | 3.643e-07 | 1.495e-07 | -1895.29009 |
| fp64 | 1024 | p6 | 3.441 ± 0.142 | 2.514 ± 0.027 | 1.369× | 1.959 ± 0.020 / 0.000 ± 0.000 / 0.553 ± 0.027 / 2.512 ± 0.027 | 0.773 | 3.251× | 8.493e-08 | 1.786e-08 | -1895.29058 |
| fp64 | 1024 | p10 | 3.847 ± 0.160 | 2.777 ± 0.134 | 1.385× | 1.971 ± 0.042 / 0.000 ± 0.000 / 0.804 ± 0.099 / 2.775 ± 0.133 | 0.765 | 3.631× | 3.621e-10 | 7.145e-11 | -1895.29094 |
| fp64 | 1024 | p15 | 4.873 ± 0.147 | 2.966 ± 0.025 | 1.643× | 1.980 ± 0.021 / 0.000 ± 0.000 / 0.984 ± 0.021 / 2.964 ± 0.025 | 0.764 | 3.885× | 1.526e-12 | 2.998e-13 | -1895.29094 |
| fp64 | 1024 | p21 | 4.853 ± 0.062 | 3.297 ± 0.039 | 1.472× | 2.038 ± 0.050 / 0.000 ± 0.000 / 1.256 ± 0.018 / 3.295 ± 0.039 | 0.764 | 4.314× | 6.393e-15 | 1.298e-15 | -1895.29094 |
| fp32 | 4096 | p6 | 23.837 ± 4.815 | 23.956 ± 5.234 | 0.995× | 2.764 ± 0.017 / 0.000 ± 0.000 / 21.184 ± 5.218 / 23.948 ± 5.234 | 19.791 | 1.210× | 3.837e-07 | 5.583e-08 | -151000.143 |
| fp64 | 4096 | p6 | 39.767 ± 4.680 | 32.260 ± 0.177 | 1.233× | 9.266 ± 0.071 / 0.000 ± 0.000 / 22.985 ± 0.129 / 32.251 ± 0.179 | 39.338 | 0.820× | 8.498e-08 | 9.903e-09 | -151000.143 |
| fp64 | 4096 | p10 | 59.771 ± 7.662 | 46.968 ± 3.541 | 1.273× | 9.782 ± 0.099 / 0.001 ± 0.000 / 37.177 ± 3.582 / 46.960 ± 3.542 | 40.486 | 1.160× | 3.626e-10 | 4.347e-11 | -151000.161 |
| fp64 | 4096 | p15 | 76.471 ± 3.638 | 59.905 ± 2.319 | 1.277× | 10.016 ± 0.096 / 0.000 ± 0.000 / 49.881 ± 2.408 / 59.897 ± 2.319 | 38.757 | 1.546× | 1.526e-12 | 1.667e-13 | -151000.161 |
| fp64 | 4096 | p21 | 99.963 ± 12.273 | 77.818 ± 3.676 | 1.285× | 9.943 ± 0.100 / 0.000 ± 0.000 / 67.867 ± 3.723 / 77.810 ± 3.677 | 38.428 | 2.025× | 6.413e-15 | 7.414e-16 | -151000.161 |
| fp32 | 8192 | p6 | 311.058 ± 6.137 | 195.997 ± 19.962 | 1.587× | 11.639 ± 0.340 / 0.000 ± 0.000 / 184.348 ± 19.749 / 195.988 ± 19.962 | 142.141 | 1.379× | 3.968e-07 | 4.165e-08 | -180496.912 |
| fp64 | 8192 | p6 | 589.681 ± 14.884 | 261.761 ± 9.228 | 2.253× | 42.249 ± 1.237 / 0.001 ± 0.000 / 219.504 ± 9.654 / 261.754 ± 9.228 | 318.416 | 0.822× | 8.495e-08 | 6.999e-09 | -180496.855 |
| fp64 | 8192 | p10 | 741.765 ± 16.030 | 356.544 ± 13.590 | 2.080× | 43.464 ± 0.453 / 0.000 ± 0.000 / 313.071 ± 13.763 / 356.536 ± 13.591 | 322.478 | 1.106× | 3.624e-10 | 3.040e-11 | -180496.852 |
| fp64 | 8192 | p15 | 1152.504 ± 239.326 | 563.323 ± 134.190 | 2.046× | 47.992 ± 4.533 / 0.001 ± 0.000 / 515.323 ± 132.476 / 563.316 ± 134.191 | 313.357 | 1.798× | 1.525e-12 | 1.287e-13 | -180496.851 |
| fp64 | 8192 | p21 | 1294.021 ± 18.654 | 632.018 ± 16.404 | 2.047× | 46.643 ± 0.587 / 0.000 ± 0.000 / 585.367 ± 16.922 / 632.010 ± 16.404 | 314.805 | 2.008× | 6.428e-15 | 5.671e-16 | -180496.851 |

## Search and reproducibility

The parameter study completed 50 jobs, 50 CTest runs, 50 strict 100-case gates and 2292 timed repetitions. Selected 16K preprocessing grain and T1 loads passed both repeated final measurements and separate 512/2048 holdouts. [Search results](8454H_SEARCH_RESULTS.md) contain the per-configuration effects and noise analysis. [Kernel ideas](8454H_KERNEL_IDEAS.md) record the deeper implementation/validation/profile cycles, accepted fusion and late64 changes, cache experiments, and rejected pending-pipeline, late32 and bounded-commit candidates.

The original study's [source base](../bench/8454h/search/source_base/README.md) matches all 17 fingerprint files and supports replaying the saved patches. The machine's independently measured SIMD/AMX and memory baseline remains in [8454H_PERFORMANCE_BASELINE.md](8454H_PERFORMANCE_BASELINE.md). These are measured results for the explored space, not a proof of globally maximum performance. An [AMX INT8 full-K integer-accumulation design](../bench/8454h/search/ideas/amx_int8_exact_accumulation.md) is recorded as an unimplemented hypothesis for a subsequent algorithm/accuracy study, and is excluded from this version's performance claims.
