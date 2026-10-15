# V4 stage 1 screen summary

Dataset: `screen_20261014_20261014T094029Z_retry2`. This is an N=8192, mode 3 candidate screen with 3 timing repetitions per each of five precision/budget workloads. Each timed candidate has a six-case bytewise V3 binary gate and all three CTest tests passing. CSVs have 37 columns and five complete `status=ok` rows. The mode 3 `accuracy_scope` remains `numeric_gate_pending`; the quick gate is not the full final numerical gate.

The 29 timed candidates comprise previously verified candidates 1–12 plus candidates 14–30. Candidate 13 (`b2_m256_n1024_p64_h1_l1`) is excluded with no timing: its default-stack quick-gate child SIGSEGVed in `f64_alias_a_equals_c_p6`; an 8 MiB stack run was diagnostic only. This was recorded as a resource/execution failure, not a numerical mismatch or pass.

Preliminary shortlist sorted by the geometric mean across the five workloads of `(candidate MKL GEMM time / API wall time) / (baseline mode 3 MKL GEMM time / API wall time)`. A score above 1 means a better ratio than the initial mode 3 baseline in these screen measurements:

| Screen rank | Candidate | FP64 batch | CBM | CBN | Relative geometric score |
|---:|---|---:|---:|---:|---:|
| 1 | `b2_m256_n256_p64_h1_l1` | 2 | 256 | 256 | 1.135× |
| 2 | `b2_m256_n512_p64_h1_l1` | 2 | 256 | 512 | 1.103× |
| 3 | `b2_m128_n256_p64_h1_l1` | 2 | 128 | 256 | 1.064× |
| 4 | `b2_m256_n128_p64_h1_l1` | 2 | 256 | 128 | 1.060× |
| 5 | `b2_m128_nauto_p64_h1_l0` | 2 | 128 | auto | 1.055× |
| 6 | `b12_m128_nauto_p64_h1_l1` | 12 | 128 | auto | 1.042× |

This is only a screen, not a winner claim. Keep the strongest geometry candidates for the planned layout variants and full 18-pair/reps-7 matched confirmation; do not promote from three reps. Performance drift is visible in the V3 controls: the averaged API wall time across the five rows was 0.354–0.419 s through the after-20 checkpoint, then 0.650 s after candidate 25 and 0.550 s after candidate 30; the final V3 control averaged 0.557 s, versus the initial V3 0.378 s. That shift limits interpretation of later candidates and makes the matched confirmation necessary.

Detailed row metrics, all validation booleans, build/library hashes, controls, and CSV hashes are in [`screen_summary.json`](screen_summary.json). The immutable V3 library used for the gate is SHA-256 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`; MKL runtime SHA-256 is `b2ff0e31d7cd18c91813d8f6500f37665597d89de22649d90687aa6bf7bd2c0f`.
