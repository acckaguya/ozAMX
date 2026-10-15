#!/usr/bin/env python3
import csv, json, math, pathlib, statistics, sys
root=pathlib.Path(sys.argv[1])
cache_tag='2g' if root.name=='2g' else '4g'
runs={name:root/'raw'/f'{name}.csv' for name in (f'frozen_{cache_tag}_a',f'control0_{cache_tag}',f'numa1_{cache_tag}_a',f'frozen_{cache_tag}_b',f'numa1_{cache_tag}_b',f'frozen_{cache_tag}_c')}
def load(path):
    with path.open(newline='') as f:
        rows=list(csv.DictReader(f))
    data={}
    for r in rows:
        if r['record']!='rep':continue
        key=(r['precision'],int(r['size']),int(r['budget']))
        data.setdefault(key,[]).append(r)
    for key,rows in data.items():
        if len(rows)!=5:raise SystemExit(f'{path}: expected 5 measured reps for {key}, got {len(rows)}')
    return rows,data
loaded={name:load(path) for name,path in runs.items()}
expected={(p,n,b) for n in (4096,8192) for p,b in [('fp32',6),('fp64',6),('fp64',21)]}
for name,(_,data) in loaded.items():
    if set(data)!=expected:raise SystemExit(f'{name}: configuration set differs: {set(data)^expected}')
metrics=('split_s','pack_s','replicate_b_s','compute_s','total_s','wall_s','minor_faults','major_faults','voluntary_switches','involuntary_switches','user_s','system_s','max_rss_kib')
def nums(rows,metric):
    if metric in ('replicate_b_s','replica_node0_workers','replica_node1_workers','replica_fallback_workers'):
        return [float(r.get(metric,0) or 0) for r in rows]
    return [float(r[metric]) for r in rows]
def median(rows,metric):return statistics.median(nums(rows,metric))
def delta(c,b):return (c/b-1.0)*100.0 if b else None
results=[];checksum_issues=[]
for key in sorted(expected,key=lambda x:(x[1],x[0],x[2])):
    frozen_a=loaded[f'frozen_{cache_tag}_a'][1][key];frozen_b=loaded[f'frozen_{cache_tag}_b'][1][key];frozen_c=loaded[f'frozen_{cache_tag}_c'][1][key]
    control=loaded[f'control0_{cache_tag}'][1][key];na=loaded[f'numa1_{cache_tag}_a'][1][key];nb=loaded[f'numa1_{cache_tag}_b'][1][key]
    f_all=frozen_a+frozen_b+frozen_c
    bases_a=frozen_a+frozen_b;bases_b=frozen_b+frozen_c
    chk={name:sorted({r['checksum'] for r in rows}) for name,rows in [('frozen',f_all),('control',control),('numa_a',na),('numa_b',nb)]}
    if any(v!=chk['frozen'] for name,v in chk.items() if name!='frozen') or len(chk['frozen'])!=1:
        checksum_issues.append({'precision':key[0],'size':key[1],'budget':key[2],'checksums':chk})
    row={'precision':key[0],'size':key[1],'budget':key[2], 'checksums_match_frozen':not any(v!=chk['frozen'] for name,v in chk.items() if name!='frozen') and len(chk['frozen'])==1,
         'replica_workers_seen':sorted({(int(r['replica_node0_workers']),int(r['replica_node1_workers']),int(r['replica_fallback_workers'])) for r in na+nb}), 'comparisons':{}}
    comparisons={'control0_vs_frozen':(control,f_all),'numa_a_vs_adjacent_frozen':(na,bases_a),'numa_b_vs_adjacent_frozen':(nb,bases_b),'numa_combined_vs_frozen':(na+nb,f_all),'numa_combined_vs_control0':(na+nb,control)}
    for label,(cand,base) in comparisons.items():
        row['comparisons'][label]={}
        for metric in metrics:
            cm=median(cand,metric);bm=median(base,metric)
            pct=None if metric=='pack_s' and bm<1e-4 else delta(cm,bm)
            row['comparisons'][label][metric]={'candidate_median':cm,'baseline_median':bm,'delta_absolute':cm-bm,'delta_percent':pct}
    results.append(row)
summary={}
for label in ('control0_vs_frozen','numa_a_vs_adjacent_frozen','numa_b_vs_adjacent_frozen','numa_combined_vs_frozen','numa_combined_vs_control0'):
    summary[label]={}
    for metric in metrics:
        all_vals=[r['comparisons'][label][metric]['delta_percent'] for r in results]
        vals=[v for v in all_vals if v is not None]
        summary[label][metric]={'configs':len(vals),'zero_baseline_configs':len(all_vals)-len(vals),
            'favorable_count_lower':sum(v<0 for v in vals),
            'delta_percent_min':min(vals) if vals else None,
            'delta_percent_median':statistics.median(vals) if vals else None,
            'delta_percent_max':max(vals) if vals else None,
            'delta_absolute_median':statistics.median([r['comparisons'][label][metric]['delta_absolute'] for r in results]),
            'candidate_median_absolute':statistics.median([r['comparisons'][label][metric]['candidate_median'] for r in results]),
            'baseline_median_absolute':statistics.median([r['comparisons'][label][metric]['baseline_median'] for r in results])}
if checksum_issues:
    status='checksum_mismatch'
else:status='pass'
result={'status':status,'policy':'Use every measured repetition; no sample is discarded. Candidate A is paired to frozen A+B; candidate B to frozen B+C; pooled NUMA is also compared with all 15 frozen repetitions. Percent delta is candidate/baseline-1, so negative wall_s means faster. pack_s percentage is suppressed when baseline pack is below 0.1 ms because the frozen direct path performs its material packing inside split_s; report absolute stage deltas instead. pack_s includes replica allocation+copy; replicate_b_s isolates copy only and is not additive with pack_s.','configurations':results,'summary':summary,'checksum_issues':checksum_issues,'rss_note':'max_rss_kib is process-wide ru_maxrss observed after each call (peak, not per-call RSS delta); fault and context-switch columns are per-call getrusage differences.'}
(root/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':status,'configs':len(results),'checksum_issues':len(checksum_issues),'numa_wall':summary['numa_combined_vs_frozen']['wall_s']},sort_keys=True))
if status!='pass':raise SystemExit(2)
