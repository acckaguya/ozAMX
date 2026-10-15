# V4 AMX load schedule experiment results

This is an isolated V4 experiment on the existing FP64 BF16-product instruction schedule. It does not change or supersede the frozen V3 release. The schedule variants change instruction ordering only; each output accumulator keeps its existing product order and each K step still issues four tile loads and four `TDPBF16PS` operations. No extra tile traffic was added. The software-pipelining rationale follows Intel Optimization Reference Manual §20.5.5, but these measurements do not establish actual load/compute overlap or a peak-throughput gain.

## Source and validation

The source kit is [`kernel_schedule_src`](../bench/8454h/roofline_v4/kernel_schedule_src/README.md); identity metadata records V3 provenance and the root-authored assembly SHA-256 `f3e2fe0e0c7f058923b675d3ab16fdc27a46c125da00539863832b5e46f01e0b`. `OZV4_LOAD_GROUP=0` is the original V3 schedule, `1` groups the B-column loads, and `2` groups the A-row loads. The pre-existing `OZAMX_LOAD_SCHEDULE=0` setting remains unchanged. Disassembly confirms group 0's `ozamx_bf16_product` instruction bytes match the frozen V3 library; groups 1 and 2 have distinct instruction sequences from the baseline and from each other.

Group 0 built to the exact frozen V3 library SHA-256 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c` and passed the three-case preflight (FP32 N=4096, FP64 p6 N=4096, FP64 p21 N=8192). Both experimental variants passed all three CTests and the full 20-case byte/transaction gate. Their library hashes are group 1 `cded4e49c1d3d883013e4e541973f9b0aeb39385b60951c72fb549e1dca99d2f` and group 2 `5fa23575f72f8a9a337ef8dc3de2b1fc4e0ddb9bb1daefef095a045be944f30c`. The gate JSON, CTest output, build logs, CMake caches, and disassembly are retained in [`bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z`](../bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/).

## Matched runtime results

Each candidate was compared with frozen V3 for FP64 N=8192 at budgets p6, p10, p15, and p21, with 11 timed pairs per configuration, one warmup, identical seeded inputs, 64 pinned threads, and GNU OpenMP runtime-default waiting (`OMP_WAIT_POLICY` and `GOMP_SPINCOUNT` unset). Full output hashes matched for all eight configurations. Samples alternate control/candidate order by repetition. The shared order sequence SHA-256 was `535e8225065c1ce49e3d9bcbdb7798b23f8ad29b272a287869c5fffffe731e40`. The result journals retain per-call phase values, input hashes, output hashes, process metadata, and order.

Speedup ratios below are control time divided by candidate time, so values above 1 favor the candidate. Paired wins count pairs where candidate API time was lower. Mean and median columns show control / candidate seconds; the paired median ratio helps limit isolated outliers but does not remove time drift.

| Group | Budget | API mean (V3 / candidate), s | API median (V3 / candidate), s | Paired API median ratio (wins) | Compute+reconstruct paired median ratio (wins) | Split paired median ratio (wins) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6 | 0.256080 / 0.252144 | 0.245062 / 0.246594 | 1.0286 (6/11) | 0.9776 (5/11) | 0.9927 (3/11) |
| 1 | 10 | 0.377993 / 0.369583 | 0.344232 / 0.356185 | 0.9767 (5/11) | 0.9454 (5/11) | 0.9801 (4/11) |
| 1 | 15 | 0.669554 / 0.593474 | 0.475448 / 0.489532 | 0.9404 (4/11) | 0.9439 (4/11) | 1.0100 (8/11) |
| 1 | 21 | 0.770861 / 0.898921 | 0.600126 / 0.631033 | 0.9435 (5/11) | 0.9452 (5/11) | 0.9663 (4/11) |
| 2 | 6 | 0.254342 / 0.254414 | 0.233881 / 0.244947 | 1.0009 (6/11) | 0.9969 (5/11) | 0.9923 (4/11) |
| 2 | 10 | 0.504259 / 0.548907 | 0.470617 / 0.599629 | 0.9440 (3/11) | 0.9613 (4/11) | 0.9669 (2/11) |
| 2 | 15 | 0.673414 / 0.518077 | 0.490475 / 0.470873 | 0.9718 (5/11) | 0.9738 (4/11) | 0.9822 (2/11) |
| 2 | 21 | 0.801806 / 0.779083 | 0.588538 / 0.619509 | 0.9706 (3/11) | 0.9628 (5/11) | 1.0197 (6/11) |

These samples do not show a repeatable advantage across budgets. Group 1 has a modest p6 paired result (1.0286, 6/11 wins), while its p10/p15/p21 paired medians favor V3. Group 2 is near even at p6 and favors V3 on the paired API median at p10/p15/p21. The differing mean, standalone median, and paired ratio behavior—especially under same-day clock/control drift—argues against choosing a scheduler from this round alone.

## Reproducibility artifacts

- Raw 88 timed pairs and phase data: [`matched_raw.csv`](../bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/matched_raw.csv).
- Mean, median, paired speedup/wins, input hashes, and order hashes by phase: [`matched_summary.json`](../bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/matched_summary.json).
- Run state, source/library/MKL identity, gates, and exact commands: [`validation_state.json`](../bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/validation_state.json).
- Per-configuration process sessions, samples, and complete-output hashes: [`matched`](../bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/matched/).
- Validation script: [`validate.py`](../bench/8454h/roofline_v4/kernel_schedule_runs/kernel_schedule_20261014T142400Z/validate.py).

No production source or V3 archive was modified. This result is an experiment only and makes no production speedup claim.
