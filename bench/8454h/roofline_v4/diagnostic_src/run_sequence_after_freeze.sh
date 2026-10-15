#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$ROOT/../../../../" && pwd)"
RESULTS="${OZV4_RESULT_ROOT:-$ROOT/results}/$(date -u +%Y%m%dT%H%M%SZ)-$$"
V3_LIB="$REPO/bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
V3_SHA="73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
FREEZE_MARKER="${OZV4_FREEZE_MARKER:-$REPO/bench/8454h/v3_paper_alignment/FROZEN_COMPLETE}"
SIZES="${OZV4_SIZES:-1024,4096,8192}"

if [[ ! -f "$FREEZE_MARKER" ]]; then
  echo "Refusing to run V4 sequence: V3 paper campaign freeze marker missing: $FREEZE_MARKER" >&2
  exit 2
fi
actual_v3_sha="$(sha256sum "$V3_LIB" | awk '{print $1}')"
[[ "$actual_v3_sha" == "$V3_SHA" ]] || { echo "Immutable V3 library SHA mismatch: $actual_v3_sha" >&2; exit 2; }
mkdir -p "$RESULTS"
sha256sum "$ROOT/src/gemm.cpp" "$ROOT/bench/benchmark.cpp" \
  "$ROOT/CMakeLists.txt" "$ROOT/tools/run_binary_gate_v4.py" \
  "$FREEZE_MARKER" "$V3_LIB" > "$RESULTS/initial_source_and_freeze.sha256"
exec 9>/tmp/ozamx-perf.lock
flock -x 9

export OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE
export MKL_NUM_THREADS=64 MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU MKL_INTERFACE_LAYER=LP64
export OZAMX_WORKSPACE_CACHE_BYTES=2147483648
export LD_LIBRARY_PATH="$REPO/third_party/code/mkl-current/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

run_one() {
  local label="$1" lib="$2" bin="$3"
  local out="$RESULTS/${label}.csv" checkpoint="$RESULTS/checkpoint_${label}"
  taskset -c 0-63 "$bin" --sizes "$SIZES" --threads 64 --reps 5 --precision all \
    --budgets 6,10,15,21 --seed 260904 --distribution uniform \
    --checkpoint "$checkpoint" --output "$out"
  sha256sum "$out" "$bin" "$lib" > "$RESULTS/${label}.sha256"
}

build_v3_driver() {
  local build="$ROOT/build/frozen_v3_control"
  mkdir -p "$build"
  g++ -O3 -std=c++17 -Wall -Wextra -Wpedantic -mamx-tile -mamx-bf16 -fopenmp \
    -I"$ROOT/include" -I"$REPO/third_party/code/mkl-current/include" \
    "$ROOT/bench/benchmark.cpp" "$V3_LIB" \
    -L"$REPO/third_party/code/mkl-current/lib" \
    -Wl,-rpath,"$REPO/third_party/code/mkl-current/lib" \
    -Wl,--no-as-needed -l:libmkl_rt.so.3 -ldl \
    -o "$build/ozamx_benchmark"
}

build_v3_driver
v3_bin="$ROOT/build/frozen_v3_control/ozamx_benchmark"
run_one frozen_v3_initial "$V3_LIB" "$v3_bin"

for mode in 0 1 2 3; do
  build="$ROOT/build/mode${mode}"
  cmake -S "$ROOT" -B "$build" -DCMAKE_BUILD_TYPE=Release \
    -DOZAMX_ENABLE_OPENMP=ON -DOZV4_MODE="$mode"
  cmake --build "$build" -j2
  if [[ "$mode" == 0 || "$mode" == 3 ]]; then
    ctest --test-dir "$build" --output-on-failure | tee "$RESULTS/ctest_mode${mode}.log"
    gate="$RESULTS/binary_gate_mode${mode}.json"
    python3 "$ROOT/tools/run_binary_gate_v4.py" \
      --candidate-library "$build/libozamx.a" --output "$gate" --lock-held
    python3 - "$gate" <<'PY'
import json,sys
with open(sys.argv[1],encoding="utf-8") as f: result=json.load(f)
if result.get("status")!="pass": raise SystemExit("binary comparison gate did not pass")
PY
  fi
  case "$mode" in
    0) label=mode0_control ;;
    1) label=mode1_diagnostic_plain_nf ;;
    2) label=mode2_diagnostic_no_reconstruction ;;
    3) label=mode3_candidate_late32_unvalidated ;;
  esac
  run_one "$label" "$build/libozamx.a" "$build/ozamx_benchmark"
done

run_one frozen_v3_final "$V3_LIB" "$v3_bin"
sha256sum "$ROOT/src/gemm.cpp" "$ROOT/bench/benchmark.cpp" \
  "$ROOT/CMakeLists.txt" "$ROOT/README.md" "$ROOT/tools/roofline_binary_gate_v4.cpp" \
  "$ROOT/tools/run_binary_gate_v4.py" \
  "$FREEZE_MARKER" "$V3_LIB" > "$RESULTS/source_and_freeze.sha256"
