#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/../../../.." && pwd)
out=${OZAMX_NUMA_SEARCH_OUT:-$root/bench/8454h/roofline/search_numa_b}
clone=${OZAMX_NUMA_CLONE:-/tmp/ozamx-roof-numa-b}
frozen=${OZAMX_FROZEN_V2_BINARY:-/tmp/ozamx-production-final/ozamx_optimization_benchmark}
lock=${OZAMX_PERF_LOCK:-/tmp/ozamx-perf.lock}
cache_bytes=${OZAMX_WORKSPACE_CACHE_BYTES:-4294967296}
cache_tag=4g
if [[ $cache_bytes == 2147483648 ]]; then cache_tag=2g; fi
sizes=4096,8192
budgets=6,21
threads=64
reps=5
mkdir -p "$out/artifacts" "$out/raw" "$out/logs"
exec 9>"$lock"
flock -x 9

cxx=${CXX:-g++}
flags=(-std=c++17 -O3 -march=sapphirerapids -ffp-contract=off -fopenmp)
"$cxx" "${flags[@]}" -I"$clone/include" "$clone/bench/optimization_benchmark.cpp" "$clone/build0/libozamx.a" -o "$out/artifacts/optimization_benchmark_control"
"$cxx" "${flags[@]}" -I"$clone/include" "$clone/bench/optimization_benchmark.cpp" "$clone/build/libozamx.a" -o "$out/artifacts/optimization_benchmark_numa1"
[[ -x "$frozen" ]] || { echo "missing frozen V2 benchmark: $frozen" >&2; exit 2; }

cp "$frozen" "$out/artifacts/optimization_benchmark_frozen_v2"
cp "$clone/build0/libozamx.a" "$out/artifacts/libozamx_control0.a"
cp "$clone/build/libozamx.a" "$out/artifacts/libozamx_numa1.a"
cp /tmp/ozamx-production-final/libozamx.a "$out/artifacts/libozamx_frozen_v2.a"
cp "$clone/include/ozamx/gemm.hpp" "$out/artifacts/gemm.hpp"
cp "$clone/src/gemm.cpp" "$clone/src/preprocess.hpp" "$clone/src/tuning.hpp" "$clone/src/kernels.S" "$out/artifacts/"
cp "$clone/bench/optimization_benchmark.cpp" "$out/artifacts/optimization_benchmark.cpp"
cp "$clone/CMakeLists.txt" "$out/artifacts/CMakeLists.txt"
cp -a "$clone/src" "$clone/include" "$out/artifacts/"
cp "$root/bench/8454h/versions/v2/MANIFEST.sha256" "$out/artifacts/frozen_v2_MANIFEST.sha256"
cp "$root/bench/8454h/versions/v2/bench/optimization_benchmark.cpp" "$out/artifacts/optimization_benchmark_frozen_v2.cpp"
cp /tmp/ozamx-production-final/CMakeCache.txt /tmp/ozamx-production-final/compile_commands.json "$out/artifacts/"
cp /tmp/ozamx-production-final/CMakeFiles/ozamx.dir/flags.make "$out/artifacts/frozen_v2_flags.make"
cp "$clone/build/CMakeFiles/ozamx.dir/flags.make" "$out/artifacts/candidate_flags.make"
cp "$clone/build0/CMakeFiles/ozamx.dir/flags.make" "$out/artifacts/control_flags.make"

cat > "$out/artifacts/command_and_environment.txt" <<EOF2
Compiler command: $cxx ${flags[*]} -I$clone/include <clone>/bench/optimization_benchmark.cpp <matching libozamx.a> -o <benchmark>
Per-process argv: --sizes $sizes --precision all --threads $threads --budgets $budgets --reps $reps --output <raw CSV>
CPU affinity: taskset -c 0-63
OpenMP: OMP_NUM_THREADS=$threads OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE
Workspace cache: OZAMX_WORKSPACE_CACHE_BYTES=$cache_bytes
NUMA locality: Linux syscall(SYS_getcpu,&cpu,&node,nullptr), once per copy worker and once per compute worker; CSV reports copy-team node 0/node 1/fallback worker counts per call.
Run order: frozen_${cache_tag}_a, control0_${cache_tag}, numa1_${cache_tag}_a, frozen_${cache_tag}_b, numa1_${cache_tag}_b, frozen_${cache_tag}_c
Measured rows: 1 warmup + $reps repetitions for each size/precision/budget; warmups are retained in raw CSV and excluded from comparison medians.
EOF2

