#!/usr/bin/env bash
set -euo pipefail

out=/home/caiweili/ozAMX/bench/8454h/roofline/search_batch64
control=/tmp/ozamx-production-final/ozamx_optimization_benchmark
root=/tmp/ozamx-roof-batch64

mkdir -p "$out"
exec 9>/tmp/ozamx-perf.lock
flock -x 9

run_one() {
  local label=$1 binary=$2
  taskset -c 0-63 env \
    OMP_NUM_THREADS=64 OMP_PROC_BIND=close OMP_PLACES=cores OMP_DYNAMIC=FALSE \
    OZAMX_WORKSPACE_CACHE_BYTES=2147483648 \
    "$binary" --sizes 1024,4096,8192 --precision fp64 --threads 64 --reps 5 --budgets 6,21 \
    --output "$out/${label}.csv"
}

# Keep these eight complete benchmark processes under one exclusive lock.
run_one run01_frozen_before "$control"
run_one run02_batch1 "$root/build-b1/ozamx_optimization_benchmark"
run_one run03_batch2 "$root/build-b2/ozamx_optimization_benchmark"
run_one run04_batch4 "$root/build-b4/ozamx_optimization_benchmark"
run_one run05_frozen_middle "$control"
run_one run06_batch4_repeat "$root/build-b4/ozamx_optimization_benchmark"
run_one run07_batch2_repeat "$root/build-b2/ozamx_optimization_benchmark"
run_one run08_frozen_after "$control"
