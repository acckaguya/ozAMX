#!/usr/bin/env python3
"""Build, gate, and matched-benchmark the current working-tree main release under one flock."""
import fcntl,hashlib,json,os,pathlib,shlex,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[5]
OUT=pathlib.Path(__file__).resolve().parent
LOCK=pathlib.Path('/tmp/ozamx-perf.lock')
RUNNER=ROOT/'bench/8454h/roofline_v4/matched_calls/run_matched_runtime.py'
GATE=OUT/'source/tools/run_binary_gate_v4.py'
FROZEN=ROOT/'bench/8454h/versions/v3_release/artifacts/libozamx_v3.a'
BUILD=OUT/'build'

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(4<<20),b''):h.update(c)
 return h.hexdigest()
def logrun(name,cmd,env=None):
 p=OUT/'logs'/f'{name}.log';p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w') as f:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,text=True)
 rec={'name':name,'command':cmd,'returncode':r.returncode,'log':str(p)}
 progress.append(rec);atomic_progress()
 if r.returncode:raise RuntimeError(f'{name} failed ({r.returncode}); inspect {p}')
def atomic_progress():
 p=OUT/'progress.json.tmp';p.write_text(json.dumps({'status':'running','steps':progress},indent=2)+'\n');p.replace(OUT/'progress.json')
def main():
 global progress
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'logs').mkdir(exist_ok=True)
 sources=['CMakeLists.txt','src/gemm.cpp','src/runtime.cpp','src/kernels.S','include/ozamx/gemm.hpp','bench/benchmark.cpp']
 sourcehash={p:sha(ROOT/p) for p in sources}
 (OUT/'source_fingerprint_before.json').write_text(json.dumps({'root':str(ROOT),'files':sourcehash},indent=2)+'\n')
 if sha(FROZEN)!='73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c':raise RuntimeError('frozen V3 library hash mismatch')
 progress=[];lock=LOCK.open('a+');fcntl.flock(lock,fcntl.LOCK_EX)
 try:
  env=os.environ.copy();env.update({'OMP_NUM_THREADS':'64','OMP_DYNAMIC':'FALSE','OMP_PLACES':'cores','OMP_PROC_BIND':'close','MKL_NUM_THREADS':'64','MKL_DYNAMIC':'FALSE','MKL_THREADING_LAYER':'GNU','MKL_INTERFACE_LAYER':'LP64','OZAMX_WORKSPACE_CACHE_BYTES':'2147483648'});env.pop('OMP_WAIT_POLICY',None);env.pop('GOMP_SPINCOUNT',None)
  logrun('cmake_configure',['cmake','-S',str(ROOT),'-B',str(BUILD),'-DCMAKE_BUILD_TYPE=Release','-DBUILD_TESTING=ON','-DOZAMX_BUILD_PROBE=OFF'],env)
  logrun('cmake_build',['cmake','--build',str(BUILD),'--parallel','24'],env)
  logrun('ctest',['ctest','--test-dir',str(BUILD),'--output-on-failure','--parallel','1'],env)
  lib=BUILD/'libozamx.a'
  if not lib.is_file():raise RuntimeError('current main static library not produced')
  (OUT/'candidate_library.json').write_text(json.dumps({'path':str(lib),'sha256':sha(lib),'frozen_v3_path':str(FROZEN),'frozen_v3_sha256':sha(FROZEN)},indent=2)+'\n')
  logrun('binary_gate_all23',[sys.executable,str(GATE),'--candidate-library',str(lib),'--output',str(OUT/'gate_all23.json'),'--lock-held'],env)
  # Full output equality plus transaction status is part of gate output.
  gate=json.load(open(OUT/'gate_all23.json'))
  if gate.get('status')!='pass' or len(gate.get('cases',[]))!=23:raise RuntimeError('expected all 23 full-output gate cases to pass')
  # Runtime-default interleaved V3 comparisons: new compact-wide target sizes, fallback, and FP64 regression.
  matrix=[]
  for n in (4096,8192):matrix.append(('fp32',6,n,11))
  matrix.append(('fp32',6,16384,5))
  for precision,budget in [('fp32',6),('fp64',6),('fp64',10),('fp64',15),('fp64',21)]:matrix.append((precision,budget,1024,7))
  for precision,budget,n,reps in matrix:
   tag=f'main_{precision}_p{budget}_n{n}_r{reps}';dest=OUT/'matched'/tag
   if dest.exists() and any(dest.iterdir()):raise RuntimeError(f'refusing to reuse existing matched directory {dest}')
   cmd=[sys.executable,str(RUNNER),'--lock-held','--wait-policy','runtime','--control-lib',str(FROZEN),'--candidate-lib',str(lib),'--candidate-tag','main_current_compactwide','--result-dir',str(dest),'--sizes',str(n),'--reps',str(reps),'--warmups','1','--precision',precision]
   if precision=='fp64':cmd.extend(['--budget',str(budget)])
   logrun(tag,cmd,env)
  # oneMKL is measured separately with its established driver; never presented as interleaved.
  mkl=BUILD/'ozamx_benchmark'
  if not mkl.is_file():raise RuntimeError('oneMKL benchmark target missing after build')
  mklenv=env.copy();mklenv.update({'OMP_WAIT_POLICY':'PASSIVE','GOMP_SPINCOUNT':'0'})
  cmd=[str(mkl),'--sizes','4096,8192','--threads','64','--reps','3','--seed','260904','--precision','all','--budgets','6,10,15,21','--distribution','uniform','--output',str(OUT/'onemkl_separate.csv'),'--checkpoint',str(OUT/'onemkl_checkpoint')]
  logrun('onemkl_separate',cmd,mklenv)
 finally:
  lock.close()
 after={p:sha(ROOT/p) for p in sources}
 (OUT/'source_fingerprint_after.json').write_text(json.dumps({'root':str(ROOT),'files':after,'unchanged':after==sourcehash},indent=2)+'\n')
 if after!=sourcehash:raise RuntimeError('source changed during validation campaign; result fingerprint is invalid')
 (OUT/'progress.json').write_text(json.dumps({'status':'complete','steps':progress,'candidate_sha256':sha(BUILD/'libozamx.a')},indent=2)+'\n')
 print(json.dumps({'status':'complete','steps':len(progress),'candidate_library':str(BUILD/'libozamx.a'),'candidate_sha256':sha(BUILD/'libozamx.a'),'output':str(OUT)},indent=2))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(f'validation failed: {type(e).__name__}: {e}',file=sys.stderr);sys.exit(2)
