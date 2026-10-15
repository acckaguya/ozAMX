#!/usr/bin/env python3
"""No-OpenMP build/CTest and eligible-shape binary gate."""
import fcntl,hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[5];OUT=pathlib.Path(__file__).resolve().parent;LOCK=pathlib.Path('/tmp/ozamx-perf.lock')
BUILD=OUT/'build_noomp';GATE=OUT/'source/tools/run_binary_gate_v4.py';LOG=OUT/'logs'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def run(name,cmd,env):
 with (LOG/f'{name}.log').open('w') as f:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,text=True)
 rec['steps'].append({'name':name,'command':cmd,'returncode':r.returncode,'log':str(LOG/f'{name}.log')});(OUT/'noomp_validation.json').write_text(json.dumps(rec,indent=2)+'\n')
 if r.returncode:raise RuntimeError(f'{name} failed; see log')
def main():
 LOG.mkdir(exist_ok=True);lock=open(LOCK,'a+');fcntl.flock(lock,fcntl.LOCK_EX)
 try:
  env=os.environ.copy();env.update({'OMP_NUM_THREADS':'1','OMP_DYNAMIC':'FALSE','OMP_PLACES':'cores','OMP_PROC_BIND':'close','GATE_THREADS':'1','MKL_NUM_THREADS':'1','MKL_DYNAMIC':'FALSE'})
  global rec;rec={'status':'running','steps':[],'source_sha256':{'gemm.cpp':sha(ROOT/'src/gemm.cpp'),'CMakeLists.txt':sha(ROOT/'CMakeLists.txt')}}
  run('cmake_configure_noomp',['cmake','-S',str(ROOT),'-B',str(BUILD),'-DCMAKE_BUILD_TYPE=Release','-DBUILD_TESTING=ON','-DOZAMX_BUILD_PROBE=OFF','-DOZAMX_ENABLE_OPENMP=OFF'],env)
  run('cmake_build_noomp',['cmake','--build',str(BUILD),'--parallel','24'],env)
  run('ctest_noomp',['ctest','--test-dir',str(BUILD),'--output-on-failure','--parallel','1'],env)
  lib=BUILD/'libozamx.a';rec['candidate_library']={'path':str(lib),'sha256':sha(lib)}
  run('noomp_full_output_eligible_fp32_4096',['/usr/bin/python3',str(GATE),'--candidate-library',str(lib),'--output',str(OUT/'noomp_eligible_gate.json'),'--case-ids','1','--lock-held'],env)
  gate=json.load(open(OUT/'noomp_eligible_gate.json'))
  if gate.get('status')!='pass' or len(gate.get('cases',[]))!=1:raise RuntimeError('no-OpenMP FP32 4096 cube full-output gate failed')
  rec['status']='complete';rec['full_output_sha256']=gate['cases'][0]['full_output_sha256'];(OUT/'noomp_validation.json').write_text(json.dumps(rec,indent=2)+'\n')
  print(json.dumps({'status':'complete','candidate_sha256':sha(lib),'gate':rec['full_output_sha256']}))
 finally:lock.close()
if __name__=='__main__':main()
