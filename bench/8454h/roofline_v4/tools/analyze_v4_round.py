#!/usr/bin/env python3
"""Read-only inventory and final plotting for the V4 roofline experiment round.

`--plan` and `--listcases` never write files. Final plots/report data are only
written with `--final` and explicit, completed confirmation inputs. Benchmark
datasets are treated as evidence records; this tool never executes benchmarks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
V4 = ROOT / "bench/8454h/roofline_v4"
FIGDIR = V4 / "round_analysis/figures"
REFS = {"reg_calibration": 161.018, "fp32mix_calibration": 151.738,
        "fp64p6mix_calibration": 84.423}
REFS_UNIT = "TFLOP/s"
REFERENCE_NOTE = ("Calibration/working-set context only; these are neither a measured "
                  "DRAM roof nor a measured hard lower bound, and do not establish "
                  "physical traffic for these API workloads.")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"expected JSON object: {path}")
    return obj


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def add_record(records: list[dict[str, Any]], path: Path, family: str,
               label: str, config: Any, status: str, details: Any = None) -> None:
    rec = {"family": family, "source": relpath(path), "label": label,
           "config": config, "status": status, "details": details}
    records.append(rec)


def inventory() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    # The completed original screen manifest is the authority for its 29 rows;
    # retries are inventoried as failed/interrupted attempts, not added again.
    screen = V4 / "search_runs/screen_20261014_20261014T094029Z_retry2/screen_summary.json"
    if screen.exists():
        x = read_json(screen)
        sources.append({"path": relpath(screen), "sha256": sha256(screen), "role": "screen manifest"})
        for row in x.get("candidates", []):
            add_record(records, screen, "screen", row.get("candidate_id", "?"),
                       row.get("config"), row.get("status", "unknown"),
                       {k: row.get(k) for k in ("ctest_3_pass", "all_gate_cases_pass", "library_sha256", "result_rows")})
        for row in x.get("excluded", []):
            add_record(records, screen, "screen-excluded", row.get("candidate_id", "?"),
                       row.get("config"), "excluded", row.get("failure", row.get("reason")))
    # Packed rotation: each of 16 layouts has 3 rotations; only the final complete
    # dataset is counted as the timing configuration set.
    packed = V4 / "search_runs/packed_rotation_screen_20261014T101506Z/dataset.json"
    if packed.exists():
        x = read_json(packed)
        sources.append({"path": relpath(packed), "sha256": sha256(packed), "role": "packed rotation dataset"})
        for i, row in enumerate(x.get("candidates", [])):
            add_record(records, packed, "packed-rotation", str(i), row,
                       "recorded" if x.get("completed_utc") else "incomplete", None)
        for failed in x.get("failed_attempts", []):
            add_record(records, packed, "packed-failure", failed.get("label", "failure"), None,
                       "failed-attempt", failed)
    ilp = V4 / "recon_ilp_runs/ilp4_recon_bracket_20261014T112800Z/analysis.json"
    if ilp.exists():
        x = read_json(ilp)
        sources.append({"path": relpath(ilp), "sha256": sha256(ilp), "role": "ILP4 analysis"})
        for row in x.get("configuration_artifacts", []):
            label = f"b{row.get('batch')}_ilp4_{row.get('ilp4')}"
            add_record(records, ilp, "reconstruct-ilp4", label, row,
                       "recorded", {"library_sha256": row.get("library_sha256"),
                                    "mode": row.get("mode"),
                                    "late64_wide_call_relocation": row.get("late64_wide_call_relocation")})
        for failed in x.get("failed_attempts", []):
            add_record(records, ilp, "ilp-failure", failed.get("label", "failure"), None,
                       "failed-attempt", failed)
    layout = V4 / "search_runs/layout_b2_m256_n256_20261014_retry2/dataset.json"
    if layout.exists():
        x = read_json(layout)
        sources.append({"path": relpath(layout), "sha256": sha256(layout), "role": "layout dataset"})
        layout_analysis = layout.parent / "layout_analysis.json"
        if layout_analysis.exists():
            la = read_json(layout_analysis)
            sources.append({"path": relpath(layout_analysis), "sha256": sha256(layout_analysis), "role": "layout analysis"})
            for key, row in la.items():
                if not key.startswith("b2_") or not isinstance(row, dict):
                    continue
                add_record(records, layout_analysis, "layout", key, row,
                           "recorded" if row.get("gate_status") == "pass" else "failed-or-incomplete",
                           {"library_sha256": row.get("library_sha256"), "gate_status": row.get("gate_status"),
                            "gate_cases": row.get("gate_cases"), "rows": len(row.get("rows", []))})
            if la.get("full_gate_p0_h1", {}).get("failure"):
                add_record(records, layout_analysis, "layout-failure", "full_gate_p0_h1", None,
                           "failed-attempt", la["full_gate_p0_h1"]["failure"])
        else:
            configs = x.get("configs", x.get("candidates", []))
            for i, row in enumerate(configs):
                add_record(records, layout, "layout", str(row.get("label", i)) if isinstance(row, dict) else str(i),
                           row, "recorded" if x.get("completed_utc") else "incomplete")
    page = V4 / "search_runs/page_layout_20261014T121831Z/dataset.json"
    if page.exists():
        x = read_json(page)
        sources.append({"path": relpath(page), "sha256": sha256(page), "role": "page layout dataset"})
        done = {r.get("label"): r for r in x.get("completed_candidates", [])}
        for row in x.get("candidates", []):
            label = row.get("label", "?")
            result = done.get(label, {})
            add_record(records, page, "page-layout", label, row,
                       "recorded" if result else "incomplete",
                       {"library_sha256": result.get("library_sha256"),
                        "gate": result.get("gate"), "ctest_log": result.get("ctest_log"),
                        "probe": result.get("probe")})
    # Preserve visible interrupted/retry attempts without turning them into timing rows.
    for p in sorted((V4 / "search_runs").glob("*/dataset.json")):
        if p in (packed, layout, page):
            continue
        x = read_json(p)
        if any(t in p.parent.name for t in ("screen_", "packed_rotation", "layout_b2")):
            sources.append({"path": relpath(p), "sha256": sha256(p), "role": "retry/interrupted provenance"})
            failure = x.get("execution_failure", x.get("failed_attempts"))
            add_record(records, p, "retry-provenance", p.parent.name, None,
                       "retry/incomplete", failure or x.get("status", "incomplete metadata"))
    # Final paired campaigns are evidence inputs, but are not counted as new
    # candidate implementations in the 63-row search/validation inventory.
    for p, role in ((V4 / "matched_calls/results/final_rc_20261014/summary.json", "final RC matched control"),
                    (V4 / "page_layout_matched_runs/page_matched_runtime_20261014T123536Z/summary.json", "page matched validation/runtime")):
        if p.exists():
            x = read_json(p)
            sources.append({"path": relpath(p), "sha256": sha256(p), "role": role,
                            "status": x.get("status"), "configuration_count": x.get("configuration_count")})
            add_record(records, p, "matched-evidence", role, None,
                       x.get("status", "unknown"),
                       {"configuration_count": x.get("configuration_count"),
                        "validation": x.get("validation", x.get("input_output_validation"))})
    for p in sorted((V4 / "adaptive_release_runs").glob("*/validation_summary.json")):
        x = read_json(p)
        sources.append({"path": relpath(p), "sha256": sha256(p), "role": "adaptive confirmation/validation",
                        "status": x.get("status"), "completed_utc": x.get("completed_utc")})
        add_record(records, p, "adaptive-validation", p.parent.name, None,
                   x.get("status", "incomplete"),
                   {"full_gate_status": x.get("full_gate_status"), "full_gate_cases": x.get("full_gate_cases"),
                    "candidate_library_sha256": x.get("candidate_library_sha256")})
    # Kernel-schedule trees currently carry two candidate variants. Count them
    # as timing configurations only once a completed validation/matched record
    # confirms their end-to-end timing; a 4-budget sweep is still one candidate.
    for p in sorted((V4 / "kernel_schedule_runs").glob("*/validation_state.json")):
        x = read_json(p)
        sources.append({"path": relpath(p), "sha256": sha256(p), "role": "kernel-schedule state",
                        "status": x.get("status"), "source_identity_sha256": x.get("source_identity_sha256"),
                        "kernel_asm_sha256": x.get("kernel_asm_sha256")})
        variants = x.get("variants", {})
        if isinstance(variants, dict):
            for key, variant in variants.items():
                is_control = variant.get("library_sha256") == x.get("frozen_v3_library_sha256")
                family = "kernel-schedule-control" if is_control else "kernel-schedule-candidate"
                add_record(records, p, family, f"{p.parent.name}:variant-{key}", variant,
                           "timed-complete" if x.get("status") == "pass" and x.get("matched") else x.get("status", "pending"),
                           {"source_identity_sha256": x.get("source_identity_sha256"),
                            "kernel_asm_sha256": x.get("kernel_asm_sha256")})
    return {"records": records, "sources": sources}


def final_summary(path: Path) -> dict[str, Any]:
    x = read_json(path)
    if x.get("status") != "pass":
        raise ValueError(f"confirmation summary not pass: {path} status={x.get('status')!r}")
    if not x.get("configurations"):
        raise ValueError(f"confirmation summary has no configurations: {path}")
    return x


def plan(args: argparse.Namespace) -> int:
    inv = inventory()
    counts: dict[str, int] = {}
    for r in inv["records"]:
        counts[r["family"]] = counts.get(r["family"], 0) + 1
    out = {"mode": "plan", "round_complete": False,
           "expected_timing_rows": {"screen": 29, "packed_rotation": 16,
                                    "reconstruct_ilp4": 8, "layout": 6, "page_layout": 4,
                                    "kernel_schedule_candidate_implementations": 2},
           "expected_total_timing_rows": 65, "baseline_search_timing_rows": 63,
           "observed_inventory_counts": counts,
           "sources": inv["sources"],
           "pending_families": ["RC_CONFIRMATION", "kernel_schedule candidates"],
           "plot_inputs": {"required_final_confirmation_summary": "explicit --final-rc-confirmation path",
                           "reference_rates_gflops": REFS,
                           "reference_interpretation": REFERENCE_NOTE,
                           "work_formula": "W=2*N^3*p, p=6 for FP32 and FP64 p6",
                           "rate_formula": "W / seconds / 1e9; API wall and compute profile time separately",
                           "sizes": [4096, 8192, 16384],
                           "pairs_scatter": "every raw paired API ratio, no filtering"}}
    if args.final_rc_confirmation:
        p = Path(args.final_rc_confirmation).resolve()
        x = final_summary(p)
        out["confirmation_preflight"] = {"path": relpath(p), "sha256": sha256(p),
                                           "status": x.get("status"),
                                           "configuration_count": x.get("configuration_count"),
                                           "created_utc": x.get("created_utc")}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def listcases(_: argparse.Namespace) -> int:
    inv = inventory()
    print("family\tstatus\tlabel\tsource\tconfig/identity")
    for r in inv["records"]:
        print("\t".join(str(r.get(k, "")).replace("\t", " ").replace("\n", " ")
                         for k in ("family", "status", "label", "source", "config")))
    return 0


def run_final(args: argparse.Namespace) -> int:
    if not args.final_rc_confirmation:
        raise ValueError("--final requires --final-rc-confirmation with an explicit completed batch summary")
    summary_path = Path(args.final_rc_confirmation).resolve()
    summary = final_summary(summary_path)
    if not math.isclose(REFS["reg_calibration"] * 1000, 161018.0) or not math.isclose(REFS["fp32mix_calibration"] * 1000, 151738.0):
        raise ValueError("calibration unit conversion invariant failed")
    # Reject incomplete configuration sets before importing plotting dependencies.
    confs = summary["configurations"]
    expected = {(p, n) for p in ("fp32", "fp64") for n in (4096, 8192, 16384)}
    observed = {(str(c.get("precision", "")).lower(), int(c.get("N", -1))) for c in confs}
    if not expected.issubset(observed):
        raise ValueError(f"final confirmation lacks required precision/N points: missing={sorted(expected-observed)}")
    declared_count = summary.get("configuration_count")
    if declared_count is not None and declared_count != len(confs):
        raise ValueError(f"confirmation configuration_count={declared_count} but rows={len(confs)}")
    invalid = [c.get("run_id", "?") for c in confs if c.get("byte_exact_match") is not True]
    if invalid:
        raise ValueError(f"confirmation contains rows without byte_exact_match=true: {invalid}")
    # Plotting implementation is deliberately isolated from plan/listcase paths.
    mpldir = Path("/tmp/ozamx-v4-mpl")
    mpldir.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(mpldir)
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise RuntimeError("matplotlib unavailable; invoke with /tmp/ozamx-v3-paper-plot-env/bin/python") from e
    FIGDIR.mkdir(parents=True, exist_ok=True)
    # Confirmation metric schema: configuration rows hold raw candidate/control
    # arrays. Preserve every paired ratio exactly as recorded.
    rate_rows: list[dict[str, Any]] = []
    rate_summary_rows: list[dict[str, Any]] = []
    ratio_rows: list[dict[str, Any]] = []
    for c in confs:
        precision = str(c.get("precision", "")).lower()
        n = int(c["N"])
        if (precision, n) not in expected:
            continue
        p = 6
        work = 2 * n**3 * p
        metrics = c.get("metrics", {})
        for metric_key, kind in (("api_wall_seconds", "api"), ("compute_reconstruct_seconds", "compute")):
            m = metrics.get(metric_key, {})
            for role in ("control", "candidate"):
                vals = m.get(f"{role}_raw", [])
                if vals:
                    tmean = sum(vals) / len(vals)
                    tsorted = sorted(vals)
                    tmedian = (tsorted[len(tsorted)//2] if len(tsorted) % 2 else
                               (tsorted[len(tsorted)//2-1] + tsorted[len(tsorted)//2]) / 2)
                    rate_summary_rows.append({"run_id": c.get("run_id"), "candidate": c.get("candidate_tag"),
                                              "precision": precision, "N": n, "metric": kind, "role": role,
                                              "rep_count": len(vals), "mean_seconds": tmean,
                                              "median_seconds": tmedian, "min_seconds": min(vals),
                                              "max_seconds": max(vals), "primary_mean_time_gflops": work/tmean/1e9,
                                              "median_time_gflops": work/tmedian/1e9,
                                              "full_range_low_gflops": work/max(vals)/1e9,
                                              "full_range_high_gflops": work/min(vals)/1e9,
                                              "primary_mean_time_tflops": work/tmean/1e12,
                                              "median_time_tflops": work/tmedian/1e12,
                                              "full_range_low_tflops": work/max(vals)/1e12,
                                              "full_range_high_tflops": work/min(vals)/1e12})
                for rep, seconds in enumerate(vals):
                    rate_rows.append({"run_id": c.get("run_id"), "candidate": c.get("candidate_tag"),
                                      "precision": precision, "N": n, "metric": kind,
                                      "role": role, "rep": rep, "seconds": seconds,
                                      "algorithmic_work_flop": work,
                                      "equivalent_gflops": work / seconds / 1e9,
                                      "equivalent_tflops": work / seconds / 1e12})
            if kind == "api":
                paired = m.get("paired_candidate_over_control_raw", m.get("paired_ratio_raw", []))
                for rep, ratio in enumerate(paired):
                    ratio_rows.append({"run_id": c.get("run_id"), "candidate": "experimental RC1",
                                       "precision": precision, "N": n, "rep": rep,
                                       "candidate_over_control_api_wall": ratio,
                                       "source": "experimental RC1 confirmation"})
    # Preserve the complete page allocator matched campaign in the same paired
    # ratio plot. Its API values are kept separate from the confirmation rates.
    page_path = V4 / "page_layout_matched_runs/page_matched_runtime_20261014T123536Z/summary.json"
    if page_path.exists():
        page_summary = read_json(page_path)
        if page_summary.get("status") == "pass":
            for c in page_summary.get("configurations", []):
                for pair in c.get("raw_samples", []):
                    calls = pair.get("calls", {})
                    a, b = calls.get("candidate", {}), calls.get("control", {})
                    if a.get("status") == "ok" and b.get("status") == "ok":
                        den = b.get("api_wall_seconds")
                        num = a.get("api_wall_seconds")
                        if den and num is not None:
                            ratio_rows.append({"run_id": c.get("runid"), "candidate": c.get("candidate"),
                                               "precision": str(c.get("precision", "")).lower(),
                                               "N": int(c.get("N", -1)), "rep": pair.get("rep"),
                                               "candidate_over_control_api_wall": num / den,
                                               "source": "page_layout_matched"})
    # Primary is work/arithmetic-mean-time, matching the round's API ratio
    # estimand. Error bars show the full min/max-time converted range, not CI.
    # Hollow markers show work/median-time as a secondary robust summary.
    plot_axis_bounds: dict[str, dict[str, float]] = {}
    for precision, color in (("fp32", "#1769aa"), ("fp64", "#c13c37")):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
        for ax, metric in zip(axes, ("api", "compute")):
            for role, marker, ls in (("control", "o", "-"), ("candidate", "s", "--")):
                xs, ys, yerr_lo, yerr_hi = [], [], [], []
                median_ys = []
                for n in (4096, 8192, 16384):
                    rows = [r for r in rate_summary_rows if r["precision"] == precision and r["N"] == n and r["metric"] == metric and r["role"] == role]
                    if not rows:
                        raise ValueError(f"missing rate samples for {precision} N={n} {metric} {role}")
                    # If the confirmed batch has more than one candidate tag for
                    # a point, preserve each row as a separate series upstream;
                    # this summary interface currently expects one per role.
                    row = rows[-1]
                    mean_rate = row["primary_mean_time_tflops"]
                    xs.append(n); ys.append(mean_rate)
                    yerr_lo.append(mean_rate-row["full_range_low_tflops"])
                    yerr_hi.append(row["full_range_high_tflops"]-mean_rate)
                    median_ys.append(row["median_time_tflops"])
                role_label = "experimental RC1" if role == "candidate" else "frozen V3"
                ax.errorbar(xs, ys, yerr=[yerr_lo, yerr_hi], marker=marker, linestyle=ls,
                            color=color if role == "candidate" else "#555555",
                            label=f"{role_label} W/mean(time); full range, not CI")
                ax.scatter(xs, median_ys, marker=marker, facecolors="none",
                           edgecolors=color if role == "candidate" else "#555555",
                           label=f"{role_label} W/median(time)")
            selected_refs = (("reg_calibration", "#7b3294"),
                             (("fp32mix_calibration" if precision == "fp32" else "fp64p6mix_calibration"), "#8c6d31"))
            for ref_key, ref_color in selected_refs:
                ref = REFS[ref_key]
                ax.axhline(ref, color=ref_color, linestyle=":", linewidth=1.2,
                           label=f"{ref_key} context {ref:.3f} TFLOP/s")
            max_y = max([r["full_range_high_tflops"] for r in rate_summary_rows
                         if r["precision"] == precision and r["metric"] == metric] +
                        [REFS[k] for k, _ in selected_refs])
            axis_high = max_y * 1.06
            ax.set_ylim(0, axis_high)
            plot_axis_bounds[f"{precision}_{metric}"] = {"low_tflops": 0.0, "high_tflops": axis_high}
            ax.set_xscale("log", base=2); ax.set_xticks([4096,8192,16384], labels=["4096","8192","16384"])
            ax.set_xlabel("N"); ax.set_ylabel("Algorithmic equivalent TFLOP/s")
            ax.set_title(f"{precision.upper()} {metric} timing")
            ax.grid(True, alpha=.25); ax.legend(fontsize=8)
        fig.suptitle(f"Frozen V3 / experimental RC1 {precision.upper()} p=6: workload-equivalent, not physical traffic")
        for ext in ("png", "svg"):
            fig.savefig(FIGDIR / f"v3_vs_v4_{precision}_p6.{ext}", dpi=180)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    groups: dict[tuple[str, str, int], list[float]] = {}
    for r in ratio_rows:
        groups.setdefault((r["precision"], str(r.get("candidate") or "candidate"), r["N"]), []).append(r["candidate_over_control_api_wall"])
    keys = sorted(groups, key=lambda z:(z[0],z[2],z[1]))
    xpos = {key:i for i,key in enumerate(keys)}
    for key, vals in groups.items():
        ax.scatter([xpos[key]]*len(vals), vals, alpha=.65, s=19, label=None)
    ax.axhline(1.0, color="black", linewidth=1, linestyle="--")
    ax.set_xticks(range(len(keys)), [f"{p.upper()} {candidate}\nN={n}" for p,candidate,n in keys], rotation=40, ha="right")
    ax.set_ylabel("paired candidate / V3 API wall ratio (all reps)")
    ax.set_title("Every paired API ratio; no outlier filtering")
    ax.grid(axis="y", alpha=.25)
    for ext in ("png", "svg"):
        fig.savefig(FIGDIR / f"all_paired_api_ratios.{ext}", dpi=180)
    plt.close(fig)
    manifest = inventory()
    output = {"schema": "ozamx-v4-round-analysis-1", "round_complete": False,
              "final_confirmation": {"path": relpath(summary_path), "sha256": sha256(summary_path),
                                     "created_utc": summary.get("created_utc"), "status": summary.get("status"),
                                     "candidate_label": "experimental RC1"},
              "figures_directory": relpath(FIGDIR), "rate_rows": rate_rows,
              "rate_summary_rows": rate_summary_rows,
              "paired_ratio_rows": ratio_rows, "references_tflops": REFS,
              "units": {"rate_plot": "TFLOP/s", "raw_equivalent_gflops_field": "GFLOP/s",
                        "raw_equivalent_tflops_field": "TFLOP/s",
                        "calibration_reference_values_unit": REFS_UNIT,
                        "reference_conversion_check": {f"{value} TFLOP/s": value * 1000 for value in REFS.values()},
                        "conversion_identity_gflops_per_tflops": 1000},
              "plot_axis_bounds_tflops": plot_axis_bounds,
              "reference_interpretation": REFERENCE_NOTE,
              "formula": {"work_flop": "2*N^3*p", "p": 6,
                          "rate_gflops": "work_flop / seconds / 1e9",
                          "rate_tflops": "work_flop / seconds / 1e12",
                          "primary_rate": "work_flop / arithmetic_mean(seconds) / 1e9",
                          "secondary_rate": "work_flop / median(seconds) / 1e9",
                          "error_bar": "full range work_flop/max(seconds) .. work_flop/min(seconds), not a confidence interval",
                          "scope": "API and compute timings reported separately"},
              "sources": manifest["sources"], "inventory": manifest["records"],
              "claim_registry": {"no_production_claim": True,
                                 "experimental_rc1_not_current_main": True,
                                 "production_scope_context": "main 0.4 defaults to FP32/CACHE128, minMN>=4096, maxMN<=8192, and uses 256x256 for K4096..8192; F64 remains V3, FP32 N=16384 falls back to V3",
                                 "no_hardware_cause_attribution": True,
                                 "no_winner_declared": True}}
    outpath = FIGDIR / "round_plot_data.json"
    outpath.write_text(json.dumps(output, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(f"wrote {len(rate_rows)} rate rows and {len(ratio_rows)} paired ratios to {relpath(outpath)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", action="store_true", help="read-only inventory and planned plot protocol")
    ap.add_argument("--listcases", action="store_true", help="read-only case inventory")
    ap.add_argument("--final", action="store_true", help="write final plots and plot-data JSON")
    ap.add_argument("--final-rc-confirmation", help="explicit completed RC confirmation summary JSON")
    args = ap.parse_args()
    try:
        if args.final:
            return run_final(args)
        if args.listcases:
            return listcases(args)
        return plan(args)
    except Exception as e:
        print(f"analyze_v4_round: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
