# 8454H roofline calibration rerun for the V4 phase

A fresh independent calibration batch is saved at [`bench/8454h/roofline_v4/calibration_20261014/`](../bench/8454h/roofline_v4/calibration_20261014/). The earlier 57-configuration raw archive and its report were left untouched. The current batch reruns the same 57 configurations and the same microkernel source/protocol, linking the frozen V3 production library (`73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`). This supplies a same-batch calibration reference for interpreting V4 diagnostic data; it does not turn diagnostic kernel timings into public GEMM timings.

## Method and audit

The raw CSV has 228 rows: one warmup and three timed repetitions for each of 57 cases. All 171 timed rows passed AMX permission and exact synthetic checksum checks. The cases cover AMX register-resident work, P6/P21 component products with and without reconstruction, FP32 six-product diagnostics with and without reconstruction, TILELOAD/TILELOADT1 at 4 KiB, 1 MiB, 2.25 MiB and 24 MiB per worker, and pure FP32/FP64 reconstruction at the old strides. Threads are 1, 32 and 64.

The run used CPUs 0–63, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, `OMP_DYNAMIC=FALSE`, worker-local allocation and first-touch, per-worker AMX permission, and an 80 ms minimum synchronized interval per sample. Allocation, initialization, tile configuration, checksum and freeing remain outside the timed interval. All compilation, disassembly, and benchmark execution held `/tmp/ozamx-perf.lock`. Summed measured windows were 13.722 s timed plus 4.574 s warmup; whole-process wall time was not separately captured. The executable does not link or call MKL, so MKL is not applicable to this calibration.

Raw data, source snapshot, exact linked `libozamx.a`, binary, disassembly, command, environment, checksums, and full per-configuration statistics are saved in the batch directory. The binary SHA is `6812e6e4873e9c0117b8ecefcd492edd30cb3d6e4b2cf4c7b9ac6f9d0c4c0f0f`; raw CSV SHA is `494fdaafe991e3f647291f986af0fc44c6ed4a33e6ecd2e7b89f94f1b738f052`. The binary is byte-identical to the previous calibration binary even though the linked static-library archive SHA differs. The fresh linked-library SHA is separately retained and verified.

## Selected 64-thread results

Values are median ± sample standard deviation over the three timed repetitions. For product rows the CSV's AMX operation rate is reported, with the MIX rate including the same counted AMX operations as in the previous report; reconstruction additions are excluded from that AMX-only figure. These are synthetic kernel diagnostics, not production GEMM rates.

| Kernel | Previous calibration | New batch | New/previous |
|---|---:|---:|---:|
| AMX register-only | 161.034 ± 0.236 TFLOP/s | 161.018 ± 0.055 TFLOP/s | 0.99990 |
| P6 no reconstruction | 121.677 ± 0.332 TFLOP/s | 121.593 ± 0.400 TFLOP/s | 0.99931 |
| P21 no reconstruction | 123.662 ± 0.465 TFLOP/s | 123.239 ± 0.389 TFLOP/s | 0.99658 |
| P6 with FP64 reconstruction | 85.443 ± 0.070 TFLOP/s | 84.423 ± 0.620 TFLOP/s | 0.98806 |
| P21 with FP64 reconstruction | 86.336 ± 0.152 TFLOP/s | 86.306 ± 0.296 TFLOP/s | 0.99965 |
| FP64 reconstruction only | 666.455 ± 0.156 GFLOP/s | 665.605 ± 0.171 GFLOP/s | 0.99872 |
| FP32 reconstruction only | 1946.547 ± 20.602 GFLOP/s | 1948.699 ± 39.734 GFLOP/s | 1.00111 |

The new register-only ceiling is 161.018 TFLOP/s for this batch. Its close agreement with the earlier measurement is a useful repeatability check, not a measured physical roof. P6-with-reconstruction differs by about 1.2%; without a larger controlled study, the difference should be treated as ordinary run-to-run or environment variation rather than attributed to the library change.

## TILELOAD payload-rate context

These are logical 4 KiB tile-load payload rates, not measured cache or memory traffic. The input footprint is per worker; it is not proof of residency at any cache level.

| Per-worker footprint | TILELOAD old → new (GB/s) | TILELOADT1 old → new (GB/s) |
|---:|---:|---:|
| 4 KiB | 20832.06 → 19377.22 | 20744.33 → 20783.06 |
| 1 MiB | 8463.06 → 8478.06 | 9337.81 → 9307.45 |
| 2.25 MiB | 2625.28 → 2537.84 | 2643.10 → 2644.26 |
| 24 MiB | 534.42 → 534.49 | 525.36 → 528.04 |

The input sizes are the worker allocations in the benchmark; the 64-thread 2.25 MiB case totals 144 MiB. `TILELOADT1` is a hint, not a cache-level selector. No PMU traffic or cache-miss counters were collected, so these rates cannot establish a physical DRAM roof or assign datapoints to cache levels.

## Use with V4 diagnostics

Use this batch as the current same-host calibration context when discussing V4 diagnostic modes. Keep its scope separate from the V4 complete-call measurements and from physical memory claims. In particular, the no-reconstruction product cases omit required numeric accumulation/reconstruction, and MIX is still a small tile-path microbenchmark rather than public GEMM. See the [V4 diagnostic report](8454H_V4_DIAGNOSTIC_RESULTS.md) for those mode timings and limits. The [machine-readable summary](../bench/8454h/roofline_v4/calibration_20261014/analysis.json) includes all 57 same-configuration old/new comparisons and every sample.
