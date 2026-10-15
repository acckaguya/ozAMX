# 8454H roofline kernel calibration analysis

This is an offline analysis of the saved kernel calibration. No benchmark was executed for this report. The raw artifact contains **228 rows**: 57 configurations, each with one warmup and three timed repetitions (171 timed rows). All rows report `passed`. The CSV hash, three input-source hashes, benchmark binary hash, and linked frozen production library hash match `kernel_metadata.json`.

Files: [`kernels.csv`](../bench/8454h/roofline/calibration/kernels.csv), [`kernel_metadata.json`](../bench/8454h/roofline/calibration/kernel_metadata.json), [`kernel_disassembly.txt`](../bench/8454h/roofline/calibration/kernel_disassembly.txt), and machine-readable [`kernel_summary.json`](../bench/8454h/roofline/calibration/kernel_summary.json). [`summarize_kernels.py`](../bench/8454h/roofline/calibration/summarize_kernels.py) rebuilds the summary from saved data. [`plot_roofline_calibration.py`](../tools/plot_roofline_calibration.py) produces the two figures when Matplotlib is available.

## Method and scope

Each worker allocates its own aligned input buffer, initializes it in the OpenMP team before timing, and owns its local scratch. Measurement uses taskset CPUs 0–63, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, `OMP_DYNAMIC=FALSE`, and 1/32/64 workers. Each case requests Linux AMX XCOMP permission on every worker, including the pure SIMD reconstruction cases. The timer surrounds the synchronized 80 ms target interval; allocation, first-touch, input initialization, tile configuration, output checksums, and free are outside the timed interval. The artifact records a warmup and three timed repetitions per configuration.

`worker_input_bytes` excludes `Local` stack arrays. `Local` reserves 4 KiB FP32 micro output + 36 KiB FP64 block + 18 KiB FP32 block = 58 KiB per worker (plus runtime/compiler stack state). For FP64 reconstruction, 4 KiB micro and 8 KiB active C are touched; FP32 reconstruction touches 4 KiB micro and 4 KiB active C. The P6/P21 worker input set is 192 KiB; the active C and micro arrays add 12 KiB. Stack and input initialization use each worker before timing.

For summary tables, ± is **sample standard deviation (n−1)** across the three timed repetitions. The JSON keeps the raw samples and the medians, means, and standard deviations. Counts are reported from the benchmark’s logical payload model; there are no PMU cache-miss counters or measured cache-residency coordinates.

## Source and disassembly audit

The metadata’s expected hashes match the current files: `tools/roofline_kernels.cpp` `ae38a0192f20bec20a220f333d3d6d70856367109e5e02ed949dd64424b64db0`, `tools/roofline_tileloads.S` `df26c82d11a73a7f16350d3dfb01ce26d11ce12b32a2c9960f642818191e41ef`, and `bench/8454h/roofline/run_kernel_calibration.sh` `b774dbb7fb4e663842e1a878eff9cf8a24d80f7b5323aab8cecb52da3b0ef779`. The CSV SHA is `2ab37da6f56bdbbc2459f5788ce379c868b4fc0c1c9ff29db50ccacb7a105179`; the saved disassembly SHA is `70150b8a81e855d2e4e4d85188c2405a1471a0e65654805bb31f48da7a22f1db`. The executable hash is `6812e6e4873e9c0117b8ecefcd492edd30cb3d6e4b2cf4c7b9ac6f9d0c4c0f0f`. The linked frozen production library is still `ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251`.

In `ozroof_tileload` and `ozroof_tileload_t1`, the loop contains exactly **four** tile loads per unit, to `tmm0–tmm3`. Each configured tile is 16 rows × 64 bytes = 1 KiB, so the recorded input payload is 4 KiB/unit. TILELOADT1 is a hint; its name does not establish where the data came from.

