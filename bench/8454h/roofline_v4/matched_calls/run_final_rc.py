#!/usr/bin/env python3
"""Run the adaptive release-candidate matched confirmation matrix under one flock."""
import fcntl, pathlib, subprocess, sys, time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
LOCK=pathlib.Path('/tmp/ozamx-perf.lock')
CONTROL=ROOT/'bench/8454h/versions/v3_release/artifacts/libozamx_v3.a'
CANDIDATES={
 'rc1_geom256': ROOT/'bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_20261014T122531Z/build/libozamx.a',
 'rc2_geom512': ROOT/'bench/8454h/roofline_v4/adaptive_release_runs/adaptive_geom_n512_20261014T134200Z/build/libozamx.a',
}
OUT=HERE/'results'/'final_rc_20261014'
RUNNER=HERE/'run_matched_runtime.py'
def main():
 for tag,p in CANDIDATES.items():
  if not p.is_file(): raise SystemExit(f'missing library {tag}: {p}')
 OUT.mkdir(parents=True,exist_ok=True)
 fd=open(LOCK,'a+'); fcntl.flock(fd,fcntl.LOCK_EX)
 matrix=[]
 try:
  # F32 large confirmation for both RCs; FP64 p6 large confirmation for RC1.
  for tag in ('rc1_geom256','rc2_geom512'):
   for n in (4096,8192):
    matrix.append((tag,'fp32',6,[n],11))
  for n in (4096,8192): matrix.append(('rc1_geom256','fp64',6,[n],11))
  # N=1024 regression sweep: both precisions and all four F64 budgets.
  for tag in ('rc1_geom256','rc2_geom512'):
   matrix.append((tag,'fp32',6,[1024],7))
   for b in (6,10,15,21): matrix.append((tag,'fp64',b,[1024],7))
  journal=[]
  for index,(tag,precision,budget,sizes,reps) in enumerate(matrix,1):
   runid=f'{tag}_{precision}_p{budget}_n{"_".join(map(str,sizes))}_r{reps}'
   dest=OUT/runid
   if (dest/'matched_calls.json').exists() or (dest/'metadata.json').exists():
    raise SystemExit(f'refusing to reuse existing result directory: {dest}')
   cmd=[sys.executable,str(RUNNER),'--lock-held','--wait-policy','runtime','--control-lib',str(CONTROL),
        '--candidate-lib',str(CANDIDATES[tag]),'--candidate-tag',tag,'--result-dir',str(dest),
        '--sizes',*map(str,sizes),'--reps',str(reps),'--warmups','1','--precision',precision]
   if precision=='fp64':cmd.extend(['--budget',str(budget)])
   print(f'[{index}/{len(matrix)}] {runid}',flush=True)
   with open(OUT/f'{runid}.command.txt','w') as f:f.write(' '.join(cmd)+'\n')
   cp=subprocess.run(cmd,cwd=ROOT)
   journal.append({'runid':runid,'returncode':cp.returncode,'finished_unix':time.time()})
   (OUT).mkdir(parents=True,exist_ok=True)
   import json
   tmp=OUT/'orchestrator_progress.json.tmp';tmp.write_text(json.dumps({'matrix':journal},indent=2)+'\n');tmp.replace(OUT/'orchestrator_progress.json')
   if cp.returncode: raise SystemExit(f'run failed ({cp.returncode}): {dest}; see failure.log')
 finally:
  fd.close()
 print(f'completed {len(journal)} matched runs in {OUT}')
if __name__=='__main__':main()
