# 8454H kernel experiments (not adopted by default)

These are isolated candidates measured against the default binary with the same benchmark driver and deterministic inputs. Each candidate/control pair used the same 64-thread CPU affinity, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, `OMP_DYNAMIC=FALSE`, a 1 GiB workspace cache cap, and a shared `flock` performance lock. Rows below use the median of `record=rep`; control is the mean of the before/after control medians. `wall_s` includes whole-call overhead, while `total_s` is the driver phase sum. Negative percentages mean faster. Warmup and summary rows are excluded. Detailed per-configuration phase and fault medians, checksums, commands, and source/build/patch hashes are in [comparison.json](../bench/8454h/search/ideas/comparison.json) and [experiment_metadata.json](../bench/8454h/search/ideas/experiment_metadata.json).

## Large FP64 case

At N=8192, the direct-pack, packed-residual, and fused-max candidates reduce default whole-call wall time by roughly 29–39%, with lower minor-fault counts in the corresponding candidate runs. These are candidate observations, not a stable winner ranking: packed-residual and fused-max are close enough that run noise can dominate their difference, and an alternating 7-repetition comparison for budgets 6 and 21 is queued. Keep their results separate; none is enabled in the production default.

| Candidate | Budget | Candidate wall median (ms) | Candidate phase total median (ms) | Wall change vs bracketed default | Candidate minor faults |
| --- | ---: | ---: | ---: | ---: | ---: |
| direct_pack | 6 | 396.06 | 340.72 | -34.7% | 131,073 |
| direct_pack | 10 | 535.60 | 480.51 | -28.4% | 131,073 |
| direct_pack | 15 | 729.07 | 650.74 | -31.4% | 262,147 |
| direct_pack | 21 | 945.23 | 843.58 | -29.4% | 262,149 |
| packed_residual | 6 | 371.99 | 315.94 | -38.7% | 131,073 |
| packed_residual | 10 | 519.46 | 459.27 | -31.6% | 131,988 |
| packed_residual | 15 | 709.17 | 628.79 | -33.8% | 198,948 |
| packed_residual | 21 | 902.94 | 799.13 | -31.1% | 262,149 |
| fused_max | 6 | 364.90 | 309.85 | -39.1% | 131,110 |
| fused_max | 10 | 511.65 | 456.12 | -31.5% | 131,073 |
| fused_max | 15 | 705.73 | 625.94 | -32.3% | 196,611 |
| fused_max | 21 | 917.81 | 815.87 | -28.8% | 262,798 |

These ratios compare each run family to its own bracket controls; they do not compare against oneMKL and are not a claim of universal speedup. Phase totals omit some call-level setup/teardown, so wall time is the more complete latency metric. Lower minor faults are consistent with less allocation/page-touch pressure but do not establish the cause by themselves.

## What changed

- **direct_pack** writes decomposed components into the packed panels directly, avoiding the full intermediate component-slice layout. The optimization is restricted to eligible aligned/divisible cases; fallback behavior remains. The patch and measurements are archived at [direct_pack.patch](../bench/8454h/search/ideas/direct_pack.patch) and [its experiment metadata](../bench/8454h/search/ideas/experiment_metadata.json).
- **packed_residual** preserves the existing floating-point decomposition order and changes residual element placement to the packed layout. This reduces a materialization stage while keeping the global maximum computation symmetric. Root reports the frozen-v1 100-case bitwise gate passed, covering 2,322,780 C slots, plus CTest.
- **fused_max** builds on the packed-residual layout and folds the next global-maximum reduction into projection. Root reports the same 100-case/2,322,780-slot bitwise gate and CTest passed. Its measurements are close to packed-residual and need the queued alternating check before selecting between them.
- **fp32_direct** directly emits the three FP32 components to packed panels and uses masked interleaving for SIMD B loads. Its N=8192 FP32 p6 sample has 202.43 ms median whole-call wall, 37.8% below its bracket controls; treat as a single candidate family observation, not as a cross-precision ranking. Validation/performance status and hashes are in metadata.
- **late_nonfinite** delays exceptional-value detection until after common finite work. It showed limited/noisy benefits on ordinary workloads; its non-finite and overflow validation is preserved with the candidate record.
- **pending_pipeline** overlaps projection/pending-component work in the candidate pipeline. Some isolated sizes/budgets improve, while other large-N cases are close to controls or regress; the aggregate does not justify adoption.
- **thread_sweep** compared 16/32/64 workers at N=1024 and 4096. At N=4096, 64 threads were generally faster; N=1024 was noisy and sometimes favored 32. This is evidence for workload-dependent thread scaling, not a replacement default.

