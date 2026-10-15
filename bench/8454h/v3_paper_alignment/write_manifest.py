#!/usr/bin/env python3
import csv, glob, hashlib, json, os, pathlib, re, subprocess
base=pathlib.Path(__file__).resolve().parent
repo=base.parents[2]
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
archive=pathlib.Path('/tmp/ozamx-roofline-production/libozamx.a')
mkl=repo/'third_party/code/mkl-current/lib/libmkl_rt.so.3'
build=base/'build'
sources={'benchmark':base/'source/benchmark.cpp','raw_bf16':base/'source/raw_bf16.cpp'}
checks={}
for x in ('main','raw'):
    p=build/('ozamx_benchmark' if x=='main' else 'raw_bf16')
    checks[x]={'binary':str(p),'binary_sha256':sha(p) if p.exists() else None}
status={}
sp=base/'config_status.csv'
if sp.exists():
    with sp.open(newline='') as f:
        for row in csv.DictReader(f):
            status[row['config']]=row
items=[]
for cmdpath in sorted((base/'logs').glob('*.command.txt')):
    key=cmdpath.name[:-len('.command.txt')]
    row=status.get(key)
    kind='raw' if key.startswith('raw_bf16_') else 'main'
    candidates=sorted((base/'checkpoints').glob(key+'.*'))
    cpinfo=[]
    for cp in candidates:
        if cp.suffix!='.json': continue
        try:
            d=json.load(open(cp))
            cpinfo.append({'path':str(cp),'source_id':d.get('source_id'),
             'completed_timed_repetitions':d.get('completed_timed_repetitions'),
             'requested_repetitions':d.get('requested_repetitions'),
             'complete':d.get('complete')})
        except Exception as e: cpinfo.append({'path':str(cp),'parse_error':str(e)})
    items.append({'config':key,'state':'complete' if row and row.get('rc')=='0' else ('failed' if row else 'in_progress'),
      'start_utc':row.get('start_utc') if row else None,'end_utc':row.get('end_utc') if row else None,
      'rc':int(row['rc']) if row and row.get('rc','').isdigit() else None,
      'command':cmdpath.read_text().strip(),'result':row.get('result') if row else str(base/'results'/f'{key}.csv'),
      'checkpoints':cpinfo,'binary':checks[kind],
      'main_source_sha256':sha(sources['benchmark']),'raw_source_sha256':sha(sources['raw_bf16']),
      'archive_sha256':sha(archive),'mkl_runtime_sha256':sha(mkl)})
out={'source_id':'v3-paper-alignment-20261014','manifest_utc':subprocess.check_output(['date','-u','+%Y-%m-%dT%H:%M:%SZ'],text=True).strip(),'configs_expected':66,'configs_with_command':len(items),'configs_completed':sum(x['state']=='complete' for x in items),'configs_failed':sum(x['state']=='failed' for x in items),'configs':items}
(base/'per_config_manifest.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['configs_with_command'],out['configs_completed'],out['configs_failed'])
