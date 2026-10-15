# V3 paper alignment campaign

This report compares frozen V3 on the current Xeon Platinum 8454H with the experimental protocol and reported values in Cui and Liu, *BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX*, arXiv:2609.04663v1. The source paper is `third_party/papers/2609.04663v1.pdf`; its protocol and extracted values are independently transcribed in [`paper_reference.json`](../bench/8454h/v3_paper_alignment/paper_reference.json). Table 4 is printed on p.21 (PDF p.21); §7.1 platform/repetitions are on p.17; §7.3 input distributions are on p.18; Figures 6–10 are on pp.20–25.

The comparison uses the 40 Table 4 cases: square sizes 256, 512, 1024, 2048, 4096, 8192, 16384 and 32768; FP32 with six component products; FP64 with 6, 10, 15 or 21 products. It also covers Figure 8's 18 FP32 scaling cases (N=1024/4096/16384 and 2/4/8/16/32/64 threads) and Figure 6's eight raw oneMKL BF16-BF16-FP32 cases. The campaign protocol is one warmup and ten timed calls per case, uniform inputs in [-1,1], 64 threads for the main and raw campaigns, and the paper's stated arithmetic-mean convention. The paper does not specify an RNG or seed. This campaign uses `std::mt19937_64` with base seed 260904 and resolves each matrix seed as 260904+N; that is a reproducibility choice, not a paper requirement.

The Table 4 comparisons use full-N×N V3 errors against oneMKL SGEMM/DGEMM: `eF=||Chat-Cref||F/||Cref||F` and `e_scaled=max_ij |(Chat-Cref)_ij|/(|A||B|)_ij`. The report gives measured-to-paper numeric ratios for both values and does not impose an invented pass threshold. High-precision diagnostic fields are supplementary; they are sampled for N>256 and are not substituted for the Table 4 metrics. A V3 row with `status=ok` means the benchmark call completed; it does not mean that its measured accuracy matches the paper.

For performance, the primary local value is the arithmetic mean of the ten `raw_api_call_wall_s` samples. This full API wall encloses the V3 call, including decomposition, packing, compute, reconstruction, dispatch and teardown. API effective GFLOP/s is recalculated as `2*N^3 / API-wall-mean`; the legacy `effective_GFLOP_s` and `profile_speedup` CSV columns use the phase profile and are secondary. `profile_total_s_mean` remains available for phase analysis. Local `mkl_gemm_s` covers oneMKL GEMM only, so `mkl_gemm_s / API-wall-mean` has narrower MKL timing scope than the V3 full call. The paper's Figure 7 FP32 speedups are recorded exactly as reported (2.56, 2.17, 1.70, 1.39, 1.14, 1.16, 1.25 and 1.32 for increasing N). Figure 9 has no exact data table, so this report preserves only its textual findings and does not manufacture curve values.

Figure 6 labels raw BF16 throughput as GFLOPS, but its values have a documented units concern. `paper_reference.json` preserves those printed labels and values without conversion. Local headroom data reports its measured GFLOP/s and TFLOP/s in separate named fields; it is an isolated `cblas_gemm_bf16bf16f32` baseline, not the ozAMX component-product algorithm.

The local platform is a dual-socket Xeon Platinum 8454H system running Ubuntu with GCC 11.4, GNU OpenMP and oneMKL 2026.1. The paper used dual-socket Xeon Platinum 8462Y+, Rocky Linux 9.3, Intel oneAPI/oneMKL 2026.1 and Intel OpenMP. Both campaigns request 64 threads, but affinity/NUMA placement, compiler and OpenMP runtime, CPU model, operating system and frequency policy are not identical. The paper says its frequency policy was fixed; the local host governor is `powersave` and frequency is not pinned. V3 also includes per-thread tile configuration in its compute timing, whereas the paper only says one-time AMX permission/config setup is excluded and does not define its per-worker setup implementation. The paper does not provide author source code or RNG details. These differences limit exact timing and same-input claims.

