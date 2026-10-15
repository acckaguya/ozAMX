# Roofline-guided production oneMKL comparison (V3)

Prepared for the final roofline candidate library. The snapshot driver uses checkpoint source ID `mkl-wall-roofline-v3-20261013`, isolating all 20 checkpoints from earlier campaigns. Do not compile or run until root supplies the final production library path and expected SHA-256.

`run.sh` accepts that path and SHA, checks the archive hash, then holds `/tmp/ozamx-perf.lock` across compilation and the matrix. It uses the frozen protocol: N=256/1024/4096/8192; FP32 p6 and FP64 p6/p10/p15/p21; five timed calls after one warmup; seed base 260904 with resolved seed 260904+N; uniform[-1,1]; CPUs 0–63; 64 OpenMP and MKL threads; GNU MKL threading; LP64; `MKL_DYNAMIC=FALSE`; and a 2 GiB workspace cache.

The CSV records full-call ozAMX API wall, ozAMX phase times, and GEMM-only MKL timing, plus raw samples, population mean and standard deviation, checksums, MKL errors, high-precision errors, product order, runtime identity, and status. The timing scopes differ, so API-wall/MKL ratios are descriptive. The result characterizes the complete ozAMX API and the oneMKL GEMM call separately.

After the authorized run, retain the complete CSV, all 20 complete checkpoints, executable and source/library/runtime hashes, compiler and command, and environment in this directory. Compare these rows to the frozen V2 data in `../mkl_v2/full_candidate.csv` and baseline production rows in `../mkl_production/full_production.csv`; do not edit those source records or raw CSVs. The combined interpretation belongs in `docs/8454H_ROOFLINE_RESULTS.md`.