python3 - "$out" "$clone" "$frozen" "$cxx" "${flags[*]}" "$cache_bytes" <<'PY'
import hashlib,json,pathlib,platform,subprocess,sys,time
out=pathlib.Path(sys.argv[1]);clone=pathlib.Path(sys.argv[2]);frozen=pathlib.Path(sys.argv[3])
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def relhash(paths):return {str(pathlib.Path(p).relative_to(clone)):sha(p) for p in paths}
files=sorted([p for d in (clone/'src',clone/'include') for p in d.rglob('*') if p.is_file()])+[clone/'bench/optimization_benchmark.cpp',clone/'CMakeLists.txt']
tag='2g' if int(sys.argv[6])==2147483648 else '4g'
manifest={"started_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),"platform":platform.platform(),"candidate_clone":str(clone),"frozen_binary_source_path":str(frozen),"cpu_allowed_list":subprocess.check_output(['bash','-lc',"grep Cpus_allowed_list /proc/self/status"],text=True).strip(),"launch_affinity":"taskset -c 0-63","openmp":{"threads":64,"places":"cores","proc_bind":"close","dynamic":False},"workspace_cache_bytes":int(sys.argv[6]),"cli":{"sizes":[4096,8192],"precision":"all","fp64_budgets":[6,21],"warmups":1,"repetitions":5},"run_order":[f"frozen_{tag}_a",f"control0_{tag}",f"numa1_{tag}_a",f"frozen_{tag}_b",f"numa1_{tag}_b",f"frozen_{tag}_c"],"driver_compile":{"compiler":sys.argv[4],"flags":sys.argv[5],"include":"clone/include for both candidate/control so GemmTimings ABI matches each library"},"numa_call":"syscall(SYS_getcpu, &cpu, &node, nullptr); copy-team workers use node/rank assignment; compute workers re-query node; non-0/1 or syscall failure falls back to original p.b","hashes_sha256":{"frozen_binary":sha(frozen),"frozen_v2_manifest":sha(out/'artifacts/frozen_v2_MANIFEST.sha256'),"frozen_lib":sha(out/'artifacts/libozamx_frozen_v2.a'),"candidate_lib":sha(out/'artifacts/libozamx_numa1.a'),"control_lib":sha(out/'artifacts/libozamx_control0.a'),"frozen_copy":sha(out/'artifacts/optimization_benchmark_frozen_v2'),"candidate_driver":sha(out/'artifacts/optimization_benchmark_numa1'),"control_driver":sha(out/'artifacts/optimization_benchmark_control'),"source_files":relhash(files),"artifact_flags_candidate":sha(out/'artifacts/candidate_flags.make'),"artifact_flags_control":sha(out/'artifacts/control_flags.make'),"artifact_flags_frozen":sha(out/'artifacts/frozen_v2_flags.make'),"frozen_CMakeCache":sha(out/'artifacts/CMakeCache.txt'),"frozen_compile_commands":sha(out/'artifacts/compile_commands.json')}}
(out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
PY

run_one() {
  local name=$1 binary=$2
  shift 2
  local csv=$out/raw/$name.csv
  local err=$out/logs/$name.stderr.log
  printf 'RUN %s:' "$name" | tee -a "$out/logs/run_order.log"
  printf ' %q' taskset -c 0-63 env OMP_NUM_THREADS="$threads" OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE OZAMX_WORKSPACE_CACHE_BYTES="$cache_bytes" "$binary" --sizes "$sizes" --precision all --threads "$threads" --budgets "$budgets" --reps "$reps" --output "$csv" | tee -a "$out/logs/run_order.log"
  printf '\n' | tee -a "$out/logs/run_order.log"
  taskset -c 0-63 env OMP_NUM_THREADS="$threads" OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE OZAMX_WORKSPACE_CACHE_BYTES="$cache_bytes" "$binary" --sizes "$sizes" --precision all --threads "$threads" --budgets "$budgets" --reps "$reps" --output "$csv" 2> "$err"
}

run_one "frozen_${cache_tag}_a" "$out/artifacts/optimization_benchmark_frozen_v2"
run_one "control0_${cache_tag}" "$out/artifacts/optimization_benchmark_control"
run_one "numa1_${cache_tag}_a" "$out/artifacts/optimization_benchmark_numa1"
run_one "frozen_${cache_tag}_b" "$out/artifacts/optimization_benchmark_frozen_v2"
run_one "numa1_${cache_tag}_b" "$out/artifacts/optimization_benchmark_numa1"
run_one "frozen_${cache_tag}_c" "$out/artifacts/optimization_benchmark_frozen_v2"

python3 "$out/analyze.py" "$out"
date -u +%Y-%m-%dT%H:%M:%SZ > "$out/completed_utc.txt"
python3 - "$out" <<'PY'
import hashlib,json,pathlib,sys,time
out=pathlib.Path(sys.argv[1])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
raw={p.name:{"sha256":sha(p),"bytes":p.stat().st_size,"lines":sum(1 for _ in p.open())} for p in sorted((out/'raw').glob('*.csv'))}
note=out/'RESULTS.md'
result={"completed_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),"raw_csv":raw,"comparison_sha256":sha(out/'comparison.json'),"runner_sha256":sha(out/'runner.sh'),"analyzer_sha256":sha(out/'analyze.py'),"results_note_sha256":sha(note) if note.exists() else None}
(out/'completion_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
PY
