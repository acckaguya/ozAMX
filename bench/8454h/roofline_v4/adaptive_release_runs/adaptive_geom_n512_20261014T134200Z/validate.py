#!/usr/bin/env python3
from __future__ import annotations
import fcntl, hashlib, json, os, pathlib, subprocess, sys, time
RUN = pathlib.Path(__file__).resolve().parent
REPO = RUN.parents[4]
SRC = REPO / 'bench/8454h/roofline_v4/adaptive_release_n512_src'
BUILD = RUN / 'build'
MKL = REPO / 'third_party/code/mkl-current'
LOCK = pathlib.Path('/tmp/ozamx-perf.lock')
GATE = REPO / 'bench/8454h/roofline_v4/recon_ilp_src/tools/run_binary_gate_v4.py'
CAND_LIB = BUILD / 'libozamx.a'
GATE_JSON = RUN / 'gates/adaptive_full20.json'
SUMMARY = RUN / 'validation_summary.json'

def sha(p: pathlib.Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def run(label: str, argv: list[str], env: dict) -> dict:
    log=RUN/'logs'/f'{label}.log'
    with log.open('wb') as f: p=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,env=env)
    return {'label':label,'argv':argv,'exit_code':p.returncode,'log':str(log.relative_to(RUN))}

def main() -> int:
    env=dict(os.environ)
    env.update({'OMP_NUM_THREADS':'64','OMP_PLACES':'cores','OMP_PROC_BIND':'close','OMP_DYNAMIC':'FALSE',
        'MKL_NUM_THREADS':'64','MKL_DYNAMIC':'FALSE','MKL_THREADING_LAYER':'GNU','MKL_INTERFACE_LAYER':'LP64',
        'OZAMX_WORKSPACE_CACHE_BYTES':'2147483648',
        'LD_LIBRARY_PATH':str(MKL/'lib')+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')})
    summary={'schema':'ozamx-adaptive-release-validation-1','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'source_tree':str(SRC),'source_identity_sha256':sha(SRC/'SOURCE_IDENTITY.json'),
        'candidate_source_sha256':sha(SRC/'src/gemm.cpp'),'frozen_library':str(REPO/'bench/8454h/versions/v3_release/artifacts/libozamx_v3.a'),
        'frozen_library_sha256':sha(REPO/'bench/8454h/versions/v3_release/artifacts/libozamx_v3.a'),
        'mkl_runtime':str(MKL/'lib/libmkl_rt.so.3'),'mkl_runtime_sha256':sha(MKL/'lib/libmkl_rt.so.3'),
        'gate_runner':str(GATE),'gate_runner_sha256':sha(GATE),'steps':[],'status':'running'}
    with LOCK.open('a') as lf:
        fcntl.flock(lf,fcntl.LOCK_EX)
        summary['lock_acquired_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        cmake=['cmake','-S',str(SRC),'-B',str(BUILD),'-DCMAKE_BUILD_TYPE=Release','-DOZAMX_ENABLE_OPENMP=ON',
            '-DOZAMX_BUILD_PROBE=ON',f'-DOZAMX_ONEMKL_ROOT={MKL}','-DOZAMX_CACHE_BLOCK=128','-DOZAMX_PREP_GRAIN=16384',
            '-DOZAMX_MIN_COMPUTE_WORK=8','-DOZAMX_TILELOAD_HINT=1','-DOZAMX_LOAD_SCHEDULE=0','-DOZAMX_LOOP_ORDER=0','-DOZAMX_MN_ORDER=0']
        steps=[('configure',cmake),('build',['cmake','--build',str(BUILD),'-j2']),
               ('ctest',['ctest','--test-dir',str(BUILD),'--output-on-failure']),
               ('full20_gate',[sys.executable,str(GATE),'--candidate-library',str(CAND_LIB),'--output',str(GATE_JSON),'--lock-held'])]
        for label,argv in steps:
            step=run(label,argv,env); summary['steps'].append(step)
            if step['exit_code']!=0:
                summary['status']='failed'; summary['failed_step']=label; break
        else:
            gate=json.loads(GATE_JSON.read_text())
            identity={'candidate_id':'adaptive_geom_n512_v1','build_type':'Release','compiler_id':'GNU expected',
              'frozen_base_library_sha256':summary['frozen_library_sha256'],'candidate_library_sha256':sha(CAND_LIB),
              'candidate_source_sha256':summary['candidate_source_sha256'],'public_header_sha256':sha(SRC/'include/ozamx/gemm.hpp'),
              'mkl_runtime_sha256':summary['mkl_runtime_sha256'],'cmake_cache':str((BUILD/'CMakeCache.txt').relative_to(RUN)),
              'validation_gate_sha256':sha(GATE_JSON),'ctest_log':summary['steps'][2]['log']}
            (RUN/'build_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
            summary['candidate_library']=str(CAND_LIB); summary['candidate_library_sha256']=identity['candidate_library_sha256']
            summary['ctest_pass']=summary['steps'][2]['exit_code']==0
            summary['full_gate_status']=gate.get('status'); summary['full_gate_cases']=len(gate.get('cases',[]))
            summary['full_gate_all_cases_pass']=all(x.get('pass') for x in gate.get('cases',[]))
            summary['status']='pass' if summary['ctest_pass'] and gate.get('status')=='pass' and len(gate.get('cases',[]))==20 and summary['full_gate_all_cases_pass'] else 'failed'
        summary['completed_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        SUMMARY.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'status':summary['status'],'run_dir':str(RUN),'summary':str(SUMMARY)}))
    return 0 if summary['status']=='pass' else 1
if __name__=='__main__': raise SystemExit(main())
