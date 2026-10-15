#!/usr/bin/env python3
"""Analyze partial or complete V3 paper-alignment records (no benchmark execution)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "bench/8454h/v3_paper_alignment"
REF = CAMPAIGN / "paper_reference.json"
SIZES = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
THREADS = [2, 4, 8, 16, 32, 64]
MODES = [("fp32", 6, "fp32_p6")] + [("fp64", b, f"fp64_p{b}") for b in (6, 10, 15, 21)]
EXPECTED_LIBRARY = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
EXPECTED_SOURCE_ID = "v3-paper-alignment-20261014"
EXPECTED_REPS = 10


def read_one(path: Path) -> dict | None:
    if not path.is_file():
        return None
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if len(rows) == 1 else None


def parse_samples(value: str | None) -> list[float]:
    if not value:
        return []
    try:
        return [float(x) for x in value.split(";") if x != ""]
    except ValueError:
        return []


def get_checkpoint(key: str, precision: str, n: int, budget: int) -> tuple[Path, dict | None]:
    suffix = f".{precision}.{n}.{budget}.json" if precision == "fp64" else f".fp32.{n}.6.json"
    path = CAMPAIGN / "checkpoints" / (key + suffix)
    if precision == "raw":
        path = CAMPAIGN / "checkpoints" / f"{key}.json"
    try:
        return path, json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return path, None


def process_status() -> dict[str, dict]:
    p = CAMPAIGN / "config_status.csv"
    rows: dict[str, dict] = {}
    if p.exists():
        with p.open(newline="") as f:
            for row in csv.DictReader(f):
                rows[row.get("config", "")] = row
    return rows


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def check_case(
    key: str,
    row: dict | None,
    precision: str,
    n: int,
    threads: int,
    budget: int | None,
    status_rows: dict[str, dict],
) -> dict:
    problems = []
    if row is None:
        return {
            "key": key,
            "present": False,
            "valid": False,
            "problems": ["missing or non-single-row CSV"],
        }
    if row.get("status") != "ok":
        problems.append(f"CSV status={row.get('status')!r}")
    try:
        reps = int(row.get("repetitions", "0"))
        if reps != EXPECTED_REPS:
            problems.append(f"repetitions={reps}, expected {EXPECTED_REPS}")
    except ValueError:
        reps = 0
        problems.append("invalid repetitions field")
    if precision == "raw":
        # The raw headroom CSV is intentionally a distinct schema: it records the
        # isolated oneMKL routine rather than the V3 precision/distribution fields.
        checks = {"N": str(n), "threads": str(threads)}
        if row.get("routine") != "raw_mkl_bf16bf16fp32":
            problems.append(f"routine={row.get('routine')!r}, expected 'raw_mkl_bf16bf16fp32'")
    else:
        checks = {
            "precision": precision,
            "N": str(n),
            "threads": str(threads),
            "distribution": "uniform",
        }
    if budget is not None:
        checks["budget"] = str(budget)
    for field, expected in checks.items():
        if row.get(field) != expected:
            problems.append(f"{field}={row.get(field)!r}, expected {expected!r}")
    try:
        seed = int(row["seed"])
        if seed != 260904 + n:
            problems.append(f"seed={seed}, expected campaign seed {260904+n}")
    except (KeyError, ValueError):
        problems.append("missing/invalid seed")
    if precision == "raw":
        samples = parse_samples(row.get("raw_seconds"))
    else:
        samples = parse_samples(row.get("raw_api_call_wall_s"))
    if len(samples) != EXPECTED_REPS:
        problems.append(f"raw timed sample count={len(samples)}, expected {EXPECTED_REPS}")
    elif any(not math.isfinite(x) or x <= 0 for x in samples):
        problems.append("raw timed samples contain non-finite/non-positive values")
    if samples:
        try:
            mean_field = "seconds_mean" if precision == "raw" else "api_call_wall_s_mean"
            reported_mean = float(row[mean_field])
            if not math.isclose(
                statistics.fmean(samples), reported_mean, rel_tol=1e-8, abs_tol=1e-12
            ):
                problems.append(f"{mean_field} does not match arithmetic mean of raw timed samples")
        except (KeyError, ValueError):
            problems.append("missing/invalid recorded mean for the primary timed samples")
    if precision != "raw":
        for field in ("eF_mkl", "e_scaled_mkl"):
            try:
                value = float(row[field])
                if not math.isfinite(value) or value < 0:
                    raise ValueError(field)
            except (KeyError, ValueError):
                problems.append(f"missing/invalid full-matrix MKL accuracy metric {field}")
    cp_path, cp = get_checkpoint(key, precision, n, budget or 6)
    if cp is None:
        problems.append(f"missing/invalid checkpoint {cp_path.name}")
    else:
        if cp.get("source_id") != EXPECTED_SOURCE_ID:
            problems.append(f"checkpoint source_id={cp.get('source_id')!r}")
        if cp.get("complete") is not True or cp.get("completed_timed_repetitions") != EXPECTED_REPS:
            problems.append("checkpoint is incomplete or has the wrong completed repetition count")
        if cp.get("requested_repetitions") != EXPECTED_REPS:
            problems.append("checkpoint requested repetition count is not 10")
        if (
            cp.get("N") != n
            or cp.get("threads") != threads
            or (precision != "raw" and cp.get("precision") != precision)
        ):
            problems.append("checkpoint configuration fields do not match CSV key")
        if budget is not None and cp.get("budget") != budget:
            problems.append("checkpoint budget does not match CSV key")
        vector = cp.get("raw_seconds") if precision == "raw" else cp.get("call_wall_seconds")
        if not isinstance(vector, list) or len(vector) != EXPECTED_REPS:
            problems.append("checkpoint timed vector length is not 10")
        elif (
            samples
            and len(vector) == len(samples)
            and any(abs(float(a) - float(b)) > 2e-9 for a, b in zip(samples, vector))
        ):
            problems.append("CSV raw samples differ from checkpoint values")
    proc = status_rows.get(key)
    if proc is None:
        problems.append("missing process status row")
    elif proc.get("rc") != "0":
        problems.append(f"process rc={proc.get('rc')!r}")
    return {
        "key": key,
        "present": True,
        "valid": not problems,
        "problems": problems,
        "checkpoint": str(cp_path.relative_to(ROOT)),
        "api_wall_samples": len(samples),
    }


def main_records(ref: dict, status_rows: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    out, cases = [], []
    expected_modes = {key: value for key, value in ref["table4_modes"].items()}
    for n in SIZES:
        for precision, budget, mode in MODES:
            key = (
                f"main_{mode.replace('_p', 'p')}_n{n}" if precision == "fp64" else f"main_fp32_n{n}"
            )
            # Campaign keys use main_fp64p10_nN; paper mode keys use fp64_p10.
            if precision == "fp64":
                key = f"main_fp64p{budget}_n{n}"
            csv_path = CAMPAIGN / "results" / f"{key}.csv"
            row = read_one(csv_path)
            case = check_case(key, row, precision, n, 64, budget, status_rows)
            cases.append(case)
            if row is None:
                continue
            scales = expected_modes[mode]
            paper = ref["table4_accuracy"]["values_as_printed_before_scale"][str(n)][mode]
            paper_ef = paper[0] * scales["eF_scale"]
            paper_es = paper[1] * scales["e_scaled_scale"]
            samples = parse_samples(row.get("raw_api_call_wall_s"))
            wall = statistics.fmean(samples) if samples else None
            # Use the primary wall samples; CSV mean is retained for consistency audit.
            try:
                recorded_wall = float(row["api_call_wall_s_mean"])
                profile_wall = float(row["profile_total_s_mean"])
                mkl = float(row["mkl_gemm_s"])
                ef = float(row["eF_mkl"])
                es = float(row["e_scaled_mkl"])
            except (KeyError, ValueError):
                continue
            out.append(
                {
                    "key": key,
                    "N": n,
                    "mode": mode,
                    "precision": precision,
                    "budget": budget,
                    "status": row.get("status"),
                    "valid": case["valid"],
                    "problems": case["problems"],
                    "accuracy_reference": "full-NxN oneMKL SGEMM/DGEMM",
                    "eF_measured": ef,
                    "eF_paper": paper_ef,
                    "eF_measured_over_paper": ef / paper_ef if paper_ef else None,
                    "e_scaled_measured": es,
                    "e_scaled_paper": paper_es,
                    "e_scaled_measured_over_paper": es / paper_es if paper_es else None,
                    "api_call_wall_s_arithmetic_mean_from_raw_samples": wall,
                    "api_call_wall_s_mean_recorded": recorded_wall,
                    "api_call_wall_mean_matches_recorded": wall is not None
                    and math.isclose(wall, recorded_wall, rel_tol=1e-8, abs_tol=1e-12),
                    "api_call_effective_GFLOP_s": 2.0 * n**3 / wall / 1e9 if wall else None,
                    "profile_total_s_mean_secondary": profile_wall,
                    "mkl_gemm_only_s_mean": mkl,
                    "mkl_gemm_only_over_api_wall_speedup": mkl / wall if wall else None,
                    "paper_figure7_speedup": (
                        ref["figure7_fp32_speedup"]["speedup"][SIZES.index(n)]
                        if mode == "fp32_p6"
                        else None
                    ),
                    "csv_path": str(csv_path.relative_to(ROOT)),
                }
            )
    return out, cases


def make_plots(report: dict, outdir: Path) -> str | None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return "Matplotlib unavailable; skipped optional plots."
    outdir.mkdir(parents=True, exist_ok=True)
    rows = report["main_results"]
    modes = [m[2] for m in MODES]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for mode in modes:
        pts = sorted(
            (r["N"], r["eF_measured_over_paper"])
            for r in rows
            if r.get("valid") and r["mode"] == mode
        )
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label=mode)
    ax.axhline(1.0, color="black", lw=0.8)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("Square matrix order N")
    ax.set_ylabel("Measured eF / paper Table 4 eF")
    ax.legend(ncol=2)
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "ef_ratio_vs_size.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    fp = sorted(
        (r["N"], r["mkl_gemm_only_over_api_wall_speedup"], r["paper_figure7_speedup"])
        for r in rows
        if r.get("valid") and r["mode"] == "fp32_p6"
    )
    if fp:
        ax.plot(
            [x[0] for x in fp],
            [x[1] for x in fp],
            marker="o",
            label="Local MKL GEMM-only / V3 full API wall",
        )
        ax.plot([x[0] for x in fp], [x[2] for x in fp], marker="s", label="Paper Figure 7")
    ax.axhline(1.0, color="black", lw=0.8)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Square matrix order N")
    ax.set_ylabel("Speedup ratio")
    ax.legend()
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "fp32_speedup_vs_size.png", dpi=180)
    plt.close(fig)

    scaling = [r for r in report["scaling_results"] if r.get("valid")]
    if scaling:
        fig, ax = plt.subplots(figsize=(9.2, 5.4))
        for n in (1024, 4096, 16384):
            by_threads = {r["threads"]: r for r in scaling if r["N"] == n}
            if not by_threads:
                continue
            api_label = f"V3 full API wall, N={n}"
            mkl_label = f"oneMKL GEMM-only, N={n}"
            api_segment, mkl_segment = [], []
            api_labeled = mkl_labeled = False

            def flush_segments() -> None:
                nonlocal api_labeled, mkl_labeled
                if api_segment:
                    ax.plot(
                        [x[0] for x in api_segment],
                        [x[1] for x in api_segment],
                        marker="o",
                        label=api_label if not api_labeled else "_nolegend_",
                    )
                    api_labeled = True
                    api_segment.clear()
                if mkl_segment:
                    ax.plot(
                        [x[0] for x in mkl_segment],
                        [x[1] for x in mkl_segment],
                        marker="s",
                        linestyle="--",
                        label=mkl_label if not mkl_labeled else "_nolegend_",
                    )
                    mkl_labeled = True
                    mkl_segment.clear()

            for t in THREADS:
                row = by_threads.get(t)
                if row is None or row.get("api_call_effective_GFLOP_s") is None:
                    flush_segments()
                    continue
                api_segment.append((t, row["api_call_effective_GFLOP_s"]))
                if row.get("mkl_effective_GFLOP_s") is not None:
                    mkl_segment.append((t, row["mkl_effective_GFLOP_s"]))
                else:
                    flush_segments()
            flush_segments()
        ax.set_xscale("log", base=2)
        ax.set_xticks(THREADS, labels=[str(t) for t in THREADS])
        ax.set_xlabel("Configured thread count (same count for V3 and oneMKL)")
        ax.set_ylabel("Effective throughput (GFLOP/s)")
        ax.set_title("FP32 scaling: MKL GEMM-only timing vs V3 full API wall")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(ncol=2)
        fig.tight_layout()
        fig.savefig(outdir / "fp32_thread_scaling_api_vs_mkl.png", dpi=180)
        plt.close(fig)

    raw = report["raw_bf16_results"]
    pts = sorted((r["N"], r.get("GFLOP_s"), r.get("TFLOP_s")) for r in raw if r.get("valid"))
    if pts:
        fig, ax = plt.subplots(figsize=(8.2, 4.8))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label="Measured GFLOP/s")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xlabel("Square matrix order N")
        ax.set_ylabel("Measured GFLOP/s")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(outdir / "raw_bf16_measured_gflops.png", dpi=180)
        plt.close(fig)
    return None


def main() -> int:
    global CAMPAIGN
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, default=CAMPAIGN)
    parser.add_argument(
        "--plots",
        action="store_true",
        help="write optional static PNG figures if Matplotlib is installed",
    )
    args = parser.parse_args()
    CAMPAIGN = args.campaign_dir.resolve()
    ref = json.loads((CAMPAIGN / "paper_reference.json").read_text())
    status_rows = process_status()
    main_results, main_cases = main_records(ref, status_rows)

    scaling_cases, scaling_results = [], []
    for n in (1024, 4096, 16384):
        for t in THREADS:
            key = f"scaling_fp32_n{n}_t{t}"
            row = read_one(CAMPAIGN / "results" / f"{key}.csv")
            case = check_case(key, row, "fp32", n, t, 6, status_rows)
            scaling_cases.append(case)
            if row:
                samples = parse_samples(row.get("raw_api_call_wall_s"))
                wall = statistics.fmean(samples) if samples else None
                try:
                    mkl_seconds = float(row["mkl_gemm_s"])
                except (KeyError, ValueError):
                    mkl_seconds = None
                scaling_results.append(
                    {
                        "key": key,
                        "N": n,
                        "threads": t,
                        "valid": case["valid"],
                        "problems": case["problems"],
                        "api_call_wall_s_arithmetic_mean": wall,
                        "api_call_effective_GFLOP_s": 2.0 * n**3 / wall / 1e9 if wall else None,
                        "profile_total_s_mean_secondary": row.get("profile_total_s_mean"),
                        "mkl_gemm_only_s_mean": mkl_seconds,
                        "mkl_effective_GFLOP_s": (
                            2.0 * n**3 / mkl_seconds / 1e9
                            if mkl_seconds and mkl_seconds > 0
                            else None
                        ),
                        "mkl_gemm_only_over_api_wall_speedup": (
                            mkl_seconds / wall if wall and mkl_seconds else None
                        ),
                        "mkl_thread_count": t,
                        "timing_scope": {"v3": "complete API call wall", "oneMKL": "GEMM only"},
                        "status": row.get("status"),
                    }
                )

    raw_results, raw_cases = [], []
    for n in SIZES:
        key = f"raw_bf16_n{n}"
        row = read_one(CAMPAIGN / "results" / f"{key}.csv")
        case = check_case(key, row, "raw", n, 64, None, status_rows)
        raw_cases.append(case)
        if row:
            raw_results.append(
                {
                    "key": key,
                    "N": n,
                    "valid": case["valid"],
                    "problems": case["problems"],
                    "seconds_mean": row.get("seconds_mean"),
                    "GFLOP_s": row.get("GFLOP_s"),
                    "TFLOP_s": row.get("TFLOP_s"),
                    "paper_figure6_label": "GFLOPS (unit caveat; no conversion)",
                    "routine": row.get("routine"),
                    "status": row.get("status"),
                }
            )

    groups = {"main": main_cases, "scaling": scaling_cases, "raw_bf16": raw_cases}
    coverage = {
        name: {
            "expected": len(cases),
            "present": sum(c["present"] for c in cases),
            "valid": sum(c["valid"] for c in cases),
            "complete": bool(cases) and all(c["valid"] for c in cases),
        }
        for name, cases in groups.items()
    }
    prov = (
        (CAMPAIGN / "provenance.txt").read_text() if (CAMPAIGN / "provenance.txt").exists() else ""
    )
    provenance = {}
    for line in prov.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            provenance[k] = v
    release_artifact = ROOT / "bench/8454h/versions/v3_release/artifacts/libozamx_v3.a"
    run_library = Path("/tmp/ozamx-roofline-production/libozamx.a")
    main_source = CAMPAIGN / "source/benchmark.cpp"
    raw_source = CAMPAIGN / "source/raw_bf16.cpp"
    mkl_runtime = ROOT / "third_party/code/mkl-current/lib/libmkl_rt.so.3"
    integrity = {
        "library_sha256_provenance": provenance.get("archive_sha256"),
        "library_sha256_run_path": sha256_file(run_library),
        "library_sha256_release_archive": sha256_file(release_artifact),
        "main_source_sha256_provenance": provenance.get("main_source_sha256"),
        "main_source_sha256_actual": sha256_file(main_source),
        "raw_source_sha256_provenance": provenance.get("raw_source_sha256"),
        "raw_source_sha256_actual": sha256_file(raw_source),
        "mkl_runtime_sha256_provenance": provenance.get("mkl_rt_sha256"),
        "mkl_runtime_sha256_actual": sha256_file(mkl_runtime),
    }
    integrity["library_hashes_match"] = all(
        integrity[k] == EXPECTED_LIBRARY
        for k in (
            "library_sha256_provenance",
            "library_sha256_run_path",
            "library_sha256_release_archive",
        )
    )
    integrity["source_and_runtime_hashes_match"] = all(
        integrity[k] is not None and integrity[k] == integrity[v]
        for k, v in (
            ("main_source_sha256_provenance", "main_source_sha256_actual"),
            ("raw_source_sha256_provenance", "raw_source_sha256_actual"),
            ("mkl_runtime_sha256_provenance", "mkl_runtime_sha256_actual"),
        )
    )
    report = {
        "schema": "ozamx_v3_paper_alignment_analysis_v1",
        "generated_by": "tools/analyze_v3_paper_alignment.py",
        "campaign_dir": (
            str(CAMPAIGN.relative_to(ROOT)) if CAMPAIGN.is_relative_to(ROOT) else str(CAMPAIGN)
        ),
        "library_sha256_in_provenance": provenance.get("archive_sha256"),
        "expected_library_sha256": EXPECTED_LIBRARY,
        "library_hash_matches_expected": integrity["library_hashes_match"],
        "artifact_integrity": integrity,
        "source_id_expected": EXPECTED_SOURCE_ID,
        "provenance_source_id_matches": f"source_id={EXPECTED_SOURCE_ID}" in prov,
        "accuracy_threshold": None,
        "coverage": coverage,
        "campaign_complete": all(v["complete"] for v in coverage.values())
        and integrity["library_hashes_match"]
        and integrity["source_and_runtime_hashes_match"],
        "main_results": main_results,
        "main_cases": main_cases,
        "scaling_results": scaling_results,
        "scaling_cases": scaling_cases,
        "raw_bf16_results": raw_results,
        "raw_bf16_cases": raw_cases,
        "notes": [
            "Accuracy ratios are measured full-NxN oneMKL error divided by the reported Table 4 value; no pass threshold is imposed.",
            "Primary V3 timing is the arithmetic mean recomputed from ten raw API-wall samples.",
            "API effective GFLOP/s uses the API-wall arithmetic mean; profile throughput fields are secondary. MKL timing remains GEMM-only, so its ratio to API wall has asymmetric scope.",
            "Figure 9 has no exact point values in the paper and is not digitized here.",
            "Raw BF16 paper values retain the source figure's GFLOPS label caveat; local GFLOP/s and TFLOP/s are separate measurements.",
        ],
    }
    out = CAMPAIGN / "analysis.json"
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if args.plots:
        msg = make_plots(report, CAMPAIGN / "plots")
        if msg:
            print(msg)
    print(
        json.dumps(
            {
                "coverage": coverage,
                "campaign_complete": report["campaign_complete"],
                "library_hash_matches_expected": report["library_hash_matches_expected"],
                "analysis": str(out),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
