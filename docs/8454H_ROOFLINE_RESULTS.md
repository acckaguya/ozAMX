# 8454H roofline-guided production results

The frozen V3 source, validation, calibration, search data, reports, and verified production library are collected in the [V3 release archive](../bench/8454h/versions/v3_release/README.md).

The roofline-guided production archive completed the 20-case oneMKL matrix with `status=ok` in every row and 20 complete checkpoints. Raw five-sample API-wall timings, phase timings, checksums, error metrics, and configuration data are retained in [`full_roofline_v3.csv`](../bench/8454h/mkl_roofline_v3/full_roofline_v3.csv); run provenance and hashes are in [`provenance.json`](../bench/8454h/mkl_roofline_v3/provenance.json). No timing samples were removed.

## Measurement protocol

All three data sets use N=256/1024/4096/8192; FP32 p6 and FP64 p6/p10/p15/p21; 5 timed calls after one warmup; uniform inputs; base seed 260904 (resolved seed 260904+N); 64 threads on CPUs 0–63; close OpenMP binding; and GNU-threaded MKL LP64. The historical candidate used a 1 GiB workspace cache; frozen V2 production and V3 used 2 GiB. The new run linked `/tmp/ozamx-roofline-production/libozamx.a`, SHA-256 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`. Driver source ID is `mkl-wall-roofline-v3-20261013`; `bench/benchmark.cpp` carries the same ID, and binary and runtime hashes are in provenance.

The `V2 historical candidate` column is the earlier isolated 1 GiB candidate in `bench/8454h/mkl_v2/full_candidate.csv`. `V2 frozen production` is the immutable production archive measurement in `bench/8454h/mkl_production/full_production.csv` (archive SHA-256 `ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251`). Those columns must not be conflated: the adaptive V3 comparison uses the frozen production column as its baseline.

ozAMX times below are complete profiled API wall means, including dispatch and teardown; V3 shows mean ± population standard deviation over five calls. The MKL column is a GEMM-only five-call mean. Consequently the `API/MKL` ratio is descriptive rather than an end-to-end matched comparison.

## All 20 configurations

Wall and MKL times are milliseconds. “Change vs frozen V2” is `100 × (1 − V3 wall mean / frozen V2 wall mean)`; positive values indicate lower measured V3 mean.

| N | Mode | V2 historical candidate | V2 frozen production | V3 API wall mean ± SD | Change vs frozen V2 | MKL GEMM mean | API/MKL |
|---:|:---|---:|---:|---:|---:|---:|---:|
| 256 | FP32 p6 | 0.480 | 0.445 | 0.424 ± 0.064 | +4.6% | 0.060 | 7.093× |
| 256 | FP64 p6 | 1.213 | 0.910 | 1.054 ± 0.105 | -15.8% | 0.103 | 10.203× |
| 256 | FP64 p10 | 0.915 | 0.943 | 0.934 ± 0.028 | +1.0% | 0.083 | 11.292× |
| 256 | FP64 p15 | 0.933 | 1.091 | 1.029 ± 0.049 | +5.7% | 0.102 | 10.090× |
| 256 | FP64 p21 | 1.018 | 1.113 | 1.033 ± 0.023 | +7.2% | 0.101 | 10.252× |
| 1024 | FP32 p6 | 0.654 | 0.634 | 0.767 ± 0.106 | -21.0% | 0.511 | 1.501× |
| 1024 | FP64 p6 | 2.689 | 2.514 | 2.576 ± 0.073 | -2.5% | 0.785 | 3.281× |
| 1024 | FP64 p10 | 3.621 | 2.777 | 2.844 ± 0.150 | -2.4% | 0.781 | 3.643× |
| 1024 | FP64 p15 | 3.434 | 2.966 | 3.193 ± 0.333 | -7.7% | 0.772 | 4.138× |
| 1024 | FP64 p21 | 3.527 | 3.297 | 3.396 ± 0.049 | -3.0% | 0.752 | 4.513× |
| 4096 | FP32 p6 | 23.165 | 23.956 | 19.962 ± 1.619 | +16.7% | 19.902 | 1.003× |
| 4096 | FP64 p6 | 36.246 | 32.260 | 31.339 ± 0.222 | +2.9% | 87.882 | 0.357× |
| 4096 | FP64 p10 | 54.483 | 46.968 | 46.355 ± 6.797 | +1.3% | 38.527 | 1.203× |
| 4096 | FP64 p15 | 69.516 | 59.905 | 54.935 ± 0.308 | +8.3% | 38.526 | 1.426× |
| 4096 | FP64 p21 | 94.881 | 77.818 | 71.206 ± 0.673 | +8.5% | 38.574 | 1.846× |
| 8192 | FP32 p6 | 192.056 | 195.997 | 157.479 ± 13.171 | +19.7% | 139.209 | 1.131× |
| 8192 | FP64 p6 | 377.161 | 261.761 | 227.725 ± 14.353 | +13.0% | 401.803 | 0.567× |
| 8192 | FP64 p10 | 481.120 | 356.544 | 429.420 ± 169.409 | -20.4% | 314.878 | 1.364× |
| 8192 | FP64 p15 | 670.237 | 563.323 | 444.752 ± 27.267 | +21.0% | 315.116 | 1.411× |
| 8192 | FP64 p21 | 874.570 | 632.018 | 579.257 ± 23.692 | +8.3% | 315.035 | 1.839× |

V3 has a lower observed API-wall mean than frozen V2 in 13 of 20 rows. The largest-N row changes versus frozen V2 are FP32 p6 +19.7%, FP64 p6 +13.0%, p10 −20.4%, p15 +21.0%, and p21 +8.3%. FP64 p10 at N=8192 had a large V3 population SD (169.409 ms against a 429.420 ms mean), and the N=4096/8192 MKL means also show isolated high timings. These are retained without outlier removal; treat the affected means as noisy and avoid reading them as stable wins or regressions. Smaller-size differences are also noisy relative to their sub-millisecond wall times.

## Accuracy and scope

Every V3 row reports `ok`. Across the matrix, the maximum relative Frobenius error against oneMKL is `3.96771e-7` (FP32 p6, N=8192); maximum scaled component error against oneMKL is `2.35746e-7` (FP32 p6, N=256). The maximum high-precision relative error is `1.84063e-7` (FP32 p6, N=8192); maximum high-precision scaled component error is `9.10035e-8` (FP32 p6, N=256). The CSV retains every per-row error and checksum.

The comparison describes the whole ozAMX profiled API against the separate GEMM-only MKL call. It does not claim equal timing scope. Source/library/runtime/driver/binary hashes, CMake options, executable command, and all 20 checkpoint hashes are recorded in the V3 provenance bundle.

## Matched frozen V2/V3 recheck

A supplemental five-process sequence compares frozen V2, V3, frozen V2, V3, frozen V2. It covers N=1024/2048/8192, FP32 p6 and FP64 p6/p10/p15/p21, with seven timed calls after one warmup per configuration. Inputs, seed rule, 64-thread placement, MKL LP64 GNU runtime, and 2 GiB workspace cache are matched. Every row completed with `status=ok`; all 75 configuration rows and all 525 timed samples are retained. The [run protocol](../bench/8454h/mkl_roofline_v3/matched_recheck/README.md), [analysis script](../bench/8454h/mkl_roofline_v3/matched_recheck/analyze.py), and complete [comparison JSON](../bench/8454h/mkl_roofline_v3/matched_recheck/comparison.json) link the five per-process CSVs, raw sample arrays, per-process medians/means/population SDs, and provenance. The individual source data are [p1 V2](../bench/8454h/mkl_roofline_v3/matched_recheck/p1_v2a/full.csv), [p2 V3](../bench/8454h/mkl_roofline_v3/matched_recheck/p2_v3a/full.csv), [p3 V2](../bench/8454h/mkl_roofline_v3/matched_recheck/p3_v2b/full.csv), [p4 V3](../bench/8454h/mkl_roofline_v3/matched_recheck/p4_v3b/full.csv), and [p5 V2](../bench/8454h/mkl_roofline_v3/matched_recheck/p5_v2c/full.csv). The analysis validates every CSV hash, checkpoint hash, source ID, and library SHA. V2 uses frozen archive SHA `ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251`; V3 uses `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`.

The primary comparison is the median of the three V2 process medians against the median of the two V3 process medians, using each process's seven raw API-wall samples. Positive change means the V3 median is lower. The table shows API-wall medians and the equivalent raw MKL GEMM medians, in milliseconds. Split and compute/reconstruction timing summaries are in the JSON as secondary diagnostics. Means and population SDs are reported independently there; they are not substituted for medians. ozAMX API wall encloses the complete profiled API call, while MKL timing encloses GEMM only, so their absolute times do not have matched scope.

| N | Mode | V2 API wall median | V3 API wall median | V3 change | V2 MKL GEMM median | V3 MKL GEMM median |
|---:|:---|---:|---:|---:|---:|---:|
| 1024 | FP32 p6 | 0.599 | 0.595 | +0.7% | 0.448 | 0.486 |
| 2048 | FP32 p6 | 3.281 | 3.172 | +3.3% | 2.559 | 2.416 |
| 8192 | FP32 p6 | 186.705 | 149.744 | +19.8% | 142.166 | 139.081 |
| 1024 | FP64 p10 | 2.820 | 2.646 | +6.2% | 0.735 | 0.732 |
| 2048 | FP64 p10 | 8.568 | 8.211 | +4.2% | 5.277 | 4.885 |
| 8192 | FP64 p10 | 362.411 | 331.131 | +8.6% | 319.843 | 314.692 |
| 1024 | FP64 p15 | 3.013 | 2.713 | +9.9% | 0.704 | 0.727 |
| 2048 | FP64 p15 | 10.355 | 9.823 | +5.1% | 5.288 | 4.910 |
| 8192 | FP64 p15 | 492.770 | 443.418 | +10.0% | 294.025 | 321.373 |
| 1024 | FP64 p21 | 3.737 | 3.107 | +16.9% | 0.761 | 0.762 |
| 2048 | FP64 p21 | 12.768 | 12.217 | +4.3% | 4.972 | 4.889 |
| 8192 | FP64 p21 | 625.264 | 577.593 | +7.6% | 325.836 | 321.345 |
| 1024 | FP64 p6 | 2.511 | 2.195 | +12.6% | 0.720 | 0.706 |
| 2048 | FP64 p6 | 6.947 | 7.060 | -1.6% | 4.823 | 5.046 |
| 8192 | FP64 p6 | 282.815 | 216.841 | +23.3% | 298.219 | 328.511 |

At N=8192, the matched V3 API-wall medians are lower by 7.6% to 23.3% across the five modes; at N=2048 they range from 1.6% higher to 5.1% lower. N=1024 shifts vary more by mode, from 0.7% to 16.9% lower. This geometry-preserving recheck does not establish a stable regression at smaller sizes, and it does not validate the earlier approximately 15% observation as a repeatable effect. The shared host showed timing variation, so no samples were dropped as outliers. Read these as results from the measured process sequence, with particular caution for the small sizes.

The earlier formal 20-configuration dataset in `full_roofline_v3.csv` remains intact and separate from this supplemental recheck. Its N=8192 FP64 p10 third-call value of 766 ms remains in the original raw samples; it was not replaced by matched-recheck data.
