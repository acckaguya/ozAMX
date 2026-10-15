#!/usr/bin/env python3
"""Four-candidate allocator alignment/THP-hint screen; holds the global perf lock."""
from __future__ import annotations
import argparse, csv, fcntl, hashlib, json, os, pathlib, shlex, subprocess, sys, time

SRC = pathlib.Path(__file__).resolve().parents[1]
REPO = SRC.parents[3]
RUNS = REPO / "bench/8454h/roofline_v4/search_runs"
LOCK = pathlib.Path("/tmp/ozamx-perf.lock")
MKL_ROOT = REPO / "third_party/code/mkl-current"
MKL_LIB = MKL_ROOT / "lib/libmkl_rt.so.3"
FROZEN_LIB = REPO / "bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
FROZEN_HEADER = REPO / "bench/8454h/versions/v3_release/repo/include"
FROZEN_SHA = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
FREEZE = REPO / "bench/8454h/v3_paper_alignment/FROZEN_COMPLETE"
CPUS, THREADS, SEED = "0-63", 64, 260904
ALL_CASES = ",".join(str(i) for i in range(1, 21))

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())

def snapshot_sources():
    out={}
    for p in sorted(SRC.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts: continue
        out[str(p.relative_to(SRC))]=sha(p)
    return out

def common_env():
    e=dict(os.environ)
    e.update({"OMP_NUM_THREADS":str(THREADS),"OMP_PLACES":"cores","OMP_PROC_BIND":"close","OMP_DYNAMIC":"FALSE",
              "MKL_NUM_THREADS":str(THREADS),"MKL_DYNAMIC":"FALSE","MKL_THREADING_LAYER":"GNU","MKL_INTERFACE_LAYER":"LP64",
              "OZAMX_WORKSPACE_CACHE_BYTES":str(2<<30),"LD_LIBRARY_PATH":str(MKL_ROOT/"lib")+(":"+e["LD_LIBRARY_PATH"] if e.get("LD_LIBRARY_PATH") else "")})
    return e

def logged(argv, path, env=None):
    pathlib.Path(path).parent.mkdir(parents=True,exist_ok=True)
    with pathlib.Path(path).open("wb") as f: p=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,env=env)
    if p.returncode: raise RuntimeError(f"exit {p.returncode}: {shlex.join(map(str,argv))}; see {path}")

def config_args(alignment,hint):
    return ["-DOZV4_MODE=0","-DOZV4_FP64_BATCH=2","-DOZV4_WIDE_CBM=128","-DOZV4_WIDE_CBN=0",
            "-DOZV4_WIDE_PAD_BYTES=64","-DOZAMX_TILELOAD_HINT=1","-DOZV4_FP32_LATE32=0",
            f"-DOZV4_PAGE_ALIGNMENT={alignment}",f"-DOZV4_MADV_HUGEPAGE={hint}"]

def build(out,label,alignment=None,hint=None):
    bdir=out/"builds"/label
    bdir.mkdir(parents=True,exist_ok=False)
    argv=["cmake","-S",str(SRC),"-B",str(bdir),"-DCMAKE_BUILD_TYPE=Release","-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
          "-DOZAMX_ENABLE_OPENMP=ON",f"-DOZAMX_ONEMKL_ROOT={MKL_ROOT}"]
    if alignment is not None: argv+=config_args(alignment,hint)
    logged(argv,out/"logs"/f"{label}_configure.log",common_env())
    logged(["cmake","--build",str(bdir),"-j2"],out/"logs"/f"{label}_build.log",common_env())
    ident=json.loads((bdir/"build_identity.json").read_text())
    ident.update({"source_tree":str(SRC),"library_sha256":sha(bdir/"libozamx.a") if (bdir/"libozamx.a").exists() else FROZEN_SHA,
                  "benchmark_binary_sha256":sha(bdir/"ozamx_benchmark"),"page_probe_binary_sha256":sha(bdir/"ozamx_page_layout_probe") if alignment is not None else None})
    (bdir/"build_identity.json").write_text(json.dumps(ident,indent=2)+"\n")
    return bdir

