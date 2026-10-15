#!/usr/bin/env python3
"""Validate and summarize the independent RC1 confirmation campaign."""
import json,pathlib,statistics,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
CAMPAIGN=ROOT/'bench/8454h/roofline_v4/matched_calls/results/rc1_independent_confirmation_20261014'
DOC=ROOT/'docs/8454H_V4_RC_CONFIRMATION.md'
PHASES=('api_wall_seconds','split_seconds','pack_seconds','compute_reconstruct_seconds','profile_total_seconds')
def stats(x):return {'count':len(x),'mean':statistics.fmean(x),'median':statistics.median(x),'min':min(x),'max':max(x)}
def main():
 rows=[];metadata=[]
 for mp in sorted(CAMPAIGN.glob('*/metadata.json')):
  folder=mp.parent;m=json.load(open(mp));cmeta=m['run_config'];j=json.load(open(folder/'matched_calls.json'))
  assert j['run_config']==cmeta
  assert cmeta['candidate_sha256']=='2a3e5533fbd5397df2c44284a7a7da54b0463558e36f8f9f284b210831c80695'
  assert cmeta['control_sha256']=='73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c'
  assert cmeta['wait_policy_variant']=='runtime' and cmeta['environment']['OMP_WAIT_POLICY'] is None and cmeta['environment']['GOMP_SPINCOUNT'] is None and cmeta['parent_inter_call_pause_seconds']==.02
  for sess in j['process_sessions']:
   for child in sess['children_ready'].values():assert child['actual_omp_threads']==64 and sorted(set(child['omp_thread_cpus']))==list(range(64))
  for key,cfg in j['configurations'].items():
   assert cfg['complete'] and cfg['byte_exact_match'] and len(cfg['samples'])==11
   ss=cfg['samples']
   for s in ss:
    a=s['calls']['control'];b=s['calls']['candidate'];assert (a['input_a_fnv1a64'],a['input_b_fnv1a64'])==(b['input_a_fnv1a64'],b['input_b_fnv1a64'])
   mm={}
   for phase in PHASES:
    cv=[s['calls']['control'][phase] for s in ss];nv=[s['calls']['candidate'][phase] for s in ss];rr=[y/x for x,y in zip(cv,nv)]
    mm[phase]={'control_raw':cv,'candidate_raw':nv,'paired_candidate_over_control_raw':rr,'control_stats':stats(cv),'candidate_stats':stats(nv),'paired_ratio_stats':stats(rr),'ratio_of_arithmetic_mean_times':statistics.fmean(nv)/statistics.fmean(cv)}
   n=cfg['N'];w=2*n**3*6
   row={'configuration':key,'precision':cfg['precision'],'budget':cfg['budget'],'N':n,'repetitions':11,'useful_work_definition':'W=2*N^3*p with requested p=6','W_ops':w,'workload_rates_ops_per_second':{},'metrics':mm,'order':[s['order'] for s in ss],'byte_exact_match':True,'output_sha256':cfg['output_sha256'],'input_fnv1a64':{'A':ss[0]['calls']['control']['input_a_fnv1a64'],'B':ss[0]['calls']['control']['input_b_fnv1a64']},'fast_count_api_wall':sum(x<1 for x in mm['api_wall_seconds']['paired_candidate_over_control_raw'])}
   for phase in ('api_wall_seconds','profile_total_seconds','compute_reconstruct_seconds'):
    row['workload_rates_ops_per_second'][phase]={'control_per_call':[w/t for t in mm[phase]['control_raw']],'candidate_per_call':[w/t for t in mm[phase]['candidate_raw']], 'control_mean_wall_implied':w/statistics.fmean(mm[phase]['control_raw']),'candidate_mean_wall_implied':w/statistics.fmean(mm[phase]['candidate_raw'])}
   rows.append(row)
  metadata.append({'run_id':folder.name,'candidate_library':cmeta['candidate_lib'],'candidate_sha256':cmeta['candidate_sha256'],'control_sha256':cmeta['control_sha256'],'precision':cmeta['precision'],'sizes':cmeta['sizes'],'reps':cmeta['reps'],'runner_sha256':cmeta['runner_sha256'],'driver_sha256':cmeta['driver_sha256'],'started_utc':m['started_utc'],'finished_utc':m['finished_utc']})
 if len(rows)!=6:raise SystemExit(f'expected 6 configs, got {len(rows)}')
 summary={'status':'pass','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'campaign_directory':str(CAMPAIGN),'configuration_count':len(rows),'validation':'all 6 completed configs have byte-identical full C outputs, matching input hashes, actual OMP team size 64 over CPUs 0-63','runtime_policy':'OMP_WAIT_POLICY and GOMP_SPINCOUNT unset; 20ms parent pause after each call, outside API timing','primary_metric':'arithmetic mean candidate API wall / arithmetic mean control API wall; paired-ratio mean and median are separate; all 11 observations retained','useful_work':'W=2*N^3*p, p=6 requested for both FP32 and FP64 p6','calibration_context_only':{'fp32_single_precision_reference_TFLOPS':161.018,'fp32_mixed_reference_TFLOPS':151.738,'fp64_p6_mixed_reference_TFLOPS':84.423,'warning':'These calibration contexts are precision-specific; rates below are operation-equivalent rates from measured API/profile intervals, not a hardware peak or guaranteed AMX issue rate.'},'runs':metadata,'configurations':rows}
 (CAMPAIGN/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
 f32={r['N']:r for r in rows if r['precision']=='fp32'};f64={r['N']:r for r in rows if r['precision']=='fp64'}
 lines=['# Independent RC1 runtime confirmation','',
  'This independent campaign rechecked the exact RC1 archive against the frozen V3 control after the earlier matched batch. The candidate archive was not rebuilt or modified; its SHA-256 is verified in every run. GNU OpenMP runtime-default waiting was restored by unsetting `OMP_WAIT_POLICY` and `GOMP_SPINCOUNT`; the parent inserted a 20 ms park after calls outside measured API intervals. Both persistent children were pinned to CPUs 0–63 and reported 64 OpenMP workers.','',
  f'Campaign data: `{CAMPAIGN}`  ',f"Startup resources: `{CAMPAIGN/'startup_resources.txt'}`  ",f"Candidate SHA-256: `{metadata[0]['candidate_sha256']}`  ",f"Frozen V3 SHA-256: `{metadata[0]['control_sha256']}`  ",
  'All six configurations ran 11 paired repetitions. Each run checked deterministic input hashes and complete C-buffer SHA-256 equality. Every raw call, phase time, order, binary/source/library hash, and output hash is in `summary.json` and the per-run journals. No observations were dropped. API wall includes allocation and the complete profiled API call. Ratios below 1 favor RC1.','',
  '| Precision/workload | N | Fast calls | Median paired API ratio | Mean paired API ratio | Ratio of arithmetic mean API times | Exact C output |','|---|---:|---:|---:|---:|---:|---|']
 for row in rows:
  t=row['metrics']['api_wall_seconds'];label='FP32' if row['precision']=='fp32' else 'FP64 p6'
  lines.append(f"| {label} | {row['N']} | {row['fast_count_api_wall']}/11 | {t['paired_ratio_stats']['median']:.5f} | {t['paired_ratio_stats']['mean']:.5f} | {t['ratio_of_arithmetic_mean_times']:.5f} | yes |")
 lines += ['', '## Complete API-wall ratio sequences','', '| Precision | N | All 11 candidate/control ratios, in call order |','|---|---:|---|']
 for row in rows:
  label='FP32' if row['precision']=='fp32' else 'FP64 p6';raw=', '.join(f'{x:.5f}' for x in row['metrics']['api_wall_seconds']['paired_candidate_over_control_raw'])
  lines.append(f'| {label} | {row["N"]} | {raw} |')
 lines += ['', '## Precision-specific operation-equivalent rates','', 'Using the requested useful-work convention `W = 2 × N³ × p`, with p=6 for both workload families, the tables give mean-wall operation-equivalent rates at API wall, total profile, and compute/reconstruct profile intervals. The compute/reconstruct interval includes reconstruction, so it is not a direct AMX instruction throughput measurement. These rates are finite performance context, not hardware guarantees. Calibration references are kept separate by precision: 161.018 TFLOP/s FP32 single-precision calibration, 151.738 TFLOP/s mixed FP32 context, and 84.423 TFLOP/s FP64 p6 mixed context. Do not pool them or interpret them as measured DRAM lower bounds.','', '| Precision | N | Control API | RC1 API | Control profile total | RC1 profile total | Control compute/reconstruct | RC1 compute/reconstruct |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for row in rows:
  rr=row['workload_rates_ops_per_second'];label='FP32' if row['precision']=='fp32' else 'FP64 p6'
  vals=[]
  for ph in ('api_wall_seconds','profile_total_seconds','compute_reconstruct_seconds'):
   vals += [rr[ph]['control_mean_wall_implied']/1e12,rr[ph]['candidate_mean_wall_implied']/1e12]
  lines.append(f"| {label} | {row['N']} | "+' | '.join(f'{x:.3f}' for x in vals)+' |')
 lines += ['', 'At N=16384 FP32, median and mean tell different stories: the median paired ratio is 0.83545, with 9/11 calls faster, but two slow calls (ratios 3.13677 and 1.24862) yield mean paired ratio 1.08055 and ratio of arithmetic mean API times 1.07427. Retaining these observations changes the mean conclusion; no average speedup claim is warranted for that size. For FP64 p6 N=16384, the complete raw series and corresponding mean and median are in the table and machine-readable summary.','', 'N=16384 is an additional implementation performance check only. Byte-exact equality to frozen V3 does not constitute a new check against paper precision metrics. The N=4096 and N=8192 FP32 results repeat the improvement direction from the earlier RC1 batch on the paired medians and mean API time, while N=16384 highlights shared-host outlier sensitivity. Treat this as a candidate for further controlled study, not a hardware-performance guarantee.','']
 DOC.write_text('\n'.join(lines))
 print(json.dumps({'summary':str(CAMPAIGN/'summary.json'),'documentation':str(DOC),'validated':len(rows),'fp32_n16384_fast_calls':f32[16384]['fast_count_api_wall']},indent=2))
if __name__=='__main__':main()
