#!/usr/bin/env python3
"""Offline integrity and descriptive ranking for the packed rotation screen."""
import csv, json, math, statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXPECTED=[f'candidate_{i:02d}' for i in range(1,17)]
BUDGETS=(6,10,15,21)
def readcsv(p):
    with p.open(newline='') as f:
        r=csv.DictReader(f,strict=True); rows=list(r)
        if len(r.fieldnames or [])!=37: raise ValueError(f'{p}: expected 37 columns')
        return rows
def main():
    records=HERE/'records'; items=[]; missing=[]
    for i in range(1,17):
        matches=list(records.glob(f'candidate_{i:02d}_*_n8192_fp64/result.csv'))
        if not matches: missing.append(f'candidate_{i:02d}'); continue
        if len(matches)!=1: raise ValueError(f'duplicate candidate result for index {i}')
        path=matches[0]; rows=readcsv(path); meta=json.loads((path.parent/'metadata.json').read_text())
        assert len(rows)==4 and {int(r['budget']) for r in rows}==set(BUDGETS)
        ident=meta['build_identity']; cid=ident['candidate_id']
        entry={'index':i,'candidate_id':cid,'csv':str(path.relative_to(HERE)),'gate':None,'ctest_log':None,'budgets':{}}
        tag=path.parent.name.removesuffix('_n8192_fp64')
        gate=HERE/'gates'/f'{tag}.json'; ctest=HERE/'logs'/f'{tag}_ctest.log'
        entry['gate']=str(gate.relative_to(HERE)) if gate.exists() else None
        entry['full20_gate_pass']=bool(gate.exists() and json.loads(gate.read_text()).get('status')=='pass' and len(json.loads(gate.read_text()).get('cases',[]))==20)
        entry['ctest_log']=str(ctest.relative_to(HERE)) if ctest.exists() else None
        entry['ctest_pass']=bool(ctest.exists() and '100% tests passed' in ctest.read_text())
        for row in rows:
            budget=int(row['budget']); reps=int(row['repetitions']); assert reps==3 and row['precision']=='fp64' and row['status']=='ok' and row['accuracy_scope']=='production_semantics'
            samples=[float(x) for x in row['raw_api_call_wall_s'].split(';')]
            cp=path.parent/f'checkpoint.fp64.8192.{budget}.json'; chk=json.loads(cp.read_text())
            assert chk.get('complete') is True and chk.get('completed_timed_repetitions')==3 and len(chk.get('call_wall_seconds',[]))==3
            assert len(samples)==3 and all(math.isclose(x,float(y),rel_tol=1e-10,abs_tol=2e-9) for x,y in zip(samples,chk['call_wall_seconds']))
            entry['budgets'][str(budget)]={'api_wall_mean_s':float(row['api_call_wall_s_mean']),'api_wall_sd_s':float(row['api_call_wall_s_std']),
                'raw_api_wall_s':samples,'split_s_mean':float(row['split_s_mean']),'pack_s_mean':float(row['pack_s_mean']),
                'compute_recon_s_mean':float(row['compute_recon_s_mean']),'profile_total_s_mean':float(row['profile_total_s_mean']),
                'mkl_gemm_s_mean':float(row['mkl_gemm_s']),'raw_mkl_gemm_s':row.get('raw_mkl_gemm_s'),
                'packed_output_allocation_bytes':next(x['packed_output_allocation_bytes'] for x in meta['packed_allocation_estimates'] if x['budget']==budget),
                'padding_extra_bytes':next(x['padding_extra_bytes'] for x in meta['packed_allocation_estimates'] if x['budget']==budget)}
        items.append(entry)
    gates_ok=len(items)==16 and all(x['full20_gate_pass'] and x['ctest_pass'] for x in items)
    leaders={}
    for b in BUDGETS:
        ranked=sorted(({'candidate_id':x['candidate_id'],'api_wall_mean_s':x['budgets'][str(b)]['api_wall_mean_s'],'record':x['csv']} for x in items),key=lambda x:x['api_wall_mean_s'])
        leaders[str(b)]={'screen_leader':ranked[0] if ranked else None,'all_candidates_ranked':ranked,
                         'interpretation':'descriptive leader from three timed repetitions; not a statistically established winner'}
    v3={}
    for p in records.glob('frozen_v3_*/result.csv'):
        rows=readcsv(p); reps=int(rows[0]['repetitions']) if rows else 0
        v3[p.parent.name]={'repetitions':reps,'records':{str(int(r['budget'])):{'api_call_wall_s_mean':float(r['api_call_wall_s_mean']),'raw_api_wall_s':r['raw_api_call_wall_s']} for r in rows}}
    payload={'schema':'ozamx-packed-rotation-screen-analysis-v1','dataset_complete':not missing and gates_ok,
      'expected_candidates':16,'completed_candidates':len(items),'missing':missing,'all_candidate_full20_gates_and_ctest_passed':gates_ok,
      'outlier_removal':False,'screen_leaders':leaders,'frozen_v3_controls':v3,'candidates':items,
      'claim_limit':'Three repetitions support descriptive screen leaders only; do not call any candidate a winner without a follow-up paired validation.'}
    (HERE/'analysis.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    lines=['# V4 zero-gap packed-slab rotation screen','',f"Coverage: {len(items)}/16 candidates; complete and all gates/CTest: {payload['dataset_complete']}.",'',
      'Each candidate passed a full 20-case numeric gate and CTest before four N=8192 FP64 budgets were timed. All three API-wall samples are retained; no outliers are removed. The lowest observed mean per budget below is a descriptive screen leader only, not a statistically validated winner.','',
      '| Budget | Descriptive screen leader | API wall mean (s) | packed output bytes | padding extra (bytes) |','|---:|---|---:|---:|---:|']
    byid={x['candidate_id']:x for x in items}
    for b in BUDGETS:
      lead=leaders[str(b)]['screen_leader']
      if not lead: lines.append(f'| P{b} | pending | | | |'); continue
      d=byid[lead['candidate_id']]['budgets'][str(b)]
      lines.append(f"| P{b} | `{lead['candidate_id']}` | {lead['api_wall_mean_s']:.9f} | {d['packed_output_allocation_bytes']} | {d['padding_extra_bytes']} |")
    lines+=['','Full phase/API and oneMKL timing values, all reps/checkpoints, controls, gate references, and incomplete coverage are in `analysis.json` and the retained result tree. The packed-output byte estimate covers persistent uint16 A/B component arrays, excluding temporary residual buffers and public input/output.','']
    (HERE/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps({'completed':len(items),'expected':16,'all_gates':gates_ok,'dataset_complete':payload['dataset_complete'],'missing':missing},indent=2))
if __name__=='__main__':main()
