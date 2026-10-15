#!/usr/bin/env python3
"""Offline summaries/provenance for saved pad, THP, rectangular and adaptive scouts."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROOF = ROOT / "bench/8454h/roofline"
FROZEN_ROOT = ROOT / "bench/8454h/versions/v2_release/repo"
FROZEN_BUILD = Path("/tmp/ozamx-production-final")

FAMILIES = {
    "pad": {
        "tmp": Path("/tmp/ozamx-roof-pad-batch"),
        "processes": {
            "pass0_frozen.csv": "frozen", "pass1_p1b1.csv": "p1b1",
            "pass2_p2b1.csv": "p2b1", "pass3_p3b1.csv": "p3b1",
            "pass4_p1b2.csv": "p1b2", "pass5_frozen.csv": "frozen",
            "pass6_p1b2.csv": "p1b2", "pass7_p1b1.csv": "p1b1",
            "pass8_frozen.csv": "frozen",
        },
        "builds": {v: f"build-{v}" for v in ("p1b1", "p2b1", "p3b1", "p1b2")},
        "description": "Four block-padding/reconstruction batch variants; ABBA-style repeats with frozen controls.",
        "argv": ["--sizes", "1024,4096,8192", "--precision", "all", "--threads", "64", "--budgets", "6,21", "--reps", "5"],
    },
    "thp": {
        "tmp": Path("/tmp/ozamx-roof-thp"),
        "processes": {"pass0_frozen.csv": "frozen", "pass1_h1.csv": "h1",
                      "pass2_frozen.csv": "frozen", "pass3_h1.csv": "h1",
                      "pass4_frozen.csv": "frozen"},
        "builds": {"h1": "build-h1"},
        "description": "Workspace huge-page hint off/on comparison with smaps probe evidence.",
        "argv": ["--sizes", "1024,4096,8192", "--precision", "all", "--threads", "64", "--budgets", "6,21", "--reps", "5"],
    },
    "rect": {
        "tmp": Path("/tmp/ozamx-roof-rect"),
        "processes": {
            "pass0_frozen.csv": "frozen", "pass1_n256p1.csv": "n256p1",
            "pass2_n512p1.csv": "n512p1", "pass3_n256p0.csv": "n256p0",
            "pass4_n256p1b2.csv": "n256p1b2", "pass5_frozen.csv": "frozen",
            "pass6_n256p1.csv": "n256p1", "pass7_n512p1.csv": "n512p1",
            "pass8_frozen.csv": "frozen",
        },
        "builds": {v: f"build-{v}" for v in ("n256p1", "n512p1", "n256p0", "n256p1b2")},
        "description": "Four rectangular cache-column / padding variants; frozen controls bracket candidate runs.",
        "argv": ["--sizes", "1024,4096,8192", "--precision", "all", "--threads", "64", "--budgets", "6,21", "--reps", "5"],
    },
    "adaptive": {
        "tmp": Path("/tmp/ozamx-roof-adaptive"),
        "processes": {"pass0_frozen.csv": "frozen", "pass1_adaptive.csv": "adaptive",
                      "pass2_frozen.csv": "frozen", "pass3_adaptive.csv": "adaptive",
                      "pass4_frozen.csv": "frozen"},
        "builds": {"adaptive": "build"},
        "description": "Adaptive small/large-shape blocking scout; not yet through the full large-matrix binary gate.",
        "argv": ["--sizes", "1024,2048,4096,8192", "--precision", "all", "--threads", "64", "--budgets", "6,10,15,21", "--reps", "7"],
    },
}

METRICS = ("split_s", "pack_s", "compute_s", "total_s", "wall_s", "user_s", "system_s")


def percent_change(candidate: float, reference: float):
    if reference == 0.0:
        return 0.0 if candidate == 0.0 else None
    return (candidate / reference - 1.0) * 100.0


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact(path: Path) -> dict:
    if not path.is_file():
        return {"path": str(path), "available": False}
    return {"path": str(path), "available": True, "bytes": path.stat().st_size, "sha256": sha(path)}


def cmake_options(cache: Path) -> dict:
    options = {}
    if cache.exists():
        for line in cache.read_text(errors="replace").splitlines():
            if line.startswith("OZAMX_") and "=" in line:
                key, value = line.split("=", 1)
                options[key.split(":", 1)[0]] = value
    return options


def frozen_artifacts() -> dict:
    srcs = ["CMakeLists.txt", "src/gemm.cpp", "src/kernels.S", "src/preprocess.hpp",
            "src/tuning.hpp", "include/ozamx/gemm.hpp", "bench/optimization_benchmark.cpp"]
    return {
        "source_root": str(FROZEN_ROOT),
        "source_files": {p: artifact(FROZEN_ROOT / p) for p in srcs},
        "cmake_cache": artifact(FROZEN_BUILD / "CMakeCache.txt"),
        "cmake_options": cmake_options(FROZEN_BUILD / "CMakeCache.txt"),
        "library": artifact(FROZEN_BUILD / "libozamx.a"),
        "benchmark_binary": artifact(FROZEN_BUILD / "ozamx_optimization_benchmark"),
        "v2_release_manifest": artifact(ROOT / "bench/8454h/versions/v2_release/MANIFEST.sha256"),
    }


def candidate_artifacts(cfg: dict, variant: str) -> dict:
    tmp = cfg["tmp"]
    build_name = cfg["builds"].get(variant)
    if build_name is None:
        return frozen_artifacts()
    build = tmp / build_name
    srcs = ["CMakeLists.txt", "src/gemm.cpp", "src/kernels.S", "src/preprocess.hpp",
            "src/tuning.hpp", "include/ozamx/gemm.hpp", "bench/optimization_benchmark.cpp"]
    cache = build / "CMakeCache.txt"
    options = cmake_options(cache)
    return {
        "variant": variant,
        "source_root": str(tmp),
        "source_files": {p: artifact(tmp / p) for p in srcs},
        "cmake_cache": artifact(cache), "cmake_options": options,
        "library": artifact(build / "libozamx.a"),
        "benchmark_binary": artifact(build / "ozamx_optimization_benchmark"),
        "candidate_cmake": artifact(tmp / "CMakeLists.txt"),
        "build_log": artifact(tmp / (f"{build_name}.log" if build_name != "build" else "build.log")),
    }


def outlier_flags(values: list[float]) -> list[int]:
    if len(values) < 4:
        return []
    ordered = sorted(values)
    q1, _, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
    spread = q3 - q1
    lo, hi = q1 - 1.5 * spread, q3 + 1.5 * spread
    return [i for i, val in enumerate(values) if val < lo or val > hi]


def load_process(path: Path, variant: str) -> dict:
    records = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    grouped: dict[tuple[str, int, int], list[dict]] = {}
    for row in records:
        if row["record"] != "rep":
            continue
        key = (row["precision"], int(row["size"]), int(row["budget"]))
        grouped.setdefault(key, []).append(row)
    configs = []
    for (precision, size, budget), rows in sorted(grouped.items()):
        rows.sort(key=lambda x: int(x["rep"]))
        nums = {m: [float(r[m]) for r in rows if r[m]] for m in METRICS}
        stats = {m: {"median": statistics.median(vals), "mean": statistics.mean(vals),
                     "sample_sd": statistics.stdev(vals) if len(vals) > 1 else 0.0,
                     "min": min(vals), "max": max(vals)} for m, vals in nums.items() if vals}
        configs.append({"precision": precision, "size": size, "budget": budget,
                        "rep_count": len(rows), "metrics": stats,
                        "raw_reps": [{k: r[k] for k in ("rep", "seed", *METRICS, "minor_faults", "major_faults",
                                                          "voluntary_switches", "involuntary_switches", "max_rss_kib")}
                                     for r in rows],
                        "potential_total_time_outlier_rep_indices_tukey_1_5_iqr": outlier_flags(nums["total_s"])})
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path), "variant": variant,
            "csv_rows": len(records), "timed_rep_rows": sum(len(v) for v in grouped.values()),
            "warmup_rows": sum(r["record"] == "warmup" for r in records), "configurations": configs}


def aggregate(processes: list[dict]) -> list[dict]:
    by_key: dict[tuple[str, int, int], dict[str, list[dict]]] = {}
    for proc in processes:
        for cfg in proc["configurations"]:
            key = (cfg["precision"], cfg["size"], cfg["budget"])
            by_key.setdefault(key, {}).setdefault(proc["variant"], []).append(cfg)
    result = []
    for key, variants in sorted(by_key.items()):
        item = {"precision": key[0], "size": key[1], "budget": key[2], "variants": {}}
        for variant, configs in variants.items():
            medians = {metric: [c["metrics"][metric]["median"] for c in configs] for metric in METRICS}
            item["variants"][variant] = {"process_count": len(configs), "process_medians": medians,
                "median_of_process_medians": {m: statistics.median(v) for m, v in medians.items()},
                "raw_samples_all_processes_retained": {m: [[float(r[m]) for r in c["raw_reps"]]
                    for c in configs] for m in METRICS}}
        if "frozen" in variants:
            for variant in variants:
                if variant == "frozen":
                    continue
                changes = {}
                for metric in METRICS:
                    frozen = item["variants"]["frozen"]["median_of_process_medians"][metric]
                    candidate = item["variants"][variant]["median_of_process_medians"][metric]
                    changes[metric] = percent_change(candidate, frozen)
                item["variants"][variant]["change_vs_frozen_percent"] = changes
                item["variants"][variant]["change_vs_frozen_api_wall_percent"] = changes["wall_s"]
                item["variants"][variant]["change_vs_frozen_profile_total_percent"] = changes["total_s"]
        result.append(item)
    return result


def adaptive_pairing(processes: list[dict], aggregates: list[dict]) -> dict:
    byname = {Path(p["path"]).name: p for p in processes}
    paired = []
    for cfg in aggregates:
        key = (cfg["precision"], cfg["size"], cfg["budget"])
        for cand_name, before_name, after_name in (("pass1_adaptive.csv", "pass0_frozen.csv", "pass2_frozen.csv"),
                                                   ("pass3_adaptive.csv", "pass2_frozen.csv", "pass4_frozen.csv")):
            lookup = {metric: [] for metric in ("wall_s", "total_s")}
            for name in (cand_name, before_name, after_name):
                match = next(x for x in byname[name]["configurations"]
                             if (x["precision"], x["size"], x["budget"]) == key)
                for metric in lookup:
                    lookup[metric].append(match["metrics"][metric]["median"])
            changes = {}
            refs = {}
            candidates = {}
            for metric, vals in lookup.items():
                cand, before, after = vals
                ref = (before + after) / 2.0
                candidates[metric] = cand
                refs[metric] = {"frozen_before_s": before, "frozen_after_s": after,
                                "bracket_mean_s": ref}
                changes[metric] = percent_change(cand, ref)
            paired.append({"config": {"precision": key[0], "size": key[1], "budget": key[2]},
                           "candidate_process": cand_name, "candidate_process_median_s": candidates,
                           "bracketing_frozen_reference_s": refs, "candidate_change_percent": changes})
    wall_values = [x["candidate_change_percent"]["wall_s"] for x in paired]
    total_values = [x["candidate_change_percent"]["total_s"] for x in paired]
    return {"method": "Each adaptive process median compared with arithmetic mean of immediately preceding/following frozen process medians; API wall is primary, profile total is secondary; all raw repetitions remain in process records.",
            "paired_process_comparisons": len(paired),
            "api_wall_median_change_percent": statistics.median(wall_values),
            "api_wall_candidate_faster_count": sum(x < 0 for x in wall_values),
            "api_wall_candidate_slower_count": sum(x > 0 for x in wall_values),
            "profile_total_median_change_percent": statistics.median(total_values),
            "profile_total_candidate_faster_count": sum(x < 0 for x in total_values),
            "profile_total_candidate_slower_count": sum(x > 0 for x in total_values),
            "paired": paired}


def main() -> None:
    for family, cfg in FAMILIES.items():
        folder = ROOF / f"search_{family}"
        processes = []
        ordered = []
        for name, variant in cfg["processes"].items():
            path = folder / name
            proc = load_process(path, variant)
            proc["artifacts"] = candidate_artifacts(cfg, variant)
            processes.append(proc)
            ordered.append({"csv": str(path.relative_to(ROOT)), "variant": variant})
        aggregates = aggregate(processes)
        summary = {"schema": "ozamx-roofline-search-summary-v1", "family": family,
                   "description": cfg["description"], "process_order": ordered,
                   "configurations": aggregates, "processes": processes}
        if family == "adaptive":
            summary["paired_comparison"] = adaptive_pairing(processes, aggregates)
        (folder / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")

        sources = ["CMakeLists.txt", "src/gemm.cpp", "src/kernels.S", "src/preprocess.hpp",
                   "src/tuning.hpp", "include/ozamx/gemm.hpp", "bench/optimization_benchmark.cpp"]
        variant_artifacts = {v: candidate_artifacts(cfg, v) for v in sorted(set(cfg["processes"].values()))}
        metadata = {"schema": "ozamx-roofline-search-metadata-v1", "family": family,
            "generated_utc": "offline; generated by summarize_searches.py; no benchmark executed",
            "timing_semantics": {"primary": "wall_s: steady_clock around complete public profiled GEMM call",
                "secondary": "total_s: library profile split+pack+compute sum; may omit setup/teardown costs in wall_s",
                "per_process_summary": "median of timed record=='rep' rows, calculated before comparing repeated processes"},
            "host_context_from_search_request": {"cpu": "Intel Xeon Platinum 8454H", "affinity": "CPUs 0-63",
                "openmp_threads": 64, "omp_places": "cores", "omp_proc_bind": "close",
                "omp_dynamic": "FALSE", "workspace_cache_bytes": 2147483648,
                "context_provenance": "Recorded as run context for these search CSVs; see v2 release machine metadata for host inventory."},
            "process_order": ordered, "argv_reconstructed_from_csv_schema": cfg["argv"],
            "command_caveat": "Original shell command/transcript was not saved beside these CSVs; command arguments are reconstructed from CSV shape/repetition counts and saved benchmark driver. Do not treat this reconstruction as an original-run transcript.",
            "frozen_artifacts": frozen_artifacts(), "candidate_artifacts_by_variant": variant_artifacts,
            "summary_script": artifact(Path(__file__).resolve()),
            "validation_note": "CTest initially had alias/late-path targets marked NotRun because they were not built; after building all targets, the full CTest suite passed. This was an incomplete test invocation, not a numerical benchmark failure.",
            "retention_policy": "All record=='rep' samples are preserved in summary.json, including potential outliers flagged by Tukey 1.5-IQR; no timed sample is discarded.",
            "commands_document": artifact(ROOF / "search_commands.md"),
            "generated_summary": artifact(folder / "summary.json"),
            "source_inputs": {p: artifact(cfg["tmp"] / p) for p in sources},
            "csv_inputs": {name: artifact(folder / name) for name in cfg["processes"]}}
        if family == "thp":
            metadata["smaps_probe_evidence"] = {name: artifact(folder / name) for name in ("probe_hint0.json", "probe_hint1.json")}
        (folder / "metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
        print(f"{family}: wrote summary.json with {len(processes)} processes/{len(aggregates)} configs; metadata.json")


if __name__ == "__main__":
    main()
