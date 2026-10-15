# oneMKL comparison for archived ozAMX v1

This is a supplemental comparison of the frozen `bench/8454h/versions/v1` library with Intel oneMKL 2026.1. It does not measure the later search winner or replace the main before/optimized results. `full_cmake.csv` is the authoritative run: it uses the v1 CMake library build flags, deterministic shared inputs, 64 physical cores, one warmup, and five timed repetitions per configuration. `full.csv` and `smoke.csv` are retained preliminary artifacts from an initial all-translation-unit `-march=sapphirerapids` build; use `full_cmake.csv` and `smoke_cmake.csv` for the reproducible CMake-v1 measurement.

The tested matrix covers N=256, 1024, 4096, and 8192, with FP32 p6 and FP64 p6/p10/p15/p21. The base seed is 260904; inputs use the driver's deterministic uniform generator with resolved seed `260904 + N`, and the same A/B arrays are used by ozAMX and MKL. Each ozAMX configuration has an untimed first call followed by five recorded API calls. MKL likewise performs an untimed call before five timed GEMM calls. The CSV keeps every ozAMX phase timing, the profile total, the full API-call wall-time repetitions and population mean/standard deviation, MKL's mean GEMM time, checksum, and error metrics. `checkpoint_v1_cmake.*.json` records all five timing values with source ID `mkl-wall-v1-cmake-20261013`.

The API wall timer encloses the complete `gemm_fp32_profiled` or `gemm_fp64_profiled` call, including dispatch and internal teardown. `GemmTimings::total_seconds` is retained as its separate phase-profile sum. At N=8192, the API wall exceeds the profile total by about 76 ms for FP32 p6 and 123–174 ms for FP64, depending on budget. This tail cost is measurable and should be included when comparing complete ozAMX calls with MKL. MKL's timer covers only its GEMM call; the ratio below is therefore wall-call time divided by MKL GEMM time, not a matched end-to-end application comparison. The warmup is the first call in each configuration, not a strict cold-process run.

| Type | N | Budget | ozAMX profile total mean (ms) | ozAMX API wall mean ± population SD (ms) | MKL GEMM mean (ms) | API wall / MKL GEMM |
|---|---:|---:|---:|---:|---:|---:|
| fp32 | 256 | p6 | 0.641 | 0.642 ± 0.142 | 0.052 | 12.41× |
| fp64 | 256 | p6 | 1.301 | 1.303 ± 0.075 | 0.101 | 12.91× |
| fp64 | 256 | p10 | 1.394 | 1.396 ± 0.024 | 0.106 | 13.22× |
| fp64 | 256 | p15 | 1.550 | 1.552 ± 0.060 | 0.108 | 14.35× |
| fp64 | 256 | p21 | 1.666 | 1.668 ± 0.049 | 0.110 | 15.19× |
| fp32 | 1024 | p6 | 2.850 | 2.853 ± 1.281 | 0.496 | 5.76× |
| fp64 | 1024 | p6 | 3.438 | 3.441 ± 0.142 | 0.794 | 4.33× |
| fp64 | 1024 | p10 | 3.845 | 3.847 ± 0.160 | 0.786 | 4.89× |
| fp64 | 1024 | p15 | 4.870 | 4.873 ± 0.147 | 0.748 | 6.52× |
| fp64 | 1024 | p21 | 4.849 | 4.853 ± 0.062 | 0.759 | 6.39× |
| fp32 | 4096 | p6 | 23.830 | 23.837 ± 4.815 | 20.581 | 1.16× |
| fp64 | 4096 | p6 | 39.759 | 39.767 ± 4.680 | 39.341 | 1.01× |
| fp64 | 4096 | p10 | 59.763 | 59.771 ± 7.662 | 39.363 | 1.52× |
| fp64 | 4096 | p15 | 76.462 | 76.471 ± 3.638 | 39.368 | 1.94× |
| fp64 | 4096 | p21 | 99.955 | 99.963 ± 12.273 | 39.127 | 2.55× |
| fp32 | 8192 | p6 | 234.741 | 311.058 ± 6.137 | 262.109 | 1.19× |
| fp64 | 8192 | p6 | 466.548 | 589.681 ± 14.884 | 314.396 | 1.88× |
| fp64 | 8192 | p10 | 640.501 | 741.765 ± 16.030 | 325.238 | 2.28× |
| fp64 | 8192 | p15 | 1005.629 | 1152.504 ± 239.326 | 312.611 | 3.69× |
| fp64 | 8192 | p21 | 1120.083 | 1294.021 ± 18.654 | 308.501 | 4.19× |

