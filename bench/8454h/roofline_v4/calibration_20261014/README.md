# V4-era roofline calibration rerun

Independent batch replacing no old raw files: `raw/kernels.csv` (228 rows), binary and disassembly in `bin/`, sources and the exact linked V3 library in `source/`, invocation in `run.sh`, environment in `environment.json`, and offline analysis in `analysis.json` / `analyze.py`.

The run uses the unchanged roofline microkernel source and protocol in the prior calibration: 57 cases, each warmup plus 3 timed repetitions, 80 ms target interval, AMX permission/checksum validation, worker-local first-touch, 1/32/64 threads, `taskset -c 0-63`, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, and `OMP_DYNAMIC=FALSE`. All benchmark windows ran under `/tmp/ozamx-perf.lock`. The executable links the frozen production V3 `libozamx.a` (SHA-256 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`).

The executable does not call MKL; no MKL number is part of this measurement. Logical payload rates are accounting for explicit kernel bytes, not PMU/cache/DRAM traffic. No physical roof claim is made.

Re-run only when explicitly intended: `./bench/8454h/roofline_v4/calibration_20261014/run.sh`. Recompute offline summary: `./bench/8454h/roofline_v4/calibration_20261014/analyze.py` (writes `analysis.json`; this rerun is read-only to measurement files).