In `ozamx_bf16_product`, each 32-deep microstep loads four 1 KiB tiles and issues **four** `TDPBF16PS` instructions to `tmm4–tmm7`. Each instruction performs `2 × 16 × 16 × 32 = 16,384` FP operations. A production BK=256 component product uses eight K=32 microsteps: 32 tile loads + 32 TDP instructions, followed by four 1 KiB output tile stores. Thus one component product performs 524,288 AMX FP operations and has 36 KiB of counted tile payload (32 KiB loads + 4 KiB stores). P6 uses six component products per BK block (192 TDP instructions); P21 uses 21 (672). In the MIX diagnostic each product result is reconstructed immediately; the MIX results remain diagnostic microkernel measurements, not full public GEMM timings.

The saved noinline SIMD disassembly contains the expected loads, conversions/adds, and stores. `reconstruct64` processes 32×32 outputs with 1,024 FP64 additions and 20 KiB logical payload (4 KiB FP32 source + 8 KiB C read + 8 KiB C write). `reconstruct32` also performs 1,024 additions, with 12 KiB logical payload (4 KiB source + 4 KiB C read + 4 KiB C write). The `stride=136` and `stride=144` variants change row spacing; they do not change the active element count.

## Measured register and TILELOAD rates

AMX register-only results are a measured register-resident ceiling for this benchmark shape: four accumulators, four TDP instructions per unit, with the input tiles already in tile registers. They exclude panel loads, packing, and output reconstruction. Values are TFLOP/s, median ± sample SD; exact raw samples are in the JSON.

| Threads | AMX register-only ceiling (TFLOP/s) |
|---:|---:|
| 1 | 2.523 ± 0.001 |
| 32 | 80.490 ± 0.165 |
| 64 | 161.034 ± 0.236 |

TILELOAD rates below are decimal logical GB/s from four 1 KiB tile-load payloads per unit. Footprint labels describe the total per-worker input allocation, not verified cache residency. `TILELOADT1` has the same logical-byte count. Exact raw values and per-case median/SD are in the JSON.

| Per-worker input footprint | Threads | TILELOAD median ± SD (GB/s) | TILELOADT1 median ± SD (GB/s) |
|---:|---:|---:|---:|
| 4 KiB | 1 | 330.23 ± 0.03 | 273.08 ± 47.07 |
| 4 KiB | 32 | 10481.96 ± 2.45 | 10323.77 ± 160.02 |
| 4 KiB | 64 | 20832.06 ± 597.49 | 20744.33 ± 85.92 |
| 1 MiB | 1 | 135.29 ± 0.02 | 146.07 ± 0.04 |
| 1 MiB | 32 | 4194.73 ± 8.87 | 4629.69 ± 5.34 |
| 1 MiB | 64 | 8463.06 ± 9.64 | 9337.81 ± 2.59 |
| 2.25 MiB | 1 | 62.21 ± 0.53 | 64.21 ± 0.21 |
| 2.25 MiB | 32 | 1248.29 ± 2.23 | 1296.31 ± 3.79 |
| 2.25 MiB | 64 | 2625.28 ± 1.26 | 2643.10 ± 66.80 |
| 24 MiB | 1 | 28.55 ± 0.01 | 28.68 ± 0.05 |
| 24 MiB | 32 | 267.74 ± 0.26 | 265.70 ± 3.08 |
| 24 MiB | 64 | 534.42 ± 1.83 | 525.36 ± 3.79 |

The 64-worker 2.25 MiB/worker case is 144 MiB in total (about 72 MiB per socket on the selected CPUs), below the host’s aggregate 165 MiB LLC size. That makes it an LLC-residency **candidate** only: other activity, tile accesses, replacement and shared-cache partitioning are not controlled or observed. The per-worker input sizes for the four TILELOAD sweeps are 4 KiB, 1 MiB, 2.25 MiB, and 24 MiB.

## FP64 P6/P21 component-product diagnostics

The no-reconstruction kernels are intentionally **not numerically equivalent public GEMM candidates**. They isolate component-product throughput and omit the required FP32-to-FP64 widening/add stage. MIX includes reconstruction after every component product. Total AI below is derived from total operation count divided by the benchmark’s logical payload bytes; MIX adds 1,024 FP64 reconstruction additions per component product. Rates are derived as total FLOP/s so the MIX reconstruction additions are included. These totals do not include full GEMM split/packing/API work.

