# Adaptive V4 release candidate matched checks

Two final adaptive release archives were compared with the frozen V3 archive using the runtime-default GNU OpenMP wait policy. The runner unset `OMP_WAIT_POLICY` and `GOMP_SPINCOUNT`, inserted a 20 ms parent pause after each call outside API timing, and kept both persistent child processes pinned across CPUs 0–63. Every configuration checked matching deterministic input hashes and equal full C-buffer SHA-256; both children reported 64 OpenMP threads. All samples, phase timings, order, hashes, commands, binaries, and metadata are retained in the campaign directory.

Campaign data: `/home/caiweili/ozAMX/bench/8454h/roofline_v4/matched_calls/results/final_rc_20261014`  
Frozen V3 SHA-256: `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`  
The primary API metric below is candidate arithmetic-mean API wall time divided by frozen-V3 arithmetic-mean API wall time. Paired-ratio mean and median are also shown because shared-host drift can make them diverge. Ratios below 1 favor the candidate; raw arrays are in `summary.json`. No outliers were discarded.

| Candidate | Workload | N | Reps | Median paired ratio | Mean paired ratio | Ratio of arithmetic mean API times | C-output exact |
|---|---|---:|---:|---:|---:|---:|---|
| `rc1_geom256` | FP32 | 1024 | 7 | 0.9341 | 0.9072 | 0.8922 | yes |
| `rc1_geom256` | FP32 | 4096 | 11 | 0.8535 | 0.8372 | 0.8012 | yes |
| `rc1_geom256` | FP32 | 8192 | 11 | 0.8095 | 0.8634 | 0.8417 | yes |
| `rc1_geom256` | FP64 p10 | 1024 | 7 | 1.0911 | 1.0212 | 1.0070 | yes |
| `rc1_geom256` | FP64 p15 | 1024 | 7 | 1.0398 | 0.9991 | 0.9664 | yes |
| `rc1_geom256` | FP64 p21 | 1024 | 7 | 1.0041 | 1.0386 | 1.0366 | yes |
| `rc1_geom256` | FP64 p6 | 1024 | 7 | 1.0311 | 0.9907 | 0.9891 | yes |
| `rc1_geom256` | FP64 p6 | 4096 | 11 | 0.9350 | 0.9195 | 0.7490 | yes |
| `rc1_geom256` | FP64 p6 | 8192 | 11 | 0.8176 | 0.8467 | 0.8350 | yes |
| `rc2_geom512` | FP32 | 1024 | 7 | 1.0822 | 1.0449 | 1.0226 | yes |
| `rc2_geom512` | FP32 | 4096 | 11 | 0.8359 | 0.8097 | 0.7592 | yes |
| `rc2_geom512` | FP32 | 8192 | 11 | 0.8858 | 0.8992 | 0.8987 | yes |
| `rc2_geom512` | FP64 p10 | 1024 | 7 | 1.0099 | 0.9798 | 0.9048 | yes |
| `rc2_geom512` | FP64 p15 | 1024 | 7 | 1.1477 | 1.0818 | 1.0758 | yes |
| `rc2_geom512` | FP64 p21 | 1024 | 7 | 0.9269 | 1.3676 | 1.3820 | yes |
| `rc2_geom512` | FP64 p6 | 1024 | 7 | 1.1291 | 1.1253 | 1.1233 | yes |

## Large FP32 detail

| Candidate | N | All 11 paired API ratios, in call order | Median | Mean paired | Ratio of mean API times |
|---|---:|---|---:|---:|---:|
| `rc1_geom256` | 4096 | 0.81190, 0.82333, 0.69544, 0.53955, 0.85375, 1.00765, 1.11787, 1.06891, 0.56926, 0.85349, 0.86797 | 0.85349 | 0.83719 | 0.80115 |
| `rc1_geom256` | 8192 | 0.76750, 1.05403, 1.14904, 0.61997, 0.62219, 0.77632, 1.00087, 0.75903, 1.07714, 0.80950, 0.86167 | 0.80950 | 0.86339 | 0.84168 |
| `rc2_geom512` | 4096 | 0.87327, 0.77113, 0.84066, 0.81645, 1.37787, 0.50410, 0.56747, 0.45844, 0.83586, 1.01595, 0.84545 | 0.83586 | 0.80970 | 0.75916 |
| `rc2_geom512` | 8192 | 0.81234, 1.02753, 0.76715, 0.97474, 0.96066, 0.71398, 0.72509, 0.95733, 1.30103, 0.88576, 0.76506 | 0.88576 | 0.89915 | 0.89872 |

## Phase-profile calibration

Per-call phase values and ratios are retained separately by precision and budget. The API-wall metric includes allocation and the whole profiled call; split, pack, compute/reconstruct, and profile-total timings must be interpreted within their matching precision/budget, not pooled as interchangeable useful-AMX work. `summary.json` gives raw phase arrays, paired ratios, means, medians, and ratios of arithmetic means for every configuration.

The large FP32 data favor each candidate against frozen V3 on average, but individual runs include substantial drift and some slow calls. These are direct release-archive checks; they do not establish a roofline claim or eliminate remaining shared-host uncertainty. Keep any production decision conditional on the project’s accuracy gates and broader deployment validation.

All N=1024 FP32 and four-budget FP64 regression checks are included in the table and raw campaign data. RC1 also includes FP64 p6 large-N checks. RC2 FP64 p6 large-N was outside the requested scope.
