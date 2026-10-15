#!/usr/bin/env python3
"""Summarize every matched call without removing any timed observation."""
import argparse, json, math, pathlib, statistics, time

ROOT=pathlib.Path(__file__).resolve().parents[4]
DOC=ROOT/"docs/8454H_V4_MATCHED_RESULTS.md"

def stat(values):
 return {"count":len(values),"mean":statistics.fmean(values),"median":statistics.median(values),
         "min":min(values),"max":max(values)}

def pos_effect(samples,label):
 first=[];second=[]
 for s in samples:
  v=s["calls"][label]["api_wall_seconds"]
  (first if s["order"][0]==label else second).append(v)
 if not first or not second:return None
 m1=statistics.median(first);m2=statistics.median(second)
 return {"first_position_median_seconds":m1,"second_position_median_seconds":m2,"second_over_first_pct":(m2/m1-1)*100}

def main():
 ap=argparse.ArgumentParser();ap.add_argument("campaign",type=pathlib.Path);a=ap.parse_args()
 path=a.campaign.resolve();campaign=json.load(open(path/"campaign.json"))
 if campaign.get("status")!="pass":raise SystemExit("campaign is not complete and passing")
 candidates={};configs=[]
 for tag,entry in campaign["candidates"].items():
  cand_rows=[]
  if entry.get("gate",{}).get("status")!="pass" or entry.get("gate",{}).get("cases")!=20:raise SystemExit(f"{tag} lacks 20 passing gate cases")
  for workload,info in entry["matched"].items():
   journal=json.load(open(info["path"]))
   rcfg=journal["run_config"]
   for key,cfg in journal["configurations"].items():
    if not cfg.get("complete") or not cfg.get("byte_exact_match"):raise SystemExit(f"incomplete/hash mismatch in {tag}/{key}")
    samples=cfg["samples"]
    if len(samples)!=7:raise SystemExit(f"expected 7 reps in {tag}/{key}, got {len(samples)}")
    control=[s["calls"]["control"] for s in samples];candidate=[s["calls"]["candidate"] for s in samples]
    raws={}
    for field in ("api_wall_seconds","split_seconds","pack_seconds","compute_reconstruct_seconds","profile_total_seconds"):
     c=[x[field] for x in control];v=[x[field] for x in candidate]
     ratios=[b/x for x,b in zip(c,v)]
     raws[field]={"control":stat(c),"candidate":stat(v),"candidate_over_control_ratio":stat(ratios),
                  "ratio_of_arithmetic_mean_times":statistics.fmean(v)/statistics.fmean(c),
                  "control_raw":c,"candidate_raw":v,"candidate_over_control_raw":ratios}
    row={"candidate":tag,"candidate_tag":rcfg["candidate_tag"],"workload":workload,
         "precision":cfg["precision"],"budget":cfg["budget"],"N":cfg["N"],"repetitions":len(samples),
         "paired_order":[s["order"] for s in samples],"raw_repetitions":[{"rep":s["rep"],"order":s["order"],
             "control":s["calls"]["control"],"candidate":s["calls"]["candidate"]} for s in samples],
         "timings":raws,"position_effect_api_wall":{"control":pos_effect(samples,"control"),"candidate":pos_effect(samples,"candidate")},
         "output_sha256":cfg["output_sha256"],"input_fnv1a64":{
             "A":samples[0]["calls"]["control"]["input_a_fnv1a64"],"B":samples[0]["calls"]["control"]["input_b_fnv1a64"]}}
    configs.append(row);cand_rows.append(row)
  ratios=[x["timings"]["api_wall_seconds"]["candidate_over_control_ratio"]["median"] for x in cand_rows]
  allrat=[r for row in cand_rows for r in row["timings"]["api_wall_seconds"]["candidate_over_control_raw"]]
  all_control=[r for row in cand_rows for r in row["timings"]["api_wall_seconds"]["control_raw"]]
  all_candidate=[r for row in cand_rows for r in row["timings"]["api_wall_seconds"]["candidate_raw"]]
  candidates[tag]={"library":entry["library"],"library_sha256":entry["library_sha256"],"gate":entry["gate"],
      "configuration_count":len(cand_rows),"per_configuration_median_ratios":ratios,
      "api_wall_ratio_summary_across_all_paired_calls":stat(allrat),
      "ratio_of_arithmetic_mean_api_wall_times":statistics.fmean(all_candidate)/statistics.fmean(all_control),
      "all_control_api_wall_raw":all_control,"all_candidate_api_wall_raw":all_candidate,
      "configurations_faster_than_v3_by_median":sum(r<1 for r in ratios),
      "configurations":cand_rows}
 if len(configs)!=30:raise SystemExit(f"expected 30 candidate/configuration rows, got {len(configs)}")
 best=min(candidates,key=lambda t:candidates[t]["api_wall_ratio_summary_across_all_paired_calls"]["median"])
 bestdata=candidates[best]
 stable=(bestdata["api_wall_ratio_summary_across_all_paired_calls"]["median"]<0.99 and
         bestdata["configurations_faster_than_v3_by_median"]>=12 and
         all(x["timings"]["api_wall_seconds"]["candidate_over_control_ratio"]["median"]<1.03 for x in bestdata["configurations"]))
 workloads={}
 for workload in ("fp32","fp64_p6","fp64_p10","fp64_p15","fp64_p21"):
  choices={}
  for tag,data in candidates.items():
   rows=[x for x in data["configurations"] if x["workload"]==workload]
   medians=[x["timings"]["api_wall_seconds"]["candidate_over_control_ratio"]["median"] for x in rows]
   raw=[r for x in rows for r in x["timings"]["api_wall_seconds"]["candidate_over_control_raw"]]
   stats=stat(raw)
   qualifies=stats["median"]<0.99 and sum(r<1 for r in medians)>=2 and max(medians)<1.03
   cwall=[r for x in rows for r in x["timings"]["api_wall_seconds"]["control_raw"]]
   vwall=[r for x in rows for r in x["timings"]["api_wall_seconds"]["candidate_raw"]]
   choices[tag]={"aggregate_paired_api_ratio":stats,
                 "ratio_of_arithmetic_mean_api_wall_times":statistics.fmean(vwall)/statistics.fmean(cwall),
                 "configuration_medians_by_N":{str(x["N"]):x["timings"]["api_wall_seconds"]["candidate_over_control_ratio"]["median"] for x in rows},
                 "configurations_faster_than_v3_by_median":sum(r<1 for r in medians),
                 "preliminary_signal_only":True}
  hint=min(choices,key=lambda tag:choices[tag]["aggregate_paired_api_ratio"]["median"])
  workloads[workload]={"candidates":choices,"initial_recheck_candidate_hint":hint,
                       "interpretation":"preliminary only; check raw mean/median divergence and order effects before treating as stable"}
 summary={"status":"pass","campaign":campaign,"summary_created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
          "analysis_policy":"all seven timed observations per configuration are retained; no outlier filtering",
          "geometry_wide_stable_gain_rule":"aggregate median paired candidate/control API-wall ratio < 0.99, at least 12/15 configuration medians < 1.0, and no configuration median > 1.03",
          "geometry_wide_stable_gain_observed":stable,"geometry_wide_winner":best if stable else None,
          "workload_rule":"Per-workload lower-median geometry is listed only as an initial recheck hint; it is not a winner or a repeatability claim.",
          "workload_analysis":workloads,"candidates":candidates}
 out=path/"summary.json";out.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
 DOC.parent.mkdir(exist_ok=True)
 lines=["# V4 matched-call geometry results","",
  "Both mode-3 geometry candidates were linked into separate persistent child processes from the same matched driver source and compared with frozen V3. The runner alternated control-first and candidate-first order for each of seven timed repetitions, retained every observation, checked deterministic full input hashes, and required equal SHA-256 hashes for each complete C output. Each candidate passed all 20 full binary-gate cases.","",
  f"Campaign: `{path}`  ",f"Control SHA-256: `{campaign['control_library_sha256']}`  ",
  "Runtime settings: 64 threads pinned to CPUs 0–63; GNU OpenMP with `OMP_WAIT_POLICY=PASSIVE`, `GOMP_SPINCOUNT=0`, `OMP_PLACES=cores`, and `OMP_PROC_BIND=close`; 2 GiB workspace cache. These passive-wait settings differ from earlier GNU OpenMP default screens.","",
  "All values below use API wall time, which includes the complete profiled call and allocation effects. Ratios are candidate/control, so values below 1.0 favor the candidate. We show the median paired ratio, the arithmetic mean of the seven paired ratios, and the ratio of arithmetic mean candidate/control API times separately. The summary JSON keeps raw per-call phase and wall timings, exact order, input hashes, and output hashes for all 30 configurations.","",
  "| Candidate | Configurations faster by median | Median paired ratio | Mean paired ratio | Ratio of mean API times | Stable gain across all configs |","|---|---:|---:|---:|---:|---|"]
 for tag,data in candidates.items():
  r=data["api_wall_ratio_summary_across_all_paired_calls"]
  lines.append(f"| `{tag}` | {data['configurations_faster_than_v3_by_median']}/15 | {r['median']:.4f} | {r['mean']:.4f} | {data['ratio_of_arithmetic_mean_api_wall_times']:.4f} | {'yes' if stable and tag==best else 'no'} |")
 lines += ["","Workload-level initial recheck candidates from per-configuration medians. These are preliminary precision clues only, not production recommendations or repeatability claims:","","| Workload | N256 geometry medians (1024/4096/8192) | N512 geometry medians (1024/4096/8192) | Lower aggregate median hint |","|---|---|---|---|"]
 for workload,data in workloads.items():
  v1=data["candidates"]["b2_m256_n256"];v2=data["candidates"]["b2_m256_n512"]
  fmt=lambda d:" / ".join(f"{x:.4f}" for _,x in sorted(d["configuration_medians_by_N"].items(),key=lambda kv:int(kv[0])))
  rec=data["initial_recheck_candidate_hint"]
  lines.append(f"| {workload} | {fmt(v1)} | {fmt(v2)} | `{rec}` (preliminary) |")
 lines += ["","Per-configuration API ratios and measured order effects:","","| Candidate | Precision/budget | N | Median paired ratio | Mean paired ratio | Ratio of mean API times | Control second/first | Candidate second/first | Output bytes equal |","|---|---|---:|---:|---:|---:|---:|---|"]
 for row in configs:
  control_fx=row["position_effect_api_wall"]["control"]["second_over_first_pct"]
  cand_fx=row["position_effect_api_wall"]["candidate"]["second_over_first_pct"]
  label=row["precision"]+(f"/p{row['budget']}" if row['budget'] else "")
  t=row["timings"]["api_wall_seconds"]
  lines.append(f"| `{row['candidate']}` | {label} | {row['N']} | {t['candidate_over_control_ratio']['median']:.4f} | {t['candidate_over_control_ratio']['mean']:.4f} | {t['ratio_of_arithmetic_mean_times']:.4f} | {control_fx:+.1f}% | {cand_fx:+.1f}% | yes |")
 if stable:
  lines += ["",f"`{best}` meets the geometry-wide stable-gain rule against V3."]
 else:
  lines += ["","No single geometry meets the geometry-wide stable-gain rule. Workload hints are preliminary recheck candidates only; order effects and mean/median divergence prevent a repeatability claim. Keep V3 selected pending runtime-policy confirmation."]
 lines += ["","Full 20-case gate records, per-configuration journals, compiler commands/logs, and hashes are retained in the campaign directory. The gate cases cover full-output wide geometry (including K=1), large-K overflow/cancellation and nonfinite transactions, and A=C/B=C alias transactions.",""]
 DOC.write_text("\n".join(lines))
 print(json.dumps({"summary":str(out),"documentation":str(DOC),"stable_gain_observed":stable,"winner":best if stable else None},indent=2))

if __name__=="__main__":main()
