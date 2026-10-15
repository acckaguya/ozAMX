# V4 matched-call geometry results

Both mode-3 geometry candidates were linked into separate persistent child processes from the same matched driver source and compared with frozen V3. The runner alternated control-first and candidate-first order for each of seven timed repetitions, retained every observation, checked deterministic full input hashes, and required equal SHA-256 hashes for each complete C output. Each candidate passed all 20 full binary-gate cases.

Campaign: `/home/caiweili/ozAMX/bench/8454h/roofline_v4/matched_calls/results/formal_20261014T121828Z_2`  
Control SHA-256: `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`  
Runtime settings: 64 threads pinned to CPUs 0–63; GNU OpenMP with `OMP_WAIT_POLICY=PASSIVE`, `GOMP_SPINCOUNT=0`, `OMP_PLACES=cores`, and `OMP_PROC_BIND=close`; 2 GiB workspace cache. These passive-wait settings differ from earlier GNU OpenMP default screens.

All values below use API wall time, which includes the complete profiled call and allocation effects. Ratios are candidate/control, so values below 1.0 favor the candidate. We show the median paired ratio, the arithmetic mean of the seven paired ratios, and the ratio of arithmetic mean candidate/control API times separately. The summary JSON keeps raw per-call phase and wall timings, exact order, input hashes, and output hashes for all 30 configurations.

| Candidate | Configurations faster by median | Median paired ratio | Mean paired ratio | Ratio of mean API times | Stable gain across all configs |
|---|---:|---:|---:|---:|---|
| `b2_m256_n256` | 11/15 | 0.9571 | 0.9492 | 0.7719 | no |
| `b2_m256_n512` | 10/15 | 0.9467 | 0.9583 | 0.8101 | no |

Workload-level initial recheck candidates from per-configuration medians. These are preliminary precision clues only, not production recommendations or repeatability claims:

| Workload | N256 geometry medians (1024/4096/8192) | N512 geometry medians (1024/4096/8192) | Lower aggregate median hint |
|---|---|---|---|
| fp32 | 0.9564 / 0.8125 / 0.8898 | 1.0033 / 0.8232 / 0.8378 | `b2_m256_n512` (preliminary) |
| fp64_p6 | 1.0047 / 0.9573 / 0.8065 | 1.0170 / 0.8645 / 0.9404 | `b2_m256_n256` (preliminary) |
| fp64_p10 | 1.0274 / 0.8029 / 0.8950 | 1.0024 / 0.9591 / 0.8007 | `b2_m256_n512` (preliminary) |
| fp64_p15 | 0.9852 / 0.9315 / 0.9515 | 1.0162 / 0.9336 / 0.9219 | `b2_m256_n512` (preliminary) |
| fp64_p21 | 1.0381 / 0.8220 / 1.0383 | 1.0091 / 0.9467 / 0.8627 | `b2_m256_n512` (preliminary) |

Per-configuration API ratios and measured order effects:

