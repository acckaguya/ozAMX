#!/usr/bin/env bash
set -euo pipefail
project=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$project"
build=/tmp/ozamx-roof-kernels
mkdir -p "$build" bench/8454h/roofline/calibration
(
 flock 9
 c++ -O3 -std=c++17 -march=sapphirerapids -ffp-contract=off -fopenmp tools/roofline_kernels.cpp tools/roofline_tileloads.S /tmp/ozamx-production-final/libozamx.a -o "$build/roofline_kernels"
 objdump -d -Mintel "$build/roofline_kernels" > bench/8454h/roofline/calibration/kernel_disassembly.txt
 env OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE taskset -c 0-63 "$build/roofline_kernels" bench/8454h/roofline/calibration/kernels.csv
) 9>/tmp/ozamx-perf.lock
