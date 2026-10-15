#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 /absolute/path/libozamx.a <expected-library-sha256>" >&2
  exit 2
fi
lib_path=$(realpath "$1")
expected_sha=$2
[[ -f "$lib_path" ]] || { echo "library not found: $lib_path" >&2; exit 2; }
actual_sha=$(sha256sum "$lib_path" | awk '{print $1}')
[[ "$actual_sha" == "$expected_sha" ]] || { echo "library SHA-256 mismatch: $actual_sha" >&2; exit 2; }

repo=/home/caiweili/ozAMX
out="$repo/bench/8454h/mkl_roofline_v3"
mkdir -p "$out"
flock -x /tmp/ozamx-perf.lock bash -c '
  set -euo pipefail
  repo=$1; out=$2; lib_path=$3; expected_sha=$4
  actual_sha=$(sha256sum "$lib_path" | awk "{print \$1}")
  [[ "$actual_sha" == "$expected_sha" ]] || { echo "library SHA-256 changed before build" >&2; exit 2; }
  g++ -O3 -std=c++17 -Wall -Wextra -Wpedantic -mamx-tile -mamx-bf16 -fopenmp \
    -I"$repo/include" -I"$repo/third_party/code/mkl-current/include" \
    "$out/benchmark_roofline_v3.cpp" "$lib_path" \
    -L"$repo/third_party/code/mkl-current/lib" \
    -Wl,-rpath,"$repo/third_party/code/mkl-current/lib" \
    -Wl,--no-as-needed -l:libmkl_rt.so.3 -ldl \
    -o "$out/ozamx_benchmark"
  LD_LIBRARY_PATH="$repo/third_party/code/mkl-current/lib" \
  OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE \
  MKL_NUM_THREADS=64 MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU MKL_INTERFACE_LAYER=LP64 \
  OZAMX_WORKSPACE_CACHE_BYTES=2147483648 taskset -c 0-63 \
    "$out/ozamx_benchmark" \
    --sizes 256,1024,4096,8192 --threads 64 --reps 5 --precision all \
    --budgets 6,10,15,21 --seed 260904 --distribution uniform \
    --checkpoint "$out/checkpoint_roofline_v3" \
    --output "$out/full_roofline_v3.csv"
' _ "$repo" "$out" "$lib_path" "$expected_sha"
