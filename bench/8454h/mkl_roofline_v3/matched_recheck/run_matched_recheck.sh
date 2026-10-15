#!/usr/bin/env bash
set -euo pipefail

repo=/home/caiweili/ozAMX
base="$repo/bench/8454h/mkl_roofline_v3/matched_recheck"
v2=/tmp/ozamx-production-final/libozamx.a
v2_sha=ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251
v3=/tmp/ozamx-roofline-production/libozamx.a
v3_sha=73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c

[[ "$(sha256sum "$v2" | awk '{print $1}')" == "$v2_sha" ]] || { echo "frozen V2 library SHA mismatch" >&2; exit 2; }
[[ "$(sha256sum "$v3" | awk '{print $1}')" == "$v3_sha" ]] || { echo "roofline V3 library SHA mismatch" >&2; exit 2; }
for d in p1_v2a p2_v3a p3_v2b p4_v3b p5_v2c; do
  [[ ! -e "$base/$d/full.csv" ]] || { echo "refusing to overwrite $base/$d/full.csv" >&2; exit 2; }
done

flock -x /tmp/ozamx-perf.lock bash -c '
  set -euo pipefail
  repo=$1; base=$2; v2=$3; v2_sha=$4; v3=$5; v3_sha=$6
  run_one() {
    local name=$1 variant=$2 source_id=$3 lib=$4 expected=$5
    local d="$base/$name"
    local current
    current=$(sha256sum "$lib" | awk "{print \$1}")
    [[ "$current" == "$expected" ]] || { echo "library changed before $name" >&2; exit 2; }
    g++ -O3 -std=c++17 -Wall -Wextra -Wpedantic -mamx-tile -mamx-bf16 -fopenmp \
      -I"$repo/include" -I"$repo/third_party/code/mkl-current/include" \
      "$d/benchmark_matched_recheck.cpp" "$lib" \
      -L"$repo/third_party/code/mkl-current/lib" \
      -Wl,-rpath,"$repo/third_party/code/mkl-current/lib" \
      -Wl,--no-as-needed -l:libmkl_rt.so.3 -ldl \
      -o "$d/ozamx_benchmark" >"$d/build.log" 2>&1
    [[ "$(sha256sum "$lib" | awk "{print \$1}")" == "$expected" ]] || { echo "library changed after $name build" >&2; exit 2; }
    LD_LIBRARY_PATH="$repo/third_party/code/mkl-current/lib" \
    OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE \
    MKL_NUM_THREADS=64 MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU MKL_INTERFACE_LAYER=LP64 \
    OZAMX_WORKSPACE_CACHE_BYTES=2147483648 taskset -c 0-63 \
      "$d/ozamx_benchmark" \
      --sizes 1024,2048,8192 --threads 64 --reps 7 --precision all \
      --budgets 6,10,15,21 --seed 260904 --distribution uniform \
      --checkpoint "$d/checkpoint_$name" --output "$d/full.csv" \
      >"$d/run.log" 2>&1
    [[ "$(sha256sum "$lib" | awk "{print \$1}")" == "$expected" ]] || { echo "library changed after $name run" >&2; exit 2; }
    python3 "$base/write_provenance.py" "$name" "$variant" "$source_id" "$lib" "$expected" "$repo"
  }
  run_one p1_v2a V2 mkl-wall-matched-recheck-p1-v2a-20261013 "$v2" "$v2_sha"
  run_one p2_v3a V3 mkl-wall-matched-recheck-p2-v3a-20261013 "$v3" "$v3_sha"
  run_one p3_v2b V2 mkl-wall-matched-recheck-p3-v2b-20261013 "$v2" "$v2_sha"
  run_one p4_v3b V3 mkl-wall-matched-recheck-p4-v3b-20261013 "$v3" "$v3_sha"
  run_one p5_v2c V2 mkl-wall-matched-recheck-p5-v2c-20261013 "$v2" "$v2_sha"
' _ "$repo" "$base" "$v2" "$v2_sha" "$v3" "$v3_sha"
