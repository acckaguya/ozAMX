# 8454H V4 diagnostic campaign results

This is an offline analysis of the six-label, 90-configuration diagnostic run `20261014T091717Z-3`. It does not promote any diagnostic mode to a production GEMM. The malformed original CSV files remain unchanged. Their only parse repair is represented by six normalized copies, each with one missing terminal CSV quote appended to each of its 15 physical data lines.

## Protocol and record integrity

Each label covers N=1024/4096/8192 and FP32 p6 plus FP64 p6/p10/p15/p21. Each configuration has one warmup and five timed repetitions. The analysis retains every timed value, removes no outliers, and verifies each of the five CSV timing vectors against the corresponding checkpoint vector; each checkpoint reports `complete=true`, five requested and five completed repetitions. Strict parsing after normalization confirms 36 header columns and 15 records per CSV.

The only CSV correction is a final closing double quote where the driver omitted it. Original files, checkpoints, and source files were read only. Original and normalized SHA-256 values for all six pairs are in `bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/analysis.json`.

The initial and final controls both reference frozen V3 static library SHA-256 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`. Mode 0 passed an 18-case full-output binary gate and 3/3 CTests; mode 3 also passed its 18-case gate and 3/3 CTests. Those tests establish the recorded gate behavior for their test cases, while the mode3 timing CSV still labels its numeric gate pending. Mode 1 is explicitly a plain finite-input diagnostic without the final non-finite guard, so its reported accuracy fields are not an accuracy pass. Mode 2 omits reconstruction and is non-numeric; its NA fields are preserved as such.

## Full API wall and compute-phase comparisons

The tables below summarize descriptive medians over the 15 configuration means in each label. Ratios are V3 baseline time divided by the mode time; values above one indicate a lower recorded time for that diagnostic mode. `compute` is the driver's combined compute/reconstruction phase. API wall encloses the complete call. The five individual repetitions remain in the analysis JSON and normalized CSVs; these medians do not delete or replace them.

| Diagnostic label | Compute speed ratio vs initial V3 | API-wall speed ratio vs initial V3 | Compute speed ratio vs final V3 | API-wall speed ratio vs final V3 |
|---|---:|---:|---:|---:|
| `mode0_control` | 1.117× | 1.125× | 0.974× | 0.957× |
| `mode1_diagnostic_plain_nf` | 1.194× | 1.208× | 0.981× | 0.995× |
| `mode2_diagnostic_no_reconstruction` | 1.415× | 1.304× | 1.130× | 1.069× |
| `mode3_candidate_late32_unvalidated` | 1.244× | 1.228× | 0.996× | 0.995× |

These aggregates mix five matrix/product shapes and should be read alongside the per-configuration records in `analysis.json`; do not treat a cross-case median as a single workload result. OneMKL `mkl_gemm_s` is retained separately in every normalized row and has not been folded into the diagnostic timings.

## Mode 2: no-reconstruction product-equivalent rate

Mode 2 executes the AMX component-product path but omits product accumulation/reconstruction, leaving a non-numeric result. The following `2 × products × N³ / compute_phase_time` rate is an operation-equivalent diagnostic for the component products, not a valid GEMM throughput or end-to-end performance result. Its phases still include the V4 call's tile, scheduling, scratch, result-copy and related overheads; they are not an ideal hot-register benchmark.

| N | FP32 p6 | FP64 p6 | FP64 p10 | FP64 p15 | FP64 p21 |
|---:|---:|---:|---:|---:|---:|
| 1024 | 39.88 TFLOP/s | 31.28 TFLOP/s | 30.11 TFLOP/s | 45.12 TFLOP/s | 47.83 TFLOP/s |
| 4096 | 43.80 TFLOP/s | 38.53 TFLOP/s | 39.73 TFLOP/s | 44.85 TFLOP/s | 47.50 TFLOP/s |
| 8192 | 45.69 TFLOP/s | 41.18 TFLOP/s | 24.95 TFLOP/s | 45.58 TFLOP/s | 51.76 TFLOP/s |

For scope only, the earlier 64-thread register-resident AMX microbenchmark reported 161.034 ± 0.236 TFLOP/s with input tiles already in tile registers. The mode-2 rates include the actual benchmark's panel/compute path and other in-phase overheads; the comparison is not an attainable bound test and does not identify cache level or external-memory traffic. The current campaign collected no PMU cache/DRAM traffic counters, so these data do not establish a physical DRAM roofline.

## Diagnostic interpretation and limits

- Mode 0 is an isolated V3-equivalent control and its full-buffer comparison passed for 18 cases. Initial/final controls bracket the four mode measurements and both use the same frozen V3 library SHA.
- Mode 1 omits eager FP32 non-finite checks on accumulated intermediate results. Treat timing as a finite-input diagnostic only; its accuracy scope explicitly says unvalidated.
- Mode 2 intentionally returns no numeric GEMM result. Only its component-product-equivalent timing is useful, with the scope limits above.
- Mode 3 selects the late FP32 check for K≥4096 while retaining eager handling below that. Its 18-case full-buffer gate and three CTests passed, but the performance-run rows keep `numeric_gate_pending`; this remains a candidate diagnostic, not a release claim.
- The local machine/compiler/runtime and frequency conditions are those recorded in the result batch and V4 source preparation. The run uses five samples per configuration, all retained; the table uses arithmetic means per configuration then a median across 15 configurations. It is not a statistical confidence interval.
- OneMKL timing is a GEMM-only baseline retained as a separate column. Modes 1–3 alter safety or numeric work, so their MKL ratios do not represent equivalent numerical GEMM performance.

Exact raw configuration values, vectors, checkpoints, original/normalized hashes, test gate summaries, and validation details are in the batch `analysis.json`. The normalized CSVs are under `normalized_csv/`; the six original CSVs are unchanged.