def build_frozen_driver(out):
    bdir=out/"builds"/"frozen_v3_driver";bdir.mkdir(parents=True,exist_ok=False)
    binary=bdir/"ozamx_benchmark"
    cmd=[os.environ.get("CXX","g++"),"-O3","-std=c++17","-Wall","-Wextra","-Wpedantic","-march=sapphirerapids",
         "-ffp-contract=off","-fno-fast-math","-mamx-tile","-mamx-bf16","-fopenmp",f"-I{SRC/'include'}",f"-I{MKL_ROOT/'include'}",
         str(SRC/"bench/benchmark.cpp"),str(FROZEN_LIB),f"-L{MKL_ROOT/'lib'}",f"-Wl,-rpath,{MKL_ROOT/'lib'}",
         "-Wl,--no-as-needed","-l:libmkl_rt.so.3","-ldl","-o",str(binary)]
    logged(cmd,out/"logs/frozen_v3_driver_build.log",common_env())
    (bdir/"build_identity.json").write_text(json.dumps({"reference":"immutable V3 release","library_sha256":sha(FROZEN_LIB),
       "benchmark_binary_sha256":sha(binary),"driver_source_sha256":sha(SRC/"bench/benchmark.cpp"),"mkl_runtime_sha256":sha(MKL_LIB),
       "snapshot_source":"same benchmark driver; V3 library has no candidate allocator snapshot symbol"},indent=2)+"\n")
    return binary

def validate_csv(path,checkpoint,reps,expected_rows=5):
    with pathlib.Path(path).open(newline="") as f:
        reader=csv.DictReader(f); rows=list(reader); cols=len(reader.fieldnames or [])
    if cols!=37 or len(rows)!=expected_rows or any(None in r for r in rows): raise RuntimeError(f"bad schema/row count: {path}: cols={cols}, rows={len(rows)}")
    expected=[("fp32","6")]+[("fp64",x) for x in ("6","10","15","21")]
    for row,(precision,budget) in zip(rows,expected):
        if (row["precision"],row["budget"],row["N"],row["threads"],row["seed"],row["repetitions"],row["status"])!=(precision,budget,"8192","64","269096",str(reps),"ok"):
            raise RuntimeError(f"unexpected benchmark row {precision}/{budget}: {row}")
        cp=pathlib.Path(f"{checkpoint}.{precision}.8192.{budget}.json")
        chk=json.loads(cp.read_text()); vals=[float(x) for x in row["raw_api_call_wall_s"].split(";")]
        if chk.get("complete") is not True or chk.get("requested_repetitions")!=reps or chk.get("completed_timed_repetitions")!=reps or len(vals)!=reps:
            raise RuntimeError(f"invalid checkpoint for {precision}/{budget}: {cp}")
        if any(abs(a-float(b))>2e-9 for a,b in zip(vals,chk.get("call_wall_seconds",[]))): raise RuntimeError(f"API wall differs from checkpoint: {cp}")
    return rows

def benchmark(binary,out,label,reps,env,library):
    od=out/"records"/label;od.mkdir(parents=True,exist_ok=False)
    csvpath=od/"result.csv";cp=od/"checkpoint";smaps=od/"allocator_smaps.json"
    argv=["taskset","-c",CPUS,str(binary),"--sizes","8192","--threads",str(THREADS),"--reps",str(reps),"--seed",str(SEED),
          "--precision","all","--budgets","6,10,15,21","--distribution","uniform","--checkpoint",str(cp),"--output",str(csvpath)]
    (od/"command.json").write_text(json.dumps(argv,indent=2)+"\n")
    e=dict(env);e["OZV4_SMAPS_OUT"]=str(smaps)
    logged(argv,od/"stderr.log",e)
    rows=validate_csv(csvpath,cp,reps)
    if not smaps.is_file(): raise RuntimeError(f"post-run smaps snapshot absent: {smaps}")
    snapshot=json.loads(smaps.read_text())
    source=json.loads((binary.parent/"build_identity.json").read_text())
    data={"label":label,"library_path":str(pathlib.Path(library).resolve()),"library_sha256":sha(library),"binary_sha256":sha(binary),
          "benchmark_source_sha256":sha(SRC/"bench/benchmark.cpp"),"source_gemm_sha256":sha(SRC/"src/gemm.cpp"),
          "source_preprocess_sha256":sha(SRC/"src/preprocess.hpp"),"mkl_runtime_sha256":sha(MKL_LIB),"seed_base":SEED,"seed_for_N8192":SEED+8192,
          "N":8192,"repetitions":reps,"threads":THREADS,"cpuset":CPUS,"distribution":"uniform",
          "workspace_cache_bytes":2<<30,"env":{"OMP_PLACES":"cores","OMP_PROC_BIND":"close","OMP_DYNAMIC":"FALSE","MKL_THREADING_LAYER":"GNU"},
          "rows":len(rows),"csv_sha256":sha(csvpath),"checkpoints_sha256":{str(p.name):sha(p) for p in sorted(od.glob("checkpoint.*.json"))},
          "smaps_sha256":sha(smaps),"smaps":snapshot,"build_identity":source}
    (od/"metadata.json").write_text(json.dumps(data,indent=2)+"\n")
    return rows

