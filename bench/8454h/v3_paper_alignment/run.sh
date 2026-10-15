#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
CAMPAIGN="$ROOT/bench/8454h/v3_paper_alignment"
BUILD="$CAMPAIGN/build"
RESULTS="$CAMPAIGN/results"
CHECKPOINTS="$CAMPAIGN/checkpoints"
LOGS="$CAMPAIGN/logs"
SOURCE_ID=v3-paper-alignment-20261014
CPUSET=0-63
mkdir -p "$BUILD" "$RESULTS" "$CHECKPOINTS" "$LOGS"
exec 9>/tmp/ozamx-perf.lock
flock -x 9

export OMP_NUM_THREADS=64 OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close
export MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU
export OZAMX_WORKSPACE_CACHE_BYTES=2147483648
export LD_LIBRARY_PATH="$ROOT/third_party/code/mkl-current/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

printf 'source_id=%s\narchive_sha256=%s\n' "$SOURCE_ID" "$(sha256sum /tmp/ozamx-roofline-production/libozamx.a | awk '{print $1}')" > "$CAMPAIGN/provenance.txt"
printf 'mkl_rt_sha256=%s\n' "$(sha256sum "$ROOT/third_party/code/mkl-current/lib/libmkl_rt.so.3" | awk '{print $1}')" >> "$CAMPAIGN/provenance.txt"
printf 'main_source_sha256=%s\nraw_source_sha256=%s\n' "$(sha256sum "$CAMPAIGN/source/benchmark.cpp" | awk '{print $1}')" "$(sha256sum "$CAMPAIGN/source/raw_bf16.cpp" | awk '{print $1}')" >> "$CAMPAIGN/provenance.txt"
printf 'compile_main=g++ -O3 -march=native -std=c++17 -fopenmp [root include] [oneMKL 2026.1 include] benchmark snapshot frozen libozamx.a libmkl_rt.so.3 -ldl\ncompile_raw=g++ -O3 -march=native -std=c++17 -fopenmp [oneMKL 2026.1 include] raw snapshot libmkl_rt.so.3 -ldl\n' >> "$CAMPAIGN/provenance.txt"
printf 'protocol=uniform[-1,1], base_seed=260904 (paper does not specify RNG/seed), warmup=1, timed_repetitions=10, report=arithmetic_mean_and_population_sd_no_outlier_removal\n' >> "$CAMPAIGN/provenance.txt"
printf 'platform_difference=Intel Xeon Platinum 8454H Ubuntu; GCC 11.4 GNU OpenMP; oneMKL 2026.1 GNU threading; paper uses 8462Y+ Rocky Linux 9.3 Intel compiler/OpenMP\n' >> "$CAMPAIGN/provenance.txt"

if [[ ! -x "$BUILD/ozamx_benchmark" ]]; then
  g++ -O3 -march=native -std=c++17 -fopenmp \
    -I"$ROOT/include" -I"$ROOT/third_party/code/mkl-current/include" \
    "$CAMPAIGN/source/benchmark.cpp" /tmp/ozamx-roofline-production/libozamx.a \
    "$ROOT/third_party/code/mkl-current/lib/libmkl_rt.so.3" -ldl \
    -Wl,-rpath,"$ROOT/third_party/code/mkl-current/lib" \
    -o "$BUILD/ozamx_benchmark" || exit $?
fi
if [[ ! -x "$BUILD/raw_bf16" ]]; then
  g++ -O3 -march=native -std=c++17 -fopenmp \
    -I"$ROOT/third_party/code/mkl-current/include" \
    "$CAMPAIGN/source/raw_bf16.cpp" \
    "$ROOT/third_party/code/mkl-current/lib/libmkl_rt.so.3" -ldl \
    -Wl,-rpath,"$ROOT/third_party/code/mkl-current/lib" \
    -o "$BUILD/raw_bf16" || exit $?
fi

