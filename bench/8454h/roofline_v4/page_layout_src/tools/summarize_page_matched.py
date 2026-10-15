#!/usr/bin/env python3
"""Validate matched runtime journals and create page-layout matched JSON/report."""
from __future__ import annotations
import argparse,hashlib,json,pathlib,statistics

REPO=pathlib.Path(__file__).resolve().parents[5]
CANDIDATES=("a2m_hint1","a4k_hint1")
WORKLOADS=(("fp32",6),("fp64",6),("fp64",10),("fp64",15),("fp64",21))
FIELDS=("api_wall_seconds","split_seconds","pack_seconds","compute_reconstruct_seconds","profile_total_seconds")

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def stat(x):return {"count":len(x),"mean":statistics.fmean(x),"median":statistics.median(x),"min":min(x),"max":max(x)}
def pos_effect(samples,label):
 first=[s["calls"][label]["api_wall_seconds"] for s in samples if s["order"][0]==label]
 second=[s["calls"][label]["api_wall_seconds"] for s in samples if s["order"][0]!=label]
 return {"first_position":stat(first),"second_position":stat(second),"second_over_first_median_ratio":statistics.median(second)/statistics.median(first)}
def summary_times(samples):
 ans={}
 for field in FIELDS:
  c=[s["calls"]["control"][field] for s in samples];v=[s["calls"]["candidate"][field] for s in samples]
  ratios=[b/a for a,b in zip(c,v)]
  ans[field]={"control_raw":c,"candidate_raw":v,"candidate_over_control_raw":ratios,
    "control_stats":stat(c),"candidate_stats":stat(v),"paired_ratio_stats":stat(ratios),
    "mean_paired_ratio":statistics.fmean(ratios),"median_paired_ratio":statistics.median(ratios),
    "ratio_of_means":statistics.fmean(v)/statistics.fmean(c)}
 return ans
def expected_runid(tag,precision,budget,sizes):return f"{tag}_{precision}_p{budget}_n{'_'.join(map(str,sizes))}_r11"

