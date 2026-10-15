#!/usr/bin/env python3
from __future__ import annotations
import csv, fcntl, hashlib, json, os, pathlib, re, shutil, statistics, subprocess, sys, time
RUN=pathlib.Path(__file__).resolve().parent
ROOT=RUN.parents[4]
SRC=ROOT/'bench/8454h/roofline_v4/kernel_schedule_src'
V3=ROOT/'bench/8454h/versions/v3_release/artifacts/libozamx_v3.a'
MKL=ROOT/'third_party/code/mkl-current'
LOCK=pathlib.Path('/tmp/ozamx-perf.lock')
GATE=SRC/'tools/run_binary_gate_v4.py'
MATCHED=ROOT/'bench/8454h/roofline_v4/matched_calls/run_matched_runtime.py'
TUNING=['-DCMAKE_BUILD_TYPE=Release','-DOZAMX_ENABLE_OPENMP=ON','-DOZAMX_BUILD_PROBE=ON',f'-DOZAMX_ONEMKL_ROOT={MKL}',
 '-DOZAMX_CACHE_BLOCK=128','-DOZAMX_PREP_GRAIN=16384','-DOZAMX_MIN_COMPUTE_WORK=8','-DOZAMX_TILELOAD_HINT=1',
 '-DOZAMX_LOAD_SCHEDULE=0','-DOZAMX_LOOP_ORDER=0','-DOZAMX_MN_ORDER=0']
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def exec_log(label,argv,env):
 log=RUN/'logs'/f'{label}.log'
 with log.open('wb') as f:p=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,env=env)
 step={'label':label,'argv':[str(x) for x in argv],'exit_code':p.returncode,'log':str(log.relative_to(RUN))}
 state['steps'].append(step);save();
 if p.returncode:raise RuntimeError(f'{label} exited {p.returncode}; see {log}')
 return step
def save(): (RUN/'validation_state.json').write_text(json.dumps(state,indent=2)+'\n')
def body_bytes(out):
 mark='<ozamx_bf16_product>:'
 if mark not in out: raise RuntimeError('objdump lacks ozamx_bf16_product')
 body=out.split(mark,1)[1].split('\n\n',1)[0]
 return [m.group(1).replace(' ','') for line in body.splitlines() if (m:=re.match(r'^\s*[0-9a-f]+:\s*((?:[0-9a-f]{2}\s+)+)',line))]