def run_candidate(out,label,alignment,hint,state,env):
    state["current_step"]=f"build {label}";state["updated_utc"]=utc();save_state(out,state)
    bdir=build(out,label,alignment,hint);lib=bdir/"libozamx.a";binary=bdir/"ozamx_benchmark"
    state["candidates"].append({"label":label,"alignment_bytes":alignment,"madv_hugepage":hint,"build_dir":str(bdir),
                                "library":str(lib),"library_sha256":sha(lib),"identity":str(bdir/"build_identity.json")})
    state["current_step"]=f"ctest {label}";state["updated_utc"]=utc();save_state(out,state)
    logged(["ctest","--test-dir",str(bdir),"--output-on-failure"],out/"logs"/f"{label}_ctest.log",env)
    ctest=(out/"logs"/f"{label}_ctest.log").read_text()
    if "100% tests passed" not in ctest or "3/3 Test" not in ctest: raise RuntimeError(f"candidate {label}: CTest not 3/3")
    state["current_step"]=f"full gate {label}";state["updated_utc"]=utc();save_state(out,state)
    gatepath=out/"gates"/f"{label}_full.json";gatepath.parent.mkdir(parents=True,exist_ok=True)
    logged([sys.executable,str(SRC/"tools/run_binary_gate_v4.py"),"--candidate-library",str(lib),"--output",str(gatepath),"--case-ids",ALL_CASES,"--lock-held"],out/"logs"/f"{label}_gate.log",env)
    gate=json.loads(gatepath.read_text())
    if gate.get("status")!="pass" or len(gate.get("cases",[]))!=20 or gate.get("candidate_library_sha256")!=sha(lib): raise RuntimeError(f"candidate {label}: full 20-case gate failed or identity mismatch")
    state["current_step"]=f"direct probe {label}";state["updated_utc"]=utc();save_state(out,state)
    probepath=out/"probes"/f"{label}.json";probepath.parent.mkdir(parents=True,exist_ok=True)
    logged(["taskset","-c",CPUS,str(bdir/"ozamx_page_layout_probe")],out/"logs"/f"{label}_probe.log",env)
    # The probe prints machine-readable alignment, madvise result and smaps line.
    probe=json.loads((out/"logs"/f"{label}_probe.log").read_text())
    if probe.get("status")!="pass" or probe.get("large_alignment_mod")!=0 or (hint and probe.get("hint_attempts")!=1): raise RuntimeError(f"candidate {label}: allocator probe failed: {probe}")
    probepath.write_text(json.dumps(probe,indent=2)+"\n")
    state["current_step"]=f"N8192 run {label}";state["updated_utc"]=utc();save_state(out,state)
    rows=benchmark(binary,out,label,3,env,lib)
    state["completed_candidates"].append({"label":label,"library":str(lib),"library_sha256":sha(lib),
       "binary_sha256":sha(binary),"gate":str(gatepath),"gate_sha256":sha(gatepath),"ctest_log":str(out/"logs"/f"{label}_ctest.log"),
       "probe":str(probepath),"probe_sha256":sha(probepath),"result_csv":str(out/"records"/label/"result.csv"),
       "result_csv_sha256":sha(out/"records"/label/"result.csv"),"rows":len(rows)})
    state["current_step"]=None;state["updated_utc"]=utc();save_state(out,state)

