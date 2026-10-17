"""Recompute retained independent results; no GEMM load is executed."""
import csv,json,statistics,hashlib,math,struct
from pathlib import Path
from collections import defaultdict
base=Path(__file__).resolve().parent/'run_20261016'
rows=list(csv.DictReader((base/'results.csv').open()));assert len(rows)==198
by=defaultdict(list)
for r in rows:
 assert r['input_unchanged']=='1' and r['nonfinite']=='0' and r['mismatches']=='0'
 assert float(r['raw_wall_s'])>0 and float(r['steady_wall_s'])>0 and float(r['cpu_s'])>=0
 by[r['family'],int(r['N']),r['routine']].append(r)
assert len(by)==18
summary=[]
for (family,n,routine),rs in sorted(by.items()):
 assert sorted(int(r['round']) for r in rs)==list(range(-1,10))
 assert all(int(r['warmup'])==(int(r['round'])==-1) for r in rs)
 a=[float(r['raw_wall_s']) for r in rs if r['warmup']=='0']; s=[float(r['steady_wall_s']) for r in rs if r['warmup']=='0']; cpu=[float(r['cpu_s']) for r in rs if r['warmup']=='0']
 assert len({r['input_a_hash'] for r in rs})==11 and len({r['input_b_hash'] for r in rs})==1
 assert len({r['output_hash'] for r in rs})==11
 summary.append({'family':family,'N':n,'routine':routine,'repetitions':len(a),'raw_mean_s':statistics.mean(a),'raw_median_s':statistics.median(a),'raw_sample_sd':statistics.stdev(a),'raw_min_s':min(a),'raw_max_s':max(a),'steady_mean_s':statistics.mean(s),'cpu_mean_s':statistics.mean(cpu),'cpu_over_wall':statistics.mean(cpu)/statistics.mean(a),'effective_TFLOP_s':2*n**3/statistics.mean(a)/1e12,'max_abs_raw_steady_difference_s':max(abs(x-y) for x,y in zip(a,s)),'max_relative_raw_steady_difference':max(abs(x-y)/x for x,y in zip(a,s)),'oracle_entries_per_call':int(rs[0]['oracle_entries']),'field_challenges_per_call':int(rs[0]['field_challenges']),'max_scaled_error':max(float(r['scaled_error']) for r in rs)})
for n in [128,1024,4096]:
 for rep in range(-1,10):
  a=[r for r in rows if r['family']=='dyadic_exact' and int(r['N'])==n and int(r['round'])==rep];assert len(a)==3
  assert len({r['output_hash'] for r in a})==1
regions=[]
for r in rows:
 if int(r['field_challenges']):
  assert int(r['field_challenges'])==3
  regions.append((int(r['challenge_offset']),int(r['N'])*12))
negatives=[json.loads(x) for x in (base/'results.negative_controls.jsonl').read_text().splitlines()]
assert len(negatives)==2 and all(r['mismatches']>0 and r['oracle_entries']==0 for r in negatives)
for r in negatives: regions.append((r['challenge_offset'],r['N']*12))
regions.sort(); end=0
for offset,size in regions:assert offset==end; end+=size
b=(base/'results.challenges.u32').read_bytes(); assert end==len(b)
vals=struct.unpack('<%dI'%(len(b)//4),b);assert max(vals)<2147483647
result={'expected_calls':198,'observed_calls':len(rows),'timed_calls':180,'correctness_failures':0,'all_dyadic_cross_routine_hashes_match':True,'input_changes_every_round':True,'output_changes_every_round':True,'input_after_call_unchanged':True,'all_challenge_regions_contiguous':True,'challenge_bytes':len(b),'negative_controls':negatives,'groups':summary,'note':'Isolated output-integrity/timing audit. Validation/hash/poison outside timers changes cache/wait conditions; do not pool with historical campaign. Effective work is conventional 2N^3, not physical instruction counting.'}
(base/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
files=[p for p in base.iterdir() if p.is_file() and p.name!='checksums.sha256']
(base/'checksums.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(files)))
print('calls',len(rows),'regions',len(regions),'challenge_bytes',len(b))
for r in summary:
 if r['N']==4096:print(r['family'],r['routine'],'ms',r['raw_mean_s']*1000,'TF',r['effective_TFLOP_s'],'CPU/wall',r['cpu_over_wall'],'scaled',r['max_scaled_error'])