The archived v1 FP64 p6 result at N=4096 is close to this oneMKL build's GEMM-only time (39.77 ms versus 39.34 ms); higher FP64 budgets take longer. At N=8192, even FP32 p6 has a 311 ms full call versus 262 ms for MKL GEMM; its in-profile phase sum alone is lower, which shows why the added call-wall metric matters. These measurements cover only one host, compiler, library release, thread placement, and input distribution. They are not a claim that ozAMX beats oneMKL.

## Build and runtime provenance

The reference library is the frozen v1 source listed in `bench/8454h/versions/v1/MANIFEST.sha256`. That archive's CMakeLists builds the ozAMX library but has no oneMKL benchmark target, so the library was built with its CMake Release configuration and the instrumented benchmark driver was separately linked to the resulting `libozamx.a`. `configure.log`, `cmake_build.log`, `driver_build.log`, `ldd.txt`, `build_recipe_cmake.txt`, `run_command.txt`, and `source_hashes_cmake.sha256` record the commands, runtime linkage, and source/binary hashes. The shared `/tmp/ozamx-perf.lock` was held during compilation and the complete benchmark run.

Compiler and flags: GCC/G++ 11.4, C++17, CMake Release. The v1 CMake target applies `-O3`, `-mamx-tile -mamx-bf16` to the library, and `-march=sapphirerapids -ffp-contract=off` to `src/gemm.cpp`; the driver is compiled with `-O3 -mamx-tile -mamx-bf16 -fopenmp`. The process used CPUs 0–63 with `OMP_NUM_THREADS=64`, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, `OMP_DYNAMIC=FALSE`, `MKL_NUM_THREADS=64`, `MKL_DYNAMIC=FALSE`, `MKL_THREADING_LAYER=GNU`, and `MKL_INTERFACE_LAYER=LP64`. `ldd.txt` shows `libgomp.so.1` and no Intel OpenMP runtime in the executable's direct dependency list. The MKL threading environment was set to GNU. The run used the default 1 GiB per-thread workspace-cache cap; frequency was not pinned.

The host is Ubuntu 22.04 on Linux 5.15, dual-socket Intel Xeon Platinum 8454H: 2 sockets × 32 physical cores, 128 logical CPUs, 165 MiB aggregate L3, and two NUMA nodes. CPU maximum/minimum are reported as 3.4/0.8 GHz; the governor was `powersave`. Cgroup `cpu.max` was unset and `cpu.stat` showed no quota throttling in the captured metadata. These observations describe this measurement environment, not a guaranteed operating frequency. See `bench/8454h/machine_metadata.txt` for the captured topology and OS details.

The local dependency lives at `third_party/code/mkl-current`; its trackable package URLs, versions, SHA-256 values, license notes, and dependency metadata are in [DEPENDENCY_PROVENANCE.md](DEPENDENCY_PROVENANCE.md), with the fetched PyPI release JSON alongside it. It uses Intel-maintained oneMKL 2026.1.0 PyPI runtime and header packages under Intel Simplified Software License terms. The full runtime wheel was SHA-verified, staged in temporary storage, and only the required dispatcher was copied from it; required GNU-thread, LP64, core, and CPU-dispatch libraries from the same wheel are present under `lib/`. `mkl-include` supplied the CBLAS headers. The benchmark reports oneMKL 2026.1 and records `MKL_THREADING_LAYER=GNU`. No system package installation was used.

Accuracy fields in `full_cmake.csv` retain all output checks. `eF_mkl` is relative Frobenius error against oneMKL; `e_scaled_mkl` is the maximum componentwise error scaled by the absolute-product reference. `eF_hp`/`e_scaled_hp` use full FP128 reference for N≤256 and a deterministic 512-output FP128 sample for larger matrices. Across this run, the largest `eF_mkl` was 3.97e-7 (FP32 p6, N=8192), and the largest `e_scaled_mkl` was 2.36e-7 (FP32 p6, N=256). Checksums and complete per-repetition values are in the CSV.