STATUS="$CAMPAIGN/config_status.csv"
if [[ ! -e "$STATUS" ]]; then echo 'config,start_utc,end_utc,rc,result,checkpoint' > "$STATUS"; fi
config_complete() {
  local kind="$1" key="$2" out="$3" cp="$4" cpfile n prec budget
  if [[ "$kind" == raw ]]; then
    cpfile="$cp"
  else
    if [[ "$key" == *fp32* ]]; then prec=fp32; budget=6
    else prec=fp64; budget="${key#*fp64p}"; budget="${budget%%_n*}"; fi
    if [[ "$key" == scaling_* ]]; then n="${key#*_n}"; n="${n%%_t*}"; else n="${key##*_n}"; fi
    cpfile="${cp}.${prec}.${n}.${budget}.json"
  fi
  python3 - "$SOURCE_ID" "$cpfile" "$out" <<'PYCFG'
import csv, json, pathlib, sys
source, cpname, result = sys.argv[1:]
try:
 d=json.load(open(cpname))
 rows=list(csv.DictReader(open(result,newline='')))
 if d.get('source_id') != source or d.get('complete') is not True or d.get('completed_timed_repetitions') != 10 or d.get('requested_repetitions') != 10: raise SystemExit(1)
 if len(rows) != 1 or rows[0].get('status') != 'ok' or int(rows[0].get('repetitions',0)) != 10: raise SystemExit(1)
 if 'raw_seconds' in d and len(d['raw_seconds']) != 10: raise SystemExit(1)
 if 'total_seconds' in d and len(d['total_seconds']) != 10: raise SystemExit(1)
except (OSError, ValueError, KeyError, TypeError):
 raise SystemExit(1)
PYCFG
}
run_cfg() {
  local kind="$1" key="$2" out="$3" cp="$4"; shift 4
  local start end rc cmdfile
  if config_complete "$kind" "$key" "$out" "$cp"; then echo "SKIP $key checkpoint+result complete" | tee -a "$CAMPAIGN/runner.log"; return 0; fi
  start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cmdfile="$LOGS/${key}.command.txt"
  if [[ "$kind" == main ]]; then printf 'taskset -c %q %q ' "$CPUSET" "$BUILD/ozamx_benchmark" > "$cmdfile"; else printf 'taskset -c %q %q ' "$CPUSET" "$BUILD/raw_bf16" > "$cmdfile"; fi
  printf '%q ' "$@" --output "$out" --checkpoint "$cp" --resume >> "$cmdfile"; printf '\n' >> "$cmdfile"
  echo "START $key $start" | tee -a "$CAMPAIGN/runner.log"
  if [[ "$kind" == main ]]; then
    taskset -c "$CPUSET" "$BUILD/ozamx_benchmark" "$@" --output "$out" --checkpoint "$cp" --resume > "$LOGS/${key}.stdout.log" 2> "$LOGS/${key}.stderr.log"
    rc=$?
  else
    taskset -c "$CPUSET" "$BUILD/raw_bf16" "$@" --output "$out" --checkpoint "$cp" --resume > "$LOGS/${key}.stdout.log" 2> "$LOGS/${key}.stderr.log"
    rc=$?
  fi
  end="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '"%s",%s,%s,%s,"%s","%s"\n' "$key" "$start" "$end" "$rc" "$out" "$cp" >> "$STATUS"
  echo "END $key $end rc=$rc" | tee -a "$CAMPAIGN/runner.log"
  return "$rc"
}

SIZES=(256 512 1024 2048 4096 8192 16384 32768)
BUDGETS=(6 10 15 21)
# Paper main table: all FP32 and FP64 budgets, ascending N.
for n in "${SIZES[@]}"; do
  key="main_fp32_n${n}"
  run_cfg main "$key" "$RESULTS/${key}.csv" "$CHECKPOINTS/${key}" --sizes "$n" --threads 64 --reps 10 --seed 260904 --precision fp32 --distribution uniform || exit $?
  for b in "${BUDGETS[@]}"; do
    key="main_fp64p${b}_n${n}"
    run_cfg main "$key" "$RESULTS/${key}.csv" "$CHECKPOINTS/${key}" --sizes "$n" --threads 64 --reps 10 --seed 260904 --precision fp64 --budgets "$b" --distribution uniform || exit $?
  done
done
# FP32 thread scaling: ascending N then thread count.
for n in 1024 4096 16384; do
  for t in 2 4 8 16 32 64; do
    key="scaling_fp32_n${n}_t${t}"
    run_cfg main "$key" "$RESULTS/${key}.csv" "$CHECKPOINTS/${key}" --sizes "$n" --threads "$t" --reps 10 --seed 260904 --precision fp32 --distribution uniform || exit $?
  done
done
# oneMKL raw BF16-BF16-FP32 headroom (separate from the emulation algorithm).
for n in "${SIZES[@]}"; do
  key="raw_bf16_n${n}"
  run_cfg raw "$key" "$RESULTS/${key}.csv" "$CHECKPOINTS/${key}.json" --sizes "$n" --threads 64 --reps 10 --seed 260904 || exit $?
done

echo "CAMPAIGN COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$CAMPAIGN/runner.log"