| Threads | Budget | No-reconstruct logical AI (op/B) | No-reconstruct (TFLOP/s) | MIX logical AI (op/B) | MIX (TFLOP/s incl. adds) | MIX logical payload (GB/s) |
|---:|:---|---:|---:|---:|---:|---:|
| 1 | P6 | 14.222 | 1.917 ± 0.017 | 9.161 | 1.341 ± 0.006 | 146.39 ± 0.71 |
| 1 | P21 | 14.222 | 1.940 ± 0.018 | 9.161 | 1.357 ± 0.006 | 148.14 ± 0.66 |
| 32 | P6 | 14.222 | 61.110 ± 0.214 | 9.161 | 40.715 ± 1.140 | 4444.55 ± 124.42 |
| 32 | P21 | 14.222 | 61.915 ± 0.360 | 9.161 | 43.281 ± 0.027 | 4724.58 ± 2.93 |
| 64 | P6 | 14.222 | 121.677 ± 0.332 | 9.161 | 85.610 ± 0.070 | 9345.31 ± 7.64 |
| 64 | P21 | 14.222 | 123.662 ± 0.465 | 9.161 | 86.505 ± 0.153 | 9443.00 ± 16.68 |

The raw CSV `amx_or_add_ops` field for MIX counts only AMX operations; the summary’s `total_ops_per_s` adds reconstruction additions explicitly for AI/roofline placement. Preserve this distinction when consuming the CSV directly.

## Pure SIMD reconstruction diagnostics

These are standalone in-place reconstruction microkernels with initialized local blocks and no AMX product stage. AI is logical operations divided by counted source/C traffic. Throughputs are GFLOP/s, median ± sample SD. The 136-stride FP64 and 144-stride FP32 options introduce row padding; see exact source hashes and raw samples above.

| Threads | Kernel | Stride (elements) | Logical AI (op/B) | Throughput (GFLOP/s) | Logical payload (GB/s) |
|---:|:---|---:|---:|---:|---:|
| 1 | reconstruct64 | 128 | 0.0500 | 10.43 ± 0.01 | 208.70 ± 0.16 |
| 1 | reconstruct64 | 136 | 0.0500 | 10.44 ± 0.00 | 208.76 ± 0.01 |
| 1 | reconstruct32 | 128 | 0.0833 | 32.36 ± 1.92 | 388.36 ± 23.04 |
| 1 | reconstruct32 | 144 | 0.0833 | 29.83 ± 4.18 | 357.96 ± 50.20 |
| 32 | reconstruct64 | 128 | 0.0500 | 319.16 ± 7.83 | 6383.12 ± 156.53 |
| 32 | reconstruct64 | 136 | 0.0500 | 324.51 ± 1.10 | 6490.12 ± 21.96 |
| 32 | reconstruct32 | 128 | 0.0833 | 907.95 ± 12.23 | 10895.46 ± 146.76 |
| 32 | reconstruct32 | 144 | 0.0833 | 889.46 ± 10.51 | 10673.50 ± 126.12 |
| 64 | reconstruct64 | 128 | 0.0500 | 666.46 ± 0.16 | 13329.11 ± 3.13 |
| 64 | reconstruct64 | 136 | 0.0500 | 666.21 ± 0.71 | 13324.10 ± 14.23 |
| 64 | reconstruct32 | 128 | 0.0833 | 1946.55 ± 20.60 | 23358.56 ± 247.22 |
| 64 | reconstruct32 | 144 | 0.0833 | 1948.76 ± 8.57 | 23385.12 ± 102.88 |

The FP64 stride effect is small at 64 threads in this sample (median about 666.5 GFLOP/s at stride 128 and 666.2 GFLOP/s at 136); this microbenchmark does not establish a production GEMM effect. The `reconstruct32` stage is a plain-add SIMD diagnostic and omits the production FP32 path's nonfinite checks and surrounding GEMM work, so its throughput is not a measurement of the complete production FP32 reconstruction path. FP32 reconstruction is faster per operation in isolation, but it performs different precision work and should not be compared as an interchangeable path.

