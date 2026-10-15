#!/usr/bin/env python3
"""Run complete gates and interleaved matched calls for the two selected geometries."""
import fcntl, hashlib, json, os, pathlib, shlex, subprocess, sys, time

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
LOCK=pathlib.Path("/tmp/ozamx-perf.lock")
V3=ROOT/"bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
GATE=ROOT/"bench/8454h/roofline_v4/recon_ilp_src/tools/run_binary_gate_v4.py"
RUNNER=HERE/"run_matched.py"
CANDIDATES={
 "b2_m256_n256":ROOT/"bench/8454h/roofline_v4/search_runs/screen_20261014_20261014T094029Z_retry2/builds/stage1_15_b2_m256_n256_p64_h1_l1__mode3_b2_m256_n256_p64_h1_l1/libozamx.a",
 "b2_m256_n512":ROOT/"bench/8454h/roofline_v4/search_runs/screen_20261014_20261014T094029Z_retry2/builds/stage1_16_b2_m256_n512_p64_h1_l1__mode3_b2_m256_n512_p64_h1_l1/libozamx.a",
}
SIZES=[1024,4096,8192]
REPS=7
FROZEN_SHA="73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for block in iter(lambda:f.read(4*1024*1024),b""):h.update(block)
 return h.hexdigest()

def atomic_json(path,obj):
 tmp=path.with_suffix(path.suffix+".tmp")
 with open(tmp,"w") as f:json.dump(obj,f,indent=2,sort_keys=True);f.write("\n");f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def invoke(cmd,log,cwd):
 with open(log,"w") as f:
  f.write("command: "+shlex.join(map(str,cmd))+"\n\n");f.flush()
  p=subprocess.run(list(map(str,cmd)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,text=True)
 return p.returncode

def main():
 stamp=time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())
 result=HERE/"results"/f"formal_{stamp}_{os.getpid()}"
 result.mkdir(parents=True,exist_ok=False);logs=result/"logs";logs.mkdir()
 manifest={"status":"running","started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
           "control_library":str(V3),"control_library_sha256":sha(V3),"required_control_sha256":FROZEN_SHA,
           "candidate_libraries":{k:{"path":str(v),"sha256":sha(v) if v.is_file() else None} for k,v in CANDIDATES.items()},
           "sizes":SIZES,"timed_repetitions":REPS,"warmups":1,
           "matched_workloads":[{"precision":"fp32","budget":None}]+[{"precision":"fp64","budget":b} for b in (6,10,15,21)],
           "matched_settings":{"threads":64,"pin":"0-63","OMP_WAIT_POLICY":"PASSIVE","GOMP_SPINCOUNT":"0","OZAMX_WORKSPACE_CACHE_BYTES":"2147483648"},
           "gate_runner":str(GATE),"gate_case_count":20,"candidates":{}}
 atomic_json(result/"campaign.json",manifest)
 lock=None
 try:
  if manifest["control_library_sha256"]!=FROZEN_SHA:raise RuntimeError("V3 archive SHA mismatch")
  for name,lib in CANDIDATES.items():
   if not lib.is_file():raise RuntimeError(f"candidate archive missing: {lib}")
  lock=LOCK.open("a+");fcntl.flock(lock,fcntl.LOCK_EX)
  for tag,lib in CANDIDATES.items():
   entry={"library":str(lib),"library_sha256":sha(lib),"gate":None,"matched":{}}
   manifest["candidates"][tag]=entry;atomic_json(result/"campaign.json",manifest)
   gate_json=result/f"gate_{tag}.json"
   gate_cmd=[sys.executable,str(GATE),"--candidate-library",str(lib),"--output",str(gate_json),"--lock-held"]
   rc=invoke(gate_cmd,logs/f"gate_{tag}.log",ROOT)
   if rc:raise RuntimeError(f"20-case full-output gate failed for {tag}, rc={rc}; see {logs/f'gate_{tag}.log'}")
   gate=json.load(open(gate_json))
   entry["gate"]={"path":str(gate_json),"status":gate.get("status"),"cases":len(gate.get("cases",[])),"candidate_library_sha256":gate.get("candidate_library_sha256")}
   atomic_json(result/"campaign.json",manifest)
   if gate.get("status")!="pass" or len(gate.get("cases",[]))!=20 or not all(c.get("pass") for c in gate["cases"]):
    raise RuntimeError(f"full gate JSON is not a 20-case pass for {tag}: {entry['gate']}")
   for precision,budget in (("fp32",None),("fp64",6),("fp64",10),("fp64",15),("fp64",21)):
    workload="fp32" if budget is None else f"fp64_p{budget}"
    out=result/tag/workload
    cmd=[sys.executable,str(RUNNER),"--control-lib",str(V3),"--candidate-lib",str(lib),
         "--candidate-tag",f"{tag}_{workload}","--result-dir",str(out),"--sizes",*map(str,SIZES),
         "--reps",str(REPS),"--warmups","1","--precision",precision,"--lock-held"]
    if budget is not None:cmd.extend(["--budget",str(budget)])
    rc=invoke(cmd,logs/f"matched_{tag}_{workload}.log",ROOT)
    if rc:raise RuntimeError(f"matched run failed for {tag}/{workload}, rc={rc}; see {logs/f'matched_{tag}_{workload}.log'}")
    journal_path=out/"matched_calls.json"
    journal=json.load(open(journal_path))
    configs=journal.get("configurations",{})
    if len(configs)!=len(SIZES) or not all(c.get("complete") and c.get("byte_exact_match") for c in configs.values()):
     raise RuntimeError(f"missing or mismatched configuration output for {tag}/{workload}")
    entry["matched"][workload]={"path":str(journal_path),"metadata":str(out/"metadata.json"),"configs":len(configs),"status":"pass"}
    atomic_json(result/"campaign.json",manifest)
  manifest["status"]="pass";manifest["finished_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
  atomic_json(result/"campaign.json",manifest)
  print(json.dumps({"status":"pass","campaign":str(result/"campaign.json")},indent=2))
 except Exception as e:
  manifest["status"]="failed";manifest["failure"]=f"{type(e).__name__}: {e}";manifest["finished_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
  atomic_json(result/"campaign.json",manifest)
  with open(result/"failure.log","a") as f:f.write(f"{type(e).__name__}: {e}\n")
  raise
 finally:
  if lock:lock.close()

if __name__=="__main__":
 try:main()
 except Exception as e:print(f"formal matched campaign failed: {e}",file=sys.stderr);sys.exit(2)
