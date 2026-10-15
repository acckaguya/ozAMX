# V4 packed-layout screen results

This is an offline analysis of the timestamped N=8192 FP64 gap/rotation screen. It does not change production V3. The report preserves every available sample and never removes an outlier. Three samples support descriptive ranking only; finalists require a paired follow-up with at least seven repetitions and the full gate.

Coverage: **16/16** candidates satisfy row, checkpoint, gate, CTest and hash checks. Missing or invalid: none. Full gate pass: 16/16; CTest pass: 16/16. Any currently missing point is retained as pending, not interpolated.

## Allocation and cache accounting

The source maps p6/p10/p15/p21 to 3/4/5/6 stored FP64 BF16 slices. `packed_allocation_estimates` in the run metadata currently uses the product budget as the slice count, so it overstates actual packed payload; this analysis recalculates from `gemm.cpp::budget_depth()` and `preprocess.hpp`. The payload formula is `4 × stored_slices × N²` bytes for persistent uint16 A and B components. Rotation permutes existing slab slots and adds no storage. Gap candidates add physical hole bytes. A temporary double residual plane is allocated while packing each operand, with A/B reusing the same-size workspace block. The 2 GiB `OZAMX_WORKSPACE_CACHE_BYTES` cap is per caller thread and limits retained workspace, not live allocation; the table estimates live packed payload plus one residual plane, excluding caller inputs/outputs and other process memory.

| Budget | Stored slices | Packed A+B payload, zero-gap | Residual plane | Packed + residual peak estimate | Above 2 GiB cache cap |
|---:|---:|---:|---:|---:|---:|
| P6 | 3 | 805,306,368 B (0.750 GiB) | 536,870,912 B (0.500 GiB) | 1,342,177,280 B (1.250 GiB) | 0 B |
| P10 | 4 | 1,073,741,824 B (1.000 GiB) | 536,870,912 B (0.500 GiB) | 1,610,612,736 B (1.500 GiB) | 0 B |
| P15 | 5 | 1,342,177,280 B (1.250 GiB) | 536,870,912 B (0.500 GiB) | 1,879,048,192 B (1.750 GiB) | 0 B |
| P21 | 6 | 1,610,612,736 B (1.500 GiB) | 536,870,912 B (0.500 GiB) | 2,147,483,648 B (2.000 GiB) | 0 B |

At N=8192 and zero gap, packed payload is 768 MiB / 1.0 GiB / 1.25 GiB / 1.5 GiB for p6/p10/p15/p21; adding the 512 MiB temporary residual plane gives 1.25 / 1.5 / 1.75 / 2.0 GiB. The p21 estimate lands exactly on the configured per-thread retention cap. Per-candidate gap-expanded bytes and the original metadata estimates are in the machine-readable analysis.

## Top two screen candidates by product budget

Ranking uses the mean of all three raw full-API wall samples. The median and sample SD are also reported; no repetition is dropped. Neighbor references show each bracketing frozen-V3 control separately, including its own mean and median; the initial control is not used as a permanent baseline or averaged away. Candidate groups are bracketed by initial/after04, after04/after08, after08/after12, or after12/after16 controls.

| Budget | Rank | Candidate | A/B gap bytes | A/B rotation | API mean (s) | API median (s) | API sample SD (s) | Compute+reconstruct mean (s) | Neighbor V3 API means (s) | Candidate / each V3 mean | Packed A+B bytes |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| P6 | 1 | `a0_b0_ra1_rb3` | 0/0 | 1/3 | 0.234284 | 0.232696 | 0.019294 | 0.189248 | 0.229723/0.231317 | 1.020×/1.013× | 805,306,368 |
| P6 | 2 | `a0_b0_ra1_rb0` | 0/0 | 1/0 | 0.235264 | 0.230741 | 0.009608 | 0.191336 | 0.225413/0.229723 | 1.044×/1.024× | 805,306,368 |
| P10 | 1 | `a0_b0_ra0_rb0` | 0/0 | 0/0 | 0.325721 | 0.319530 | 0.017746 | 0.280583 | 0.704846/0.348002 | 0.462×/0.936× | 1,073,741,824 |
| P10 | 2 | `a0_b0_ra1_rb3` | 0/0 | 1/3 | 0.326022 | 0.321135 | 0.017142 | 0.281189 | 0.354221/0.359037 | 0.920×/0.908× | 1,073,741,824 |
| P15 | 1 | `a0_b0_ra1_rb3` | 0/0 | 1/3 | 0.451333 | 0.455083 | 0.027972 | 0.404740 | 0.462618/0.462520 | 0.976×/0.976× | 1,342,177,280 |
| P15 | 2 | `a0_b0_ra3_rb1` | 0/0 | 3/1 | 0.453526 | 0.459538 | 0.013212 | 0.407140 | 0.462618/0.462520 | 0.980×/0.981× | 1,342,177,280 |
| P21 | 1 | `a0_b0_ra1_rb1` | 0/0 | 1/1 | 0.596286 | 0.599955 | 0.011472 | 0.548425 | 0.608358/0.595488 | 0.980×/1.001× | 1,610,612,736 |
| P21 | 2 | `a0_b0_ra1_rb0` | 0/0 | 1/0 | 0.608896 | 0.595325 | 0.033209 | 0.560842 | 0.585563/0.608358 | 1.040×/1.001× | 1,610,612,736 |

