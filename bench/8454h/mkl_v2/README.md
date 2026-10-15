# oneMKL comparison for selected v2 candidate

This checkpoint is an independent v2 measurement against Intel oneMKL 2026.1 using the same host, GNU threading layer, 64-core affinity, deterministic uniform inputs, seed base 260904, N=256/1024/4096/8192, FP32 p6 and FP64 p6/p10/p15/p21, one untimed ozAMX call and five timed calls, and the wall-instrumented `bench/benchmark.cpp` method used in v1. It links the already CMake-built selected candidate archive at `/tmp/ozamx-v2-candidate/build/libozamx.a`; no source in that tree is modified by this comparison. Benchmark API wall includes full profiled ozAMX call/teardown; profile phases are reported separately. oneMKL time covers its GEMM only.

The driver is copied to `benchmark_v2.cpp` from the wall-instrumented common driver with only the checkpoint source ID changed to `mkl-wall-v2-candidate-20261013`, preventing v1 checkpoint reuse. SHA-256 of this driver, linked candidate archive, candidate source tree, output binary, and CMake options are captured in `provenance.json` after compilation. Full command and environment are in `run_command.txt`. The command is intentionally prepared for one locked build-and-run; results and checkpoint files are written here. `full_candidate.csv` is complete with all 20 configurations (one FP32 p6 plus four FP64 budgets for each of four sizes), five raw repetitions per configuration, and 20 complete checkpoints. Its v1 side-by-side API-wall table is in [comparison_v1_v2.md](comparison_v1_v2.md). Provenance hashes, exact environment, seed protocol, CMake options, and the driver hash are in [provenance.json](provenance.json).

Candidate selection was made by the root agent: `/tmp/ozamx-v2-candidate` (eager checks, prep grain 16K / T1 configuration, FP32 direct panel generation, FP64 fused max); fusion applies only when min(M,N)≥1024 and M/N/K are divisible by 256. The benchmark here is square GEMM. Candidate gate and final integrated test status should be attached as evidence separately from these MKL measurements.


Across the matched v1/v2 run, v2 is faster in most configurations, with per-configuration ratios shown in the comparison table; interpretation remains specific to this host and this oneMKL build. The selected v2 candidate was also measured against MKL GEMM-only time, as separately recorded in the CSV.

The matched v1/v2 table shows v2 API-wall means lower for each of the 20 configurations, ranging from 0.229× to 0.972× the corresponding v1 mean. The N=8192 FP32 p6 mean was 192.056 ± 9.728 ms versus 311.058 ± 6.137 ms in v1; N=8192 FP64 p6/p10/p15/p21 means were 377.161/481.120/670.237/874.570 ms. These are host-specific before/after results for the frozen v1 and selected v2 sources.

The largest relative error against MKL was `eF_mkl = 3.97e-7` (FP32 p6, N=8192); the largest scaled component error was `2.36e-7` (FP32 p6, N=256). Complete errors, checksums, raw wall samples, profile phases, and oneMKL GEMM means are recorded per row in `full_candidate.csv`. The candidate archive and all source/build/runtime hashes are in `provenance.json`.


This run does not represent the later proposed 2 GiB cache default or the separately gated late64 variant. Once the final production source/defaults are frozen, rerun the matrix against that exact library before treating this as the final production comparison.


**Historical candidate data:** this run used the isolated eager-check v2 library and 1 GiB cap. The frozen final production 2 GiB build has now been measured separately; use [mkl_production](../mkl_production/README.md) and [the final report](../../../docs/8454H_FINAL_PERFORMANCE_REPORT.md) for production results. The candidate CSV remains unchanged for provenance.
