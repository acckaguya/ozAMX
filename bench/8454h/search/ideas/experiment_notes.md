# Candidate family notes

- `direct_pack`: writes decomposed components directly into packed panels for eligible divisible/aligned cases; fallback handles other shapes. 8192 FP64 measurements show roughly 28–35% lower wall medians than bracketed defaults, with markedly fewer minor faults.
- `packed_residual`: retains the decomposition arithmetic order while storing residual components in packed layout. Frozen-v1 gate passed 100 cases / 2,322,780 C slots; measured 8192 FP64 wall reductions were roughly 31–39% against bracketed controls.
- `fused_max`: folds next-maximum reduction into projection on the packed-residual layout. Frozen-v1 gate passed the same reported corpus; measured results are close to packed-residual. Four alternating 7-repetition passes are archived: the 8192 p6/p21 fused-max medians are about 3–4% faster, while 4096 p21 is effectively tied; see `../packed_vs_max/comparison.json` and retain the variance caveat.
- `fp32_direct`: directly writes three FP32 components into packed panels and uses masked SIMD interleaving for B. N8192 FP32 p6 measured 202.43 ms wall median (-37.8% vs bracket controls). Root reports the 100-case/2,322,780-slot frozen-v1 gate passed with zero mismatches, plus CTest; `fp32_direct_gate_summary.json` records that the evidence came from root-reported tool stdout.
- `late_nonfinite`: delays exceptional-value detection; ordinary workloads are mixed/noisy, while the change carries additional validation complexity.
- `pending_pipeline`: overlaps projection/pending work; improvements are configuration-specific and large-N measurements are mixed.
- `thread_sweep`: 64 workers generally win at N4096; at N1024 small-workload variance makes the result less decisive.

All numbers use `record=rep` medians and whole-call `wall_s`; detailed phase and fault summaries are in `comparison.json`. Candidate deltas use the mean of the before/after control medians. These are isolated experiments, not adopted behavior or a comparison with oneMKL.

Root selected a combined v2 candidate and completed a matched oneMKL 20-configuration run; see `bench/8454h/mkl_v2/README.md` and its v1/v2 wall comparison. The late-checks variant was rejected after no stable gain and a 4096 regression.

- **v2 workspace cache**: N8192 FP64 p6/p21 wall medians improve from 360.5/886.3 ms (1G cap, pooled repeated passes) to 290.1/735.3 ms at 2G; 4G single-pass results are nearly identical to 2G. Root proposes a 2G default; no broad shape/concurrency claim.
- **v2_late64**: FP32 checks stay eager; FP64 component and per-accumulation checks move to the final block scan. Root reports the 100-case gate, 2,322,780 slots, zero mismatch, CTest, and four overflow/cancellation probes passed. N8192 p21 candidate median 649.6ms vs eager bracket 744.3ms; p6 gain is small/unstable. Four alternating p6/p21 confirmation passes are complete: N8192 p21 late64 passes measured 681/654ms vs eager 754/763ms; N4096 p21 measured 89.3/89.8ms vs 96.2/93.9ms. N1024 is mixed. Root proposes late64 only for FP64 K≥4096; the bounded-commit combination still needs confirmation.

The final production performance report skeleton is `docs/8454H_FINAL_PERFORMANCE_REPORT.md`; it keeps production-linked oneMKL metrics pending until the combined candidate is frozen.