| Candidate | Precision/budget | N | Median paired ratio | Mean paired ratio | Ratio of mean API times | Control second/first | Candidate second/first | Output bytes equal |
|---|---|---:|---:|---:|---:|---:|---|
| `b2_m256_n256` | fp32/p6 | 1024 | 0.9564 | 0.9712 | 0.9505 | +8.2% | -2.8% | yes |
| `b2_m256_n256` | fp32/p6 | 4096 | 0.8125 | 0.7572 | 0.7411 | +27.0% | -23.3% | yes |
| `b2_m256_n256` | fp32/p6 | 8192 | 0.8898 | 0.8663 | 0.8384 | +8.7% | -16.3% | yes |
| `b2_m256_n256` | fp64/p10 | 1024 | 1.0274 | 1.1165 | 1.1146 | -1.1% | +2.3% | yes |
| `b2_m256_n256` | fp64/p10 | 4096 | 0.8029 | 1.0267 | 0.9326 | -0.8% | -37.5% | yes |
| `b2_m256_n256` | fp64/p10 | 8192 | 0.8950 | 1.0246 | 0.8275 | +4.8% | +4.5% | yes |
| `b2_m256_n256` | fp64/p15 | 1024 | 0.9852 | 0.9897 | 0.9895 | +1.1% | +0.2% | yes |
| `b2_m256_n256` | fp64/p15 | 4096 | 0.9315 | 1.0210 | 1.0090 | +4.0% | -11.5% | yes |
| `b2_m256_n256` | fp64/p15 | 8192 | 0.9515 | 0.8832 | 0.7589 | -1.3% | +4.2% | yes |
| `b2_m256_n256` | fp64/p21 | 1024 | 1.0381 | 1.0322 | 1.0305 | -2.5% | -2.0% | yes |
| `b2_m256_n256` | fp64/p21 | 4096 | 0.8220 | 0.8442 | 0.7339 | -22.4% | -19.2% | yes |
| `b2_m256_n256` | fp64/p21 | 8192 | 1.0383 | 0.9485 | 0.8282 | +6.1% | -12.8% | yes |
| `b2_m256_n256` | fp64/p6 | 1024 | 1.0047 | 1.0596 | 1.0595 | -3.0% | -1.2% | yes |
| `b2_m256_n256` | fp64/p6 | 4096 | 0.9573 | 0.9621 | 0.9621 | +1.0% | -7.6% | yes |
| `b2_m256_n256` | fp64/p6 | 8192 | 0.8065 | 0.7353 | 0.5078 | -6.5% | +1.4% | yes |
| `b2_m256_n512` | fp32/p6 | 1024 | 1.0033 | 0.9997 | 0.9922 | -2.2% | +5.9% | yes |
| `b2_m256_n512` | fp32/p6 | 4096 | 0.8232 | 0.8983 | 0.9005 | +2.8% | +12.2% | yes |
| `b2_m256_n512` | fp32/p6 | 8192 | 0.8378 | 0.8411 | 0.8378 | +9.4% | -7.7% | yes |
| `b2_m256_n512` | fp64/p10 | 1024 | 1.0024 | 0.9967 | 0.9961 | -0.2% | +0.5% | yes |
| `b2_m256_n512` | fp64/p10 | 4096 | 0.9591 | 1.1509 | 0.9015 | +18.9% | -16.3% | yes |
| `b2_m256_n512` | fp64/p10 | 8192 | 0.8007 | 0.9308 | 0.7857 | -34.7% | +4.4% | yes |
| `b2_m256_n512` | fp64/p15 | 1024 | 1.0162 | 1.0200 | 1.0200 | +1.9% | -2.0% | yes |
| `b2_m256_n512` | fp64/p15 | 4096 | 0.9336 | 0.8793 | 0.7196 | +30.3% | -2.0% | yes |
| `b2_m256_n512` | fp64/p15 | 8192 | 0.9219 | 0.8409 | 0.6747 | +132.5% | +23.5% | yes |
| `b2_m256_n512` | fp64/p21 | 1024 | 1.0091 | 0.9140 | 0.8727 | -9.8% | -16.4% | yes |
| `b2_m256_n512` | fp64/p21 | 4096 | 0.9467 | 0.9759 | 0.8089 | -12.1% | +14.4% | yes |
| `b2_m256_n512` | fp64/p21 | 8192 | 0.8627 | 0.9024 | 0.8897 | +24.4% | +1.4% | yes |
| `b2_m256_n512` | fp64/p6 | 1024 | 1.0170 | 1.0171 | 1.0167 | +0.3% | -0.4% | yes |
| `b2_m256_n512` | fp64/p6 | 4096 | 0.8645 | 1.0458 | 1.0439 | -17.8% | +53.6% | yes |
| `b2_m256_n512` | fp64/p6 | 8192 | 0.9404 | 0.9610 | 0.9562 | +3.0% | -0.6% | yes |

No single geometry meets the geometry-wide stable-gain rule. Workload hints are preliminary recheck candidates only; order effects and mean/median divergence prevent a repeatability claim. Keep V3 selected pending runtime-policy confirmation.

Full 20-case gate records, per-configuration journals, compiler commands/logs, and hashes are retained in the campaign directory. The gate cases cover full-output wide geometry (including K=1), large-K overflow/cancellation and nonfinite transactions, and A=C/B=C alias transactions.

## Runtime-default p6 recheck

A separate, later recheck used the n256 mode-3 candidate at FP64 p6, with inherited `OMP_WAIT_POLICY` and `GOMP_SPINCOUNT` unset and a 20 ms parent pause after every child call (outside API timing). This tests transfer from the passive-wait campaign toward GNU OpenMP runtime defaults. Both sizes used 11 alternating paired observations, all retained; per-call logs, full-buffer checksums, binaries and metadata are in `bench/8454h/roofline_v4/matched_calls/results/runtime_recheck_b2_m256_n256_fp64_p6_20261014`.

| N | Raw candidate/control API ratios (all 11) | Median paired ratio | Mean paired ratio | Ratio of mean API times |
|---:|---|---:|---:|---:|
| 4096 | 1.19773, 0.79077, 0.98234, 0.96949, 0.92129, 0.94025, 0.52681, 0.55314, 1.54196, 1.33050, 0.90024 | 0.94025 | 0.96859 | 0.92122 |
| 8192 | 0.97402, 0.69745, 1.03250, 1.05708, 0.80610, 1.21299, 0.96971, 0.91689, 0.87949, 0.86548, 1.32158 | 0.96971 | 0.97575 | 0.97455 |

The broad spread and mean/median differences leave this as preliminary evidence, not confirmation of a production win. Across the passive campaign, workload labels are likewise only initial recheck candidates by precision. In particular, the mode-3 FP32 geometry observations do not validate the minimal-release FP32 implementation. Keep frozen V3 as the production baseline until a candidate’s release build is directly validated under the intended runtime policy.
