#!/usr/bin/env python3
"""Run the ordered-reconstruction ILP4 ON/OFF bracket campaign under global perf lock."""
from __future__ import annotations
import argparse, csv, fcntl, hashlib, json, os, pathlib, shlex, subprocess, time

SRC = pathlib.Path(__file__).resolve().parents[1]
REPO = SRC.parents[3]
LOCK = pathlib.Path('/tmp/ozamx-perf.lock')
MKL = REPO / 'third_party/code/mkl-current'
FROZEN = REPO / 'bench/8454h/versions/v3_paper_release/v3_release/artifacts/libozamx_v3.a'
FROZEN_OTHER = REPO / 'bench/8454h/versions/v3_release/artifacts/libozamx_v3.a'
V3_BIN = REPO / 'bench/8454h/versions/v3_paper_release/campaign/build/ozamx_benchmark'
SEED, THREADS, CPUSET = 260904, 64, '0-63'
BUDGETS = '6,10,15,21'

def sha(p: pathlib.Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def env():
    e=dict(os.environ,OMP_NUM_THREADS='64',OMP_PLACES='cores',OMP_PROC_BIND='close',OMP_DYNAMIC='FALSE',
           MKL_NUM_THREADS='64',MKL_DYNAMIC='FALSE',MKL_THREADING_LAYER='GNU',MKL_INTERFACE_LAYER='LP64',
           OZAMX_WORKSPACE_CACHE_BYTES='2147483648')
    e['LD_LIBRARY_PATH']=str(MKL/'lib')+(':'+e['LD_LIBRARY_PATH'] if e.get('LD_LIBRARY_PATH') else '')
    return e

def run(argv, log, e=None):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('wb') as f: p=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,env=e)
    if p.returncode: raise RuntimeError(f'failed ({p.returncode}): {shlex.join(map(str,argv))}; see {log}')

def benchmark(binary, out, label, mode, n, reps, precision='fp64', budgets=BUDGETS):
    d=out/'records'/label
    d.mkdir(parents=True)
    csvp=d/'result.csv'; chk=d/'checkpoint'
    argv=['taskset','-c',CPUSET,str(binary),'--sizes',str(n),'--threads',str(THREADS),'--reps',str(reps),
          '--seed',str(SEED),'--precision',precision,'--budgets',budgets,'--distribution','uniform',
          '--checkpoint',str(chk),'--output',str(csvp)]
    (d/'command.json').write_text(json.dumps(argv,indent=2)+'\n')
    run(argv,d/'run.log',env())
    with csvp.open(newline='') as f:
        rd=csv.DictReader(f); rows=list(rd)
        if len(rd.fieldnames or [])!=37: raise RuntimeError(f'{csvp}: expected 37 fields, got {len(rd.fieldnames or [])}')
    expected=4 if precision=='fp64' else (1 if precision=='fp32' else 5)
    expected_status={0:'ok',1:'diagnostic_only_accuracy_unvalidated',
                     2:'diagnostic_no_reconstruction_non_numeric',3:'ok'}[mode]
    if len(rows)!=expected or any(r['status']!=expected_status for r in rows):
        raise RuntimeError(f'{csvp}: malformed rows or unexpected mode status')
    return csvp

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--result-dir',type=pathlib.Path,required=True)
    ap.add_argument('--resume',action='store_true')
    a=ap.parse_args(); out=a.result_dir.resolve()
    if out.exists() and not a.resume: raise SystemExit(f'result path exists: {out}; use --resume to continue verified data')
    out.mkdir(parents=True,exist_ok=True)
    with LOCK.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        execute(out,a.resume)