## Roofline views and memory references

The Matplotlib plotting source is [`tools/plot_roofline_calibration.py`](../tools/plot_roofline_calibration.py). It defines two views: (1) AMX register ceiling and P6/P21 points versus total logical-payload AI, and (2) stage diagnostics adding pure FP32/FP64 reconstruction points. Both plot footprint-derived and triad logical-payload reference slopes, not physical cache-level bandwidth roofs. Static figures: [AMX total-AI SVG](figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg), [AMX total-AI PNG](figures/8454H_ROOFLINE_AMX_LOGICAL_AI.png), [stage diagnostic SVG](figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg), and [stage diagnostic PNG](figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.png). [Plot provenance](figures/8454H_ROOFLINE_PLOTS_METADATA.json) records package versions and input/output hashes. Re-render with `PYTHONPATH=/tmp/ozamx-roof-plotlibs python3 tools/plot_roofline_calibration.py` after installing the listed dependencies in a temporary target.

The saved tileload rates provide footprint-based payload references, but no PMU cache-miss or traffic counters were collected. They cannot assign a datapoint to L1/L2/LLC/DRAM. Intel’s Integrated Roofline documentation describes CARM-style code traffic and separate cache-level traffic, with simulated/instrumented level-specific intensities; this analysis has only hand-counted logical payload and therefore uses “CARM-style” descriptively, not as an Advisor measurement. See [Intel Integrated Roofline Model with Advisor](https://www.intel.com/content/www/us/en/developer/articles/technical/integrated-roofline-model-with-intel-advisor.html) and Berkeley Lab’s [publications directory](https://crd.lbl.gov/news-and-publications/publications/) and [Roofline model publication material](https://crd.lbl.gov/assets/pubs_presos/swwilliams-mundie-poster.pdf).

### Legacy and new DRAM-footprint triad measurements

The two probes give different results and should remain separate references until their differences are reconciled. The table reports medians and sample SD over five timed samples; the older platform report also has a mean/population SD, so those published values are retained in its source.

| Threads | Legacy 768 MiB float triad median ± sample SD (GB/s) | New 24 MiB/worker double triad median ± sample SD (GB/s) |
|---:|---:|---:|
| 1 | 12.55 ± 0.52 | 25.40 ± 0.27 |
| 32 | 202.19 ± 22.49 | 189.00 ± 5.20 |
| 64 | 191.22 ± 2.69 | 368.00 ± 2.51 |

The legacy probe uses three 256 MiB float arrays, static OpenMP initialization, and roughly 50 ms minimum timed batches. The newer probe uses three independent 8 MiB double arrays per worker (24 MiB/worker; 1.5 GiB aggregate at 64 workers), per-worker static first-touch, and calibrated pass batches of at least 0.1 seconds. The new 64-thread median is 368 GB/s; this is not a correction to the legacy 190.88 ± 2.41 GB/s mean ± population SD. Element type, working-set partitioning, first-touch placement, and timer/runtime protocol differ. Neither number is cache-counter-derived physical DRAM traffic. Sources: [legacy platform CSV](../bench/8454h/platform_baseline.csv), [new triad CSV](../bench/8454h/roofline/memory_calibration_20261013.csv), and [new triad metadata](../bench/8454h/roofline/memory_calibration_20261013.json).

## Interpretation limits

- The 80 ms target is a synchronized microkernel window, not the full GEMM API. The CSV has only three timed reps per configuration; SD is descriptive and should not be read as a confidence interval.
- Hand-counted logical payload is not physical cache or memory traffic. Tile stores, write allocation, reloads, cache-line movement, and inter-cache traffic are not counted by PMU here.
- Input footprint size is only a residency hypothesis. In particular `LLC_candidate` does not prove LLC hits.
- `TILELOADT1` does not force a particular cache source or eviction policy.
- P6/P21 no-reconstruction measurements omit part of the required numerical result and are upper-bound diagnostics only. MIX remains a small tile-path microbenchmark; it is not the production call.
- These measurements guide the next experiments. They do not yet identify a production bottleneck or certify a physical roof.
