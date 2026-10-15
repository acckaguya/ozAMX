#!/usr/bin/env python3
"""Validate and summarize a completed page-layout campaign into its report."""
from __future__ import annotations
import argparse,csv,hashlib,json,pathlib,statistics

REPO=pathlib.Path(__file__).resolve().parents[5]
CASES=[("FP32", "fp32", "6"),("FP64 p6","fp64","6"),("FP64 p10","fp64","10"),("FP64 p15","fp64","15"),("FP64 p21","fp64","21")]
CONFIGS=[("a4k_hint0",4096,0),("a4k_hint1",4096,1),("a2m_hint0",2097152,0),("a2m_hint1",2097152,1)]

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def samples(row,key): return [float(x) for x in row[key].split(";")]
def mean(xs): return statistics.fmean(xs)
def pct(x,base): return (100*(x/base-1)) if base else float("nan")
def ms(x): return f"{1000*x:.3f}"
def rel(path): return pathlib.Path(path).resolve().relative_to(REPO).as_posix()
def load_csv(p):
    with pathlib.Path(p).open(newline="") as f:
        r=csv.DictReader(f); rows=list(r)
        if len(r.fieldnames or [])!=37: raise RuntimeError(f"37-column schema mismatch: {p}")
    got={(x["precision"],x["budget"]):x for x in rows}
    expected={(p,b) for _,p,b in CASES}
    if set(got)!=expected or len(rows)!=5: raise RuntimeError(f"five workload rows missing: {p}")
    return got
def vec_text(xs): return "`["+", ".join(ms(x) for x in xs)+"]`"

