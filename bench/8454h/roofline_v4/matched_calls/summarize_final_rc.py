#!/usr/bin/env python3
"""Validate and summarize the final adaptive-RC matched campaign, retaining raw observations."""
import json, pathlib, statistics, time
ROOT=pathlib.Path(__file__).resolve().parents[4]
CAMPAIGN=ROOT/'bench/8454h/roofline_v4/matched_calls/results/final_rc_20261014'
DOC=ROOT/'docs/8454H_V4_ADAPTIVE_RC_MATCHED.md'
PHASES=('api_wall_seconds','split_seconds','pack_seconds','compute_reconstruct_seconds','profile_total_seconds')
def stat(xs):return {'count':len(xs),'mean':statistics.fmean(xs),'median':statistics.median(xs),'min':min(xs),'max':max(xs)}
def main():
 rows=[];runs=[]
 for meta_path in sorted(CAMPAIGN.glob('*/metadata.json')):
  run=meta_path.parent;meta=json.load(open(meta_path));cfgmeta=meta['run_config']
  journal=json.load(open(run/'matched_calls.json'))
  assert journal['run_config']==cfgmeta,(run,'metadata mismatch')
  assert cfgmeta['wait_policy_variant']=='runtime' and cfgmeta['environment']['OMP_WAIT_POLICY'] is None and cfgmeta['environment']['GOMP_SPINCOUNT'] is None
  assert cfgmeta['parent_inter_call_pause_seconds']==.02 and cfgmeta['threads']==64
  for ps in journal['process_sessions']:
   for child in ps['children_ready'].values():
    assert child['actual_omp_threads']==64 and sorted(set(child['omp_thread_cpus']))==list(range(64))
  for key,cfg in journal['configurations'].items():
   assert cfg['complete'] is True and cfg['byte_exact_match'] is True,(run,key,'not complete and byte exact')
   samples=cfg['samples']; assert len(samples)==cfgmeta['reps']
   for s in samples:
    calls=s['calls'];assert (calls['control']['input_a_fnv1a64'],calls['control']['input_b_fnv1a64'])==(calls['candidate']['input_a_fnv1a64'],calls['candidate']['input_b_fnv1a64'])
   metrics={};ratios={}
   for phase in PHASES:
    control=[s['calls']['control'][phase] for s in samples];candidate=[s['calls']['candidate'][phase] for s in samples]
    paired=[b/a for a,b in zip(control,candidate)]
    metrics[phase]={'control_raw':control,'candidate_raw':candidate,'paired_ratio_raw':paired,
      'control_stats':stat(control),'candidate_stats':stat(candidate),'paired_ratio_stats':stat(paired),
      'ratio_of_arithmetic_mean_times':statistics.fmean(candidate)/statistics.fmean(control)}
    ratios[phase]=paired
   row={'run_id':run.name,'candidate_tag':cfgmeta['candidate_tag'],'candidate_library_sha256':cfgmeta['candidate_sha256'],
    'precision':cfg['precision'],'budget':cfg['budget'],'N':cfg['N'],'reps':len(samples),
    'order':[s['order'] for s in samples],'metrics':metrics,'byte_exact_match':cfg['byte_exact_match'],
    'output_sha256':cfg['output_sha256'],'input_fnv1a64':{
      'A':samples[0]['calls']['control']['input_a_fnv1a64'],'B':samples[0]['calls']['control']['input_b_fnv1a64']},
    'position_effect_api_wall':{}}
   for label in ('control','candidate'):
    first=[];second=[]
    for sample in samples:
     val=sample['calls'][label]['api_wall_seconds']
     (first if sample['order'][0]==label else second).append(val)
    row['position_effect_api_wall'][label]={'first_position_median_seconds':statistics.median(first),'second_position_median_seconds':statistics.median(second),'second_over_first_pct':(statistics.median(second)/statistics.median(first)-1)*100}
   rows.append(row)
  runs.append({'run_id':run.name,'candidate_tag':cfgmeta['candidate_tag'],'candidate_library':cfgmeta['candidate_lib'],'candidate_sha256':cfgmeta['candidate_sha256'],'control_sha256':cfgmeta['control_sha256'],'reps':cfgmeta['reps'],'precision':cfgmeta['precision'],'sizes':cfgmeta['sizes'],'budget':cfgmeta['budget'],'runner_sha256':cfgmeta['runner_sha256'],'driver_sha256':cfgmeta['driver_sha256'],'started_utc':meta['started_utc'],'finished_utc':meta['finished_utc']})
 if len(rows)!=16:raise SystemExit(f'expected 16 configurations, saw {len(rows)}')
 by={tag:[r for r in rows if r['candidate_tag']==tag] for tag in ('rc1_geom256','rc2_geom512')}
 for tag,items in by.items():
  expected=9 if tag=='rc1_geom256' else 7
  if len(items)!=expected:raise SystemExit(f'{tag}: expected {expected} configurations, got {len(items)}')
 summary={'status':'pass','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
  'campaign_directory':str(CAMPAIGN),'configuration_count':len(rows),'validation':'all completed configurations have equal full-output SHA-256, matching deterministic input checksums, and both persistent children reported 64 OpenMP workers across CPUs 0-63',
  'wait_policy':'GNU runtime default: OMP_WAIT_POLICY and GOMP_SPINCOUNT unset; parent parks 20ms between calls, outside timed API intervals','primary_metric':'ratio of arithmetic mean candidate API wall time to arithmetic mean frozen-V3 API wall time; paired ratio means and medians are separately reported',
  'runs':runs,'configurations':rows}
 (CAMPAIGN/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
 lines=['# Adaptive V4 release candidate matched checks','',
  'Two final adaptive release archives were compared with the frozen V3 archive using the runtime-default GNU OpenMP wait policy. The runner unset `OMP_WAIT_POLICY` and `GOMP_SPINCOUNT`, inserted a 20 ms parent pause after each call outside API timing, and kept both persistent child processes pinned across CPUs 0–63. Every configuration checked matching deterministic input hashes and equal full C-buffer SHA-256; both children reported 64 OpenMP threads. All samples, phase timings, order, hashes, commands, binaries, and metadata are retained in the campaign directory.','',
  f"Campaign data: `{CAMPAIGN}`  ",f"Frozen V3 SHA-256: `{runs[0]['control_sha256']}`  ",
  'The primary API metric below is candidate arithmetic-mean API wall time divided by frozen-V3 arithmetic-mean API wall time. Paired-ratio mean and median are also shown because shared-host drift can make them diverge. Ratios below 1 favor the candidate; raw arrays are in `summary.json`. No outliers were discarded.','',
  '| Candidate | Workload | N | Reps | Median paired ratio | Mean paired ratio | Ratio of arithmetic mean API times | C-output exact |','|---|---|---:|---:|---:|---:|---:|---|']
 for r in rows:
  t=r['metrics']['api_wall_seconds']
  work='FP32' if r['precision']=='fp32' else f"FP64 p{r['budget']}"
  lines.append(f"| `{r['candidate_tag']}` | {work} | {r['N']} | {r['reps']} | {t['paired_ratio_stats']['median']:.4f} | {t['paired_ratio_stats']['mean']:.4f} | {t['ratio_of_arithmetic_mean_times']:.4f} | yes |")
 lines += ['', '## Large FP32 detail','', '| Candidate | N | All 11 paired API ratios, in call order | Median | Mean paired | Ratio of mean API times |','|---|---:|---|---:|---:|---:|']
 for r in rows:
  if r['precision']=='fp32' and r['N']>1024:
   t=r['metrics']['api_wall_seconds'];raw=', '.join(f'{x:.5f}' for x in t['paired_ratio_raw'])
   lines.append(f"| `{r['candidate_tag']}` | {r['N']} | {raw} | {t['paired_ratio_stats']['median']:.5f} | {t['paired_ratio_stats']['mean']:.5f} | {t['ratio_of_arithmetic_mean_times']:.5f} |")
 lines += ['', '## Phase-profile calibration','', 'Per-call phase values and ratios are retained separately by precision and budget. The API-wall metric includes allocation and the whole profiled call; split, pack, compute/reconstruct, and profile-total timings must be interpreted within their matching precision/budget, not pooled as interchangeable useful-AMX work. `summary.json` gives raw phase arrays, paired ratios, means, medians, and ratios of arithmetic means for every configuration.','', 'The large FP32 data favor each candidate against frozen V3 on average, but individual runs include substantial drift and some slow calls. These are direct release-archive checks; they do not establish a roofline claim or eliminate remaining shared-host uncertainty. Keep any production decision conditional on the project’s accuracy gates and broader deployment validation.','', 'All N=1024 FP32 and four-budget FP64 regression checks are included in the table and raw campaign data. RC1 also includes FP64 p6 large-N checks. RC2 FP64 p6 large-N was outside the requested scope.','']
 DOC.write_text('\n'.join(lines))
 print(json.dumps({'summary':str(CAMPAIGN/'summary.json'),'documentation':str(DOC),'validated_configurations':len(rows)},indent=2))
if __name__=='__main__':main()
