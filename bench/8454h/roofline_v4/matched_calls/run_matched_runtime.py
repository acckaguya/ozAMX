#!/usr/bin/env python3
"""Runtime-default-wait interleaved API benchmark, revision 2 of run_matched."""
import argparse, fcntl, hashlib, json, math, os, pathlib, platform, select, shlex, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DRIVER = HERE / "driver.cpp"
LOCK = pathlib.Path("/tmp/ozamx-perf.lock")
PIN = "0-63"
ENV_KEYS = ("OMP_NUM_THREADS", "OMP_DYNAMIC", "OMP_WAIT_POLICY", "GOMP_SPINCOUNT", "OMP_PLACES", "OMP_PROC_BIND",
            "MKL_NUM_THREADS", "MKL_DYNAMIC", "MKL_THREADING_LAYER", "MKL_INTERFACE_LAYER", "OZAMX_WORKSPACE_CACHE_BYTES")
RUN_RESULT = None

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
    return h.hexdigest()

def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with open(tmp,"w") as f: json.dump(obj,f,indent=2,sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def parse_json_line(line,where):
    try: x=json.loads(line,parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid numeric constant {value}")))
    except Exception as e: raise RuntimeError(f"malformed JSON from {where}: {line!r}") from e
    if not isinstance(x,dict): raise RuntimeError(f"non-object JSON from {where}: {line!r}")
    return x

class Child:
    def __init__(self,label,binary,env,log):
        self.label=label; self.log=open(log,"a",buffering=1)
        self.timeout=300
        self.p=subprocess.Popen(["taskset","-c",PIN,str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                stderr=self.log,text=True,bufsize=1,env=env)
        try:
            ready=parse_json_line(self._read(),label+" ready")
            if ready.get("event")!="ready": raise RuntimeError(f"{label}: expected ready event, got {ready}")
            if not ready.get("amx_permission"): raise RuntimeError(f"{label}: AMX permission unavailable")
            if ready.get("requested_omp_threads")!=64 or ready.get("max_omp_threads")!=64: raise RuntimeError(f"{label}: unexpected OpenMP thread configuration: {ready}")
            if ready.get("actual_omp_threads")!=64: raise RuntimeError(f"{label}: unexpected actual OpenMP team size: {ready}")
            if ready.get("calling_cpu") not in range(64): raise RuntimeError(f"{label}: calling thread is outside CPUs 0-63: {ready}")
            if sorted(set(ready.get("omp_thread_cpus",[])))!=list(range(64)) or len(ready.get("omp_thread_cpus",[]))!=64:
                raise RuntimeError(f"{label}: OpenMP team did not occupy CPUs 0-63 exactly once: {ready}")
            self.ready=ready
        except Exception:
            self.p.kill(); self.p.wait(); self.log.close(); raise
    def _read(self):
        ready,_,_=select.select([self.p.stdout],[],[],self.timeout)
        if not ready: raise RuntimeError(f"{self.label}: protocol reply timed out after {self.timeout}s")
        line=self.p.stdout.readline()
        if not line: raise RuntimeError(f"{self.label}: child exited before protocol reply (rc={self.p.poll()})")
        return line.strip()
    def command(self,s):
        if self.p.poll() is not None: raise RuntimeError(f"{self.label}: child exited rc={self.p.returncode}")
        self.p.stdin.write(s+"\n"); self.p.stdin.flush()
        x=parse_json_line(self._read(),self.label+" reply")
        if x.get("status")=="error": raise RuntimeError(f"{self.label}: child error: {x}")
        return x
    def close(self):
        if self.p.poll() is None:
            try: self.command("quit")
            except Exception: self.p.terminate()
        try: self.p.wait(timeout=10)
        except subprocess.TimeoutExpired: self.p.kill(); self.p.wait()
        self.log.close()

def main():
    global RUN_RESULT
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--control-lib",required=True); ap.add_argument("--candidate-lib",required=True)
    ap.add_argument("--candidate-tag",required=True); ap.add_argument("--result-dir",required=True)
    ap.add_argument("--sizes",nargs="+",type=int,default=[1024,4096,8192])
    ap.add_argument("--reps",type=int,default=7); ap.add_argument("--warmups",type=int,default=1)
    ap.add_argument("--precision",choices=["fp32","fp64"],default="fp32")
    ap.add_argument("--wait-policy",choices=["runtime"],default="runtime")
    ap.add_argument("--budget",type=int,choices=[6,10,15,21],default=6)
    ap.add_argument("--resume",action="store_true")
    ap.add_argument("--lock-held",action="store_true",help=argparse.SUPPRESS)
    a=ap.parse_args()
    if min(a.sizes)<=0 or len(set(a.sizes))!=len(a.sizes) or a.reps<1 or a.warmups<1: ap.error("sizes must be unique positive values and reps/warmups positive")
    control=pathlib.Path(a.control_lib).resolve(); candidate=pathlib.Path(a.candidate_lib).resolve()
    if not control.is_file() or not candidate.is_file(): ap.error("both archive libraries must exist")
    result=pathlib.Path(a.result_dir).resolve(); result.mkdir(parents=True,exist_ok=True)
    RUN_RESULT=result
    lockfile=None
    if not a.lock_held:
        lockfile=open(LOCK,"a+"); fcntl.flock(lockfile,fcntl.LOCK_EX)
    try:
        meta_path=result/"metadata.json"; journal_path=result/"matched_calls.json"
        if journal_path.exists() and not a.resume: raise RuntimeError("result journal exists; choose a fresh result directory or pass --resume")
        if meta_path.exists() and not a.resume: raise RuntimeError("metadata exists; choose a fresh result directory or pass --resume")
        env=os.environ.copy()
        env.update({"OMP_NUM_THREADS":"64","OMP_DYNAMIC":"FALSE","OMP_WAIT_POLICY":"PASSIVE",
                    "GOMP_SPINCOUNT":"0","OMP_PLACES":"cores","OMP_PROC_BIND":"close",
                    "MKL_NUM_THREADS":"64","MKL_DYNAMIC":"FALSE",
                    "MKL_THREADING_LAYER":"GNU","MKL_INTERFACE_LAYER":"LP64","OZAMX_WORKSPACE_CACHE_BYTES":"2147483648"})
        # Recheck the old GNU OpenMP runtime defaults explicitly, independent
        # of any inherited environment from the passive-wait formal campaign.
        env.pop("OMP_WAIT_POLICY",None)
        env.pop("GOMP_SPINCOUNT",None)
        cmdflags=["-std=c++17","-O3","-march=sapphirerapids","-mamx-tile","-mamx-bf16","-ffp-contract=off","-fopenmp","-pthread"]
        bins={}
        logs=result/"logs"; logs.mkdir(exist_ok=True)
        build_commands=[]
        for label,lib in (("control",control),("candidate",candidate)):
            binary=result/f"child_{label}"
            cmd=["g++",*cmdflags,"-I",str(ROOT/"include"),str(DRIVER),str(lib),"-o",str(binary)]
            build_commands.append(cmd)
            atomic_json(result/"build_commands.json",{"commands":build_commands})
            with open(logs/f"build_{label}.log","w") as f:
                cp=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,text=True)
            if cp.returncode: raise RuntimeError(f"build {label} failed ({cp.returncode}); see {logs/f'build_{label}.log'}")
            bins[label]=binary
        config={"control_lib":str(control),"control_sha256":sha(control),"candidate_lib":str(candidate),"candidate_sha256":sha(candidate),
                "child_binaries":{k:{"path":str(v),"sha256":sha(v)} for k,v in bins.items()},
                "openmp_runtime_request":{"threads":64,"places":"cores","proc_bind":"close"},
                "candidate_tag":a.candidate_tag,"sizes":a.sizes,"reps":a.reps,"warmups":a.warmups,"precision":a.precision,
                "budget":a.budget if a.precision=="fp64" else None,"seed_rule":"260904 + N",
                "distribution":"std::uniform_real_distribution<T>(-1,1), mt19937_64; A then B",
                "threads":64,"cpu_affinity":PIN,"environment":{k:env.get(k) for k in ENV_KEYS},
                "shared_host_note":"GNU OpenMP runtime-default waiting is explicitly restored for both children; OMP_WAIT_POLICY and GOMP_SPINCOUNT are unset, with a 20 ms parent-side pause after each API call.",
                "wait_policy_variant":a.wait_policy,"wait_policy_environment":"OMP_WAIT_POLICY and GOMP_SPINCOUNT unset",
                "parent_inter_call_pause_seconds":0.020,"runner_source":str(pathlib.Path(__file__).resolve()),"runner_sha256":sha(__file__),
                "driver_source":str(DRIVER),"driver_sha256":sha(DRIVER),"compiler":subprocess.run(["g++","--version"],capture_output=True,text=True).stdout.splitlines()[0],
                "compile_flags":cmdflags,"build_commands":build_commands,"python":platform.python_version()}
        if meta_path.exists():
            old=json.load(open(meta_path))
            if old.get("run_config")!=config: raise RuntimeError("resume metadata differs from requested run")
        else: atomic_json(meta_path,{"run_config":config,"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
        if journal_path.exists(): journal=json.load(open(journal_path))
        else: journal={"run_config":config,"configurations":{},"process_sessions":[]}
        if journal.get("run_config")!=config: raise RuntimeError("resume journal config mismatch")
        children={}
        try:
            for label in ("control","candidate"): children[label]=Child(label,bins[label],env,logs/f"child_{label}.log")
            journal.setdefault("process_sessions",[]).append({
                "started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                "children_ready":{label:child.ready for label,child in children.items()}})
            atomic_json(journal_path,journal)
            for n in a.sizes:
                key=f"{a.precision}_n{n}_b{a.budget if a.precision=='fp64' else 6}"
                cfg=journal["configurations"].setdefault(key,{"N":n,"precision":a.precision,"budget":a.budget if a.precision=="fp64" else 6,"warmups":[],"samples":[],"complete":False})
                if cfg.get("complete"): continue
                recorded_samples=len(cfg["samples"])
                # Re-establish equal deterministic inputs/state in both persistent children.
                warm_session=[]
                for wi in range(a.warmups):
                    warm={"rep":wi,"order":[],"calls":{}}
                    for label in ("control","candidate"):
                        warm["order"].append(label)
                        warm["calls"][label]=children[label].command(f"warm {a.precision} {n}"+(f" {a.budget}" if a.precision=="fp64" else ""))
                        time.sleep(0.020)
                    pair=((warm["calls"]["control"].get("input_a_fnv1a64"),warm["calls"]["control"].get("input_b_fnv1a64")),
                          (warm["calls"]["candidate"].get("input_a_fnv1a64"),warm["calls"]["candidate"].get("input_b_fnv1a64")))
                    if pair[0]!=pair[1]: raise RuntimeError(f"warmup input hashes differ between children for {key}: {pair}")
                    warm_session.append(warm)
                cfg.setdefault("warmup_sessions",[]).append({"process_session":len(journal["process_sessions"]),"calls":warm_session})
                atomic_json(journal_path,journal)
                if recorded_samples>=a.reps:
                    restore={}
                    for label in ("control","candidate"):
                        restore[label]=children[label].command(f"run {a.precision} {n}"+(f" {a.budget}" if a.precision=="fp64" else ""))
                        time.sleep(0.020)
                    cfg["output_restore_call"]={"reason":"resume after timed calls completed before full-output hash checkpoint","calls":restore}
                for rep in range(recorded_samples,a.reps):
                    order=("control","candidate") if rep%2==0 else ("candidate","control")
                    sample={"rep":rep,"order":list(order),"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"calls":{}}
                    for label in order:
                        call_started=time.time()
                        x=children[label].command(f"run {a.precision} {n}"+(f" {a.budget}" if a.precision=="fp64" else ""))
                        call_finished=time.time()
                        # Give a default spinning GNU OpenMP team time to park
                        # before the opposite binary receives its next call.
                        time.sleep(0.020)
                        required=("api_wall_seconds","split_seconds","pack_seconds","compute_reconstruct_seconds","profile_total_seconds")
                        if any(type(x.get(k)) not in (int,float) or not math.isfinite(x[k]) for k in required): raise RuntimeError(f"malformed timing reply from {label}: {x}")
                        if x["api_wall_seconds"]<=0 or any(x[k]<0 for k in required[1:]): raise RuntimeError(f"non-positive API wall or negative phase timing from {label}: {x}")
                        x["parent_started_unix_seconds"]=call_started; x["parent_finished_unix_seconds"]=call_finished
                        sample["calls"][label]=x
                    hashes={(sample["calls"][label]["input_a_fnv1a64"],sample["calls"][label]["input_b_fnv1a64"]) for label in order}
                    if len(hashes)!=1: raise RuntimeError(f"input hashes differ between children for {key} rep {rep}: {sample['calls']}")
                    sample["finished_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
                    cfg["samples"].append(sample); atomic_json(journal_path,journal)
                with tempfile.TemporaryDirectory(prefix="ozamx-matched-") as td:
                    hashes={}
                    for label in ("control","candidate"):
                        path=pathlib.Path(td)/f"{label}.bin"
                        x=children[label].command(f"dump {a.precision} {n} {path}")
                        expected=n*n*(4 if a.precision=="fp32" else 8)
                        if x.get("status")!="dumped" or x.get("N")!=n or x.get("bytes")!=expected or path.stat().st_size!=expected: raise RuntimeError(f"invalid full output dump from {label}")
                        hashes[label]=sha(path)
                cfg["output_sha256"]=hashes
                cfg["byte_exact_match"]=hashes["control"]==hashes["candidate"]
                cfg["complete"]=cfg["byte_exact_match"]; atomic_json(journal_path,journal)
                if not cfg["byte_exact_match"]: raise RuntimeError(f"full output mismatch for {key}: {hashes}")
        finally:
            for c in children.values(): c.close()
        meta={"run_config":config,"started_utc":json.load(open(meta_path)).get("started_utc"),
              "finished_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}; atomic_json(meta_path,meta)
        print(json.dumps({"status":"complete","journal":str(journal_path),"metadata":str(meta_path)},indent=2))
    finally:
        if lockfile: lockfile.close()

if __name__=="__main__":
    try: main()
    except Exception as e:
        if RUN_RESULT is not None:
            p=RUN_RESULT/"failure.log"
            with open(p,"a") as f:
                f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())+"\n")
                f.write("command: "+shlex.join([sys.executable,*sys.argv])+"\n")
                f.write(f"error: {type(e).__name__}: {e}\n\n")
        print(f"matched benchmark failed: {e}",file=sys.stderr);sys.exit(2)
