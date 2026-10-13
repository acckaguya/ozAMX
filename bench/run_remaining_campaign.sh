#!/usr/bin/env bash
set -euo pipefail
cd /data/home/caiwl/ozAMX

export LD_LIBRARY_PATH="$PWD/third_party/code/mkl-2026/venv/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=64 OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close
export MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU
BENCH=${OZAMX_BENCH:-build/ozamx_benchmark}
LOGDIR=bench/campaign_logs
mkdir -p "$LOGDIR"
exec 9>bench/campaign.lock
if ! flock -n 9; then
  echo "$(date -u +%FT%TZ) REFUSED: another campaign owns bench/campaign.lock" | tee -a "$LOGDIR/runner.log" >&2
  exit 73
fi
echo "$(date -u +%FT%TZ) LOCK_ACQUIRED pid=$$ lock=bench/campaign.lock" | tee -a "$LOGDIR/runner.log"

run_cfg() {
  local tag="$1"; shift
  local output="bench/${tag}.csv"
  local checkpoint="bench/${tag}_progress"
  local log="$LOGDIR/${tag}.log"
  local precision="" size="" budget=""
  local previous=""
  for arg in "$@"; do
    case "$previous:$arg" in
      --precision:*) precision="$arg" ;;
      --sizes:*) size="$arg" ;;
      --budgets:*) budget="$arg" ;;
    esac
    case "$arg" in --precision|--sizes|--budgets) previous="$arg" ;; *) previous="" ;; esac
  done
  local completed_checkpoint="${checkpoint}.${precision}.${size}.${budget}.json"
  if [[ "$precision" == fp32 ]]; then
    budget=6
    completed_checkpoint="${checkpoint}.${precision}.${size}.${budget}.json"
  fi
  if [[ -s "$output" && -f "$completed_checkpoint" ]] && \
     python3 -c 'import json,sys; raise SystemExit(0 if json.load(open(sys.argv[1])).get("complete") is True else 1)' "$completed_checkpoint"; then
    echo "$(date -u +%FT%TZ) SKIP_COMPLETE $tag" | tee -a "$LOGDIR/runner.log"
    return 0
  fi
  echo "$(date -u +%FT%TZ) START $tag $*" | tee -a "$LOGDIR/runner.log"
  timeout --signal=TERM --kill-after=60 4h taskset -c 0-63 "$BENCH" "$@" \
    --output "$output" --checkpoint "$checkpoint" --resume > /dev/null 2> "$log"
  echo "$(date -u +%FT%TZ) DONE $tag" | tee -a "$LOGDIR/runner.log"
}

# Rerun all 32768 FP64 budgets under clean prefixes. The earlier p6 checkpoint is
# retained as a potentially contaminated diagnostic after an accidental overlap.
for budget in 6 10 15 21; do
  run_cfg "full_sweep_32768_fp64_clean_p${budget}" \
    --sizes 32768 --threads 64 --reps 10 --precision fp64 --budgets "$budget" \
    --distribution uniform --seed 260904
done

# FP32 thread scaling: 1 warmup + 10 timed repetitions per (N, thread count).
for n in 1024 4096 16384; do
  for threads in 2 4 8 16 32 64; do
    export OMP_NUM_THREADS="$threads"
    run_cfg "thread_scaling_fp32_n${n}_t${threads}" \
      --sizes "$n" --threads "$threads" --reps 10 --precision fp32 \
      --distribution uniform --seed 260904
  done
done

# Raw oneMKL BF16 headroom run; persist one complete row per size so a stopped
# campaign can resume without overwriting finished sizes or repeating them.
export OMP_NUM_THREADS=64
for n in 256 512 1024 2048 4096 8192 16384 32768; do
  raw_csv="bench/raw_bf16_n${n}.csv"
  if [[ -s "$raw_csv" ]] && python3 -c 'import csv,sys; rows=list(csv.DictReader(open(sys.argv[1]))); raise SystemExit(0 if len(rows)==1 and rows[0].get("status")=="ok" else 1)' "$raw_csv"; then
    echo "$(date -u +%FT%TZ) SKIP_COMPLETE raw_bf16_n${n}" | tee -a "$LOGDIR/runner.log"
    continue
  fi
  echo "$(date -u +%FT%TZ) START raw_bf16_n${n}" | tee -a "$LOGDIR/runner.log"
  timeout --signal=TERM --kill-after=60 4h bench/run_raw_bf16.sh \
    --sizes "$n" --threads 64 --reps 10 --seed 260904 \
    --output "$raw_csv" \
    > /dev/null 2> "$LOGDIR/raw_bf16_n${n}.log"
  echo "$(date -u +%FT%TZ) DONE raw_bf16_n${n}" | tee -a "$LOGDIR/runner.log"
done
python3 - <<'PY'
import csv
from pathlib import Path

root = Path("bench")
parts = [root / f"raw_bf16_n{n}.csv" for n in (256, 512, 1024, 2048, 4096, 8192, 16384, 32768)]
rows = []
header = None
for path in parts:
    with path.open(newline="") as stream:
        reader = csv.reader(stream)
        part_header = next(reader)
        row = next(reader)
        if next(reader, None) is not None:
            raise SystemExit(f"unexpected extra row in {path}")
    if header is None:
        header = part_header
    elif part_header != header:
        raise SystemExit(f"header mismatch in {path}")
    rows.append(row)
tmp = root / "raw_bf16.csv.tmp"
with tmp.open("w", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
tmp.replace(root / "raw_bf16.csv")
PY
echo "$(date -u +%FT%TZ) DONE raw_bf16" | tee -a "$LOGDIR/runner.log"