def main():
    ap=argparse.ArgumentParser();ap.add_argument("dataset",type=pathlib.Path);args=ap.parse_args()
    out=args.dataset.resolve();d=json.loads((out/"dataset.json").read_text())
    if d.get("status")!="complete": raise RuntimeError(f"campaign is not complete: status={d.get('status')}")
    if d.get("frozen_library_sha256")!="73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c": raise RuntimeError("frozen V3 library identity mismatch")
    source0=d.get("source_snapshot_sha256",{});source1=d.get("source_snapshot_sha256_final",{})
    changed={k for k in set(source0)&set(source1) if source0[k]!=source1[k]}
    added=set(source1)-set(source0);removed=set(source0)-set(source1)
    if changed or removed or added-{"tools/analyze_page_layout.py"}: raise RuntimeError(f"experiment source changed during campaign: changed={changed}, added={added}, removed={removed}")
    data={}; gates=[]; ctests=[]; probes={}; libs={}
    for label,alignment,hint in CONFIGS:
        gatep=out/"gates"/f"{label}_full.json"; gate=json.loads(gatep.read_text())
        if gate.get("status")!="pass" or len(gate.get("cases",[]))!=20 or not all(x.get("pass") for x in gate["cases"]): raise RuntimeError(f"20-case gate not pass: {gatep}")
        cand=next((x for x in d["completed_candidates"] if x["label"]==label),None)
        if not cand: raise RuntimeError(f"candidate not recorded complete: {label}")
        lib=pathlib.Path(cand["library"]); identity_path=out/"builds"/label/"build_identity.json"; identity=json.loads(identity_path.read_text())
        if sha(lib)!=cand["library_sha256"] or sha(lib)!=gate.get("candidate_library_sha256"): raise RuntimeError(f"library hash mismatch {label}")
        if identity.get("page_alignment_bytes")!=alignment or identity.get("madv_hugepage")!=hint: raise RuntimeError(f"build knob mismatch {label}")
        ctestp=out/"logs"/f"{label}_ctest.log"; ctest=ctestp.read_text()
        if "100% tests passed" not in ctest or "3/3 Test" not in ctest: raise RuntimeError(f"three CTests incomplete: {ctestp}")
        rec=out/"records"/label; rows=load_csv(rec/"result.csv")
        meta=json.loads((rec/"metadata.json").read_text())
        if meta.get("library_sha256")!=sha(lib) or meta.get("mkl_runtime_sha256")!=d["mkl_runtime_sha256"]: raise RuntimeError(f"metadata identity mismatch {label}")
        sm=json.loads((rec/"allocator_smaps.json").read_text())
        if not sm.get("buffers") or sm.get("hint_attempts",0)<0: raise RuntimeError(f"candidate mapping snapshot missing: {label}")
        probe=json.loads((out/"probes"/f"{label}.json").read_text())
        if probe.get("status")!="pass" or probe.get("large_alignment_mod")!=0: raise RuntimeError(f"direct allocator probe failed: {label}")
        if hint and probe.get("hint_attempts")!=1: raise RuntimeError(f"hint attempt not recorded: {label}")
        data[label]={"alignment":alignment,"hint":hint,"rows":rows,"smaps":sm,"probe":probe,"identity":identity,"lib":str(lib),"libsha":sha(lib)}
        gates.append(f"`{label}`: 20/20 output-byte/semantic cases passed; gate `{rel(gatep)}` (SHA `{sha(gatep)}`).")
        ctests.append(f"`{label}`: 3/3 passed; log `{rel(ctestp)}`.")
        probes[label]=probe;libs[label]=(str(lib),sha(lib))
    v3rows={};v3metadata=[]
    for label in ("frozen_v3_initial","frozen_v3_final"):
        rp=out/"records"/label; rows=load_csv(rp/"result.csv");meta=json.loads((rp/"metadata.json").read_text())
        if meta.get("library_sha256")!=d["frozen_library_sha256"]: raise RuntimeError(f"V3 control library mismatch: {label}")
        if any(len(samples(r,"raw_api_call_wall_s"))!=7 for r in rows.values()): raise RuntimeError(f"V3 control reps incomplete: {label}")
        v3rows[label]=rows;v3metadata.append(meta)
    perf=[]
    for name,precision,budget in CASES:
        kr=(precision,budget);v3i=v3rows["frozen_v3_initial"][kr];v3f=v3rows["frozen_v3_final"][kr]
        vi=samples(v3i,"raw_api_call_wall_s");vf=samples(v3f,"raw_api_call_wall_s");mid=(mean(vi)+mean(vf))/2
        drift=pct(mean(vf),mean(vi))
        basecomp=(mean(samples(v3i,"raw_compute_recon_s"))+mean(samples(v3f,"raw_compute_recon_s")))/2
        for label,alignment,hint in CONFIGS:
            row=data[label]["rows"][kr];wall=samples(row,"raw_api_call_wall_s");comp=samples(row,"raw_compute_recon_s")
            split=samples(row,"raw_split_s");pack=samples(row,"raw_pack_s");total=samples(row,"raw_profile_total_s")
            perf.append({"workload":name,"label":label,"alignment":alignment,"hint":hint,"wall":wall,"compute":comp,
                "split":split,"pack":pack,"total":total,"wall_delta_pct":pct(mean(wall),mid),"v3_drift_pct":drift,
                "compute_delta_pct":pct(mean(comp),basecomp),"mkl":float(row["mkl_gemm_s"]),"api_mean":mean(wall),"compute_mean":mean(comp)})
    lines=[]
    lines += ["# V4 large-workspace page alignment and THP hint screen","",
      f"Dataset: `{rel(out)}` (completed {d.get('completed_utc')}; wait for exclusive global perf lock: {d.get('lock_wait_seconds',0):.1f}s).",
      "This is a four-configuration, three-repetition screen. It reports observations for a later matched run and does not establish a winner.","",
      "## Implementation and verification","",
      "Only the isolated page-layout source tree changed. Allocations with logical payloads below 2 MiB retain 64-byte alignment. For logical payloads at least 2 MiB, `posix_memalign` uses the configured 4 KiB or 2 MiB alignment and the original logical byte count; exact-size pool keys, cache accounting, and `std::free` remain unchanged. With the hint enabled, the allocator calls `madvise(pointer, floor(bytes/4096)*4096, MADV_HUGEPAGE)`. The pointer is page-aligned and the advised range stays inside the allocation. A failed hint is recorded and does not change allocation/API behavior. Larger allocator alignment can add allocator-internal padding/fragmentation; this is not an RSS measurement and is not included in the logical pool byte cap.",
      "",
      "The benchmark driver is shared by the V3 controls and all candidates. Candidate workspace addresses and `/proc/self/smaps` VMA `AnonHugePages` values are dumped once, after all five workloads and timed calls finish. The independent probe reports its own hint return count/errno and the mapping containing its large allocation. A successful `madvise` return is advisory acceptance only; actual `AnonHugePages` is reported separately. V3's frozen library has no candidate allocator snapshot hook, so its post-run marker is unavailable by design. These observations do not measure global traffic or identify a hardware bottleneck.",
      "",
      "Assembly is unchanged byte-for-byte from the isolated base (`src/kernels.S` SHA-256 `94af3cf4345b2383100e4d8d883be57b084ec68d12e056f80c4a8bb77bc9bd68`). The experiment-specific source identity is [`PAGE_LAYOUT_SOURCE_SNAPSHOT.json`](../bench/8454h/roofline_v4/page_layout_src/PAGE_LAYOUT_SOURCE_SNAPSHOT.json); the prior `SOURCE_ORIGIN.json` is retained only as base provenance. CMake identities record both page knobs, assembly/core/allocator/driver hashes, and the oneMKL runtime hash. Checkpoints include alignment and hint in their source ID.",
      "",
      f"System THP state was not modified. The official Linux kernel THP manual was saved at [`third_party/manuals/linux-transhuge.html`](../third_party/manuals/linux-transhuge.html), SHA-256 `{sha(REPO/'third_party/manuals/linux-transhuge.html')}`; [official online manual](https://docs.kernel.org/admin-guide/mm/transhuge.html). It describes MADV_HUGEPAGE as a range-level hint and transparent promotion as conditional. This experiment neither changed sysfs nor NUMA settings.",
      "",
      "| Candidate | Large allocation alignment | MADV_HUGEPAGE | Direct probe result | Probe calls / success / failure / errno | Benchmark calls / success / failure / errno | Probe VMA AnonHugePages | Benchmark cached buffers with AnonHugePages > 0 | Max reported VMA AnonHugePages |",
      "|---|---:|---:|---|---:|---:|---:|---:|---:|"]
    for label,alignment,hint in CONFIGS:
        pr=probes[label];sm=data[label]["smaps"];vals=[int(x.get("anon_huge_kb_in_vma",0)) for x in sm.get("buffers",[])]
        lines.append(f"| {label} | {alignment} B | {hint} | {pr['status']} | {pr.get('hint_attempts',0)} / {pr.get('hint_successes',0)} / {pr.get('hint_failures',0)} / {pr.get('hint_last_errno',0)} | {sm.get('hint_attempts',0)} / {sm.get('hint_successes',0)} / {sm.get('hint_failures',0)} / {sm.get('hint_last_errno',0)} | {pr.get('anon_huge_kb_in_mapping',0)} KiB | {sum(x>0 for x in vals)}/{len(vals)} | {max(vals,default=0)} KiB |")
    lines += ["","The per-process smaps dump is linked from each candidate's `records/<candidate>/allocator_smaps.json`. Each value covers the VMA containing the cached allocation pointer, which may include allocator mapping overhead. Values from multiple pointers can refer to the same VMA; counts/sums must not be interpreted as unique resident bytes.","","## Numerical and timing protocol","",
      f"The immutable V3 library SHA-256 is `{d['frozen_library_sha256']}`; the oneMKL runtime SHA-256 is `{d['mkl_runtime_sha256']}`. All builds use mode 0, FP64 batch 2, CBM 128, automatic CBN, 64-byte wide-row padding, tileloaddt1, BK=256, and FP32 late32 off. Inputs use uniform generation with seed base {d['seed_base']} (N=8192 seed {d['seed_base']+8192}), 64 threads on cpuset `{d['cpuset']}`, OMP places `cores`, bind `close`, and MKL GNU threading. Each candidate has 3 CTests, the full 20-case byte/semantic gate, a separate allocation probe, and N=8192 five-workload measurements with 3 repetitions. Frozen V3 controls bracket the candidates with 7 repetitions each. Full API wall is primary; profile phases and the MKL GEMM-only reference remain separate.","",
      "Gate evidence:",""]
    lines += ["- "+x for x in gates]
    lines += ["","CTest evidence:",""]
    lines += ["- "+x for x in ctests]
    lines += ["","## Per-workload raw timings","","All times below are milliseconds. `API [3]` and `compute+recon [3]` list the preserved per-repetition raw samples in their original order. `Δ API` compares the candidate mean to the midpoint of the initial/final V3 API means; `V3 drift` is final versus initial V3. Positive deltas mean slower. Three samples are descriptive only.","",
      "| Workload | Candidate | API raw [3] | Δ API vs V3 midpoint | V3 drift | Compute+recon raw [3] | Δ compute vs V3 midpoint | Split / pack / profile-total means | MKL GEMM mean |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for x in perf:
        base=(x["compute_mean"]/(1+x["compute_delta_pct"]/100)) if x["compute_delta_pct"]!=-100 else 0
        # Phase means are derived directly from the same three preserved API rows.
        lines.append(f"| {x['workload']} | {x['label']} | {vec_text(x['wall'])} | {x['wall_delta_pct']:+.2f}% | {x['v3_drift_pct']:+.2f}% | {vec_text(x['compute'])} | {x['compute_delta_pct']:+.2f}% | {ms(mean(x['split']))} / {ms(mean(x['pack']))} / {ms(mean(x['total']))} | {ms(x['mkl'])} |")
    lines += ["","Frozen-control API wall means (ms), initial → final, and drift:",""]
    lines += [f"- {name}: {ms(mean(samples(v3rows['frozen_v3_initial'][ (p,b) ],'raw_api_call_wall_s')))} → {ms(mean(samples(v3rows['frozen_v3_final'][ (p,b) ],'raw_api_call_wall_s')))} ({pct(mean(samples(v3rows['frozen_v3_final'][(p,b)],'raw_api_call_wall_s')),mean(samples(v3rows['frozen_v3_initial'][(p,b)],'raw_api_call_wall_s'))):+.2f}%)." for name,p,b in CASES]
    maxdrift=max(abs(x["v3_drift_pct"]) for x in perf)
    mindrift=min(abs(x["v3_drift_pct"]) for x in perf)
    lines += ["",f"The bracketing V3 control moved substantially: absolute drift ranged from {mindrift:.2f}% to {maxdrift:.2f}% across the five workloads. Candidates ran sequentially in the stated order rather than interleaved, so candidate-versus-midpoint deltas are strongly exposed to shared-host drift and are descriptive only. The table retains the raw triples for later review; the matched follow-up should make any performance comparison.","","## Artifact paths and limits","","Candidate libraries:",""]
    lines += [f"- `{label}`: [`{rel(lib)}`](../{rel(lib)}) — SHA-256 `{libsha}`; build identity `{rel(out/'builds'/label/'build_identity.json')}`." for label,(lib,libsha) in libs.items()]
    lines += ["","V3 matched follow-up should use these exact paths and library hashes. No candidate is declared a winner from this three-repetition screen. `madvise` success and VMA `AnonHugePages` are reported independently; even a rise in huge-page backing does not establish that address translation limited GEMM. No PMU evidence or whole-system traffic attribution was collected. The run preserves every build log, gate, probe, benchmark CSV/checkpoint, metadata record, and post-run smaps snapshot under the dataset directory.",""]
    report=REPO/"docs/8454H_V4_PAGE_LAYOUT_RESULTS.md";report.parent.mkdir(parents=True,exist_ok=True);report.write_text("\n".join(lines))
    print(report)

if __name__=="__main__": main()
