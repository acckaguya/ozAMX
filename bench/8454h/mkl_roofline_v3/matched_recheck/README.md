# Matched V2/V3 recheck

This is a supplemental five-process sequence in fixed order: frozen V2, roofline V3, frozen V2, roofline V3, frozen V2. Each process has its own driver snapshot and checkpoint source ID, binary, CSV, logs, provenance, and checkpoints. The runner verifies both library SHAs and holds `/tmp/ozamx-perf.lock` across all builds and runs.

Each process measures N=1024/2048/8192, FP32 p6 and FP64 p6/p10/p15/p21, seven timed repetitions after one warmup, seed base 260904 resolved as 260904+N, uniform[-1,1], 64 threads on CPUs 0–63, GNU-threaded MKL LP64, and the 2 GiB workspace cache. The CSV adds `raw_mkl_gemm_s`, preserving each of the seven oneMKL GEMM timing samples in addition to the raw seven ozAMX API-wall samples, their mean and population standard deviation, error metrics, and checksums.

The original 20-case result at the parent directory remains unchanged. These matched measurements supplement it and do not replace or splice into it. Summaries use each process's median for a configuration, then the median across the three V2 or two V3 process medians; all means, standard deviations, raw samples, and process-level values remain available.
