#!/usr/bin/env bash
set -euo pipefail
project=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$project"
binary=${1:-/tmp/ozamx-search-default/ozamx_optimization_benchmark}
(
 flock 9
 export OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE OZAMX_WORKSPACE_CACHE_BYTES=1073741824
 for threads in 64 32 16 32 64; do
  ordinal=${ordinal:-0}
  export OMP_NUM_THREADS=$threads
  taskset -c 0-63 "$binary" --sizes 1024,4096 --precision all --budgets 6,21 --threads "$threads" --reps 5 --output "bench/8454h/search/thread_sweep/pass${ordinal}_t${threads}.csv"
  ordinal=$((ordinal+1))
 done
) 9>/tmp/ozamx-perf.lock
