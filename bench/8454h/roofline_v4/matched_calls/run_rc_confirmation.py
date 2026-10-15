#!/usr/bin/env python3
"""Independent RC1 confirmation: runtime-default matched trials under one performance lock."""
import fcntl,json,pathlib,subprocess,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[3]
LOCK=pathlib.Path('/tmp/ozamx-perf.lock')
CONTROL=ROOT/'bench/8454h/versions/v3_release/artifacts/libozamx_v3.a'
CANDIDATE=ROOT/'bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/build/libozamx.a'
OUT=HERE/'results'/'rc1_independent_confirmation_20261014'
RUNNER=HERE/'run_matched_runtime.py'
EXPECTED='2a3e5533fbd5397df2c44284a7a7da54b0463558e36f8f9f284b210831c80695'
def sha(p):
 import hashlib
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 if sha(CANDIDATE)!=EXPECTED:raise SystemExit('RC1 library SHA-256 mismatch')
 # Preserve startup resource range before acquiring the serialized benchmark slot.
 cp=subprocess.run(['bash','-lc','free -h; df -h /tmp'],capture_output=True,text=True)
 (OUT/'startup_resources.txt').write_text(cp.stdout+'\n'+cp.stderr)
 lock=open(LOCK,'a+');fcntl.flock(lock,fcntl.LOCK_EX)
 matrix=[]
 try:
  for precision in ('fp32','fp64'):
   for n in (4096,8192,16384):matrix.append((precision,6,n,11))
  progress=[]
  for i,(precision,budget,n,reps) in enumerate(matrix,1):
   runid=f'rc1_{precision}_p{budget}_n{n}_r{reps}'
   dest=OUT/runid
   if dest.exists() and any(dest.iterdir()):raise SystemExit(f'refusing to reuse existing output directory: {dest}')
   cmd=[sys.executable,str(RUNNER),'--lock-held','--wait-policy','runtime','--control-lib',str(CONTROL),'--candidate-lib',str(CANDIDATE),'--candidate-tag','rc1_geom256_independent','--result-dir',str(dest),'--sizes',str(n),'--reps',str(reps),'--warmups','1','--precision',precision]
   if precision=='fp64':cmd.extend(['--budget',str(budget)])
   dest.mkdir(parents=True,exist_ok=True)
   (dest/'command.txt').write_text(' '.join(cmd)+'\n')
   print(f'[{i}/{len(matrix)}] {runid}',flush=True)
   r=subprocess.run(cmd,cwd=ROOT)
   progress.append({'run_id':runid,'returncode':r.returncode,'finished_unix':time.time()})
   t=OUT/'progress.json.tmp';t.write_text(json.dumps({'progress':progress},indent=2)+'\n');t.replace(OUT/'progress.json')
   if r.returncode:raise SystemExit(f'failed: {dest}; inspect failure.log')
 finally:lock.close()
 print(f'completed {len(progress)} configs: {OUT}')
if __name__=='__main__':main()