def execute(out,resume=False):
    expected='73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c'
    if sha(FROZEN)!=expected or sha(FROZEN_OTHER)!=expected or not V3_BIN.is_file():
        raise RuntimeError('frozen V3 library or control driver identity mismatch')
    frozen_headers=REPO/'bench/8454h/versions/v3_paper_release/v3_release/repo/include/ozamx/gemm.hpp'
    if sha(frozen_headers)!=sha(SRC/'include/ozamx/gemm.hpp'): raise RuntimeError('public header differs from frozen V3')
    source_files=[p for p in SRC.rglob('*') if p.is_file() and 'recon_ilp_runs' not in str(p)]
    ds={'schema':'ozamx-v4-reconstruction-ilp4-1','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'source_tree':str(SRC),'source_sha256':{str(p.relative_to(SRC)):sha(p) for p in sorted(source_files)},
        'v3_library_sha256':sha(FROZEN),'v3_original_path_library_sha256':sha(FROZEN_OTHER),
        'v3_control_binary_sha256':sha(V3_BIN),'mkl_runtime_sha256':sha(MKL/'lib/libmkl_rt.so.3'),
        'cpuset':CPUSET,'threads':THREADS,'seed':SEED,'workspace_cache_bytes':2147483648,
        'fixed':{'cbm':128,'cbn':0,'pad_bytes':64,'tileload_hint':1,'bk':256},'configs':[]}
    dataset_path=out/'dataset.json'
    if resume:
        old=json.loads(dataset_path.read_text())
        if old.get('schema')!='ozamx-v4-reconstruction-ilp4-1' or old.get('v3_library_sha256')!=sha(FROZEN):
            raise RuntimeError('resume dataset schema or frozen library identity mismatch')
        ds=old
        ds.setdefault('failed_attempts',[])
    else:
        dataset_path.write_text(json.dumps(ds,indent=2)+'\n')
    e=env(); build_dirs={}
    def build(batch, ilp, mode, tag):
        name=f'{tag}_b{batch}_{"on" if ilp else "off"}_m{mode}'
        b=out/'builds'/name
        if b.exists() and (b/'build_identity.json').is_file():
            ident=json.loads((b/'build_identity.json').read_text())
            if (ident.get('fp64_batch')!=batch or ident.get('reconstruction_ilp4')!=('ON' if ilp else 'OFF') or
                ident.get('mode')!=mode or ident.get('reconstruction_source_sha256')!=sha(SRC/'src/reconstruct_ilp4.S') or
                ident.get('gemm_source_sha256')!=sha(SRC/'src/gemm.cpp') or sha(b/'libozamx.a')!=ident.get('library_sha256')):
                raise RuntimeError(f'existing build identity mismatch: {b}')
            build_dirs[(batch,ilp,mode)]=b
            return b
        b.mkdir(parents=True)
        cfg=['cmake','-S',str(SRC),'-B',str(b),'-DCMAKE_BUILD_TYPE=Release',f'-DOZAMX_ONEMKL_ROOT={MKL}',
             f'-DOZV4_FP64_BATCH={batch}',f'-DOZV4_RECON_ILP4={"ON" if ilp else "OFF"}',f'-DOZV4_MODE={mode}',
             '-DOZV4_WIDE_CBM=128','-DOZV4_WIDE_CBN=0','-DOZV4_WIDE_PAD_BYTES=64','-DOZAMX_TILELOAD_HINT=1']
        run(cfg,out/'logs'/f'{name}_configure.log')
        run(['cmake','--build',str(b),'-j2'],out/'logs'/f'{name}_build.log')
        ident=json.loads((b/'build_identity.json').read_text()); ident['library_sha256']=sha(b/'libozamx.a')
        ident['benchmark_binary_sha256']=sha(b/'ozamx_benchmark'); ident['source_tree']=str(SRC)
        (b/'build_identity.json').write_text(json.dumps(ident,indent=2)+'\n')
        build_dirs[(batch,ilp,mode)]=b
        return b

    # One mode-0 all-precision N=256/reps=1 ON/OFF preflight. Reuse the completed
    # OFF half from the immediately preceding, interrupted preparation run.
    if not ds.get('preflight'):
        prior=REPO/'bench/8454h/roofline_v4/recon_ilp_runs/ilp4_batch_bracket_20261014T111500Z'
        reused_off=prior/'records/preflight_b2_off_m0_n256/result.csv'
        reused_off_identity=prior/'builds/preflight_b2_off_m0/build_identity.json'
        if not reused_off.is_file() or not reused_off_identity.is_file():
            raise RuntimeError('completed OFF N256 preflight evidence is missing')
        ds['preflight']=[{'batch':2,'ilp4':False,'mode':0,'reused_from':str(reused_off.relative_to(REPO)),
            'csv_sha256':sha(reused_off),'build_identity':str(reused_off_identity.relative_to(REPO)),
            'library_sha256':json.loads(reused_off_identity.read_text())['library_sha256']}]
        pre_on=build(2,True,0,'preflight')
        pre_csv=benchmark(pre_on/'ozamx_benchmark',out,'preflight_b2_on_m0_n256',0,256,1,'all')
        ds['preflight'].append({'batch':2,'ilp4':True,'mode':0,'csv':str(pre_csv.relative_to(out)),
            'csv_sha256':sha(pre_csv),'build_identity':str((pre_on/'build_identity.json').relative_to(out)),
            'library_sha256':sha(pre_on/'libozamx.a')})
    if not ds.get('configs'):
        ds['configs']=[{'batch':b,'ilp4':flag,'gates':[],'screen':[]} for b in (2,8,12,21) for flag in (False,True)]
    # Build the only measured mode (0: FP32 production and wide FP64 Late64).
    # Its >=4096 FP64 path is the assembly candidate, so mode-0 gates cover it.
    for state in ds['configs']:
        batch,ilp=state['batch'],state['ilp4']; suffix='on' if ilp else 'off'
        b=build(batch,ilp,0,'candidate')
        gemm_obj=b/'CMakeFiles/ozamx.dir/src/gemm.cpp.o'
        disasm=subprocess.run(['objdump','-dr',str(gemm_obj)],check=True,text=True,stdout=subprocess.PIPE).stdout
        calls='ozamx_reconstruct64_ilp4' in disasm
        (out/'disassembly').mkdir(exist_ok=True)
        (out/'disassembly'/f'b{batch}_{suffix}_m0_gemm_objdump.txt').write_text(disasm)
        if calls!=ilp:
            raise RuntimeError(f'ILP4 Late64 linkage mismatch for batch={batch}, ilp={ilp}: call_ref={calls}')
        gate=out/'gates'/f'b{batch}_{suffix}_m0_full.json'
        ctestlog=out/'logs'/f'gate_b{batch}_{suffix}_m0_ctest.log'
        gate_done=gate.is_file() and json.loads(gate.read_text()).get('status')=='pass' and len(json.loads(gate.read_text()).get('cases',[]))==20
        ctest_done=ctestlog.is_file() and '100% tests passed' in ctestlog.read_text()
        if not ctest_done: run(['ctest','--test-dir',str(b),'--output-on-failure'],ctestlog,e)
        if not gate_done:
            run(['python3',str(SRC/'tools/run_binary_gate_v4.py'),'--candidate-library',str(b/'libozamx.a'),
                 '--output',str(gate),'--case-ids',','.join(map(str,range(1,21))),'--lock-held'],
                out/'logs'/f'gate_b{batch}_{suffix}_m0_full.log',e)
        gd=json.loads(gate.read_text())
        if gd.get('status')!='pass' or len(gd.get('cases',[]))!=20: raise RuntimeError(f'full gate failed: {gate}')
        if not any(x.get('mode')==0 for x in state['gates']):
            state['gates'].append({'mode':0,'gate':str(gate.relative_to(out)),'gate_sha256':sha(gate),
                'ctest_log':str(ctestlog.relative_to(out)),
                'library_sha256':sha(b/'libozamx.a'),'objdump_contains_call':calls})
        build_dirs[(batch,ilp,0)]=b
        (out/'dataset.json').write_text(json.dumps(ds,indent=2)+'\n')
    # Paired 8192 FP64 screens. Immutable V3 controls bracket the beginning and every two batches.
    # The archived V3 binary is read-only and non-executable. Link a fresh
    # control driver from its frozen static library, recording this exact build.
    frozen_driver=out/'builds/frozen_v3_driver/ozamx_benchmark'
    if not frozen_driver.exists():
        frozen_driver.parent.mkdir(parents=True,exist_ok=True)
        cmd=[os.environ.get('CXX','g++'),'-O3','-std=c++17','-Wall','-Wextra','-Wpedantic','-march=sapphirerapids',
             '-ffp-contract=off','-fno-fast-math','-mamx-tile','-mamx-bf16','-fopenmp',f'-I{SRC/"include"}',
             f'-I{MKL/"include"}',str(SRC/'bench/benchmark.cpp'),str(FROZEN),f'-L{MKL/"lib"}',
             f'-Wl,-rpath,{MKL/"lib"}','-Wl,--no-as-needed','-l:libmkl_rt.so.3','-ldl','-o',str(frozen_driver)]
        run(cmd,out/'logs/frozen_v3_driver_build.log',e)
        (frozen_driver.parent/'build_identity.json').write_text(json.dumps({'reference':'immutable V3 paper release',
            'library_sha256':sha(FROZEN),'driver_sha256':sha(frozen_driver),
            'driver_source_sha256':sha(SRC/'bench/benchmark.cpp'),'mkl_runtime_sha256':sha(MKL/'lib/libmkl_rt.so.3'),
            'argv':cmd},indent=2)+'\n')
    failed_dir=out/'records/frozen_v3_initial'
    if failed_dir.exists() and not (failed_dir/'result.csv').exists() and not ds.get('controls'):
        failed_log=failed_dir/'run.log'
        ds['failed_attempts'].append({'label':'frozen_v3_initial','reason':'permission denied: archived binary mode 0444',
            'run_log':str(failed_log.relative_to(out)),'run_log_sha256':sha(failed_log)})
    if not ds.get('controls'):
        v3label='frozen_v3_initial_retry1'
        initial=benchmark(frozen_driver,out,v3label,0,8192,7,'fp64')
        ds['controls']=[{'label':v3label,'csv':str(initial.relative_to(out)),'csv_sha256':sha(initial),'repetitions':7,
                         'build_identity':str((frozen_driver.parent/'build_identity.json').relative_to(out))}]
    order=[]
    for ix,batch in enumerate((2,8,12,21)):
        pairs=[(batch,False),(batch,True)] if ix%2==0 else [(batch,True),(batch,False)]
        for b,ilp in pairs:
            state=next(s for s in ds['configs'] if s['batch']==b and s['ilp4']==ilp)
            if state.get('screen'):
                for row in state['screen']:
                    p=out/row['csv']
                    if not p.is_file() or sha(p)!=row['csv_sha256']:
                        raise RuntimeError(f'resumed screen output identity mismatch: {p}')
                order.append({'batch':b,'ilp4':ilp,'reused':True})
                continue
            mode=0
            binary=build_dirs[(b,ilp,mode)]/'ozamx_benchmark'
            label=f'b{b}_{"on" if ilp else "off"}_m0_n8192_fp64'
            csvp=benchmark(binary,out,label,mode,8192,3,'fp64')
            state['screen'].append({'mode':mode,'csv':str(csvp.relative_to(out)),'csv_sha256':sha(csvp),'repetitions':3})
            order.append({'batch':b,'ilp4':ilp})
        if ix in (1,3) and not any(x['label']==f'frozen_v3_after_batch{batch}' for x in ds.get('controls',[])):
            label=f'frozen_v3_after_batch{batch}'
            csvp=benchmark(frozen_driver,out,label,0,8192,7,'fp64')
            ds['controls'].append({'label':label,'csv':str(csvp.relative_to(out)),'csv_sha256':sha(csvp),'repetitions':7})
        (out/'dataset.json').write_text(json.dumps(ds,indent=2)+'\n')
    ds['candidate_order']=order; ds['completed_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    (out/'dataset.json').write_text(json.dumps(ds,indent=2)+'\n')

if __name__=='__main__': main()
