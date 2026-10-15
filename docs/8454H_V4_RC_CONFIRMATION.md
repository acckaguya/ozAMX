# Independent RC1 runtime confirmation

This independent campaign rechecked the exact RC1 archive against the frozen V3 control after the earlier matched batch. The candidate archive was not rebuilt or modified; its SHA-256 is verified in every run. GNU OpenMP runtime-default waiting was restored by unsetting `OMP_WAIT_POLICY` and `GOMP_SPINCOUNT`; the parent inserted a 20 ms park after calls outside measured API intervals. Both persistent children were pinned to CPUs 0–63 and reported 64 OpenMP workers.

Campaign data: `/home/caiweili/ozAMX/bench/8454h/roofline_v4/matched_calls/results/rc1_independent_confirmation_20261014`  
Startup resources: `/home/caiweili/ozAMX/bench/8454h/roofline_v4/matched_calls/results/rc1_independent_confirmation_20261014/startup_resources.txt`  
Candidate SHA-256: `2a3e5533fbd5397df2c44284a7a7da54b0463558e36f8f9f284b210831c80695`  
Frozen V3 SHA-256: `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`  
All six configurations ran 11 paired repetitions. Each run checked deterministic input hashes and complete C-buffer SHA-256 equality. Every raw call, phase time, order, binary/source/library hash, and output hash is in `summary.json` and the per-run journals. No observations were dropped. API wall includes allocation and the complete profiled API call. Ratios below 1 favor RC1.

| Precision/workload | N | Fast calls | Median paired API ratio | Mean paired API ratio | Ratio of arithmetic mean API times | Exact C output |
|---|---:|---:|---:|---:|---:|---|
| FP32 | 16384 | 9/11 | 0.83545 | 1.08055 | 1.07427 | yes |
| FP32 | 4096 | 11/11 | 0.92430 | 0.91232 | 0.91063 | yes |
| FP32 | 8192 | 10/11 | 0.93251 | 0.92001 | 0.91086 | yes |
| FP64 p6 | 16384 | 9/11 | 0.93392 | 0.95903 | 0.95659 | yes |
| FP64 p6 | 4096 | 5/11 | 1.00815 | 1.19631 | 1.14271 | yes |
| FP64 p6 | 8192 | 6/11 | 0.92574 | 0.96782 | 0.95450 | yes |

## Complete API-wall ratio sequences

| Precision | N | All 11 candidate/control ratios, in call order |
|---|---:|---|
| FP32 | 16384 | 0.83518, 0.85468, 0.80791, 0.83516, 0.83545, 0.82457, 3.13677, 1.24862, 0.83623, 0.84656, 0.82490 |
| FP32 | 4096 | 0.94582, 0.88413, 0.92202, 0.92430, 0.95245, 0.88510, 0.97749, 0.98594, 0.91427, 0.93714, 0.70689 |
| FP32 | 8192 | 0.93251, 0.94602, 0.94768, 0.60250, 0.92486, 0.96958, 0.99736, 0.88600, 1.23511, 0.79759, 0.88089 |
| FP64 p6 | 16384 | 0.95626, 0.97111, 0.91996, 0.93798, 0.93392, 1.19291, 0.87880, 1.11906, 0.87083, 0.87834, 0.89013 |
| FP64 p6 | 4096 | 1.52090, 2.47349, 0.85984, 1.20767, 1.71811, 0.58752, 0.90157, 1.00815, 1.02172, 0.93170, 0.92871 |
| FP64 p6 | 8192 | 0.83010, 1.00112, 0.88057, 0.92574, 0.88682, 0.81750, 1.01843, 1.07265, 0.87489, 1.16411, 1.17411 |

## Precision-specific operation-equivalent rates

Using the requested useful-work convention `W = 2 × N³ × p`, with p=6 for both workload families, the tables give mean-wall operation-equivalent rates at API wall, total profile, and compute/reconstruct profile intervals. The compute/reconstruct interval includes reconstruction, so it is not a direct AMX instruction throughput measurement. These rates are finite performance context, not hardware guarantees. Calibration references are kept separate by precision: 161.018 TFLOP/s FP32 single-precision calibration, 151.738 TFLOP/s mixed FP32 context, and 84.423 TFLOP/s FP64 p6 mixed context. Do not pool them or interpret them as measured DRAM lower bounds.

| Precision | N | Control API | RC1 API | Control profile total | RC1 profile total | Control compute/reconstruct | RC1 compute/reconstruct |
|---|---:|---:|---:|---:|---:|---:|---:|
| FP32 | 16384 | 33.778 | 31.443 | 39.288 | 36.187 | 42.527 | 38.706 |
| FP32 | 4096 | 22.015 | 24.176 | 22.022 | 24.184 | 25.189 | 27.960 |
| FP32 | 8192 | 25.434 | 27.923 | 25.436 | 27.925 | 27.186 | 30.052 |
| FP64 p6 | 16384 | 17.257 | 18.040 | 19.330 | 20.313 | 23.191 | 24.361 |
| FP64 p6 | 4096 | 14.790 | 12.943 | 14.793 | 12.945 | 18.575 | 18.503 |
| FP64 p6 | 8192 | 16.181 | 16.952 | 16.181 | 16.953 | 18.939 | 19.790 |

At N=16384 FP32, median and mean tell different stories: the median paired ratio is 0.83545, with 9/11 calls faster, but two slow calls (ratios 3.13677 and 1.24862) yield mean paired ratio 1.08055 and ratio of arithmetic mean API times 1.07427. Retaining these observations changes the mean conclusion; no average speedup claim is warranted for that size. For FP64 p6 N=16384, the complete raw series and corresponding mean and median are in the table and machine-readable summary.

N=16384 is an additional implementation performance check only. Byte-exact equality to frozen V3 does not constitute a new check against paper precision metrics. The N=4096 and N=8192 FP32 results repeat the improvement direction from the earlier RC1 batch on the paired medians and mean API time, while N=16384 highlights shared-host outlier sensitivity. Treat this as a candidate for further controlled study, not a hardware-performance guarantee.
