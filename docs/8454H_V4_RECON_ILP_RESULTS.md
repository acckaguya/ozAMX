# V4 ordered reconstruction ILP4 results

The 8-configuration, three-repetition N=8192 FP64 screen completed 2026-10-14T11:00:48Z–2026-10-14T11:13:07Z on 64 pinned CPUs. Each configuration passed four CTests and a strict 20-case byte/transaction gate before timing. The new assembly was enabled only for late FP64 wide reconstruction; FP32 behavior remained in mode 0.

The direct assembly probe compared all 32×32 outputs against an independent scalar reference for strides 32, 40, 136, 264 and 1032 double elements, counts 1, 2, 4, 8, 12 and 21, finite and special-value inputs. Every finite output matched bitwise, including finite lanes in special-value runs; nonfinite classifications and infinity signs matched; row padding and trailing guards remained unchanged. The ABI shim verified rbx, rbp and r12–r15. ON and OFF probes both passed.

ON object disassembly contains the `ozamx_reconstruct64_ilp4` relocation in the mode-0 Late64 wide path; OFF objects contain no call relocation. The source assembly SHA-256 is `4af3698492a1b33d5ccd702fa628f1ba13ef866104333f2da0f07b6535782fde`.

## Paired API wall and reconstruction profile medians

| Batch | FP64 budget | OFF API (s) | ON API (s) | API change | OFF compute/reconstruct (s) | ON compute/reconstruct (s) | Compute change | Profile-total change |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 6 | 0.230458 | 0.242010 | +5.01% | 0.188561 | 0.200114 | +6.13% | +5.01% |
| 2 | 10 | 0.329935 | 0.332091 | +0.65% | 0.286712 | 0.289029 | +0.81% | +0.65% |
| 2 | 15 | 0.450807 | 0.448388 | -0.54% | 0.405544 | 0.403735 | -0.45% | -0.54% |
| 2 | 21 | 0.585609 | 0.575972 | -1.65% | 0.539668 | 0.530011 | -1.79% | -1.64% |
| 8 | 6 | 0.227604 | 0.238095 | +4.61% | 0.185923 | 0.195573 | +5.19% | +4.61% |
| 8 | 10 | 0.335620 | 0.338999 | +1.01% | 0.292228 | 0.295625 | +1.16% | +1.01% |
| 8 | 15 | 0.455553 | 0.437153 | -4.04% | 0.410841 | 0.392391 | -4.49% | -4.04% |
| 8 | 21 | 0.604290 | 0.577870 | -4.37% | 0.558454 | 0.531757 | -4.78% | -4.37% |
| 12 | 6 | 0.251990 | 0.402561 | +59.75% | 0.210467 | 0.359291 | +70.71% | +59.76% |
| 12 | 10 | 0.355174 | 0.609371 | +71.57% | 0.310664 | 0.563096 | +81.26% | +71.57% |
| 12 | 15 | 0.871958 | 0.823567 | -5.55% | 0.827359 | 0.769415 | -7.00% | -5.55% |
| 12 | 21 | 1.161154 | 1.170195 | +0.78% | 1.086640 | 1.117365 | +2.83% | +0.78% |
| 21 | 6 | 0.425026 | 0.303274 | -28.65% | 0.379133 | 0.259183 | -31.64% | -28.65% |
| 21 | 10 | 0.797261 | 0.611624 | -23.28% | 0.740536 | 0.564451 | -23.78% | -23.28% |
| 21 | 15 | 0.918136 | 0.878641 | -4.30% | 0.871214 | 0.822736 | -5.56% | -4.30% |
| 21 | 21 | 0.631271 | 1.197992 | +89.77% | 0.574449 | 1.150120 | +100.21% | +89.78% |

## Frozen V3 control drift

| Control interval | Budget | V3 API median before (s) | V3 API median after (s) | Drift |
|---|---:|---:|---:|---:|
| frozen_v3_initial_retry1 → frozen_v3_after_batch8 | 6 | 0.230805 | 0.239522 | +3.78% |
| frozen_v3_initial_retry1 → frozen_v3_after_batch8 | 10 | 0.342656 | 0.329874 | -3.73% |
| frozen_v3_initial_retry1 → frozen_v3_after_batch8 | 15 | 0.477226 | 0.451695 | -5.35% |
| frozen_v3_initial_retry1 → frozen_v3_after_batch8 | 21 | 0.592241 | 0.590757 | -0.25% |
| frozen_v3_after_batch8 → frozen_v3_after_batch21 | 6 | 0.239522 | 0.244744 | +2.18% |
| frozen_v3_after_batch8 → frozen_v3_after_batch21 | 10 | 0.329874 | 0.333694 | +1.16% |
| frozen_v3_after_batch8 → frozen_v3_after_batch21 | 15 | 0.451695 | 0.461441 | +2.16% |
| frozen_v3_after_batch8 → frozen_v3_after_batch21 | 21 | 0.590757 | 0.599491 | +1.48% |

The rows retain every three-sample API vector and the matching raw compute/reconstruction and profile-total vectors in the per-configuration CSV files. The full CSV also retains MKL GEMM timings and runtime fields. N=8192 control CSVs retain seven samples per budget. The N=256 OFF preflight is reused from the prior preparation run; the ON half is recorded in this run.

This short screen has no declared winner. Batch 12 ON showed a marked increase for budgets 6 and 10, visible in both API wall and compute/reconstruction samples. Batch 21 ON was faster for budgets 6 and 10 but about 90% slower for budget 21. These large changes remain in the data and should be checked in the matched seven-repetition follow-up. Batch 2 and 8 changes are smaller and comparable to some V3 bracket drift.

## Reproducibility artifacts

- Dataset: `bench/8454h/roofline_v4/recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z/dataset.json`
- Analysis JSON: `bench/8454h/roofline_v4/recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z/analysis.json`
- Build and library manifest: `bench/8454h/roofline_v4/recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z/dataset.json` (`candidate_artifacts`)
- Global lock: `/tmp/ozamx-perf.lock` held exclusively from campaign start through the final control.
- Immutable V3 SHA-256: `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`; original and paper-release archive paths were byte-identical.
- First V3 timing attempt hit the archive binary permission mode 0444. Its log and SHA are preserved; timing resumed with a freshly linked driver against the same frozen V3 static library.
