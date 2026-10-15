#!/usr/bin/env python3
import csv, glob, hashlib, json, os, sys

name, variant, source_id, library_path, expected_sha, repo = sys.argv[1:]
base = os.path.dirname(os.path.abspath(__file__))
d = os.path.join(base, name)
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
with open(os.path.join(d,'full.csv'),newline='') as f:
    rows=list(csv.DictReader(f))
checkpoints=sorted(glob.glob(os.path.join(d,'checkpoint_'+name+'.*.json')))
if len(rows)!=15 or len(checkpoints)!=15 or any(r['status']!='ok' for r in rows):
    raise SystemExit('expected 15 successful rows and 15 checkpoints')
checkpoint_hashes={}
for p in checkpoints:
    with open(p) as f: c=json.load(f)
    if not c['complete'] or c['source_id']!=source_id or c['requested_repetitions']!=7 or c['completed_timed_repetitions']!=7:
        raise SystemExit('checkpoint parameters or completion status mismatch: '+p)
    checkpoint_hashes[os.path.basename(p)]=sha(p)
order=['p1_v2a','p2_v3a','p3_v2b','p4_v3b','p5_v2c']
position=order.index(name)+1
runtime=os.path.join(repo,'third_party/code/mkl-current/lib/libmkl_rt.so.3')
source=os.path.join(d,'benchmark_matched_recheck.cpp')
source_set=['CMakeLists.txt','include/ozamx/gemm.hpp','src/gemm.cpp','src/kernels.S','src/preprocess.hpp','src/runtime.cpp','src/tuning.hpp','bench/benchmark.cpp']
provenance={
 'schema':'ozamx-matched-recheck-provenance-v1','status':'complete','sequence_position':position,
 'sequence':['V2','V3','V2','V3','V2'],'process_name':name,'library_variant':variant,
 'source_id':source_id,'benchmark_source':os.path.relpath(source,repo),'benchmark_source_sha256':sha(source),
 'benchmark_binary_sha256':sha(os.path.join(d,'ozamx_benchmark')),
 'library_path':library_path,'library_sha256':sha(library_path),'expected_library_sha256':expected_sha,
 'mkl_runtime_path':runtime,'mkl_runtime_sha256':sha(runtime),'mkl_version':rows[0]['mkl_version'],
 'mkl_threading_layer':rows[0]['mkl_threading_layer'],'compiler':'GCC/G++ 11.4.0',
 'driver_compile_flags':'-O3 -std=c++17 -Wall -Wextra -Wpedantic -mamx-tile -mamx-bf16 -fopenmp',
 'cmake_cache_sha256':sha('/tmp/ozamx-roofline-production/CMakeCache.txt'),
 'cmake_compile_commands_sha256':sha('/tmp/ozamx-roofline-production/compile_commands.json'),
 'source_sha256':{p:sha(os.path.join(repo,p)) for p in source_set},
 'measurement':{'sizes':[1024,2048,8192],'precision':'FP32 p6; FP64 p6,p10,p15,p21','timed_repetitions':7,
   'warmup':'one first call per configuration','seed_base':260904,'resolved_seed':'260904+N','distribution':'uniform[-1,1]',
   'threads':64,'cpu_set':'0-63','OMP_NUM_THREADS':64,'OMP_PLACES':'cores','OMP_PROC_BIND':'close','OMP_DYNAMIC':'FALSE',
   'MKL_NUM_THREADS':64,'MKL_DYNAMIC':'FALSE','MKL_THREADING_LAYER':'GNU','MKL_INTERFACE_LAYER':'LP64',
   'OZAMX_WORKSPACE_CACHE_BYTES':2147483648,'lock':'flock -x /tmp/ozamx-perf.lock',
   'ozamx_scope':'complete gemm_*_profiled API call including dispatch and teardown','mkl_scope':'GEMM call only'},
 'cli':['--sizes','1024,2048,8192','--threads','64','--reps','7','--precision','all','--budgets','6,10,15,21','--seed','260904','--distribution','uniform'],
 'outputs':{'configuration_count':len(rows),'checkpoint_count':len(checkpoints),'csv':'full.csv','csv_sha256':sha(os.path.join(d,'full.csv')),
   'build_log_sha256':sha(os.path.join(d,'build.log')),'run_log_sha256':sha(os.path.join(d,'run.log')),
   'checkpoint_prefix':'checkpoint_'+name,'checkpoint_hashes':checkpoint_hashes},
 'status_counts':{s:sum(r['status']==s for r in rows) for s in sorted(set(r['status'] for r in rows))}}
with open(os.path.join(d,'provenance.json'),'w') as f:
    json.dump(provenance,f,indent=2);f.write('\n')
