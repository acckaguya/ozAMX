#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/../../../.." && pwd)
clone=${OZAMX_NUMA_CLONE:-/tmp/ozamx-roof-numa-b}
control=${OZAMX_NUMA_CONTROL_LIBRARY:-$clone/build0/libozamx.a}
candidate=${OZAMX_NUMA_CANDIDATE_LIBRARY:-$clone/build/libozamx.a}
lock=${OZAMX_PERF_LOCK:-/tmp/ozamx-perf.lock}
summary=${OZAMX_NUMA_GATE_SUMMARY:-$root/bench/8454h/roofline/ideas/numa_b_gate.json}
work=$(mktemp -d /tmp/ozamx-numa-gates.XXXXXX)
trap 'rm -rf "$work"' EXIT
exec 9>"$lock"
flock -x 9

flags=(-std=c++17 -O2 -march=sapphirerapids -ffp-contract=off -mamx-tile -mamx-bf16 -fopenmp)
"${CXX:-g++}" "${flags[@]}" -I"$clone/include" "$root/bench/8454h/equivalence_driver.cpp" "$control" -o "$work/equiv-control"
"${CXX:-g++}" "${flags[@]}" -I"$clone/include" "$root/bench/8454h/equivalence_driver.cpp" "$candidate" -o "$work/equiv-candidate"
"${CXX:-g++}" "${flags[@]}" -I"$clone/include" "$clone/tests/extended_validation.cpp" "$control" -o "$work/extended-control"
"${CXX:-g++}" "${flags[@]}" -I"$clone/include" "$clone/tests/extended_validation.cpp" "$candidate" -o "$work/extended-candidate"

python3 - "$work" "$summary" <<'PY'
import hashlib, json, os, pathlib, subprocess, sys
w=sys.argv[1];target=pathlib.Path(sys.argv[2])
def signature(exe,threads,cache=None):
    env=os.environ.copy();env.update(OMP_NUM_THREADS=str(threads),OMP_DYNAMIC="FALSE")
    if cache is not None:env["OZAMX_WORKSPACE_CACHE_BYTES"]=str(cache)
    else:env.pop("OZAMX_WORKSPACE_CACHE_BYTES",None)
    proc=subprocess.Popen([exe],stdout=subprocess.PIPE,env=env,text=True,bufsize=1)
    sig=[]
    assert proc.stdout is not None
    for i,line in enumerate(proc.stdout):
        try:row=json.loads(line)
        except Exception as e:raise SystemExit(f"invalid JSON from {exe} row {i}: {e}")
        sig.append(hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest())
    rc=proc.wait()
    if rc:raise SystemExit(f"{exe} failed with exit code {rc}")
    return sig
checks={}
for threads in (1,4,64):
    a=signature(w+"/equiv-control",threads)
    b=signature(w+"/equiv-candidate",threads)
    if a!=b or len(a)!=100:raise SystemExit(f"100-case mismatch or row count at t{threads}: {len(a)}")
    checks[f"equivalence_100_t{threads}"]={"rows":len(a),"mismatches":0}
    for cache in (1073741824,0):
        a=signature(w+"/extended-control",threads,cache)
        b=signature(w+"/extended-candidate",threads,cache)
        if a!=b or len(a)!=47:raise SystemExit(f"47-case mismatch or row count at t{threads}, cache={cache}: {len(a)}")
        checks[f"extended47_t{threads}_cache{cache}"]={"rows":len(a),"mismatches":0}
result={"status":"pass","checks":checks}
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
print(json.dumps(result,sort_keys=True,separators=(",",":")))
PY
