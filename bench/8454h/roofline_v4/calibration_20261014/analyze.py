#!/usr/bin/env python3
"""Analyze saved V4 roofline calibration only; never runs benchmark code."""
import csv, hashlib, json, statistics
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RAW = HERE / 'raw/kernels.csv'
OLD = ROOT / 'bench/8454h/roofline/calibration/kernels.csv'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def summarize(rows):
    groups=defaultdict(list); warm=0
    for r in rows:
        if r['record']=='warmup': warm+=1; continue
        key=(r['kernel'],int(r['threads']),int(r['worker_input_bytes']),int(r['stride_elements']))
        groups[key].append(r)
    configs=[]
    for key, rs in sorted(groups.items()):
        vals={k:[float(r[k]) for r in rs] for k in ('elapsed_s','ops_per_s','logical_B_per_s','checksum')}
        configs.append({'kernel':key[0],'threads':key[1],'worker_input_bytes':key[2],'stride_elements':key[3],
          'timed_repetitions':len(rs),'validation':[r['validation'] for r in rs],
          'raw_samples':[{k:r[k] for k in ('record','rep','elapsed_s','units','amx_or_add_ops','logical_bytes','ops_per_s','logical_B_per_s','checksum','validation')} for r in rs],
          'elapsed_s':{'median':statistics.median(vals['elapsed_s']),'mean':statistics.mean(vals['elapsed_s']),'sample_sd':statistics.stdev(vals['elapsed_s'])},
          'reported_ops_per_s':{'median':statistics.median(vals['ops_per_s']),'mean':statistics.mean(vals['ops_per_s']),'sample_sd':statistics.stdev(vals['ops_per_s'])},
          'logical_B_per_s':{'median':statistics.median(vals['logical_B_per_s']),'mean':statistics.mean(vals['logical_B_per_s']),'sample_sd':statistics.stdev(vals['logical_B_per_s'])},
          'checksums':vals['checksum']})
    return warm,groups,configs

def main():
    rows=list(csv.DictReader(RAW.open(newline=''))); oldrows=list(csv.DictReader(OLD.open(newline='')))
    warm,g,configs=summarize(rows); ow,og,oldconfigs=summarize(oldrows)
    if len(rows)!=228 or len(configs)!=57 or warm!=57 or set(len(v) for v in g.values())!={3}: raise SystemExit('new campaign dimensions/reps mismatch')
    if any(r['validation']!='passed' for r in rows): raise SystemExit('new raw contains failed validation')
    if len(oldrows)!=228 or len(oldconfigs)!=57 or ow!=57: raise SystemExit('old reference dimensions mismatch')
    # Correct equal-input cases using the same reported rate and three timed reps.
    comparisons=[]
    oldmap={ (c['kernel'],c['threads'],c['worker_input_bytes'],c['stride_elements']):c for c in oldconfigs }
    for c in configs:
        key=(c['kernel'],c['threads'],c['worker_input_bytes'],c['stride_elements']); o=oldmap[key]
        new=c['reported_ops_per_s']['median']; old=o['reported_ops_per_s']['median']
        comparisons.append({'kernel':key[0],'threads':key[1],'worker_input_bytes':key[2],'stride_elements':key[3],
          'old_median_ops_per_s':old,'new_median_ops_per_s':new,'new_over_old':new/old if old else None,
          'old_sample_sd_ops_per_s':o['reported_ops_per_s']['sample_sd'],'new_sample_sd_ops_per_s':c['reported_ops_per_s']['sample_sd']})
    payload={'schema':'ozamx-roofline-calibration-v2-offline','batch_id':HERE.name,'raw_csv_sha256':sha(RAW),'old_raw_csv_sha256':sha(OLD),
      'counts':{'raw_rows':len(rows),'warmups':warm,'timed_rows':171,'configurations':57,'timed_reps_each':3,'all_validation_passed':True},
      'linked_library_sha256':'73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c',
      'old_linked_library_sha256':'ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251',
      'comparability':'same calibration source and 57 cases; V3 linked library differs, V4 host/toolchain/environment and run batch differ; use new control for within-batch diagnostics, not as physical traffic measurement',
      'configurations':configs,'old_vs_new_same_configuration_comparison':comparisons}
    (HERE/'analysis.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'counts':payload['counts'],'sha256':payload['raw_csv_sha256']},indent=2))
if __name__=='__main__': main()
