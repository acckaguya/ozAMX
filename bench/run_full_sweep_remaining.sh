#!/usr/bin/env bash
set -euo pipefail
cd /data/home/caiwl/ozAMX
export LD_LIBRARY_PATH="$PWD/third_party/code/mkl-2026/venv/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=64 OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close OMP_DISPLAY_ENV=VERBOSE
export MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU
exec timeout --signal=TERM --kill-after=60 4h taskset -c 0-63 \
  /tmp/ozamx-build/ozamx_benchmark \
  --sizes 8192,16384,32768 --threads 64 --reps 10 --precision all \
  --distribution uniform --seed 260904 \
  --output bench/full_sweep_resume.csv \
  --checkpoint bench/full_sweep_resume_progress \
  > /dev/null 2> bench/full_sweep_resume_runtime.log
