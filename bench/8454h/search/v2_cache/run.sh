#!/usr/bin/env bash
set -euo pipefail
project=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$project"
binary=${1:-/tmp/ozamx-v2-candidate/build/ozamx_optimization_benchmark}
(
 flock 9
 export OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE
 for entry in 0:1073741824 1:2147483648 2:4294967296 3:2147483648 4:1073741824; do
  ordinal=${entry%%:*};cap=${entry#*:}
  export OZAMX_WORKSPACE_CACHE_BYTES=$cap
  taskset -c 0-63 "$binary" --sizes 8192 --precision all --budgets 6,10,15,21 --threads 64 --reps 7 --output "bench/8454h/search/v2_cache/pass${ordinal}_cap${cap}.csv"
 done
) 9>/tmp/ozamx-perf.lock