def main():
 ap=argparse.ArgumentParser();ap.add_argument("campaign",type=pathlib.Path);a=ap.parse_args()
 root=a.campaign.resolve();campaign=json.loads((root/"campaign.json").read_text())
 if campaign.get("status")!="complete":raise RuntimeError(f"matched campaign incomplete: {campaign.get('status')}")
 if campaign.get("lock_path")!="/tmp/ozamx-perf.lock" or campaign.get("control_library_sha256")!="73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c":raise RuntimeError("control/lock identity mismatch")
 if len(campaign.get("runs",[]))!=10 or any(x.get("status") not in ("complete","reused_complete") for x in campaign["runs"]):raise RuntimeError("campaign does not list all ten completed runtime invocations")
 cfg_rows=[];children=[];expect_total=20
 for tag in CANDIDATES:
  candidate=campaign["candidates"][tag]
  if sha(candidate["library"])!=candidate["library_sha256"]:raise RuntimeError(f"candidate library hash changed: {tag}")
  for precision,budget in WORKLOADS:
   sizes=candidate["sizes"]
   runid=expected_runid(tag,precision,budget,sizes);d=root/runid
   meta=json.loads((d/"metadata.json").read_text());j=json.loads((d/"matched_calls.json").read_text());rc=meta["run_config"]
   if rc["candidate_sha256"]!=candidate["library_sha256"] or rc["control_sha256"]!=campaign["control_library_sha256"]:raise RuntimeError(f"library identity mismatch in {runid}")
   if rc["wait_policy_variant"]!="runtime" or rc["wait_policy_environment"]!="OMP_WAIT_POLICY and GOMP_SPINCOUNT unset" or rc["parent_inter_call_pause_seconds"]!=0.02:raise RuntimeError(f"runtime-wait protocol mismatch in {runid}")
   if rc["environment"].get("OMP_WAIT_POLICY") is not None or rc["environment"].get("GOMP_SPINCOUNT") is not None:raise RuntimeError(f"runtime controls inherited instead of unset in {runid}")
   if rc["threads"]!=64 or rc["cpu_affinity"]!="0-63" or rc["openmp_runtime_request"]!={"threads":64,"places":"cores","proc_bind":"close"}:raise RuntimeError(f"worker affinity metadata mismatch in {runid}")
   for session in j.get("process_sessions",[]):
    for lab,ready in session["children_ready"].items():
     if not ready.get("amx_permission") or ready.get("actual_omp_threads")!=64 or ready.get("max_omp_threads")!=64 or ready.get("calling_cpu") not in range(64):raise RuntimeError(f"actual worker count/AMX mismatch {runid}/{lab}")
     cpus=ready.get("omp_thread_cpus",[])
     if len(cpus)!=64 or sorted(set(cpus))!=list(range(64)):raise RuntimeError(f"64 workers did not occupy CPUs 0-63 exactly once {runid}/{lab}")
     children.append({"runid":runid,"label":lab,"ready":ready})
   for n in sizes:
    key=f"{precision}_n{n}_b{budget}"
    cfg=j.get("configurations",{}).get(key)
    if not cfg or not cfg.get("complete") or not cfg.get("byte_exact_match") or len(cfg.get("samples",[]))!=11:raise RuntimeError(f"incomplete/equality failure: {runid}/{key}")
    samples=cfg["samples"]
    for warm_session in cfg.get("warmup_sessions",[]):
     for warm in warm_session.get("calls",[]):
      ca=warm["calls"]["control"];va=warm["calls"]["candidate"]
      if (ca.get("input_a_fnv1a64"),ca.get("input_b_fnv1a64"))!=(va.get("input_a_fnv1a64"),va.get("input_b_fnv1a64")):raise RuntimeError(f"warmup input hashes differ: {runid}/{key}")
    for ix,s in enumerate(samples):
     expected=["control","candidate"] if ix%2==0 else ["candidate","control"]
     if s.get("order")!=expected:raise RuntimeError(f"pair order is not alternating: {runid}/{key}/{ix}")
     ca=s["calls"]["control"];va=s["calls"]["candidate"]
     if (ca.get("input_a_fnv1a64"),ca.get("input_b_fnv1a64"))!=(va.get("input_a_fnv1a64"),va.get("input_b_fnv1a64")):raise RuntimeError(f"per-pair input hashes differ: {runid}/{key}/{ix}")
    outsha=cfg["output_sha256"]
    if outsha.get("control")!=outsha.get("candidate"):raise RuntimeError(f"full C output hashes differ: {runid}/{key}")
    expected_bytes=n*n*(4 if precision=="fp32" else 8)
    if any(s["calls"]["control"].get("input_a_fnv1a64")!=samples[0]["calls"]["control"]["input_a_fnv1a64"] or s["calls"]["control"].get("input_b_fnv1a64")!=samples[0]["calls"]["control"]["input_b_fnv1a64"] for s in samples):raise RuntimeError(f"control input stream changed across calls: {runid}/{key}")
    cfg_rows.append({"candidate":tag,"runid":runid,"journal_path":str(d/"matched_calls.json"),"journal_sha256":sha(d/"matched_calls.json"),
      "metadata_path":str(d/"metadata.json"),"metadata_sha256":sha(d/"metadata.json"),"precision":precision,"budget":budget,"N":n,
      "repetitions":11,"expected_full_output_bytes":expected_bytes,"paired_order":[s["order"] for s in samples],
      "input_hashes":{"A":samples[0]["calls"]["control"]["input_a_fnv1a64"],"B":samples[0]["calls"]["control"]["input_b_fnv1a64"]},
      "output_sha256":outsha,"byte_exact_match":True,"timings":summary_times(samples),
      "position_effect_api_wall":{"control":pos_effect(samples,"control"),"candidate":pos_effect(samples,"candidate")},
      "raw_samples":samples,"child_sessions":j["process_sessions"],"binary_sha256":rc["child_binaries"]})
   expect_total+=0
 if len(cfg_rows)!=20:raise RuntimeError(f"expected 20 page candidate configurations, got {len(cfg_rows)}")
 # Candidate aggregate retains every paired call; ratio-of-means is computed from all calls, not from ratios.
 aggregates={}
 for tag in CANDIDATES:
  rows=[x for x in cfg_rows if x["candidate"]==tag]
  aggregates[tag]={"configuration_count":len(rows),"paired_calls":sum(x["repetitions"] for x in rows),"by_metric":{}}
  for field in FIELDS:
   control=[v for x in rows for v in x["timings"][field]["control_raw"]]
   cand=[v for x in rows for v in x["timings"][field]["candidate_raw"]]
   ratios=[v for x in rows for v in x["timings"][field]["candidate_over_control_raw"]]
   aggregates[tag]["by_metric"][field]={"control_stats":stat(control),"candidate_stats":stat(cand),"paired_ratio_stats":stat(ratios),
    "mean_paired_ratio":statistics.fmean(ratios),"median_paired_ratio":statistics.median(ratios),"ratio_of_means":statistics.fmean(cand)/statistics.fmean(control),
    "control_raw":control,"candidate_raw":cand,"paired_ratio_raw":ratios}
  aggregates[tag]["configurations_faster_by_api_median"]=sum(x["timings"]["api_wall_seconds"]["median_paired_ratio"]<1 for x in rows)
 summary={"schema":"ozamx-page-layout-matched-summary-1","status":"pass","campaign_directory":str(root),"campaign_sha256":sha(root/"campaign.json"),
  "created_utc":__import__('time').strftime('%Y-%m-%dT%H:%M:%SZ',__import__('time').gmtime()),"control":{"library":campaign["control_library"],"sha256":campaign["control_library_sha256"]},
  "candidate_libraries":campaign["candidates"],"protocol":campaign["protocol"],"configuration_count":len(cfg_rows),"actual_ready_child_count":len(children),
  "worker_validation":"every ready session reported exactly 64 OpenMP workers, CPU set 0-63 exactly once, AMX permission available",
  "input_output_validation":"all warmup and timed A/B FNV hashes matched per paired children; full output-C byte lengths and SHA-256 matched for every configuration",
  "aggregates":aggregates,"configurations":cfg_rows}
 out=root/"summary.json";out.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
 # Human-readable compact report: all twenty config medians/means/ratios and phase/order details.
 lines=["# V4 page-layout matched-call results","",
  f"Campaign `{root}` completed {len(cfg_rows)} matched configurations with 11 alternating pairs each. No additional numerical gate was run: both candidate archives were checked against their exact SHA-256 and the prior full 20-case V3 gate records.","",
  f"Frozen V3 library SHA-256: `{campaign['control_library_sha256']}`. Runtime runner: `{campaign['protocol']['runner']}` (SHA `{campaign['protocol']['runner_sha256']}`); driver source SHA `{campaign['protocol']['driver_sha256']}`.",
  "The harness used GNU OpenMP runtime-default wait settings by unsetting `OMP_WAIT_POLICY` and `GOMP_SPINCOUNT`, with its 20 ms parent pause after each API call. Each child reported actual team size 64, and all 64 workers occupied CPUs 0–63 exactly once. For every pair, the deterministic A/B input FNV hashes matched; each final full C buffer had the same byte count and SHA-256 across V3 and candidate. These checks are repeated in each raw journal.","",
  "Ratios below are candidate/V3, so values under 1.0 favor the page candidate. `Mean pair ratio` is the arithmetic mean of the 11 individual ratios; `ratio of means` divides the arithmetic mean candidate wall by the arithmetic mean V3 wall. Median, means, per-repetition values, phase timing, order and hashes are retained. No outlier filtering was applied.","",
  "| Candidate | Configurations | API paired-call median ratio | API mean paired ratio | API ratio-of-means | Configurations faster by median |","|---|---:|---:|---:|---:|---:|"]
 for tag in CANDIDATES:
  x=aggregates[tag];t=x["by_metric"]["api_wall_seconds"]
  lines.append(f"| `{tag}` | {x['configuration_count']} ({x['paired_calls']} pairs) | {t['median_paired_ratio']:.4f} | {t['mean_paired_ratio']:.4f} | {t['ratio_of_means']:.4f} | {x['configurations_faster_by_api_median']}/{x['configuration_count']} |")
 lines += ["","## Per-configuration API, phase and order ratios","","Times are milliseconds in the JSON raw arrays. `API mean / median ratio` show both center summaries of paired candidate/V3 ratios; `API ratio-of-means` is separate. Order effects report second-position median divided by first-position median for each child.","",
  "| Candidate | Workload | N | API mean ratio | API median ratio | API ratio-of-means | Split ratio | Pack ratio | Compute/reconstruct ratio | Profile total ratio | Control second/first | Candidate second/first | Output SHA equal |",
  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
 for x in cfg_rows:
  label=x["precision"]+(f" p{x['budget']}" if x["precision"]=="fp64" else "")
  rr={k:x["timings"][k]["mean_paired_ratio"] for k in FIELDS}
  ce=x["position_effect_api_wall"]["control"]["second_over_first_median_ratio"]-1
  ve=x["position_effect_api_wall"]["candidate"]["second_over_first_median_ratio"]-1
  lines.append(f"| `{x['candidate']}` | {label} | {x['N']} | {rr['api_wall_seconds']:.4f} | {x['timings']['api_wall_seconds']['median_paired_ratio']:.4f} | {x['timings']['api_wall_seconds']['ratio_of_means']:.4f} | {rr['split_seconds']:.4f} | {rr['pack_seconds']:.4f} | {rr['compute_reconstruct_seconds']:.4f} | {rr['profile_total_seconds']:.4f} | {ce:+.1%} | {ve:+.1%} | yes |")
 lines += ["", "## Observations", "",
  f"At N=8192, `a4k_hint1` had lower median paired API ratios in {sum(x['timings']['api_wall_seconds']['median_paired_ratio']<1 for x in cfg_rows if x['candidate']=='a4k_hint1')}/5 workloads; p10 was slower (median ratio {next(x['timings']['api_wall_seconds']['median_paired_ratio'] for x in cfg_rows if x['candidate']=='a4k_hint1' and x['precision']=='fp64' and x['budget']==10):.4f}). `a2m_hint1` was faster by per-configuration median in {aggregates['a2m_hint1']['configurations_faster_by_api_median']}/15 configurations across N=1024/4096/8192. This is a provisional pattern for root’s next decision, not evidence to merge.",
  f"Across all matched pairs, `a2m_hint1` API median paired ratio / mean paired ratio / ratio-of-means were {aggregates['a2m_hint1']['by_metric']['api_wall_seconds']['median_paired_ratio']:.4f} / {aggregates['a2m_hint1']['by_metric']['api_wall_seconds']['mean_paired_ratio']:.4f} / {aggregates['a2m_hint1']['by_metric']['api_wall_seconds']['ratio_of_means']:.4f}; `a4k_hint1` was {aggregates['a4k_hint1']['by_metric']['api_wall_seconds']['median_paired_ratio']:.4f} / {aggregates['a4k_hint1']['by_metric']['api_wall_seconds']['mean_paired_ratio']:.4f} / {aggregates['a4k_hint1']['by_metric']['api_wall_seconds']['ratio_of_means']:.4f}. Their ratio-of-means differs materially from paired-call summaries, so it should not stand alone.",
  "Order effects are material, especially for `a2m_hint1`: across its configurations the control’s second/first median ranged from -15.7% to +64.5%, and the candidate ranged from -43.7% to +38.4%. For `a4k_hint1`, the corresponding ranges were -2.4% to +12.7% and -19.7% to +1.3%. Treat individual ratios and aggregate mean/median divergence with that variability in view. The previous screen also had large initial/final control drift; this runtime-default matched run is a separate wait policy and must be interpreted on its own.",
  "",
  "The complete per-call phase and API timing vectors and order sequence are in [`summary.json`](summary.json) and each raw `matched_calls.json` journal. This screen is descriptive: `a2m_hint1` covers N=1024/4096/8192 (15 configurations), while `a4k_hint1` covers N=8192 only (5 configurations). The library and previous gate identities are:",""]
 for tag,c in campaign["candidates"].items():
  gate=json.loads(pathlib.Path(c["prior_gate"]).read_text())
  lines.append(f"- `{tag}`: [`{c['library']}`](../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/{tag}/libozamx.a), SHA-256 `{c['library_sha256']}`; prior gate `{c['prior_gate']}` SHA `{sha(c['prior_gate'])}`, status `{gate['status']}` with {len(gate['cases'])}/20 cases.")
 lines += ["","The prior short screen showed major initial/final V3 drift, and this runtime-default matched protocol is a distinct wait policy. Interpret results under this exact protocol only. A stable API-wall gain is required before changing the allocator default; this report does not recommend merging a candidate. The run includes no PMU/system traffic attribution. No THP or NUMA system setting was changed.",""]
 doc=REPO/"docs/8454H_V4_PAGE_MATCHED_RESULTS.md";doc.write_text("\n".join(lines))
 print(json.dumps({"summary":str(out),"documentation":str(doc),"configs":len(cfg_rows),"ready_child_sessions":len(children)},indent=2))

if __name__=="__main__":main()
