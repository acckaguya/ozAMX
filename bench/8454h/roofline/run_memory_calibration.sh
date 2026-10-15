#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT_DIR="$ROOT/bench/8454h/roofline"
BUILD_DIR=/tmp/ozamx-roof-memory
BIN="$BUILD_DIR/roofline_memory"
DATE_TAG=$(date -u +%Y%m%d)
CSV="$OUT_DIR/memory_calibration_${DATE_TAG}.csv"
METADATA="$OUT_DIR/memory_calibration_${DATE_TAG}.json"
DISASM="$OUT_DIR/memory_calibration_${DATE_TAG}.disasm.txt"
mkdir -p "$OUT_DIR" "$BUILD_DIR"

exec 9>/tmp/ozamx-perf.lock
flock -x 9

COMPILE=(g++ -O3 -std=c++17 -Wall -Wextra -Wpedantic -march=sapphirerapids -ffp-contract=off -fopenmp "$ROOT/tools/roofline_memory.cpp" -o "$BIN")
"${COMPILE[@]}"

objdump -d -C "$BIN" > "$BUILD_DIR/roofline_memory.objdump"
python3 - "$BUILD_DIR/roofline_memory.objdump" "$DISASM" <<'PY'
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
lines = text.splitlines()
start = next((i for i, line in enumerate(lines) if 'triad_pass(double*' in line and line.rstrip().endswith('>:')), None)
if start is None:
    raise SystemExit('could not find triad_pass in disassembly')
body = [lines[start]]
for line in lines[start + 1:]:
    if re.match(r'^[0-9a-f]+ <.*>:$', line.strip()):
        break
    body.append(line)
assembly = '\n'.join(body) + '\n'
Path(sys.argv[2]).write_text(assembly)
fmas = re.findall(r'\bvfmadd\w*pd\b', assembly)
loads_stores = re.findall(r'\bvmovapd\b', assembly)
fma_lines = [line for line in body if re.search(r'\bvfmadd\w*pd\b', line)]
explicit_loads = [line for line in body if re.search(r'\bvmovapd\s+\([^)]*\),\s*%zmm', line)]
explicit_stores = [line for line in body if re.search(r'\bvmovapd\s+%zmm[^,]*,\s*\(', line)]
fma_memory_loads = [line for line in fma_lines if '(' in line]
if len(fmas) != 1 or len(loads_stores) != 2 or len(explicit_loads) != 1 or len(explicit_stores) != 1 or len(fma_memory_loads) != 1:
    raise SystemExit(f'unexpected triad assembly: FMA={len(fmas)}, vmovapd={len(loads_stores)}, explicit loads={len(explicit_loads)}, stores={len(explicit_stores)}, FMA memory loads={len(fma_memory_loads)}')
print(f'triad_disassembly: packed_double_fma={len(fmas)} explicit_vector_loads={len(explicit_loads)} fma_memory_source_loads={len(fma_memory_loads)} vector_stores={len(explicit_stores)}')
print('one vector loop performs 2 x 64B loads (one explicit vmovapd and one FMA memory source) + 1 x 64B store, with 8 x 2 FP64 ops; counted as 24 logical bytes and 2 ops per element.')
PY

OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE \
  taskset -c 0-63 "$BIN" "$CSV"

python3 - "$ROOT" "$BIN" "$CSV" "$METADATA" "${COMPILE[*]}" "$DISASM" <<'PY'
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1])
binary = Path(sys.argv[2])
csv = Path(sys.argv[3])
metadata = Path(sys.argv[4])
compile_command = sys.argv[5]
disassembly = Path(sys.argv[6])
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

lscpu = subprocess.run(["lscpu"], check=True, capture_output=True, text=True).stdout
payload = {
    "schema": "ozamx-roofline-memory-calibration-v1",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "host": platform.node(),
    "platform": platform.platform(),
    "lscpu": lscpu,
    "compiler": subprocess.run(["g++", "--version"], check=True, capture_output=True, text=True).stdout.splitlines()[0],
    "compile_command": compile_command,
    "source": str(root / "tools/roofline_memory.cpp"),
    "source_sha256": sha(root / "tools/roofline_memory.cpp"),
    "runner": str(root / "bench/8454h/roofline/run_memory_calibration.sh"),
    "runner_sha256": sha(root / "bench/8454h/roofline/run_memory_calibration.sh"),
    "binary": str(binary),
    "binary_sha256": sha(binary),
    "raw_csv": str(csv),
    "raw_csv_sha256": sha(csv),
    "disassembly": str(disassembly),
    "disassembly_sha256": sha(disassembly),
    "disassembly_check": "one packed-double FMA, one explicit vmovapd load, one FMA memory-source load, and one vmovapd store found in triad_pass; 2 loads and 1 store per 8 FP64 elements",
    "binding": {
        "taskset_cpu_list": "0-63",
        "omp_num_threads": [1, 32, 64],
        "omp_places": "cores",
        "omp_proc_bind": "close",
        "omp_dynamic": "FALSE",
        "lock": "flock -x /tmp/ozamx-perf.lock held for build, disassembly inspection, and complete run",
    },
    "protocol": {
        "timed_repetitions": 5,
        "warmup_repetitions": 1,
        "calibration_target_minimum_seconds": 0.15,
        "batch_passes": "power-of-two calibrated per thread-count/footprint, then fixed across warmup and five timed repetitions",
        "timing": "each OpenMP worker times the synchronized batch; CSV records maximum worker elapsed time",
        "checksum": "complete output-array sum after each timed batch, outside the timed OpenMP region",
        "triad": "a[i] = b[i] + 0.5*c[i], FP64; 2 logical ops and 24 logical bytes per element",
        "bandwidth_semantics": "logical traffic rate; hardware cache misses and physical DRAM traffic are not measured",
    },
    "footprint_hypotheses": [
        {"label": "L1_footprint", "arrays_per_worker": 3, "bytes_per_array": 8192, "bytes_per_worker": 24576},
        {"label": "L2_footprint", "arrays_per_worker": 3, "bytes_per_array": 262144, "bytes_per_worker": 786432},
        {"label": "LLC_candidate", "arrays_per_worker": 3, "bytes_per_array": 786432, "bytes_per_worker": 2359296, "bytes_total_at_64_workers": 150994944, "caveat": "candidate footprint only; not a guarantee of LLC residency"},
        {"label": "DRAM_footprint", "arrays_per_worker": 3, "bytes_per_array": 8388608, "bytes_per_worker": 25165824, "bytes_total_at_64_workers": 1610612736},
    ],
    "allocation": "three independent 64-byte-aligned allocations per worker; each worker first-touches its own arrays via an OpenMP static, one-worker-per-partition schedule",
    "analysis": "L1/L2/LLC labels are footprint hypotheses, not measured cache-bandwidth classes. Rates are logical bytes/s and logical GFLOP/s, not hardware-counter traffic.",
}
metadata.write_text(json.dumps(payload, indent=2) + "\n")
print(f"csv={csv}")
print(f"metadata={metadata}")
print(f"disassembly={disassembly}")
PY
