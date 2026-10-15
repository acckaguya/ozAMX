#!/usr/bin/env python3
"""Capture whitelisted oneMKL dispatch env and run an excluded N=256 raw-BF16 verbose diagnostic."""
import fcntl,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[5];OUT=pathlib.Path(__file__).resolve().parent/'onemkl_verbose_diagnostic';LOCK=pathlib.Path('/tmp/ozamx-perf.lock')
SRC=ROOT/'bench/raw_bf16.cpp';MKL=ROOT/'third_party/code/mkl-current';WHITELIST=('MKL_ENABLE_INSTRUCTIONS','MKL_CBWR','MKL_VERBOSE','OMP_WAIT_POLICY','GOMP_SPINCOUNT')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 OUT.mkdir(parents=True,exist_ok=True);lock=open(LOCK,'a+');fcntl.flock(lock,fcntl.LOCK_EX)
 try:
  env=os.environ.copy();inherited={k:env.get(k) for k in WHITELIST}
  env.update({'MKL_VERBOSE':'1','MKL_THREADING_LAYER':'GNU','MKL_NUM_THREADS':'64','MKL_DYNAMIC':'FALSE','OMP_NUM_THREADS':'64','OMP_DYNAMIC':'FALSE','OMP_WAIT_POLICY':'PASSIVE','GOMP_SPINCOUNT':'0'})
  effective={k:env.get(k) for k in WHITELIST}
  mkl_lib=MKL/'lib';bin=OUT/'raw_bf16_verbose'
  cmd=['g++','-std=c++17','-O3','-Wall','-Wextra',f'-I{MKL/"include"}',str(SRC),str(mkl_lib/'libmkl_rt.so.3'),f'-Wl,-rpath,{mkl_lib}','-ldl','-o',str(bin)]
  with (OUT/'build.log').open('w') as f:cp=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,text=True)
  if cp.returncode:raise RuntimeError('raw BF16 diagnostic build failed')
  run=['taskset','-c','0-63',str(bin),'--sizes','256','--threads','64','--reps','1','--seed','260904','--output',str(OUT/'raw_bf16.csv')]
  with (OUT/'mkl_verbose.log').open('w') as f:rp=subprocess.run(run,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,text=True)
  rec={'status':'pass' if rp.returncode==0 else 'fail','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'diagnostic only; excluded from all quiet timing summaries','source':str(SRC),'source_sha256':sha(SRC),'binary':str(bin),'binary_sha256':sha(bin),'build_command':cmd,'run_command':run,'exit_code':rp.returncode,'mkl_root':str(MKL),'runtime':str(mkl_lib/'libmkl_rt.so.3'),'runtime_sha256':sha(mkl_lib/'libmkl_rt.so.3'),'whitelist':list(WHITELIST),'inherited_values_before_diagnostic_overrides':inherited,'effective_values_for_verbose_diagnostic':effective,'explicit_runtime_settings':{'MKL_THREADING_LAYER':'GNU','MKL_NUM_THREADS':'64','MKL_DYNAMIC':'FALSE','OMP_NUM_THREADS':'64','OMP_DYNAMIC':'FALSE'},'quiet_baseline_environment_note':'The original separate 3-repetition quiet run did not persist this five-key environment snapshot. Its explicit wrapper settings OMP_WAIT_POLICY=PASSIVE and GOMP_SPINCOUNT=0 are known; the other three inherited values cannot be reconstructed exactly after the fact. This diagnostic records its own effective values.','csv':str(OUT/'raw_bf16.csv'),'verbose_log':str(OUT/'mkl_verbose.log')}
  (OUT/'metadata.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
  if rp.returncode:raise RuntimeError('verbose diagnostic execution failed')
  import csv
  rows=list(csv.DictReader(open(OUT/'raw_bf16.csv')))
  if len(rows)!=1 or rows[0]['routine']!='raw_mkl_bf16bf16fp32' or rows[0]['N']!='256' or rows[0]['repetitions']!='1' or rows[0]['status']!='ok':raise RuntimeError('raw BF16 one-call CSV schema/value mismatch')
  rec['result_row']=rows[0];(OUT/'metadata.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
  print(json.dumps({'status':rec['status'],'csv':rec['csv'],'verbose_log':rec['verbose_log'],'metadata':str(OUT/'metadata.json')}))
 finally:lock.close()
if __name__=='__main__':main()
