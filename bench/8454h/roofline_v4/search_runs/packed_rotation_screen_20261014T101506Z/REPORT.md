# V4 zero-gap packed-slab rotation screen

Coverage: 16/16 candidates; complete and all gates/CTest: True.

Each candidate passed a full 20-case numeric gate and CTest before four N=8192 FP64 budgets were timed. All three API-wall samples are retained; no outliers are removed. The lowest observed mean per budget below is a descriptive screen leader only, not a statistically validated winner.

| Budget | Descriptive screen leader | API wall mean (s) | packed output bytes | padding extra (bytes) |
|---:|---|---:|---:|---:|
| P6 | `a0_b0_ra1_rb3` | 0.234284082 | 1610612736 | 0 |
| P10 | `a0_b0_ra0_rb0` | 0.325720591 | 2684354560 | 0 |
| P15 | `a0_b0_ra1_rb3` | 0.451332914 | 4026531840 | 0 |
| P21 | `a0_b0_ra1_rb1` | 0.596285820 | 5637144576 | 0 |

Full phase/API and oneMKL timing values, all reps/checkpoints, controls, gate references, and incomplete coverage are in `analysis.json` and the retained result tree. The packed-output byte estimate covers persistent uint16 A/B component arrays, excluding temporary residual buffers and public input/output.
