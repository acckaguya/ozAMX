#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../.." && pwd)
out="$root/bench/8454h/roofline_v4/calibration_20261014"
cd "$root"
exec 9>/tmp/ozamx-perf.lock
flock 9
c++ -O3 -std=c++17 -march=sapphirerapids -ffp-contract=off -fopenmp \
  "$out/source/roofline_kernels.cpp" "$out/source/roofline_tileloads.S" \
  "$out/source/libozamx.a" -o "$out/bin/roofline_kernels"
objdump -d -Mintel "$out/bin/roofline_kernels" > "$out/bin/roofline_kernels.disassembly.txt"
env OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE \
  taskset -c 0-63 "$out/bin/roofline_kernels" "$out/raw/kernels.csv"
