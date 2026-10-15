# Current main candidate validation

This validates the current working-tree main candidate after adding the CompactWide FP32 dispatch guarded by `CACHE_BLOCK == 128`. It builds the actual CMake target and compares the resulting static archive with frozen V3 through a per-call interleaved persistent-process runner. This is a candidate-validation record, not a release declaration.

Validation directory: `/home/caiweili/ozAMX/bench/8454h/roofline_v4/production_validation_runs/main_current_20261014`  
Main archive SHA-256: `7adcc98996d5a88aa21f74038a42710a28496cf601f2127c016b8e8687801b68`  
Frozen V3 SHA-256: `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`  
`src/gemm.cpp` SHA-256: `498fe70a1c7d343c67b19b495409fe0bbfb4440746fca4d03e7a02ce282c3eba`  
The before/after fingerprints of CMakeLists, gemm/runtime sources, assembly, public header, and benchmark driver match. Full compile commands and logs are preserved. OpenMP configuration passed CTest 3/3; the original frozen 20 binary-gate cases plus three eligible CompactWide-specific cases passed. These verify full output and padding bytes on a padded eligible shape, eligible A=C alias semantics, and large-K overflow raising `ozamx::Error` while leaving the complete caller C allocation unchanged.

| Candidate | Gate case | Full C bytes compared | V3/Candidate output SHA-256 | Status |
|---|---|---:|---|---|
| Main OpenMP | f32_compactwide_padded_eligible | 67190864 | `934799ebb7b1910b545969d4850f06982c5fedce0b318d973857cf614c846a82` | pass |
| Main OpenMP | f32_compactwide_alias_a_equals_c | 67125312 | `c8d69cc762835c62962321f76f14fc59f18036ab168b8723471ff26bd37849b4` | pass |
| Main OpenMP | f32_compactwide_overflow_transaction | 67125312 | `93305d7220c1894d83c00bb7dfee2901c12fe3aa5e3751a1cc3e9fb3b5c85eff` | pass |

The no-OpenMP build also passed CTest 3/3. Its eligible FP32 4096³ full-output check matched frozen V3 SHA-256 `c8d69cc762835c62962321f76f14fc59f18036ab168b8723471ff26bd37849b4` exactly (no-OpenMP archive SHA-256 `c3baf4364d7dbf7b22e12a7f2662b7c03bc9ebd2696f86564e84f1cc800abe27`).

## Interleaved runtime-default matched calls

Both children ran at 64 threads pinned to CPUs 0–63. `OMP_WAIT_POLICY` and `GOMP_SPINCOUNT` were unset, with a 20 ms parent pause after each child call outside the timed API. Each configuration checked deterministic input hashes and full C-output SHA-256. API wall is the primary end-to-end measure; candidate/control ratios below 1 favor the candidate. Mean paired ratios and medians remain separate from the ratio of arithmetic mean times; no samples were excluded.

| Workload | N | Reps | Fast calls | Median paired API ratio | Mean paired API ratio | Ratio of mean API times |
|---|---:|---:|---:|---:|---:|---:|
| FP32 | 1024 | 7 | 4/7 | 0.90941 | 0.93412 | 0.91455 |
| FP32 | 4096 | 11 | 10/11 | 0.94806 | 0.95785 | 0.95902 |
| FP32 | 8192 | 11 | 11/11 | 0.92544 | 0.92436 | 0.92416 |
| FP32 | 16384 | 5 | 2/5 | 1.00014 | 0.84280 | 0.60487 |
| FP64 p6 | 1024 | 7 | 4/7 | 0.90307 | 0.95754 | 0.95325 |
| FP64 p10 | 1024 | 7 | 3/7 | 1.02258 | 0.95591 | 0.89042 |
| FP64 p15 | 1024 | 7 | 3/7 | 1.00880 | 1.05011 | 1.02825 |
| FP64 p21 | 1024 | 7 | 4/7 | 0.97287 | 0.93890 | 0.92597 |

Complete raw API and phase arrays, orders, input checksums, output hashes, warmup records, readiness/affinity data, and child binaries are retained in `summary.json` and individual journals. N=1024 contains four FP64 budget regressions and FP32; N=16384 FP32 is the fallback path because it lies outside CompactWide’s upper size bound. Its five samples are too few and unusually dispersed for a speed claim.