All patch files and the analysis output are under [bench/8454h/search/ideas](../bench/8454h/search/ideas). These findings document experiments only; they do not imply production source changes.

## Follow-up selection and v2 oneMKL run

Root selected the combined isolated v2 candidate: 16K prep grain / T1 settings, direct FP32 panel generation, and FP64 fused max, with fusion gated to `min(M,N) >= 1024` and M/N/K all divisible by 256. The FP32-direct frozen-v1 gate is now recorded as 100 cases, 2,322,780 C slots, zero mismatches, plus CTest, in [fp32_direct_gate_summary.json](../bench/8454h/search/ideas/fp32_direct_gate_summary.json). The tool's stdout was reported by root but not independently archived, which the summary explicitly records.

The four alternating packed-residual/fused-max passes are in `bench/8454h/search/packed_vs_max/`; pooled medians show fused-max is about 3–4% faster at N=8192 for p6 and p21 in this pass set, while N=4096 p21 is essentially tied (+0.3%). See [comparison.json](../bench/8454h/search/packed_vs_max/comparison.json). This supports the selected fused-max configuration as a practical candidate but does not remove measurement uncertainty.

A separate selected-v2 oneMKL full matrix run is archived at [bench/8454h/mkl_v2/README.md](../bench/8454h/mkl_v2/README.md), including all 20 matched configurations and five API-wall samples each. Its [v1/v2 wall table](../bench/8454h/mkl_v2/comparison_v1_v2.md) preserves the distinction between complete ozAMX call wall time and MKL GEMM-only time.

## Cache-capacity and late64 follow-up

The selected eager-check v2 candidate was tested at 1/2/4 GiB workspace-cache caps for N=8192, with 1G/2G bracket repeats. The 2 GiB cap reduced FP64 p6/p21 wall medians from 360.5/886.3 ms to 290.1/735.3 ms; the single 4 GiB pass was nearly unchanged from 2 GiB. Root proposes a 2 GiB default; the cap is a workspace-cache limit, not measured resident-memory use. Full per-phase/fault data and pass hashes are in [v2_cache/comparison.json](../bench/8454h/search/v2_cache/comparison.json).

A separate late64 candidate keeps FP32 checks eager and defers FP64 component/per-accumulation non-finite checks to a final block scan. Root reports its 100-case/2,322,780-slot bitwise gate, four overflow/cancellation probes, and CTest all passed. The 8192 FP64 p21 wall median is 649.6 ms versus 744.3 ms from eager bracketing controls; p6 shows only a small, unstable improvement. The four-pass alternating p6/p21 confirmation is complete: N=8192 p21 medians were 681/654 ms late64 versus 754/763 ms eager; N=4096 p21 was 89.3/89.8 ms versus 96.2/93.9 ms. N=1024 remains mixed across the two eager passes. Root proposes late64 for FP64 K≥4096 and eager below that threshold. A bounded-commit + late64 combined candidate is still being confirmed before production freeze. See [candidate note](../bench/8454h/search/ideas/v2_late64.md), [gate summary](../bench/8454h/search/ideas/v2_late64_gate_summary.json), [initial phase comparison](../bench/8454h/search/v2_late64/comparison.json), and [four-pass confirmation](../bench/8454h/search/v2_late64_confirm/comparison.json).

The existing [mkl_v2 report](../bench/8454h/mkl_v2/README.md) measures the isolated eager-check candidate with a 1 GiB cap. It is not a measurement of the proposed 2 GiB setting or of late64/final production. A separate production-linked oneMKL run remains necessary if final source or cache defaults differ.

A production report template is available at [8454H_FINAL_PERFORMANCE_REPORT.md](8454H_FINAL_PERFORMANCE_REPORT.md). It intentionally leaves final production-linked oneMKL numbers pending until source and build hashes are frozen.

## 后续尚未实现的 ISA 探索

[AMX INT8 全 K 精确整数累加设计](../bench/8454h/search/ideas/amx_int8_exact_accumulation.md)记录了格点、符号、四种点积、128位还原与精度门的推导。这是待验证假设，不能归入已实测收益。
