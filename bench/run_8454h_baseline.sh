#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
SIZES="256,1024,4096"
PRECISION="all"
THREADS="64"
REPS="5"
BUDGET=""
BUDGETS=""
OUTPUT_DIR=""
HARDWARE=0
CPUSET="${OZAMX_CPUSET:-0-63}"

usage() {
  cat << 'USAGE'
Usage: bench/run_8454h_baseline.sh [options]
  --sizes CSV       GEMM sizes (default 256,1024,4096)
  --precision P     all, fp32, or fp64 (default all)
  --threads N       GEMM OpenMP threads (default 64)
  --reps N          Recorded repetitions (default 5; each run has one warmup)
  --budget N        Restrict FP64 to one budget, or 0/all for default 6,21
  --budgets CSV     Explicit FP64 budget list, e.g. 6,10,15,21
  --output-dir DIR  New run directory (default: bench/8454h/runs/<UTC timestamp>)
  --hardware        Run only the independent CPU/AMX/memory microbenchmarks
Set OZAMX_CPUSET to override the default CPU affinity list (0-63).
USAGE
}
while (($#)); do
  case "$1" in
    --sizes)
      SIZES="$2"
      shift 2
      ;;
    --precision)
      PRECISION="$2"
      shift 2
      ;;
    --threads)
      THREADS="$2"
      shift 2
      ;;
    --reps)
      REPS="$2"
      shift 2
      ;;
    --budget)
      BUDGET="$2"
      shift 2
      ;;
    --budgets)
      BUDGETS="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --hardware)
      HARDWARE=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done
if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$SCRIPT_DIR/runs/$(date -u +%Y%m%dT%H%M%SZ)"
fi
mkdir -p "$OUTPUT_DIR"
if [[ -n "$(find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Output directory is not empty: $OUTPUT_DIR" >&2
  exit 2
fi

# Include compilation in the shared lock so it cannot perturb another run.
exec 9> /tmp/ozamx-perf.lock
flock -x 9
BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ozamx-8454h-build.XXXXXX")"
trap 'rm -rf "$BUILD_DIR"' EXIT
if ((HARDWARE)); then
  g++ -O3 -std=c++17 -march=sapphirerapids -fopenmp \
    "$ROOT/tools/platform_baseline.cpp" -o "$BUILD_DIR/platform_baseline"
else
  g++ -O3 -std=c++17 -mamx-tile -mamx-bf16 -fopenmp \
    -I"$SCRIPT_DIR/8454h/before/include" \
    "$SCRIPT_DIR/8454h/before/src/gemm.cpp" \
    "$SCRIPT_DIR/8454h/before/src/runtime.cpp" \
    "$ROOT/bench/optimization_benchmark.cpp" \
    -o "$BUILD_DIR/optimization_benchmark_before"
  cmake -S "$ROOT" -B "$BUILD_DIR/new" -DCMAKE_BUILD_TYPE=Release \
    -DOZAMX_ENABLE_OPENMP=ON -DOZAMX_BUILD_PROBE=OFF -DBUILD_TESTING=OFF
  cmake --build "$BUILD_DIR/new" --target ozamx_optimization_benchmark -j
fi

# Hold the shared performance lock across all runs in this script. CPU placement
# and OpenMP behavior match the baseline capture; the user can override CPUSET.
export OMP_NUM_THREADS="$THREADS" OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE
if ((HARDWARE)); then
  taskset -c "$CPUSET" "$BUILD_DIR/platform_baseline" --output "$OUTPUT_DIR/platform_baseline.csv"
else
  BENCH_ARGS=(--sizes "$SIZES" --precision "$PRECISION" --threads "$THREADS" --reps "$REPS")
  if [[ -n "$BUDGET" ]]; then BENCH_ARGS+=(--budget "$BUDGET"); fi
  if [[ -n "$BUDGETS" ]]; then BENCH_ARGS+=(--budgets "$BUDGETS"); fi
  taskset -c "$CPUSET" "$BUILD_DIR/optimization_benchmark_before" \
    "${BENCH_ARGS[@]}" --output "$OUTPUT_DIR/before.csv"
  taskset -c "$CPUSET" "$BUILD_DIR/new/ozamx_optimization_benchmark" \
    "${BENCH_ARGS[@]}" --output "$OUTPUT_DIR/current.csv"
fi
printf 'Results: %s\n' "$OUTPUT_DIR"