## Bracketing frozen-V3 control drift

Each cell is control API mean / median in seconds; each control retains its own full raw vectors and actual repetition count in `analysis.json`. This avoids selecting an early control as a fixed baseline. The initial control has seven samples; later drift controls have three. The initial p10 mean/median divergence is left visible rather than filtered.

| V3 control | p6 mean / median | p10 mean / median | p15 mean / median | p21 mean / median |
|---|---:|---:|---:|---:|
| frozen_v3_initial (n=7) | 0.232435 / 0.230613 | 0.704846 / 0.349348 | 0.482232 / 0.478183 | 0.642886 / 0.614517 |
| frozen_v3_drift_after_04 (n=3) | 0.242709 / 0.247283 | 0.348002 / 0.355560 | 0.459475 / 0.454901 | 0.602778 / 0.600112 |
| frozen_v3_drift_after_08 (n=3) | 0.225413 / 0.220458 | 0.342539 / 0.338158 | 0.450539 / 0.448219 | 0.585563 / 0.588328 |
| frozen_v3_drift_after_12 (n=3) | 0.229723 / 0.232011 | 0.354221 / 0.357529 | 0.462618 / 0.471634 | 0.608358 / 0.614702 |
| frozen_v3_drift_after_16 (n=3) | 0.231317 / 0.226709 | 0.359037 / 0.364094 | 0.462520 / 0.458920 | 0.595488 / 0.608276 |

## Phase behavior

Changes below compare each gap/rotation candidate with zero-gap, zero-rotation candidate 1 using the full three-sample means. `API−compute` is API wall minus the compute/reconstruction phase; it is a descriptive proxy for noncompute time, not a separately instrumented timer. Symmetric-gap summaries are medians across the five nonzero symmetric gaps; rotation summaries are medians/ranges across the five zero-gap rotations. Asymmetric cases are summarized by their observed min/max. No sample is removed.

| Budget | Symmetric gaps: median API Δ | median compute Δ | median API−compute added | Asymmetric gaps: API Δ range | compute Δ range | Zero-gap rotations: API Δ range | compute Δ range |
|---:|---:|---:|---:|---:|---:|---:|---:|
| P6 | +39.1% | -9.4% | +121.8 ms | +61.4% … +157.3% | -8.0% … +74.6% | -9.7% … -5.2% | -12.1% … -6.4% |
| P10 | +44.8% | +7.7% | +118.2 ms | +62.1% … +170.8% | +9.6% … +113.1% | +0.1% … +8.0% | +0.2% … +9.4% |
| P15 | +35.2% | -3.7% | +171.8 ms | +34.2% … +155.1% | -3.2% … +110.9% | -4.6% … +0.8% | -5.2% … +0.9% |
| P21 | +33.2% | -4.6% | +221.9 ms | +34.8% … +126.9% | -4.9% … +92.9% | -2.7% … +0.8% | -3.0% … +0.9% |

## Interpretation limits

The full-API result includes input splitting, packing, component-product compute/reconstruction, dispatch and teardown. Source-sized symmetric gaps usually increase API time sharply while compute/reconstruct stays flat or falls versus zero-gap candidate 1; the exact deltas are summarized by budget in `analysis.json`. This places much of the symmetric-gap penalty outside compute, but without PMU counters it does not identify the cause. Some asymmetric-gap candidates also show large compute/reconstruct regressions, so not every gap penalty is noncompute-only. Do not infer cache/TLB causality from wall-time phase labels alone.

For zero-gap rotation candidates (12–16), source-derived packed payload and allocation are identical to candidate 1; rotation changes only which existing slab slot each component uses. The observed rotation deltas change sign across p6/p10/p15/p21, and the largest API/compute changes remain comparable to run-to-run control movement. There is no stable all-budget compute/API trend in this three-repetition screen. Current V3 remains the production release; these candidates are exploratory and not a V4 performance claim.

Raw data, gates, checkpoints, builds and metadata remain under [`bench/8454h/roofline_v4/search_runs/packed_rotation_screen_20261014T101506Z/`](../bench/8454h/roofline_v4/search_runs/packed_rotation_screen_20261014T101506Z/). Full raw vectors, validation flags, source/library/runtime hashes, source-derived allocation accounting and candidate detail are in that directory's `analysis.json`. The offline analyzer is [`tools/analyze_v4_packed_screen.py`](../tools/analyze_v4_packed_screen.py).
