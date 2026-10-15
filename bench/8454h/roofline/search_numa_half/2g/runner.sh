#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../../.." && pwd)
out=$root/bench/8454h/roofline/search_numa_half/2g
clone=/tmp/ozamx-roof-numa-half
frozen=/tmp/ozamx-production-final/ozamx_optimization_benchmark
lock=/tmp/ozamx-perf.lock
cache_bytes=2147483648
sizes=4096,8192
budgets=6,21
threads=64
reps=5
mkdir -p "$out/raw" "$out/logs" "$out/artifacts"
exec 9>"$lock"
flock -x 9
cxx=${CXX:-g++}
flags=(-std=c++17 -O3 -march=sapphirerapids -ffp-contract=off -fopenmp)
"$cxx" "${flags[@]}" -I"$clone/include" "$clone/bench/optimization_benchmark.cpp" "$clone/build-half0/libozamx.a" -o "$out/artifacts/optimization_benchmark_control0"
"$cxx" "${flags[@]}" -I"$clone/include" "$clone/bench/optimization_benchmark.cpp" "$clone/build-half/libozamx.a" -o "$out/artifacts/optimization_benchmark_numa_half"
cp "$frozen" "$out/artifacts/optimization_benchmark_frozen_v2"
cp "$clone/build-half0/libozamx.a" "$out/artifacts/libozamx_control0.a"
cp "$clone/build-half/libozamx.a" "$out/artifacts/libozamx_numa_half.a"
cp /tmp/ozamx-production-final/libozamx.a "$out/artifacts/libozamx_frozen_v2.a"
cp "$clone/include/ozamx/gemm.hpp" "$clone/src/gemm.cpp" "$clone/src/preprocess.hpp" "$clone/src/tuning.hpp" "$clone/src/kernels.S" "$clone/CMakeLists.txt" "$clone/bench/optimization_benchmark.cpp" "$out/artifacts/"
cp "$clone/build-half/CMakeFiles/ozamx.dir/flags.make" "$out/artifacts/candidate_flags.make"
cp "$clone/build-half0/CMakeFiles/ozamx.dir/flags.make" "$out/artifacts/control_flags.make"
cat > "$out/artifacts/command_and_environment.txt" <<EOF
Compiler: $cxx ${flags[*]} -I$clone/include, matching source-header ABI for control and candidate.
Per-call: --sizes $sizes --precision all --threads $threads --budgets $budgets --reps $reps --output <CSV>
CPU: taskset -c 0-63; OMP_NUM_THREADS=$threads OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE
Cache: OZAMX_WORKSPACE_CACHE_BYTES=$cache_bytes
Order: frozen_2g_a, control0_2g, numa_half_2g_a, frozen_2g_b, numa_half_2g_b, frozen_2g_c
Warmup: 1/config, retained in CSV and excluded from median; measured reps=5/config.
EOF
python3 - "$out" "$clone" "$frozen" <<'PY'
import hashlib,json,pathlib,platform,subprocess,sys,time
out=pathlib.Path(sys.argv[1]);clone=pathlib.Path(sys.argv[2]);frozen=pathlib.Path(sys.argv[3])
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
files=sorted([p for d in (clone/'src',clone/'include') for p in d.rglob('*') if p.is_file()])+[clone/'bench/optimization_benchmark.cpp',clone/'CMakeLists.txt']
manifest={'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'platform':platform.platform(),'candidate_clone':str(clone),'frozen_binary':str(frozen),'cpu_allowed_list':subprocess.check_output(['bash','-lc','grep Cpus_allowed_list /proc/self/status'],text=True).strip(),'affinity':'taskset -c 0-63','openmp':{'threads':64,'places':'cores','proc_bind':'close','dynamic':False},'workspace_cache_bytes':2147483648,'cli':{'sizes':[4096,8192],'precision':'all','fp64_budgets':[6,21],'warmups':1,'repetitions':5},'run_order':['frozen_2g_a','control0_2g','numa_half_2g_a','frozen_2g_b','numa_half_2g_b','frozen_2g_c'],'driver_compile':{'compiler':subprocess.check_output(['bash','-lc','command -v g++'],text=True).strip(),'flags':'-std=c++17 -O3 -march=sapphirerapids -ffp-contract=off -fopenmp','header_abi':'clone/include for both half-control and half-candidate'},'partial_replica':'two NUMA buffers per packed B slice, each size=size/2; node0 contains second half and node1 first half; per-actual-offset selection avoids invalid base pointers','sha256':{'frozen_binary':sha(frozen),'frozen_library':sha('/tmp/ozamx-production-final/libozamx.a'),'candidate_library':sha(clone/'build-half/libozamx.a'),'control_library':sha(clone/'build-half0/libozamx.a'),'candidate_driver':sha(out/'artifacts/optimization_benchmark_numa_half'),'control_driver':sha(out/'artifacts/optimization_benchmark_control0'),'source_files':{str(p.relative_to(clone)):sha(p) for p in files},'candidate_flags':sha(clone/'build-half/CMakeFiles/ozamx.dir/flags.make'),'control_flags':sha(clone/'build-half0/CMakeFiles/ozamx.dir/flags.make')}}
(out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
PY
run_one(){ local name=$1 binary=$2 csv=$out/raw/$1.csv; printf 'RUN %s\n' "$name" | tee -a "$out/logs/run_order.log"; taskset -c 0-63 env OMP_NUM_THREADS=$threads OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE OZAMX_WORKSPACE_CACHE_BYTES=$cache_bytes "$binary" --sizes "$sizes" --precision all --threads "$threads" --budgets "$budgets" --reps "$reps" --output "$csv" 2>"$out/logs/$name.stderr.log"; }
run_one frozen_2g_a "$out/artifacts/optimization_benchmark_frozen_v2"
run_one control0_2g "$out/artifacts/optimization_benchmark_control0"
run_one numa_half_2g_a "$out/artifacts/optimization_benchmark_numa_half"
run_one frozen_2g_b "$out/artifacts/optimization_benchmark_frozen_v2"
run_one numa_half_2g_b "$out/artifacts/optimization_benchmark_numa_half"
run_one frozen_2g_c "$out/artifacts/optimization_benchmark_frozen_v2"
date -u +%Y-%m-%dT%H:%M:%SZ > "$out/completed_utc.txt"
