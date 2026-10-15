#!/usr/bin/env python3
"""Validate and summarize a completed reconstruction-ILP4 campaign."""
import csv, hashlib, json, pathlib, statistics, sys

REPO=pathlib.Path(__file__).resolve().parents[5]
SRC=REPO/'bench/8454h/roofline_v4/recon_ilp_src'
RUN=REPO/'bench/8454h/roofline_v4/recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z'
DOC=REPO/'docs/8454H_V4_RECON_ILP_RESULTS.md'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load_csv(label, reps):
    d=RUN/'records'/label; p=d/'result.csv'
    with p.open(newline='') as f:
        reader=csv.DictReader(f); rows=list(reader)
        if len(reader.fieldnames or [])!=37 or len(rows)!=4: raise RuntimeError(f'bad CSV schema/rows: {p}')
    by={r['budget']:r for r in rows}
    if set(by)!=set(('6','10','15','21')): raise RuntimeError(f'budget set mismatch: {p}')
    for budget,row in by.items():
        if row['status']!='ok' or int(row['repetitions'])!=reps or int(row['N'])!=8192: raise RuntimeError(f'row status/reps mismatch: {p} {budget}')
        vectors={k:[float(x) for x in row[k].split(';')] for k in ('raw_api_call_wall_s','raw_compute_recon_s','raw_profile_total_s')}
        if any(len(v)!=reps for v in vectors.values()): raise RuntimeError(f'raw sample count mismatch: {p} {budget}')
        chk=d/f'checkpoint.fp64.8192.{budget}.json'; q=json.loads(chk.read_text())
        if q.get('complete') is not True or q.get('requested_repetitions')!=reps or q.get('completed_timed_repetitions')!=reps:
            raise RuntimeError(f'incomplete checkpoint: {chk}')
        if any(abs(float(a)-b)>2e-9 for a,b in zip(q['call_wall_seconds'],vectors['raw_api_call_wall_s'])):
            raise RuntimeError(f'API raw sample/checkpoint mismatch: {chk}')
    return by

def med(row,key): return statistics.median(float(x) for x in row[key].split(';'))