def main():
 global state
 if not SRC.is_dir():raise RuntimeError(f'missing source {SRC}')
 source_id=json.loads((SRC/'SOURCE_IDENTITY.json').read_text())
 env=dict(os.environ)
 env.update({'OMP_NUM_THREADS':'64','OMP_PLACES':'cores','OMP_PROC_BIND':'close','OMP_DYNAMIC':'FALSE','MKL_NUM_THREADS':'64','MKL_DYNAMIC':'FALSE','MKL_THREADING_LAYER':'GNU','MKL_INTERFACE_LAYER':'LP64','OZAMX_WORKSPACE_CACHE_BYTES':'2147483648','LD_LIBRARY_PATH':str(MKL/'lib')+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')})
 state={'schema':'ozamx-v4-kernel-schedule-validation-1','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_tree':str(SRC),'source_identity_sha256':sha(SRC/'SOURCE_IDENTITY.json'),'kernel_asm_sha256':sha(SRC/'src/kernels.S'),'frozen_v3_library':str(V3),'frozen_v3_library_sha256':sha(V3),'mkl_runtime':str(MKL/'lib/libmkl_rt.so.3'),'mkl_runtime_sha256':sha(MKL/'lib/libmkl_rt.so.3'),'status':'running','steps':[],'variants':{},'matched':[]}
 save()
 with LOCK.open('a') as lf:
  fcntl.flock(lf,fcntl.LOCK_EX);state['lock_acquired_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save()
  for group in (0,1,2):
   build=RUN/f'build_group{group}';tag=f'group{group}'
   cm=['cmake','-S',str(SRC),'-B',str(build),*TUNING,f'-DOZV4_LOAD_GROUP={group}']
   exec_log(f'{tag}_configure',cm,env)
   exec_log(f'{tag}_build',['cmake','--build',str(build),'-j2'],env)
   lib=build/'libozamx.a'
   if not lib.is_file():raise RuntimeError(f'missing candidate library {lib}')
   # Keep a generated disassembly and compare the assembled schedule bytes.
   dis=RUN/'disassembly'/f'{tag}_bf16_product.txt'
   with dis.open('wb') as f:p=subprocess.run(['objdump','-d','-M','intel','--disassemble=ozamx_bf16_product',str(lib)],stdout=f,stderr=subprocess.STDOUT)
   if p.returncode:raise RuntimeError(f'objdump failed for group {group}')
   state['variants'][str(group)]={'library':str(lib),'library_sha256':sha(lib),'cmake_cache':str(build/'CMakeCache.txt'),'disassembly':str(dis.relative_to(RUN)),'disassembly_sha256':sha(dis)};save()
   ctest=exec_log(f'{tag}_ctest',['ctest','--test-dir',str(build),'--output-on-failure'],env)
   state['variants'][str(group)]['ctest_exit_code']=ctest['exit_code'];save()
   gateout=RUN/'gates'/f'{tag}.json'
   args=[sys.executable,str(GATE),'--candidate-library',str(lib),'--output',str(gateout),'--lock-held']
   if group==0:args+=['--case-ids','1,2,20']
   exec_log(f'{tag}_gate',args,env)
   gate=json.loads(gateout.read_text());expected=3 if group==0 else 20
   if gate.get('status')!='pass' or len(gate.get('cases',[]))!=expected or not all(x.get('pass') for x in gate['cases']):raise RuntimeError(f'group {group} gate failed or incomplete')
   state['variants'][str(group)].update({'gate':str(gateout),'gate_status':gate.get('status'),'gate_cases':len(gate.get('cases',[])),'gate_all_pass':True});save()
  # Prove the preprocessor-selected instruction schedules survive assembly.
  frozen=subprocess.check_output(['objdump','-d','-M','intel','--disassemble=ozamx_bf16_product',str(V3)],text=True)
  disasm={g:(RUN/'disassembly'/f'group{g}_bf16_product.txt').read_text() for g in (0,1,2)}
  codes={'v3':body_bytes(frozen),**{str(g):body_bytes(disasm[g]) for g in (0,1,2)}}
  if not codes['v3'] or codes['0']!=codes['v3']:raise RuntimeError('OZV4_LOAD_GROUP=0 BF16 product instruction bytes differ from frozen V3')
  if codes['1']==codes['0'] or codes['2']==codes['0'] or codes['1']==codes['2']:raise RuntimeError('the three schedule branches did not produce three distinct BF16 product byte sequences')
  state['disassembly_check']={'frozen_v3_instruction_bytes':codes['v3'],'group0_matches_v3':True,'group1_distinct':True,'group2_distinct':True,'group1_differs_group2':True};save()
  # Eight runtime-default full-output paired configurations: two variants x four FP64 budgets.
  for group in (1,2):
   for budget in (6,10,15,21):
    tag=f'group{group}_fp64_n8192_b{budget}';out=RUN/'matched'/tag
    args=[sys.executable,str(MATCHED),'--control-lib',str(V3),'--candidate-lib',state['variants'][str(group)]['library'],'--candidate-tag',tag,'--result-dir',str(out),'--sizes','8192','--reps','11','--warmups','1','--precision','fp64','--budget',str(budget),'--lock-held']
    exec_log(tag,args,env)
    j=json.loads((out/'matched_calls.json').read_text());key=f'fp64_n8192_b{budget}';cfg=j['configurations'][key]
    if not cfg.get('complete') or not cfg.get('byte_exact_match') or len(cfg.get('samples',[]))!=11:raise RuntimeError(f'incomplete or non-bit-exact matched config {tag}')
    state['matched'].append({'group':group,'budget':budget,'journal':str((out/'matched_calls.json').relative_to(RUN)),'metadata':str((out/'metadata.json').relative_to(RUN)),'output_sha256':cfg['output_sha256'],'reps':11,'byte_exact_match':True});save()
  # Raw paired records and drift-aware summaries preserve order and timing phases.
  rows=[];summ=[]
  for item in state['matched']:
   j=json.loads((RUN/item['journal']).read_text());key=f"fp64_n8192_b{item['budget']}";cfg=j['configurations'][key]
   for s in cfg['samples']:
    a=s['calls']['control'];b=s['calls']['candidate']
    row={'group':item['group'],'budget':item['budget'],'rep':s['rep'],'order':'>'.join(s['order']),'input_a_hash':a.get('input_a_fnv1a64'),'input_b_hash':a.get('input_b_fnv1a64'),'control_api_s':a['api_wall_seconds'],'candidate_api_s':b['api_wall_seconds'],'control_split_s':a['split_seconds'],'candidate_split_s':b['split_seconds'],'control_pack_s':a['pack_seconds'],'candidate_pack_s':b['pack_seconds'],'control_compute_reconstruct_s':a['compute_reconstruct_seconds'],'candidate_compute_reconstruct_s':b['compute_reconstruct_seconds'],'control_profile_total_s':a['profile_total_seconds'],'candidate_profile_total_s':b['profile_total_seconds'],'control_recon_s':a.get('reconstruct_seconds'),'candidate_recon_s':b.get('reconstruct_seconds')}
    rows.append(row)
   vals=[r for r in rows if r['group']==item['group'] and r['budget']==item['budget']]
   orders=[r['order'] for r in vals];order_hash=hashlib.sha256(json.dumps(orders,separators=(',',':')).encode()).hexdigest()
   for field in ('api_s','split_s','pack_s','compute_reconstruct_s','profile_total_s','recon_s'):
    c=[r['control_'+field] for r in vals if r['control_'+field] is not None];d=[r['candidate_'+field] for r in vals if r['candidate_'+field] is not None]
    if not c or not d:continue
    summ.append({'group':item['group'],'budget':item['budget'],'metric':field,'control_mean':statistics.mean(c),'control_median':statistics.median(c),'candidate_mean':statistics.mean(d),'candidate_median':statistics.median(d),'mean_paired_speedup_control_over_candidate':statistics.mean(x/y for x,y in zip(c,d)),'median_paired_speedup':statistics.median(x/y for x,y in zip(c,d)),'paired_wins':sum(x>y for x,y in zip(c,d)),'paired_n':len(c),'order_sequence_sha256':order_hash,'input_hash_pairs':[[r['input_a_hash'],r['input_b_hash']] for r in vals]})
  with (RUN/'matched_raw.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  (RUN/'matched_summary.json').write_text(json.dumps({'schema':'ozamx-v4-kernel-schedule-matched-summary-1','configs':summ},indent=2)+'\n')
  state['status']='pass';state['completed_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());state['raw_csv']=str((RUN/'matched_raw.csv').relative_to(RUN));state['summary_json']=str((RUN/'matched_summary.json').relative_to(RUN));save()
  print(json.dumps({'status':state['status'],'run_dir':str(RUN),'summary':str(RUN/'validation_state.json'),'raw_csv':str(RUN/'matched_raw.csv')}))
if __name__=='__main__':
 try:main()
 except Exception as e:
  import traceback
  (RUN/'failure.log').write_text(f'{type(e).__name__}: {e}\n'+traceback.format_exc())
  raise