At N=4096, the current main candidate is faster in 10/11 paired FP32 calls, with median 0.948 and arithmetic-mean API-time ratio 0.959. At N=8192 it is faster in 11/11, median 0.925 and ratio of mean API times 0.924. This supports a promising FP32 direction under this run, while retaining ordinary shared-host uncertainty; it does not prove a roofline ceiling or hardware guarantee.

## Separate oneMKL reference

The existing standalone `bench/benchmark.cpp` driver was run separately (not interleaved with V3) for N=4096 and 8192, all five workloads, three timed repetitions, seed 260904 and uniform inputs. It reports a warmup, native profile/API wall timing, and oneMKL GEMM-only timing using Intel oneMKL 2026.1 with GNU threading and 64 threads. Its CSV contains all ten rows and raw native phase/API repetitions. Because MKL intervals cover GEMM only while ozAMX API wall includes preprocessing/allocation, compare timing scopes carefully; this is calibration context, not the matched V3 result.

| Workload | N | Main profile GFLOP/s | oneMKL GEMM GFLOP/s | Main profile / oneMKL ratio |
|---|---:|---:|---:|---:|
| fp32 p6 | 4096 | 8191.9 | 7311.5 | 1.120 |
| fp64 p6 | 4096 | 2808.3 | 3595.2 | 0.781 |
| fp64 p10 | 4096 | 1960.9 | 3494.4 | 0.561 |
| fp64 p15 | 4096 | 1482.0 | 3601.1 | 0.412 |
| fp64 p21 | 4096 | 1110.1 | 3595.6 | 0.309 |
| fp32 p6 | 8192 | 4929.6 | 7875.8 | 0.626 |
| fp64 p6 | 8192 | 3507.8 | 3761.8 | 0.932 |
| fp64 p10 | 8192 | 2196.5 | 3764.4 | 0.583 |
| fp64 p15 | 8192 | 1560.8 | 3733.1 | 0.418 |
| fp64 p21 | 8192 | 1078.5 | 3722.9 | 0.290 |

The standalone CSV records the exact oneMKL version, library path, GNU threading layer, seed, phase profile, API wall, and native/MKL timings. No paper precision claim is inferred from these comparisons.

## oneMKL dispatch diagnostic

The separate N=256 raw BF16 diagnostic is not included in the quiet three-repetition timing CSV. It records a single timed `cblas_gemm_bf16bf16f32` sample; MKL_VERBOSE also shows the routine's warmup invocation and two tiny API smoke calls. The verbose header reports oneMKL 2026 Update 1, GNU threading, 64 threads, and host support for AVX-512 plus AMX BF16/INT8; the call record identifies `GEMM_BF16BF16F32(N,N,256,256,256,...)`. This confirms the selected API, shape, runtime, and advertised host ISA support. The verbose text does not prove which machine instructions every library routine used. The diagnostic CSV and log are isolated under `onemkl_verbose_diagnostic/` and are excluded from performance summaries.

The five requested environment keys are recorded in `onemkl_environment_metadata.json`. The quiet benchmark explicitly set `OMP_WAIT_POLICY=PASSIVE` and `GOMP_SPINCOUNT=0`; its original runner did not persist a snapshot of inherited `MKL_ENABLE_INSTRUCTIONS`, `MKL_CBWR`, or `MKL_VERBOSE`, so the metadata marks those quiet-run values as unavailable rather than retroactively assuming them. Their effective values for the verbose diagnostic are captured as unset except `MKL_VERBOSE=1`.

Intel's [oneMKL Linux ISA dispatch guidance](https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-linux/2026-0/instruction-set-specific-dispatch-on-intel-archs.html) documents the default dispatch policy. ISA support reported in the verbose header is capability context, not proof that every library call executed an AMX kernel.

## API-wall performance, matched phases, and source identity