def main():
    ds=json.loads((RUN/'dataset.json').read_text())
    if ds.get('completed_utc') is None: raise RuntimeError('campaign is not complete')
    full_gates=[]; artifacts=[]; results={}
    for state in ds['configs']:
        b,flag=state['batch'],state['ilp4']; tag='on' if flag else 'off'
        identp=RUN/f'builds/candidate_b{b}_{tag}_m0/build_identity.json'
        ident=json.loads(identp.read_text()); lib=identp.parent/'libozamx.a'; binary=identp.parent/'ozamx_benchmark'
        if sha(lib)!=ident['library_sha256'] or sha(binary)!=ident['benchmark_binary_sha256']:
            raise RuntimeError(f'build artifact SHA mismatch: {identp.parent}')
        if ident['reconstruction_ilp4']!=('ON' if flag else 'OFF') or ident['fp64_batch']!=b:
            raise RuntimeError(f'wrong build options: {identp}')
        if ident['reconstruction_source_sha256']!=sha(REPO/'bench/8454h/roofline_v4/recon_ilp_src/src/reconstruct_ilp4.S'):
            raise RuntimeError(f'assembly SHA mismatch: {identp}')
        gate_rel=state['gates'][0]['gate']; gate=RUN/gate_rel; gd=json.loads(gate.read_text())
        if gd.get('status')!='pass' or len(gd.get('cases',[]))!=20: raise RuntimeError(f'full gate incomplete: {gate}')
        full_gates.append({'path':gate_rel,'sha256':sha(gate),'cases':20,'status':'pass'})
        ct=RUN/state['gates'][0]['ctest_log']
        if '100% tests passed' not in (RUN/ct).read_text(): raise RuntimeError(f'CTest failed: {ct}')
        obj=RUN/f'disassembly/b{b}_{tag}_m0_gemm_objdump.txt'; calls='ozamx_reconstruct64_ilp4' in obj.read_text()
        if calls!=flag: raise RuntimeError(f'ON/OFF relocation proof failed: {obj}')
        csvlabel=f'b{b}_{tag}_m0_n8192_fp64'; rows=load_csv(csvlabel,3)
        artifacts.append({'batch':b,'ilp4':'ON' if flag else 'OFF','library_path':str(lib.relative_to(REPO)),
          'library_sha256':sha(lib),'binary_path':str(binary.relative_to(REPO)),'binary_sha256':sha(binary),
          'build_identity_path':str(identp.relative_to(REPO)),'build_identity_sha256':sha(identp),
          'mode':0,'late64_wide_call_relocation':calls,'objdump_path':str(obj.relative_to(REPO))})
        for budget,row in rows.items():
            results[(b,flag,budget)]={key:med(row,key) for key in ('raw_api_call_wall_s','raw_compute_recon_s','raw_profile_total_s')}
    control_labels=['frozen_v3_initial_retry1','frozen_v3_after_batch8','frozen_v3_after_batch21']
    controls={label:load_csv(label,7) for label in control_labels}
    controls_json=[]
    for label,rows in controls.items():
        cp=RUN/'records'/label/'result.csv'
        controls_json.append({'label':label,'csv':str(cp.relative_to(REPO)),'csv_sha256':sha(cp),'repetitions':7,
          'api_wall_median_by_budget':{b:med(row,'raw_api_call_wall_s') for b,row in rows.items()},
          'compute_recon_median_by_budget':{b:med(row,'raw_compute_recon_s') for b,row in rows.items()}})
    control_drift=[]
    for left,right in zip(control_labels,control_labels[1:]):
        for budget in ('6','10','15','21'):
            a=med(controls[left][budget],'raw_api_call_wall_s'); b=med(controls[right][budget],'raw_api_call_wall_s')
            control_drift.append({'from':left,'to':right,'budget':budget,'api_wall_median_s':[a,b],'delta_percent':100*(b/a-1)})
    paired=[]
    for b in (2,8,12,21):
        for budget in ('6','10','15','21'):
            off=results[(b,False,budget)]; on=results[(b,True,budget)]
            paired.append({'batch':b,'budget':budget,
              'off_api_wall_median_s':off['raw_api_call_wall_s'],'on_api_wall_median_s':on['raw_api_call_wall_s'],
              'api_wall_delta_percent':100*(on['raw_api_call_wall_s']/off['raw_api_call_wall_s']-1),
              'off_compute_recon_median_s':off['raw_compute_recon_s'],'on_compute_recon_median_s':on['raw_compute_recon_s'],
              'compute_recon_delta_percent':100*(on['raw_compute_recon_s']/off['raw_compute_recon_s']-1),
              'off_profile_total_median_s':off['raw_profile_total_s'],'on_profile_total_median_s':on['raw_profile_total_s'],
              'profile_total_delta_percent':100*(on['raw_profile_total_s']/off['raw_profile_total_s']-1),
              'off_api_wall_samples':[float(x) for x in load_csv(f'b{b}_off_m0_n8192_fp64',3)[budget]['raw_api_call_wall_s'].split(';')],
              'on_api_wall_samples':[float(x) for x in load_csv(f'b{b}_on_m0_n8192_fp64',3)[budget]['raw_api_call_wall_s'].split(';')],
              'off_compute_recon_samples':[float(x) for x in load_csv(f'b{b}_off_m0_n8192_fp64',3)[budget]['raw_compute_recon_s'].split(';')],
              'on_compute_recon_samples':[float(x) for x in load_csv(f'b{b}_on_m0_n8192_fp64',3)[budget]['raw_compute_recon_s'].split(';')],
              'off_profile_total_samples':[float(x) for x in load_csv(f'b{b}_off_m0_n8192_fp64',3)[budget]['raw_profile_total_s'].split(';')],
              'on_profile_total_samples':[float(x) for x in load_csv(f'b{b}_on_m0_n8192_fp64',3)[budget]['raw_profile_total_s'].split(';')]})
    source_map=ds['source_sha256']
    strict_probe_dirs=sorted((REPO/'bench/8454h/roofline_v4/recon_ilp_runs').glob('probe_bits_strict_*'))
    if not strict_probe_dirs: raise RuntimeError('strict finite-bit probe rerun is missing')
    probe_dir=strict_probe_dirs[-1]
    probe_logs={s:(probe_dir/f'probe_{s}.log') for s in ('ON','OFF')}
    if any(not p.is_file() or p.read_text().strip()!='direct ordered reconstruction probe passed' for p in probe_logs.values()):
        raise RuntimeError('strict ON/OFF direct probe failed or has no passing log')
    tree_hash=hashlib.sha256(json.dumps(source_map,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    summary={'schema':'ozamx-v4-reconstruction-ilp4-results-1','run_dir':str(RUN.relative_to(REPO)),
      'started_utc':ds['started_utc'],'completed_utc':ds['completed_utc'],'source_tree_sha256':tree_hash,
      'core_source_sha256':{'gemm.cpp':source_map['src/gemm.cpp'],'reconstruct_ilp4.S':source_map['src/reconstruct_ilp4.S']},
      'runtime_protocol':{'cpu_affinity':ds['cpuset'],'threads':ds['threads'],'OMP_PLACES':'cores','OMP_PROC_BIND':'close',
        'MKL_THREADING_LAYER':'GNU','MKL_NUM_THREADS':ds['threads'],'workspace_cache_bytes':ds['workspace_cache_bytes'],'seed':ds['seed']},
      'mkl_runtime_sha256':ds['mkl_runtime_sha256'],'frozen_v3_library_sha256':ds['v3_library_sha256'],
      'serialization_lock':{'path':'/tmp/ozamx-perf.lock','exclusive_flock_held_for_campaign':True,
                            'started_utc':ds['started_utc'],'completed_utc':ds['completed_utc']},
      'verification':{'candidate_configs':8,'all_full20_gates_pass':len(full_gates)==8,'all_full20_cases_pass':sum(x['cases'] for x in full_gates),
        'ctest_pass_count':8,'all_mode0_on_builds_reference_assembly':all(x['late64_wide_call_relocation'] for x in artifacts if x['ilp4']=='ON'),
        'all_mode0_off_builds_omit_assembly_call':not any(x['late64_wide_call_relocation'] for x in artifacts if x['ilp4']=='OFF'),
        'probe_on_and_off_direct_reference_pass':True},
      'configuration_artifacts':artifacts,'gates':full_gates,'controls':controls_json,'adjacent_v3_control_drift':control_drift,
      'strict_probe':{'run_dir':str(probe_dir.relative_to(REPO)),'source_sha256':{'probe_cpp':sha(SRC/'tests/reconstruct_ilp4_probe.cpp'),
        'abi_shim':sha(SRC/'tests/reconstruct_ilp4_abi_probe.S'),'assembly':sha(SRC/'src/reconstruct_ilp4.S')},
        'on_log_sha256':sha(probe_logs['ON']),'off_log_sha256':sha(probe_logs['OFF'])},
      'paired_medians':paired,'failed_attempts':ds.get('failed_attempts',[]),
      'interpretation':'Three-repetition screen only. Report observed differences; this is not a winner selection.'}
    (RUN/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
    ds['analysis_path']=str((RUN/'analysis.json').relative_to(REPO)); ds['analysis_sha256']=sha(RUN/'analysis.json')
    ds['candidate_artifacts']=artifacts; ds['serialization_lock']=summary['serialization_lock']
    (RUN/'dataset.json').write_text(json.dumps(ds,indent=2)+'\n')
    lines=['# V4 ordered reconstruction ILP4 results','',
      f"The 8-configuration, three-repetition N=8192 FP64 screen completed {ds['started_utc']}–{ds['completed_utc']} on 64 pinned CPUs. Each configuration passed four CTests and a strict 20-case byte/transaction gate before timing. The new assembly was enabled only for late FP64 wide reconstruction; FP32 behavior remained in mode 0.",'',
      'The direct assembly probe compared all 32×32 outputs against an independent scalar reference for strides 32, 40, 136, 264 and 1032 double elements, counts 1, 2, 4, 8, 12 and 21, finite and special-value inputs. Every finite output matched bitwise, including finite lanes in special-value runs; nonfinite classifications and infinity signs matched; row padding and trailing guards remained unchanged. The ABI shim verified rbx, rbp and r12–r15. ON and OFF probes both passed.','',
      'ON object disassembly contains the `ozamx_reconstruct64_ilp4` relocation in the mode-0 Late64 wide path; OFF objects contain no call relocation. The source assembly SHA-256 is `'+summary['core_source_sha256']['reconstruct_ilp4.S']+'`.','',
      '## Paired API wall and reconstruction profile medians','',
      '| Batch | FP64 budget | OFF API (s) | ON API (s) | API change | OFF compute/reconstruct (s) | ON compute/reconstruct (s) | Compute change | Profile-total change |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for x in paired:
        lines.append(f"| {x['batch']} | {x['budget']} | {x['off_api_wall_median_s']:.6f} | {x['on_api_wall_median_s']:.6f} | {x['api_wall_delta_percent']:+.2f}% | {x['off_compute_recon_median_s']:.6f} | {x['on_compute_recon_median_s']:.6f} | {x['compute_recon_delta_percent']:+.2f}% | {x['profile_total_delta_percent']:+.2f}% |")
    lines += ['', '## Frozen V3 control drift','', '| Control interval | Budget | V3 API median before (s) | V3 API median after (s) | Drift |','|---|---:|---:|---:|---:|']
    for x in control_drift: lines.append(f"| {x['from']} → {x['to']} | {x['budget']} | {x['api_wall_median_s'][0]:.6f} | {x['api_wall_median_s'][1]:.6f} | {x['delta_percent']:+.2f}% |")
    lines += ['', 'The rows retain every three-sample API vector and the matching raw compute/reconstruction and profile-total vectors in the per-configuration CSV files. The full CSV also retains MKL GEMM timings and runtime fields. N=8192 control CSVs retain seven samples per budget. The N=256 OFF preflight is reused from the prior preparation run; the ON half is recorded in this run.','',
      'This short screen has no declared winner. Batch 12 ON showed a marked increase for budgets 6 and 10, visible in both API wall and compute/reconstruction samples. Batch 21 ON was faster for budgets 6 and 10 but about 90% slower for budget 21. These large changes remain in the data and should be checked in the matched seven-repetition follow-up. Batch 2 and 8 changes are smaller and comparable to some V3 bracket drift.','',
      '## Reproducibility artifacts','',f"- Dataset: `{(RUN/'dataset.json').relative_to(REPO)}`",f"- Analysis JSON: `{(RUN/'analysis.json').relative_to(REPO)}`",f"- Build and library manifest: `{(RUN/'dataset.json').relative_to(REPO)}` (`candidate_artifacts`)",
      '- Global lock: `/tmp/ozamx-perf.lock` held exclusively from campaign start through the final control.',
      '- Immutable V3 SHA-256: `'+ds['v3_library_sha256']+'`; original and paper-release archive paths were byte-identical.',
      '- First V3 timing attempt hit the archive binary permission mode 0444. Its log and SHA are preserved; timing resumed with a freshly linked driver against the same frozen V3 static library.','']
    DOC.write_text('\n'.join(lines))
    print(json.dumps({'analysis':str((RUN/'analysis.json').relative_to(REPO)),'doc':str(DOC.relative_to(REPO)),
                      'artifact_count':len(artifacts),'paired_rows':len(paired)},indent=2))

if __name__=='__main__': main()
