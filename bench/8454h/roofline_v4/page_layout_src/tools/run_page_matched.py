#!/usr/bin/env python3
"""Interleaved matched calls for the page-layout candidates against frozen V3."""
from __future__ import annotations
import argparse,fcntl,hashlib,json,pathlib,subprocess,sys,time

SRC=pathlib.Path(__file__).resolve().parents[1]
REPO=SRC.parents[3]
HERE=REPO/"bench/8454h/roofline_v4/matched_calls"
RUNNER=HERE/"run_matched_runtime.py"
DRIVER=HERE/"driver.cpp"
LOCK=pathlib.Path("/tmp/ozamx-perf.lock")
CONTROL=REPO/"bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
CONTROL_SHA="73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
PAGE_RUN=REPO/"bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z"
CANDIDATES={
 "a2m_hint1":{"path":PAGE_RUN/"builds/a2m_hint1/libozamx.a","sha":"91ce6bdf48976cc5f9a60db6b15f7861547099060341fc9a57bc6652aa9fbfd4","sizes":[1024,4096,8192]},
 "a4k_hint1":{"path":PAGE_RUN/"builds/a4k_hint1/libozamx.a","sha":"dbec090534a1c920ebc533e4a5394c1a0a7b83582526ea1d7362f9f43face1af","sizes":[8192]},
}
WORKLOADS=[("fp32",None),("fp64",6),("fp64",10),("fp64",15),("fp64",21)]
REPS=11;WARMUPS=1

def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open("rb") as f:
  for b in iter(lambda:f.read(4*1024*1024),b""):h.update(b)
 return h.hexdigest()
def utc():return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
def atomic(path,obj):
 tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n");tmp.replace(path)