The earlier oneMKL table uses profile-interval GFLOP/s. The table below adds the primary full-API measure from the same existing ten-row, three-repetition CSV: API arithmetic-mean milliseconds, conventional useful `2N³` divided by full API wall in GFLOP/s, oneMKL GEMM mean milliseconds, and the ratio `MKL GEMM mean / full ozAMX API mean`. The CSV’s raw API-wall samples were re-averaged and checked against `api_call_wall_s_mean` for every row. It contains no individual MKL GEMM samples: `mkl_gemm_s` is the driver’s three-call arithmetic mean, so the per-call MKL distribution cannot be independently reconstructed.

| Workload | N | ozAMX API mean (ms) | Useful 2N³ / API (GFLOP/s) | oneMKL GEMM mean (ms) | MKL GEMM mean / full API mean |
|---|---:|---:|---:|---:|---:|
| fp32 p6 | 4096 | 16.7873 | 8187.1 | 18.7975 | 1.120 |
| fp64 p6 | 4096 | 48.9498 | 2807.8 | 38.2281 | 0.781 |
| fp64 p10 | 4096 | 70.0993 | 1960.6 | 39.3313 | 0.561 |
| fp64 p15 | 4096 | 92.7522 | 1481.8 | 38.1654 | 0.411 |
| fp64 p21 | 4096 | 123.8188 | 1110.0 | 38.2247 | 0.309 |
| fp32 p6 | 8192 | 223.0538 | 4929.4 | 139.6060 | 0.626 |
| fp64 p6 | 8192 | 313.4587 | 3507.7 | 292.2832 | 0.932 |
| fp64 p10 | 8192 | 500.5763 | 2196.5 | 292.0798 | 0.583 |
| fp64 p15 | 8192 | 704.4668 | 1560.8 | 294.5300 | 0.418 |
| fp64 p21 | 8192 | 1019.4521 | 1078.5 | 295.3353 | 0.290 |

For the main-versus-frozen-V3 matched calls, the following table records arithmetic means, not medians: full API wall and compute/reconstruction profile phase for each child. The operation-equivalent column uses `2N³p` with p=6 for FP32 and p equal to each FP64 product budget. It is deliberately labeled operation-equivalent: it is not conventional useful FLOP/s and the measured phase includes reconstruction, so it does not prove AMX issue throughput.

| Workload | N | Control API mean (ms) | Main API mean (ms) | Control compute/recon mean (ms) | Main compute/recon mean (ms) | Control 2N³p equivalent (TOP/s) | Main 2N³p equivalent (TOP/s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| fp32 p6 | 1024 | 1.2124 | 1.1088 | 0.6296 | 0.5621 | 20.465 | 22.925 |
| fp32 p6 | 16384 | 4107.1647 | 2484.3105 | 3776.5907 | 2147.0665 | 13.975 | 24.581 |
| fp32 p6 | 4096 | 34.2623 | 32.8583 | 29.4983 | 28.1097 | 27.955 | 29.336 |
| fp32 p6 | 8192 | 273.2435 | 252.5215 | 255.2470 | 234.9350 | 25.846 | 28.080 |
| fp64 p10 | 1024 | 5.5505 | 4.9423 | 0.9604 | 0.9521 | 22.360 | 22.554 |
| fp64 p15 | 1024 | 5.0989 | 5.2430 | 1.3298 | 1.1207 | 24.224 | 28.743 |
| fp64 p21 | 1024 | 5.7129 | 5.2900 | 1.7964 | 1.4542 | 25.104 | 31.011 |
| fp64 p6 | 1024 | 4.9186 | 4.6887 | 0.6736 | 0.5754 | 19.128 | 22.392 |

Calibration contexts are shown only as separate references: 161.018 TFLOP/s FP32 regular, 151.738 TFLOP/s mixed FP32, and 84.423 TFLOP/s mixed FP64 p6. Their useful-work conventions and phase scopes differ; do not pool them, infer software throttling from their gaps, or present the operation-equivalent phase rate as hardware throughput.

The eight-file identity record is `main_source_identity.json`: only `CMakeLists.txt` and `src/gemm.cpp` differ from the frozen V3 source tree; `src/runtime.cpp`, `src/kernels.S`, the public GEMM header, benchmark driver, preprocessing header, and tuning header are byte-identical. The main archive SHA-256 is recorded there and remains `7adcc98996d5a88aa21f74038a42710a28496cf601f2127c016b8e8687801b68`. Full numerical results and raw timing samples are in `api_metrics_supplement.json`.
