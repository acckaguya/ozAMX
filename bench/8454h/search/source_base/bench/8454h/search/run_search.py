#!/usr/bin/env python3
"""Reproducible, lock-serialized tuning search for the Xeon 8454H GEMM.

This runner is intentionally inert until invoked. It expects compile-time CMake
cache variables from the production tuning patch and fingerprints those sources
before deciding whether an existing ledger row can be resumed.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SEARCH = ROOT / "bench/8454h/search"
LOCK = Path("/tmp/ozamx-perf.lock")
RUNNER_VERSION = 2
SCOUT_SIZES = "1024,4096"
FINAL_SIZES = "256,1024,4096,8192"
HOLDOUT_SIZES = "512,2048"
POOL_SIZES = "8192"
SCOUT_BUDGETS = "6,21"
FINAL_BUDGETS = "6,10,15,21"
SCOUT_REPS = 3
FINAL_REPS = 7
FINAL_PASSES = 3
POOL_REPS = 5
POOL_PASSES = 3
THREADS = 64
CPUSET = os.environ.get("OZAMX_CPUSET", "0-63")
OMP_ENV = {
    "OMP_NUM_THREADS": str(THREADS),
    "OMP_PLACES": "cores",
    "OMP_PROC_BIND": "close",
    "OMP_DYNAMIC": "FALSE",
}
FINGERPRINT_PATHS = (
    "CMakeLists.txt",
    "src/gemm.cpp",
    "src/preprocess.hpp",
    "src/kernels.S",
    "src/runtime.cpp",
    "src/tuning.hpp",
    "include/ozamx/gemm.hpp",
    "bench/optimization_benchmark.cpp",
    "tests/validation.cpp",
    "bench/8454h/search/run_search.py",
    "bench/8454h/search/variants.json",
    "bench/8454h/equivalence_driver.cpp",
    "bench/8454h/run_equivalence.sh",
    "bench/8454h/search/run_variant_gate.sh",
    "bench/8454h/before/src/gemm.cpp",
    "bench/8454h/before/src/runtime.cpp",
    "bench/8454h/before/include/ozamx/gemm.hpp",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_fingerprint() -> tuple[str, dict[str, str]]:
    files = {}
    for rel in FINGERPRINT_PATHS:
        path = ROOT / rel
        if not path.is_file():
            raise RuntimeError(f"fingerprint input is missing: {rel}")
        files[rel] = sha(path.read_bytes())
    return sha(json.dumps(files, sort_keys=True).encode()), files


def command_text(args: list[str]) -> str:
    return subprocess.list2cmdline(args)


def run_checked(args: list[str], *, cwd: Path, env: dict[str, str], log: Path) -> float:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as out:
        out.write("$ " + command_text(args) + "\n")
        out.flush()
        began = time.perf_counter()
        result = subprocess.run(args, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}); see {log}")
    return time.perf_counter() - began


def append_ledger(row: dict) -> None:
    path = SEARCH / "ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        f.flush()
        os.fsync(f.fileno())


def ledger_rows() -> list[dict]:
    path = SEARCH / "ledger.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # A killed writer can leave a torn final line; earlier fsynced rows
            # remain valid and a fresh completion row will be appended.
            continue
    return rows


def append_lineage() -> tuple[str, dict]:
    src_hash, files = source_fingerprint()
    compiler = subprocess.run(["g++", "--version"], text=True, capture_output=True, check=True).stdout.splitlines()[0]
    cmake = subprocess.run(["cmake", "--version"], text=True, capture_output=True, check=True).stdout.splitlines()[0]
    lineage = {
        "runner_version": RUNNER_VERSION,
        "source_fingerprint": src_hash,
        "source_files": files,
        "compiler": compiler,
        "cmake": cmake,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpuset": CPUSET,
        "openmp_environment": OMP_ENV,
        "thread_count": THREADS,
        "scout_sizes": SCOUT_SIZES,
        "final_sizes": FINAL_SIZES,
        "scout_budgets": SCOUT_BUDGETS,
        "final_budgets": FINAL_BUDGETS,
        "scout_repetitions": SCOUT_REPS,
        "final_repetitions": FINAL_REPS,
        "final_passes": FINAL_PASSES,
        "pool_sizes": POOL_SIZES,
        "pool_repetitions": POOL_REPS,
        "pool_passes": POOL_PASSES,
    }
    return sha(json.dumps(lineage, sort_keys=True).encode()), lineage


def load_variants() -> list[dict]:
    data = json.loads((SEARCH / "variants.json").read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise RuntimeError("unsupported variants.json version")
    variants = data.get("variants", [])
    if not 6 <= len(variants) <= 18:
        raise RuntimeError("search plan must contain 6 to 18 variants")
    names = [v.get("name") for v in variants]
    if len(set(names)) != len(names) or "default" not in names:
        raise RuntimeError("variant names must be unique and include default")
    for v in variants:
        if not isinstance(v.get("definitions", {}), dict):
            raise RuntimeError(f"definitions for {v['name']} must be an object")
    return variants


def completed_runs() -> dict[tuple, dict]:
    done = {}
    for row in ledger_rows():
        if row.get("event") == "completed":
            key = (row.get("study_fingerprint"), row.get("stage"), row.get("variant"), row.get("pass"))
            done[key] = row
    return done


def read_raw(csv_path: Path) -> dict:
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
    fields = rows[0].keys() if rows else ()
    wall_fields = [f for f in fields if "wall" in f.lower() and f.lower().endswith(("_s", "_seconds"))]
    def wall_priority(name: str) -> tuple[int, str]:
        n = name.lower()
        if "true" in n and "call" in n:
            p = 0
        elif "call" in n:
            p = 1
        elif "total" in n:
            p = 2
        else:
            p = 3
        return p, name
    objective_field = sorted(wall_fields, key=wall_priority)[0] if wall_fields else "total_s"
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        if row.get("record") != "rep":
            continue
        key = (row["precision"], int(row["size"]), int(row["budget"]))
        groups.setdefault(key, []).append(row)
    metrics = {}
    for key, group in groups.items():
        totals = [float(x["total_s"]) for x in group]
        objective = [float(x[objective_field]) for x in group]
        checksums = [float(x["checksum"]) for x in group]
        metrics["/".join(map(str, key))] = {
            "n": len(group),
            "total_median_s": statistics.median(totals),
            "objective_field": objective_field,
            "objective_median_s": statistics.median(objective),
            "total_mean_s": statistics.mean(totals),
            "total_stdev_s": statistics.stdev(totals) if len(totals) > 1 else 0.0,
            "total_min_s": min(totals),
            "total_max_s": max(totals),
            "split_median_s": statistics.median(float(x["split_s"]) for x in group),
            "pack_median_s": statistics.median(float(x["pack_s"]) for x in group),
            "compute_median_s": statistics.median(float(x["compute_s"]) for x in group),
            "checksums": checksums,
            "extra_numeric_medians": {
                field: statistics.median(float(x[field]) for x in group)
                for field in group[0]
                if field not in {"record", "precision", "size", "budget", "rep", "seed", "split_s", "pack_s",
                                 "compute_s", "total_s", "checksum", "mean_s", "std_s", "min_s", "max_s"}
                and all(x.get(field, "") != "" for x in group)
                and all(_is_float(x[field]) for x in group)
            },
        }
    dimensions = len({k[1] for k in groups})
    fp64_budgets = len({k[2] for k in groups if k[0] == "fp64"})
    expected = dimensions * (1 + fp64_budgets)
    if len(metrics) != expected:
        raise RuntimeError(f"expected {expected} precision/size/budget rows, found {len(metrics)} in {csv_path}")
    if not metrics:
        raise RuntimeError(f"no timed result rows found in {csv_path}")
    return {"metrics": metrics, "raw_rows": len(rows), "expected_configurations": expected}


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def cmake_definitions(variant: dict) -> dict[str, int | str]:
    return dict(variant.get("definitions", {}))


def ensure_baseline_binary(study_fp: str, env: dict[str, str], outdir: Path) -> tuple[Path, str]:
    baseline_dir = Path("/tmp/ozamx-search") / f"v{RUNNER_VERSION}" / study_fp[:16]
    binary = baseline_dir / "frozen_baseline_equivalence"
    metadata = baseline_dir / "frozen_baseline_equivalence.json"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    paths = ("bench/8454h/before/src/gemm.cpp", "bench/8454h/before/src/runtime.cpp",
             "bench/8454h/before/include/ozamx/gemm.hpp", "bench/8454h/equivalence_driver.cpp")
    hashes = {p: sha((ROOT / p).read_bytes()) for p in paths}
    fingerprint = sha(json.dumps(hashes, sort_keys=True).encode())
    if binary.is_file() and metadata.is_file():
        prior = json.loads(metadata.read_text(encoding="utf-8"))
        digest = sha(binary.read_bytes())
        if prior.get("fingerprint") == fingerprint and prior.get("binary_sha256") == digest:
            return binary, digest
    command = ["g++", "-O3", "-std=c++17", "-mamx-tile", "-mamx-bf16", "-fopenmp",
               "-I" + str(ROOT / "bench/8454h/before/include"),
               str(ROOT / "bench/8454h/before/src/gemm.cpp"),
               str(ROOT / "bench/8454h/before/src/runtime.cpp"),
               str(ROOT / "bench/8454h/equivalence_driver.cpp"), "-o", str(binary)]
    log = outdir / "baseline_build.log"
    run_checked(command, cwd=ROOT, env=env, log=log)
    digest = sha(binary.read_bytes())
    metadata.write_text(json.dumps({"fingerprint": fingerprint, "source_hashes": hashes,
                                    "binary_sha256": digest, "command": command},
                                   indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return binary, digest


def parse_gate_summary(log: Path) -> dict:
    for line in reversed(log.read_text(encoding="utf-8").splitlines()):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and any(k.startswith("baseline_t1_vs_optimized") for k in item):
            return item
    raise RuntimeError(f"100-case equivalence gate summary missing from {log}")


def one_run(variant: dict, stage: str, pass_index: int, sizes: str, reps: int,
            budgets: str, study_fp: str, lineage: dict, resume: bool) -> dict | None:
    key = (study_fp, stage, variant["name"], pass_index)
    existing = completed_runs().get(key)
    if resume and existing:
        raw = ROOT / existing["raw_csv"]
        if raw.is_file() and sha(raw.read_bytes()) == existing.get("raw_sha256"):
            print(f"resume: reusing verified {stage}/{variant['name']}/pass{pass_index}", flush=True)
            return existing
        print(f"resume: prior result artifact missing or changed; rerunning {stage}/{variant['name']}/pass{pass_index}", flush=True)

    overrides = cmake_definitions(variant)
    definitions = dict(TUNING_DEFAULTS)
    definitions.update(overrides)
    run_environment = {"OZAMX_WORKSPACE_CACHE_BYTES": str(1 << 30)}
    run_environment.update(variant.get("environment", {}))
    config_fp = sha(json.dumps(definitions, sort_keys=True).encode())
    identity = sha(json.dumps({"study": study_fp, "stage": stage, "variant": variant["name"],
                              "pass": pass_index, "definitions": definitions,
                              "environment": run_environment, "sizes": sizes, "budgets": budgets,
                              "reps": reps}, sort_keys=True).encode())
    build = Path("/tmp/ozamx-search") / f"v{RUNNER_VERSION}" / study_fp[:16] / stage / variant["name"] / f"pass{pass_index}" / "build"
    outdir = SEARCH / "runs" / study_fp[:16] / stage / variant["name"] / f"pass{pass_index}"
    raw = outdir / "optimization_benchmark.csv"
    outdir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(OMP_ENV)
    env.update({str(k): str(v) for k, v in run_environment.items()})
    cmake_args = ["cmake", "-S", str(ROOT), "-B", str(build),
                  "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
                  "-DOZAMX_ENABLE_OPENMP=ON", "-DOZAMX_BUILD_PROBE=OFF", "-DBUILD_TESTING=ON"]
    cmake_args += [f"-D{k}={v}" for k, v in sorted(definitions.items())]
    build_args = ["cmake", "--build", str(build), "--target", "ozamx_optimization_benchmark", "ozamx_validation", "-j4"]
    test_args = ["ctest", "--test-dir", str(build), "--output-on-failure"]
    bench = build / "ozamx_optimization_benchmark"
    bench_args = ["taskset", "-c", CPUSET, str(bench), "--sizes", sizes,
                  "--precision", "all", "--threads", str(THREADS), "--reps", str(reps),
                  "--budgets", budgets, "--output", str(raw)]

    with LOCK.open("a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        print(f"[{stage}] {variant['name']} pass {pass_index}: lock acquired; compiling and validating", flush=True)
        started = time.time()
        started_row = {
            "event": "started", "runner_version": RUNNER_VERSION, "study_fingerprint": study_fp,
            "job_fingerprint": identity, "stage": stage, "variant": variant["name"], "pass": pass_index,
            "definitions": definitions, "sizes": sizes, "repetitions": reps,
            "budgets": budgets, "environment_overrides": run_environment,
            "started_unix": started, "lineage": lineage,
        }
        append_ledger(started_row)
        joblog = outdir / "run.log"
        phase_wall = {}
        gate_summary_path = outdir / "gate_summary.json"
        baseline_digest = None
        try:
            phase_wall["cmake_configure_s"] = run_checked(cmake_args, cwd=ROOT, env=env, log=joblog)
            compile_commands = build / "compile_commands.json"
            if definitions:
                compile_text = compile_commands.read_text(encoding="utf-8")
                absent = [f"-D{k}={v}" for k, v in definitions.items() if f"-D{k}={v}" not in compile_text]
                if absent:
                    raise RuntimeError("requested tuning definitions did not reach compiler commands: " + ", ".join(absent))
            phase_wall["build_s"] = run_checked(build_args, cwd=ROOT, env=env, log=joblog)
            # CTest launches native validation with the same CPU placement and
            # OpenMP settings, under the lock before any timing is collected.
            phase_wall["ctest_s"] = run_checked(["taskset", "-c", CPUSET, *test_args], cwd=ROOT, env=env, log=joblog)
            baseline_binary, baseline_digest = ensure_baseline_binary(study_fp, env, outdir)
            gate_env = dict(env)
            gate_env.update({
                "OZAMX_PERF_LOCK_HELD": "1",
                "OZAMX_PERF_LOCK": str(LOCK),
                "OZAMX_BASELINE_BINARY": str(baseline_binary),
                "OZAMX_BASELINE_SOURCE_DIR": str(ROOT / "bench/8454h/before"),
                "OZAMX_BUILD_DIR": str(build.parent / "equivalence_build"),
            })
            shutil.rmtree(gate_env["OZAMX_BUILD_DIR"], ignore_errors=True)
            gate_args = ["bash", str(ROOT / "bench/8454h/search/run_variant_gate.sh")]
            gate_args += [f"-D{k}={v}" for k, v in sorted(definitions.items())]
            phase_wall["equivalence_gate_s"] = run_checked(gate_args, cwd=ROOT, env=gate_env, log=joblog)
            gate_summary = parse_gate_summary(joblog)
            for comparison, result in gate_summary.items():
                if result.get("cases") != 100 or result.get("bitwise_mismatches_including_signed_zero") != 0 or result.get("padding_guard_failures") != 0:
                    raise RuntimeError(f"100-case gate failed ({comparison}): {result}")
            gate_doc = {"gate_source_fingerprint": sha(json.dumps({p: sha((ROOT / p).read_bytes())
                                                                        for p in FINGERPRINT_PATHS},
                                                                       sort_keys=True).encode()),
                        "frozen_baseline_binary_sha256": baseline_digest,
                        "source_hashes": {p: sha((ROOT / p).read_bytes()) for p in FINGERPRINT_PATHS},
                        "summary": gate_summary}
            gate_summary_path.write_text(json.dumps(gate_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            phase_wall["benchmark_process_wall_s"] = run_checked(bench_args, cwd=ROOT, env=env, log=joblog)
            result = read_raw(raw)
            raw_hash = sha(raw.read_bytes())
            metrics_path = outdir / "metrics.json"
            metrics_doc = {"runner_version": RUNNER_VERSION, "study_fingerprint": study_fp,
                           "job_fingerprint": identity, "stage": stage, "variant": variant["name"],
                           "pass": pass_index, "definitions": definitions, "sizes": sizes,
                           "repetitions": reps, "budgets": budgets, "environment_overrides": run_environment,
                           "phase_wall_s": phase_wall, "gate_summary_json": str(gate_summary_path.relative_to(ROOT)),
                           "gate_summary_sha256": sha(gate_summary_path.read_bytes()),
                           "frozen_baseline_binary_sha256": baseline_digest,
                           "raw_csv": str(raw.relative_to(ROOT)),
                           "raw_sha256": raw_hash, **result}
            metrics_path.write_text(json.dumps(metrics_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            completed = {"event": "completed", **{k: v for k, v in metrics_doc.items() if k != "metrics"},
                         "metrics": result["metrics"], "metrics_json": str(metrics_path.relative_to(ROOT)),
                         "metrics_sha256": sha(metrics_path.read_bytes()),
                         "elapsed_s": time.time() - started, "config_fingerprint": config_fp}
            append_ledger(completed)
            print(f"[{stage}] {variant['name']} pass {pass_index}: completed in {completed['elapsed_s']:.1f}s", flush=True)
            # Keep only measured artifacts and logs in the repository. Builds
            # are reproducible from the fingerprint and are cheap to recreate;
            # retaining each clone would exhaust the small search volume.
            shutil.rmtree(build, ignore_errors=True)
            return completed
        except Exception as exc:
            append_ledger({"event": "failed", "runner_version": RUNNER_VERSION,
                           "study_fingerprint": study_fp, "job_fingerprint": identity,
                           "stage": stage, "variant": variant["name"], "pass": pass_index,
                           "error": str(exc), "elapsed_s": time.time() - started})
            print(f"[{stage}] {variant['name']} pass {pass_index}: FAILED: {exc}; see {joblog}", flush=True)
            raise
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def latest_stage(study_fp: str, stage: str) -> dict[str, list[dict]]:
    grouped: dict[str, dict[int, dict]] = {}
    for row in completed_runs().values():
        if row.get("study_fingerprint") == study_fp and row.get("stage") == stage:
            grouped.setdefault(row["variant"], {})[int(row["pass"])] = row
    return {name: [runs[i] for i in sorted(runs)] for name, runs in grouped.items()}


def geomean_speedup(candidate: dict, baseline: dict) -> float | None:
    common = set(candidate) & set(baseline)
    if not common:
        return None
    ratios = []
    for key in sorted(common):
        b = baseline[key]["objective_median_s"]
        c = candidate[key]["objective_median_s"]
        if b > 0 and c > 0:
            ratios.append(b / c)
    return math.exp(statistics.mean(math.log(x) for x in ratios)) if ratios else None


def aggregate_pass_metrics(runs: list[dict]) -> dict:
    keys = set.intersection(*(set(row["metrics"]) for row in runs))
    combined = {}
    for key in keys:
        totals = [row["metrics"][key]["total_median_s"] for row in runs]
        objective = [row["metrics"][key]["objective_median_s"] for row in runs]
        combined[key] = {"total_median_s": statistics.median(totals),
                         "objective_median_s": statistics.median(objective),
                         "objective_field": runs[0]["metrics"][key]["objective_field"],
                         "pass_medians_s": totals,
                         "objective_pass_medians_s": objective,
                         "pass_median_stdev_s": statistics.stdev(totals) if len(totals) > 1 else 0.0}
    return combined


def select_variants(study_fp: str, stage: str, variants: list[dict], count: int) -> list[dict]:
    grouped = latest_stage(study_fp, stage)
    required_passes = FINAL_PASSES if stage == "final" else 1
    incomplete = [v["name"] for v in variants
                  if v["name"] not in grouped or len(grouped[v["name"]]) < required_passes]
    if incomplete:
        raise RuntimeError(f"cannot rank incomplete {stage} runs: {', '.join(incomplete)}")
    if "default" not in grouped:
        raise RuntimeError(f"cannot select from {stage}: default variant has not completed")
    baseline = aggregate_pass_metrics(grouped["default"])
    ranking = []
    for variant in variants:
        if variant["name"] not in grouped:
            continue
        metrics = aggregate_pass_metrics(grouped[variant["name"]])
        score = geomean_speedup(metrics, baseline)
        if score is not None:
            ranking.append((score, variant))
    ranking.sort(key=lambda x: x[0], reverse=True)
    if not ranking:
        raise RuntimeError(f"no completed {stage} variants to rank")
    selected = [next(v for v in variants if v["name"] == "default")]
    for _, v in ranking:
        if v not in selected:
            selected.append(v)
        if len(selected) >= count:
            break
    report = SEARCH / f"selection_{stage}_{study_fp[:16]}.json"
    report.write_text(json.dumps([{"variant": v["name"], "geomean_speedup_vs_default": score,
                                  "metrics": aggregate_pass_metrics(grouped[v["name"]])}
                                 for score, v in ranking], indent=2) + "\n", encoding="utf-8")
    print(f"selection report: {report}", flush=True)
    return selected


TUNING_AXES = {
    "OZAMX_CACHE_BLOCK": (32, 64, 128, 256),
    "OZAMX_PREP_GRAIN": (16384, 32768, 65536),
    "OZAMX_MIN_COMPUTE_WORK": (1, 4, 8, 16),
    "OZAMX_TILELOAD_HINT": (0, 1),
    "OZAMX_LOAD_SCHEDULE": (0, 1),
    "OZAMX_LOOP_ORDER": (0, 1),
    "OZAMX_MN_ORDER": (0, 1),
}
TUNING_DEFAULTS = {"OZAMX_CACHE_BLOCK": 128, "OZAMX_PREP_GRAIN": 32768,
                   "OZAMX_MIN_COMPUTE_WORK": 8, "OZAMX_TILELOAD_HINT": 0,
                   "OZAMX_LOAD_SCHEDULE": 0, "OZAMX_LOOP_ORDER": 0,
                   "OZAMX_MN_ORDER": 0}


def generate_refine_variants(study_fp: str, scout_variants: list[dict]) -> list[dict]:
    grouped = latest_stage(study_fp, "scout")
    if "default" not in grouped:
        raise RuntimeError("refine requires completed scout results")
    baseline = aggregate_pass_metrics(grouped["default"])
    scores = {}
    for name, runs in grouped.items():
        scores[name] = geomean_speedup(aggregate_pass_metrics(runs), baseline)
    best_variant = max((v for v in scout_variants if v["name"] in scores),
                       key=lambda v: scores[v["name"]] if scores[v["name"]] is not None else -1)
    center = dict(TUNING_DEFAULTS)
    center.update(cmake_definitions(best_variant))

    axis_effects = []
    for axis, values in TUNING_AXES.items():
        single = [v for v in scout_variants if set(cmake_definitions(v)) == {axis} and v["name"] in scores]
        measured = sorted(single, key=lambda v: scores[v["name"]] or -1, reverse=True)
        alternate = next((cmake_definitions(v)[axis] for v in measured
                          if cmake_definitions(v)[axis] != center[axis]), None)
        if alternate is None:
            remaining = [x for x in values if x != center[axis]]
            alternate = min(remaining, key=lambda x: abs(float(x) - float(center[axis])))
            effect = 0.0
        else:
            effect = abs(math.log(max(scores[measured[0]["name"]] or 1.0, 1e-12)))
        axis_effects.append((effect, axis, alternate))
    axis_effects.sort(reverse=True)
    singles = axis_effects[:6]
    pairs = axis_effects[:4]
    definitions = []

    def add(name: str, changes: list[tuple[str, int]]) -> None:
        config = dict(center)
        for key, value in changes:
            config[key] = value
        defs = {k: v for k, v in config.items() if v != TUNING_DEFAULTS[k]}
        if defs and defs not in definitions:
            definitions.append(defs)

    for _, axis, value in singles:
        add("single", [(axis, value)])
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            add("pair", [(pairs[i][1], pairs[i][2]), (pairs[j][1], pairs[j][2])])
    generated = [{"name": f"refine_{i:02d}", "definitions": defs}
                 for i, defs in enumerate(definitions, 1)]
    if not 6 <= len(generated) <= 12:
        raise RuntimeError(f"refine generation produced {len(generated)} unique variants, expected 6..12")
    plan = SEARCH / f"refine_plan_{study_fp[:16]}.json"
    plan.write_text(json.dumps({"center_variant": best_variant["name"],
                                "center": center, "variants": generated}, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(f"refine center {best_variant['name']}; generated {len(generated)} nearby single/cross variants: {plan}", flush=True)
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("scout", "refine", "final", "holdout", "pool"))
    parser.add_argument("--resume", action="store_true", help="skip only artifacts whose fingerprints and CSV hash verify")
    parser.add_argument("--variants", help="comma-separated variants; scout defaults to full grid")
    args = parser.parse_args()

    variants = load_variants()
    study_fp, lineage = append_lineage()
    print(f"study fingerprint: {study_fp}; runner v{RUNNER_VERSION}; source set fingerprinted", flush=True)
    selected = variants
    if args.variants:
        wanted = set(args.variants.split(","))
        unknown = wanted - {v["name"] for v in variants}
        if unknown:
            raise RuntimeError(f"unknown variant(s): {', '.join(sorted(unknown))}")
        selected = [v for v in variants if v["name"] in wanted]
    if args.stage == "refine":
        selected = [next(v for v in variants if v["name"] == "default")]
        selected += generate_refine_variants(study_fp, variants)
    if args.stage == "final" and not args.variants:
        refine_plan = SEARCH / f"refine_plan_{study_fp[:16]}.json"
        if not refine_plan.exists():
            raise RuntimeError("run the refine stage before final confirmation")
        refine_variants = json.loads(refine_plan.read_text(encoding="utf-8"))["variants"]
        selected = [next(v for v in variants if v["name"] == "default")]
        selected += select_variants(study_fp, "refine", refine_variants, count=3)[1:]
    if args.stage == "holdout" and not args.variants:
        refine_plan = SEARCH / f"refine_plan_{study_fp[:16]}.json"
        if not refine_plan.exists():
            raise RuntimeError("holdout requires a completed refine plan")
        refine_variants = json.loads(refine_plan.read_text(encoding="utf-8"))["variants"]
        final_rows = latest_stage(study_fp, "final")
        candidates = [next(v for v in variants if v["name"] == "default")]
        candidates += [v for v in refine_variants if v["name"] in final_rows]
        selected = select_variants(study_fp, "final", candidates, count=2)
    if args.stage == "pool":
        selected = [
            {"name": "pool_1g", "definitions": {},
             "environment": {"OZAMX_WORKSPACE_CACHE_BYTES": str(1 << 30)}},
            {"name": "pool_4g", "definitions": {},
             "environment": {"OZAMX_WORKSPACE_CACHE_BYTES": str(4 << 30)}},
        ]

    jobs = []
    if args.stage == "scout":
        jobs = [(v, "scout", 0, SCOUT_SIZES, SCOUT_REPS, SCOUT_BUDGETS) for v in selected]
    elif args.stage == "refine":
        jobs = [(v, "refine", 0, SCOUT_SIZES, SCOUT_REPS, SCOUT_BUDGETS) for v in selected]
    elif args.stage == "final":
        # Default acts as a temporal control on both sides of candidates.
        jobs = [(v, "final", p, FINAL_SIZES, FINAL_REPS, FINAL_BUDGETS)
                for p in range(FINAL_PASSES) for v in selected]
    elif args.stage == "holdout":
        jobs = [(v, "holdout", p, HOLDOUT_SIZES, FINAL_REPS, FINAL_BUDGETS)
                for p in range(FINAL_PASSES) for v in selected]
    else:
        jobs = [(v, "pool", p, POOL_SIZES, POOL_REPS, SCOUT_BUDGETS)
                for p in range(POOL_PASSES) for v in selected]

    for variant, stage, pass_index, sizes, reps, budgets in jobs:
        one_run(variant, stage, pass_index, sizes, reps, budgets, study_fp, lineage, args.resume)
    print(f"stage {args.stage} complete; inspect {SEARCH / 'ledger.jsonl'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"run_search: {error}", file=sys.stderr)
        raise SystemExit(2)
