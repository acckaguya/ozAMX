#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/../.." && pwd)
baseline_source=${OZAMX_BASELINE_SOURCE_DIR:-$repo/bench/8454h/before}
lock=${OZAMX_PERF_LOCK:-/tmp/ozamx-perf.lock}
cxx=${CXX:-c++}
work=$(mktemp -d /tmp/ozamx-equivalence.XXXXXX)
trap 'rm -rf "$work"' EXIT
build=${OZAMX_BUILD_DIR:-$work/optimized-build}

[[ -f "$baseline_source/include/ozamx/gemm.hpp" ]] || { echo "missing baseline header: $baseline_source/include/ozamx/gemm.hpp" >&2; exit 2; }
[[ -f "$baseline_source/src/gemm.cpp" && -f "$baseline_source/src/runtime.cpp" ]] || { echo "missing frozen baseline sources under $baseline_source" >&2; exit 2; }

if [[ ${OZAMX_PERF_LOCK_HELD:-0} != 1 ]]; then
  exec 9>"$lock"
  flock -x 9
fi

if [[ -n ${OZAMX_BASELINE_BINARY:-} ]]; then
  [[ -x $OZAMX_BASELINE_BINARY ]] || { echo "missing baseline executable: $OZAMX_BASELINE_BINARY" >&2; exit 2; }
  cp "$OZAMX_BASELINE_BINARY" "$work/before"
else
  "$cxx" -O3 -std=c++17 -mamx-tile -mamx-bf16 -fopenmp \
    -I"$baseline_source/include" \
    "$baseline_source/src/gemm.cpp" "$baseline_source/src/runtime.cpp" \
    "$repo/bench/8454h/equivalence_driver.cpp" -o "$work/before"
fi
cmake -S "$repo" -B "$build" -DCMAKE_BUILD_TYPE=Release \
  -DOZAMX_ENABLE_OPENMP=ON -DOZAMX_BUILD_PROBE=OFF -DBUILD_TESTING=OFF
if [[ -n ${OZAMX_CMAKE_DEFINITIONS:-} ]]; then
  read -r -a cmake_definitions <<<"$OZAMX_CMAKE_DEFINITIONS"
  cmake -S "$repo" -B "$build" "${cmake_definitions[@]}"
fi
cmake --build "$build" --target ozamx -j"${OZAMX_BUILD_JOBS:-2}"

flags=(-std=c++17 -O3 -march=sapphirerapids -ffp-contract=off -fopenmp)
"$cxx" "${flags[@]}" -I"$repo/include" "$repo/bench/8454h/equivalence_driver.cpp" \
  "$build/libozamx.a" -o "$work/after"
OMP_NUM_THREADS=1 "$work/before" > "$work/baseline-t1.jsonl"
OMP_NUM_THREADS=1 "$work/after" > "$work/optimized-t1.jsonl"
OMP_NUM_THREADS=4 "$work/after" > "$work/optimized-t4.jsonl"
OMP_NUM_THREADS=64 "$work/after" > "$work/optimized-t64.jsonl"
python3 - "$work" <<'PY'
import json, pathlib, sys
work=pathlib.Path(sys.argv[1])
files={
  "baseline_t1":work/"baseline-t1.jsonl",
  "optimized_t1":work/"optimized-t1.jsonl",
  "optimized_t4":work/"optimized-t4.jsonl",
  "optimized_t64":work/"optimized-t64.jsonl",
}
rows={name:[json.loads(line) for line in path.read_text().splitlines()] for name,path in files.items()}
base=rows["baseline_t1"]
identity=("type","m","n","k","ldc","budget")

def identity_of(row):
    return tuple(row.get(k) for k in identity)+(len(row.get("bits",[])),)

def compare(lhs_name, lhs, rhs_name, rhs):
    if len(lhs)!=len(rhs): raise SystemExit(f"{lhs_name}/{rhs_name}: case counts differ")
    slots=mismatches=padding_failures=0
    for i,(a,b) in enumerate(zip(lhs,rhs)):
        if identity_of(a)!=identity_of(b): raise SystemExit(f"{lhs_name}/{rhs_name}: case identity differs at {i}")
        if len(a["bits"])!=len(b["bits"]) or len(a["bits"])!=a["m"]*a["ldc"]:
            raise SystemExit(f"{lhs_name}/{rhs_name}: output length differs at {i}")
        slots+=len(a["bits"])
        padding_failures+=int(not a["padding_ok"])+int(not b["padding_ok"])
        mismatches+=sum(x!=y for x,y in zip(a["bits"],b["bits"]))
    result={"cases":len(lhs),"compared_c_slots_including_padding":slots,"bitwise_mismatches_including_signed_zero":mismatches,"padding_guard_failures":padding_failures}
    if mismatches or padding_failures: raise SystemExit(f"{lhs_name} vs {rhs_name}: {result}")
    return result

summary={}
for name in ("optimized_t1","optimized_t4","optimized_t64"):
    summary[f"baseline_t1_vs_{name}"]=compare("baseline_t1",base,name,rows[name])
for a,b in (("optimized_t1","optimized_t4"),("optimized_t1","optimized_t64"),("optimized_t4","optimized_t64")):
    summary[f"{a}_vs_{b}"]=compare(a,rows[a],b,rows[b])
print(json.dumps(summary,sort_keys=True,separators=(",",":")))
PY