def completed(dest,sizes,precision,budget):
 j=dest/"matched_calls.json"
 if not j.is_file():return False
 try:d=json.loads(j.read_text())
 except Exception:return False
 cfgs=d.get("configurations",{})
 for n in sizes:
  key=f"{precision}_n{n}_b{budget if precision=='fp64' else 6}"
  x=cfgs.get(key)
  if not x or x.get("complete") is not True or x.get("byte_exact_match") is not True or len(x.get("samples",[]))!=REPS:return False
  if x.get("output_sha256",{}).get("control")!=x.get("output_sha256",{}).get("candidate"):return False
 return True

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--out",type=pathlib.Path);ap.add_argument("--resume",type=pathlib.Path)
 a=ap.parse_args()
 if a.resume and a.out:ap.error("choose --out or --resume")
 if a.resume:
  out=a.resume.resolve()
  if not (out/"campaign.json").is_file():ap.error("resume directory has no campaign.json")
  state=json.loads((out/"campaign.json").read_text())
  if state.get("status") not in ("running","interrupted","failed"):ap.error(f"cannot resume status={state.get('status')}")
  if state.get("runner_sha256")!=sha(RUNNER) or state.get("driver_sha256")!=sha(DRIVER):raise RuntimeError("matched harness source changed since partial campaign")
 else:
  out=(a.out.resolve() if a.out else REPO/"bench/8454h/roofline_v4/page_layout_matched_runs"/f"page_matched_runtime_{time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())}")
  out.mkdir(parents=True,exist_ok=False)
  if sha(CONTROL)!=CONTROL_SHA:raise RuntimeError("immutable V3 archive SHA mismatch")
  page=json.loads((PAGE_RUN/"dataset.json").read_text())
  if page.get("status")!="complete":raise RuntimeError("page screen dataset is not complete")
  entries={x["label"]:x for x in page.get("completed_candidates",[])}
  for tag,c in CANDIDATES.items():
   p=c["path"]
   if not p.is_file() or sha(p)!=c["sha"] or entries.get(tag,{}).get("library_sha256")!=c["sha"]:raise RuntimeError(f"candidate identity mismatch for {tag}")
   gate=json.loads((PAGE_RUN/"gates"/f"{tag}_full.json").read_text())
   if gate.get("status")!="pass" or len(gate.get("cases",[]))!=20 or gate.get("candidate_library_sha256")!=c["sha"]:raise RuntimeError(f"candidate has no exact-SHA 20-case gate: {tag}")
  state={"schema":"ozamx-page-layout-matched-campaign-1","status":"waiting_for_global_lock","created_utc":utc(),"lock_path":str(LOCK),
   "control_library":str(CONTROL),"control_library_sha256":CONTROL_SHA,
   "candidates":{k:{"library":str(v["path"]),"library_sha256":v["sha"],"sizes":v["sizes"],"prior_gate":str(PAGE_RUN/"gates"/f"{k}_full.json")} for k,v in CANDIDATES.items()},
   "protocol":{"runner":str(RUNNER),"runner_sha256":sha(RUNNER),"driver":str(DRIVER),"driver_sha256":sha(DRIVER),"precision_budget_workloads":[{"precision":p,"budget":b or 6} for p,b in WORKLOADS],"repetitions":REPS,"warmups":WARMUPS,"wait_policy":"GNU runtime defaults; OMP_WAIT_POLICY and GOMP_SPINCOUNT unset","parent_inter_call_pause_seconds":0.020,"thread_count":64,"cpuset":"0-63","omp_places":"cores","omp_proc_bind":"close","workspace_cache_bytes":2147483648,"repeated_gate":False,
    "validation":"same deterministic full input FNVs each paired call; dump entire output C and compare SHA-256; verify exactly 64 workers occupy CPUs 0-63"},"runs":[]}
  atomic(out/"campaign.json",state)
 print(f"WAITING for exclusive lock: {out}",flush=True)
 fd=LOCK.open("a+");wait0=time.time();fcntl.flock(fd,fcntl.LOCK_EX);acquired=time.time()
 state["status"]="running";state["lock_wait_started_utc"]=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(wait0));state["lock_acquired_utc"]=utc();state["lock_wait_seconds"]=acquired-wait0;atomic(out/"campaign.json",state)
 print(f"LOCK ACQUIRED after {acquired-wait0:.1f}s",flush=True)
 try:
  total=len(CANDIDATES)*len(WORKLOADS);index=0
  for tag,c in CANDIDATES.items():
   for precision,budget in WORKLOADS:
    index+=1;sizes=c["sizes"]
    runid=f"{tag}_{precision}_p{budget or 6}_n{'_'.join(map(str,sizes))}_r{REPS}"
    dest=out/runid;dest.mkdir(parents=True,exist_ok=True)
    if completed(dest,sizes,precision,budget):
     print(f"[{index}/{total}] reuse complete {runid}",flush=True)
     entry={"runid":runid,"candidate":tag,"precision":precision,"budget":budget or 6,"sizes":sizes,"repetitions":REPS,"status":"reused_complete","journal":str(dest/"matched_calls.json")}
    else:
     cmd=[sys.executable,str(RUNNER),"--lock-held","--wait-policy","runtime","--control-lib",str(CONTROL),"--candidate-lib",str(c["path"]),
       "--candidate-tag",tag,"--result-dir",str(dest),"--sizes",*map(str,sizes),"--reps",str(REPS),"--warmups",str(WARMUPS),"--precision",precision]
     if precision=="fp64":cmd += ["--budget",str(budget)]
     if (dest/"matched_calls.json").exists() or (dest/"metadata.json").exists():cmd.append("--resume")
     print(f"[{index}/{total}] {runid}",flush=True);(dest/"command.json").write_text(json.dumps(cmd,indent=2)+"\n")
     cp=subprocess.run(cmd,cwd=REPO)
     entry={"runid":runid,"candidate":tag,"precision":precision,"budget":budget or 6,"sizes":sizes,"repetitions":REPS,"returncode":cp.returncode,"finished_utc":utc(),"journal":str(dest/"matched_calls.json")}
     if cp.returncode:state["runs"].append(entry);state["status"]="failed";state["failure"]={"runid":runid,"returncode":cp.returncode};state["updated_utc"]=utc();atomic(out/"campaign.json",state);raise RuntimeError(f"matched run failed: {runid}; see {dest}")
     if not completed(dest,sizes,precision,budget):raise RuntimeError(f"matched run lacks complete/hash-equal checkpoints: {runid}")
     entry["status"]="complete"
    state["runs"].append(entry);state["updated_utc"]=utc();atomic(out/"campaign.json",state)
  state["status"]="complete";state["completed_utc"]=utc();state["source_hashes_at_completion"]={"runner":sha(RUNNER),"driver":sha(DRIVER)};atomic(out/"campaign.json",state)
  print(f"COMPLETE matched page-layout campaign: {out}",flush=True)
 except Exception as e:
  if state.get("status")=="running":state["status"]="failed";state["failure"]=repr(e);state["failed_utc"]=utc();atomic(out/"campaign.json",state)
  raise
 finally:fd.close()

if __name__=="__main__":main()