def save_state(out,state):
    (out/"dataset.json").write_text(json.dumps(state,indent=2)+"\n")

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",type=pathlib.Path);args=ap.parse_args()
    RUNS.mkdir(parents=True,exist_ok=True)
    out=args.out.resolve() if args.out else RUNS/f"page_layout_20261014T{time.strftime('%H%M%SZ',time.gmtime())}"
    out.mkdir(parents=True,exist_ok=False);(out/"logs").mkdir();
    if not FREEZE.is_file() or sha(FROZEN_LIB)!=FROZEN_SHA or sha(FROZEN_HEADER/"ozamx/gemm.hpp")!=sha(SRC/"include/ozamx/gemm.hpp"):
        raise RuntimeError("V3 freeze/library/header validation failed")
    origin=json.loads((SRC/"SOURCE_ORIGIN.json").read_text())
    expected_asm=origin["diagnostic_selective_copy"]["src/kernels.S"]["diagnostic_source_sha256"]
    if sha(SRC/"src/kernels.S")!=expected_asm: raise RuntimeError("page-layout experiment must keep the original assembly byte-for-byte")
    if not MKL_LIB.is_file():raise RuntimeError(f"MKL runtime missing: {MKL_LIB}")
    state={"schema":"ozamx-v4-page-layout-run-1","status":"waiting_for_global_lock","created_utc":utc(),"lock_path":str(LOCK),
       "protocol":{"candidate_configs":[{"label":"a4k_hint0","alignment_bytes":4096,"madv_hugepage":0},{"label":"a4k_hint1","alignment_bytes":4096,"madv_hugepage":1},
          {"label":"a2m_hint0","alignment_bytes":2097152,"madv_hugepage":0},{"label":"a2m_hint1","alignment_bytes":2097152,"madv_hugepage":1}],
        "large_threshold_bytes":2<<20,"small_allocation_alignment_bytes":64,"madvise_length":"floor(logical_bytes/4096)*4096, pointer page-aligned, within logical allocation",
        "mode":0,"late32":0,"fp64_batch":2,"wide_cbm":128,"wide_cbn":0,"wide_pad_bytes":64,"tileload_hint":1,"bk":256,
        "workloads":["N8192 FP32","N8192 FP64 p6","N8192 FP64 p10","N8192 FP64 p15","N8192 FP64 p21"],"candidate_reps":3,"frozen_v3_control_reps":7,
        "gate_cases":20,"ctests_per_candidate":3,"timing_scope":"full profiled API wall primary; phase/compute raw and MKL GEMM-only preserved",
        "no_hardware_attribution":"smaps only reports mapping AnonHugePages; no PMU or system traffic inference"},
       "frozen_library_sha256":FROZEN_SHA,"mkl_runtime_sha256":sha(MKL_LIB),"seed_base":SEED,"threads":THREADS,"cpuset":CPUS,
       "workspace_cache_bytes":2<<30,"source_snapshot_sha256":snapshot_sources(),"candidates":[],"completed_candidates":[],"controls":[]}
    save_state(out,state);print(f"WAITING lock {LOCK}; dataset={out}",flush=True)
    with LOCK.open("a") as lock:
        wait0=time.time();fcntl.flock(lock,fcntl.LOCK_EX);acquired=time.time()
        state.update({"status":"running","lock_wait_started_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(wait0)),
          "lock_acquired_utc":utc(),"lock_wait_seconds":acquired-wait0});save_state(out,state)
        print(f"LOCK ACQUIRED after {acquired-wait0:.1f}s",flush=True)
        env=common_env()
        try:
            state["current_step"]="build immutable V3 control";save_state(out,state)
            v3=build_frozen_driver(out)
            state["controls"].append({"label":"frozen_v3_initial","library":str(FROZEN_LIB),"library_sha256":sha(FROZEN_LIB)})
            benchmark(v3,out,"frozen_v3_initial",7,env,FROZEN_LIB)
            for label,alignment,hint in (("a4k_hint0",4096,0),("a4k_hint1",4096,1),("a2m_hint0",2097152,0),("a2m_hint1",2097152,1)):
                run_candidate(out,label,alignment,hint,state,env)
            state["current_step"]="frozen V3 final control";save_state(out,state)
            benchmark(v3,out,"frozen_v3_final",7,env,FROZEN_LIB)
            state["controls"].append({"label":"frozen_v3_final","library":str(FROZEN_LIB),"library_sha256":sha(FROZEN_LIB)})
            state.update({"status":"complete","completed_utc":utc(),"current_step":None,"source_snapshot_sha256_final":snapshot_sources()})
            save_state(out,state);print(f"COMPLETE dataset={out}",flush=True)
        except Exception as ex:
            state.update({"status":"failed","failed_utc":utc(),"failure":repr(ex),"source_snapshot_sha256_final":snapshot_sources()})
            save_state(out,state);raise

if __name__=="__main__":main()