The evaluated static library is the frozen V3 release with SHA-256 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`. Its paper-literal FP64 rho=45 decomposition and the BK=256 panel schedule are retained. Existing accuracy analyses in [`NATIVE_ALTERNATIVE_ACCURACY.md`](NATIVE_ALTERNATIVE_ACCURACY.md) and [`REPRODUCTION_RESULTS.md`](REPRODUCTION_RESULTS.md) document prior observations; they do not predetermine this campaign's measured values.

## Coverage and results

Campaign inputs are one CSV per configuration under `bench/8454h/v3_paper_alignment/results/`, matching the keys `main_fp32_nN`, `main_fp64pB_nN`, `scaling_fp32_nN_tT` and `raw_bf16_nN`. Checkpoints, commands, per-case process return codes, machine metadata and source/library hashes are retained beside the CSVs. The analysis utility is [`analyze_v3_paper_alignment.py`](../tools/analyze_v3_paper_alignment.py). Run it from the repository root with:

```sh
python3 tools/analyze_v3_paper_alignment.py
```

It reads available rows, reports missing/invalid cases, checks ten-sample vectors and expected library/source provenance where present, and writes machine-readable partial results to `bench/8454h/v3_paper_alignment/analysis.json`. It adds no accuracy pass/fail threshold. Matplotlib is optional; if installed, `--plots` writes static figures into the campaign directory. Do not describe the campaign as complete until all 40 main, 18 scaling and 8 raw-headroom configurations have valid ten-repetition records and successful process/checkpoint status.

| Campaign | Expected configurations | Current coverage |
|---|---:|---|
| Table 4 main | 40 | 40 present and valid |
| Figure 8 FP32 scaling | 18 | 18 present and valid |
| Figure 6 raw BF16 headroom | 8 | 8 present and valid |

The campaign completed with all 66 configurations validated: every row has successful process status, ten timed samples, and a complete matching checkpoint. Table 4 metrics cover the full N×N output. The frozen library SHA-256 is `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`; the recorded main-source, raw-source and oneMKL runtime hashes match their actual files. The analyzer reports `campaign_complete=true` and all three groups complete. No exact Figure 9 performance points are claimed. The analysis utility leaves no missing campaign cases and writes the four current static figures: [Table 4 error ratios](../bench/8454h/v3_paper_alignment/plots/ef_ratio_vs_size.png), [FP32 speedup](../bench/8454h/v3_paper_alignment/plots/fp32_speedup_vs_size.png), [FP32 thread scaling](../bench/8454h/v3_paper_alignment/plots/fp32_thread_scaling_api_vs_mkl.png), and [raw BF16 headroom](../bench/8454h/v3_paper_alignment/plots/raw_bf16_measured_gflops.png). The write-once supplemental archive generator is [`create_v3_paper_release.py`](../bench/8454h/create_v3_paper_release.py); this report update and analysis do not freeze or publish it.

For Table 4, `analysis.json` contains every measured value and its measured-to-paper ratio. The following compact summary reports the median ratio and observed range across the eight matrix sizes. These are comparisons, not pass/fail thresholds. The eight-size FP32 p6 ratios stay close to the paper values (median 1.004 for eF and 1.003 for e_scaled). FP64 differs substantially: median eF ratios range from 5.701 to 21.916 for p6/p10/p15 and 8.207 for p21; e_scaled medians range from 4.404 to 21.856. The wide p21 ranges are retained as measured and are not reduced to a claim of pointwise agreement. Full per-size values and ratios remain in `analysis.json`.

| Mode | eF measured / paper median (range) | e_scaled measured / paper median (range) |
|---|---:|---:|
| FP32 p6 | 1.004 (0.999–1.038) | 1.003 (0.889–1.226) |
| FP64 p6 | 5.701 (5.693–5.703) | 5.563 (5.285–6.218) |
| FP64 p10 | 11.146 (11.090–11.156) | 10.835 (10.300–11.595) |
| FP64 p15 | 21.916 (21.887–21.962) | 21.856 (20.921–23.252) |
| FP64 p21 | 8.207 (4.475–11.186) | 4.404 (1.520–6.723) |

For FP32 p6, the recalculated local API throughput is 59.9, 308.7, 2418.7, 3023.8, 3339.8, 3454.2, 2302.7 and 3157.4 GFLOP/s as N increases. `mkl_gemm_s / API-wall-mean` is 2.220, 1.086, 0.662, 0.591, 0.631, 0.506, 0.377 and 0.507. This local ratio exceeds one at N=256 and 512, then falls below one; it does not match Figure 7's reported 1.14×–2.56× speedups. Scope is asymmetric because the local MKL timing is GEMM-only while the V3 timing includes the complete API call.

The Figure 8 thread-scaling comparison uses the same configured thread count for V3 and oneMKL. API throughput is recalculated from ten full-call wall samples; oneMKL throughput uses its GEMM-only timer. These timing scopes differ, and the paper reports only qualitative Figure 8 trends, not point values. All 18 configured thread-count points are present; the plot connects only measured points. See [the full scaling plot](../bench/8454h/v3_paper_alignment/plots/fp32_thread_scaling_api_vs_mkl.png).

| N | Threads | V3 API-wall GFLOP/s | oneMKL GEMM-only GFLOP/s |
|---:|---:|---:|---:|
| 1024 | 2 | 264.1 | 242.1 |
| 1024 | 4 | 482.5 | 451.9 |
| 1024 | 8 | 803.7 | 794.1 |
| 1024 | 16 | 1216.7 | 1658.5 |
| 1024 | 32 | 2835.2 | 2890.6 |
| 1024 | 64 | 2954.5 | 3708.2 |
| 4096 | 2 | 360.5 | 294.6 |
| 4096 | 4 | 700.1 | 553.4 |
| 4096 | 8 | 1288.8 | 1083.3 |
| 4096 | 16 | 2561.3 | 2049.5 |
| 4096 | 32 | 4107.1 | 3940.5 |
| 4096 | 64 | 6271.9 | 6822.4 |
| 16384 | 2 | 387.1 | 297.9 |
| 16384 | 4 | 691.0 | 598.0 |
| 16384 | 8 | 1365.6 | 1200.1 |
| 16384 | 16 | 2523.0 | 2382.4 |
| 16384 | 32 | 3260.5 | 4100.7 |
| 16384 | 64 | 5591.5 | 7306.1 |

The paper's Figure 8 text says N=1024 peaks at 32 threads and falls at 64; N=4096 and 16384 throughput rises with thread count; and reported FP32-over-SGEMM points remain above 1.1×. The exact points are not tabulated, so this report preserves those statements without inventing paper values. The eight local raw BF16-BF16-FP32 measurements are complete. The table preserves the measured mean time and both locally computed throughput fields; Figure 6's printed `GFLOPS` values remain as transcribed in `paper_reference.json`, without conversion or an assumed unit equivalence. The measured routine is isolated `cblas_gemm_bf16bf16f32`, not the ozAMX component-product method. See the [raw BF16 measured-throughput plot](../bench/8454h/v3_paper_alignment/plots/raw_bf16_measured_gflops.png).

| N | Mean seconds | Local GFLOP/s | Local TFLOP/s |
|---:|---:|---:|---:|
| 256 | 0.0000336582 | 996.9 | 0.9969 |
| 512 | 0.0001027502 | 2612.5 | 2.6125 |
| 1024 | 0.0002801459 | 7665.6 | 7.6656 |
| 2048 | 0.0006549749 | 26229.8 | 26.2298 |
| 4096 | 0.0048192198 | 28518.9 | 28.5189 |
| 8192 | 0.0298952581 | 36778.8 | 36.7788 |
| 16384 | 0.2266286439 | 38812.8 | 38.8128 |
| 32768 | 1.7897276629 | 39318.1 | 39.3181 |
