#!/usr/bin/env python3
"""Recompute paired CSV results, cross-check the checkpoint evidence, and show paper targets.

Integrity gates (exit 2 if any fails):
  * paper protocol / timing schema / single run identity across every CSV row;
  * provenance.json status/returncode/source-unchanged and artifact fingerprints;
  * CSV <-> checkpoint cross-checks (identity, hashes, seed, complete, 10 pairs,
    raw sample vectors) for exactly the declared configurations (default: all 40);
  * no missing/extra configs within the explicitly declared size/mode scope.
Target gate (--require-paper-speedups, exit 1 if missed):
  * full 40-configuration coverage and all eight FP32 p6 API speedups >=
    the paper's Figure 7 points; a partial scope never passes this gate.
Table 4 values remain ratio-only empirical references: no accuracy threshold is invented.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
SIZES = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
MODES = [("fp32", 6), ("fp64", 6), ("fp64", 10), ("fp64", 15), ("fp64", 21)]
SOURCE_ID = "paper-alignment-paired-api-v2-20261016"
TIMING_SCHEMA = "api-wall-headline-v2"
MEASUREMENT_PROTOCOL = "paired-alternating-api-first-even"
SEED_BASE = 260904
LAUNCH_MASK = "0-63"
# Same ten frozen sources as run_paper_alignment.py; snapshot policy must not
# silently accept a provenance manifest with a source entry removed.
FROZEN_SOURCES = {"CMakeLists.txt", "include/ozamx/gemm.hpp", "src/gemm.cpp",
                  "src/preprocess.hpp", "src/tuning.hpp", "src/runtime.cpp", "src/kernels.S",
                  "bench/benchmark.cpp", "tests/paper_alignment_probe.cpp",
                  "tools/run_paper_alignment.py"}
REQUIRED_ENV = {
    "LD_LIBRARY_PATH": str(ROOT / "third_party/code/mkl-current/lib"),
    "OMP_NUM_THREADS": "64", "OMP_PLACES": "cores", "OMP_PROC_BIND": "close",
    "OMP_DYNAMIC": "FALSE", "OMP_WAIT_POLICY": "PASSIVE", "GOMP_SPINCOUNT": "0",
    "MKL_NUM_THREADS": "64", "MKL_DYNAMIC": "FALSE", "MKL_THREADING_LAYER": "GNU",
    "MKL_INTERFACE_LAYER": "LP64", "OZAMX_WORKSPACE_CACHE_BYTES": "2147483648",
}
CSV_TO_CHECKPOINT_RAW = [("raw_api_call_wall_s", "call_wall_seconds"),
                         ("raw_mkl_gemm_s", "mkl_gemm_seconds"),
                         ("raw_split_s", "split_seconds"),
                         ("raw_pack_s", "pack_seconds"),
                         ("raw_compute_recon_s", "compute_reconstruction_seconds"),
                         ("raw_profile_total_s", "total_seconds")]


def fingerprint(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def decode_identity(encoded):
    """Decode the driver's length-prefixed canonical record, including repeats."""
    raw = bytes.fromhex(encoded)
    cursor, fields = 0, {}
    while cursor < len(raw):
        values = []
        for _ in range(2):
            end = raw.index(b":", cursor)
            size = int(raw[cursor:end])
            cursor = end + 1
            assert cursor + size <= len(raw)
            values.append(raw[cursor:cursor + size].decode())
            cursor += size
        fields.setdefault(values[0], []).append(values[1])
    return fields


def single(fields, key):
    values = fields.get(key)
    return values[0] if values and len(values) == 1 else None


def parse_floats(text):
    return [float(x) for x in text.split(";") if x != ""]


def declared_scope(parser, args):
    """Resolve explicit selectors; never infer a smaller scope from missing data."""
    try:
        sizes = [int(n) for n in args.sizes.split(",")] if args.sizes is not None else list(SIZES)
        if not sizes or len(sizes) != len(set(sizes)) or not set(sizes) <= set(SIZES):
            raise ValueError("--sizes must contain distinct paper sizes")
        if args.modes is not None:
            if args.precision is not None or args.budgets is not None:
                raise ValueError("--modes cannot be combined with --precision/--budgets")
            names = args.modes.split(",")
            lookup = {f"{p}_p{b}": (p, b) for p, b in MODES}
            if len(names) != len(set(names)) or any(n not in lookup for n in names):
                raise ValueError("--modes must contain distinct paper modes")
            modes = [lookup[n] for n in names]
        else:
            budgets = [int(b) for b in args.budgets.split(",")] if args.budgets is not None else None
            if budgets is not None and (len(budgets) != len(set(budgets)) or
                                        not set(budgets) <= {6, 10, 15, 21}):
                raise ValueError("--budgets must contain distinct paper budgets")
            modes = [(p, b) for p, b in MODES
                     if args.precision in (None, "all", p) and (budgets is None or b in budgets)]
            if not modes or (budgets is not None and {b for _, b in modes} != set(budgets)):
                raise ValueError("--precision/--budgets select an unsupported paper mode")
        if args.expect_cache_bytes < 0:
            raise ValueError("--expect-cache-bytes must be non-negative")
    except ValueError as error:
        parser.error(str(error))
    return [n for n in SIZES if n in sizes], [m for m in MODES if m in modes]


def load_checkpoints(directory):
    checkpoints, problems = {}, []
    for path in sorted(directory.glob("checkpoint.*.json")):
        parts = path.name.split(".")
        if len(parts) != 5 or parts[0] != "checkpoint" or parts[4] != "json":
            problems.append(f"unexpected checkpoint file name {path.name}")
            continue
        precision, n, budget = parts[1], int(parts[2]), int(parts[3])
        key = (precision, budget, n)
        if key in checkpoints:
            problems.append(f"duplicate checkpoint for {key}")
        checkpoints[key] = json.loads(path.read_text())
    return checkpoints, problems


def check_run_commands(provenance):
    commands = []
    if provenance.get("command"):
        commands.append(provenance["command"])
    for event in provenance.get("resume_events", []):
        if event.get("command"):
            commands.append(event["command"])
    problems = []
    for command in commands:
        if len(command) < 3 or command[0] != "taskset" or command[1] != "-c" or command[2] != LAUNCH_MASK:
            problems.append(f"campaign command is not pinned to taskset -c {LAUNCH_MASK}: {command[:3]}")
    return problems


def check_identity(rows, checkpoints, provenance, directory, issues, notes,
                   expected_keys, required_env, absent_env, source_policy):
    if any(r["measurement_protocol"] != MEASUREMENT_PROTOCOL or
           r["timing_schema"] != TIMING_SCHEMA for r in rows):
        issues.append("Wrong timing schema or paired measurement protocol")
    for key in ["driver_source_sha256", "benchmark_executable_sha256", "mkl_runtime_sha256",
                "run_identity"]:
        values = {r[key] for r in rows}
        if len(values) != 1 or any(not v for v in values):
            issues.append(f"Missing or mixed {key}")
    if any(int(r["threads"]) != 64 or r["distribution"] != "uniform" or
           int(r["repetitions"]) != 10 for r in rows):
        issues.append("Paper main protocol requires 64 threads, uniform input, ten timed pairs")
    if any((r["precision"], int(r["budget"])) not in MODES for r in rows):
        issues.append("Unexpected precision/product-budget combination")
    if any(int(r["N"]) not in SIZES for r in rows):
        issues.append("Unexpected matrix size in campaign rows")
    issues.extend(check_run_commands(provenance))
    if provenance.get("status") != "complete" or provenance.get("returncode") != 0 or \
            provenance.get("source_unchanged") is not True:
        issues.append("Campaign did not complete with frozen source identity")
    if not provenance.get("resume_events"):
        notes.append("campaign has no resume_events entry")
    executable = provenance.get("artifact_sha256", {}).get("candidate")
    source = provenance.get("source_sha256", {}).get("bench/benchmark.cpp")
    for name in ["candidate", "libozamx.a", "CMakeCache.txt"]:
        p = directory / name
        if not p.is_file() or fingerprint(p) != provenance.get("artifact_sha256", {}).get(name):
            issues.append(f"Campaign artifact missing or changed: {name}")
    if source_policy == "snapshot":
        missing_sources = FROZEN_SOURCES - set(provenance.get("source_sha256", {}))
        if missing_sources:
            issues.append(f"Frozen source manifest is incomplete: {sorted(missing_sources)}")
    for name, digest in provenance.get("source_sha256", {}).items():
        snapshot = directory / "source_snapshot" / name
        live = ROOT / name
        if snapshot.is_file():
            if fingerprint(snapshot) != digest:
                issues.append(f"source snapshot differs from provenance hash: {name}")
        else:
            if source_policy == "snapshot":
                issues.append(f"source snapshot missing for {name}")
            else:
                notes.append(f"source snapshot missing for {name}")
        if source_policy == "current" and (not live.is_file() or fingerprint(live) != digest):
            issues.append(f"working tree source differs from frozen provenance hash: {name}")
    for r in rows:
        if r["benchmark_executable_sha256"] != executable or r["driver_source_sha256"] != source:
            issues.append("CSV executable/source does not match campaign provenance")
            break
        fields = decode_identity(r["run_identity"])
        expected = {"compiled_executable_sha256": r["benchmark_executable_sha256"],
                    "runtime_source_sha256": r["driver_source_sha256"],
                    "mkl_runtime_sha256": r["mkl_runtime_sha256"],
                    "timing_schema": TIMING_SCHEMA,
                    "measurement_protocol": MEASUREMENT_PROTOCOL}
        if any(fields.get(k) != [v] for k, v in expected.items()):
            issues.append("CSV identity record contradicts declared protocol/hash fields")
            break
        recorded_env = dict(v.split("=", 1) for v in fields.get("environment", []))
        if any(recorded_env.get(k) != v for k, v in provenance.get("environment", {}).items()):
            issues.append("CSV environment does not match campaign provenance")
            break
        missing_env = {k: v for k, v in required_env.items() if recorded_env.get(k) != v}
        if missing_env:
            issues.append(f"CSV identity environment lacks required entries: {sorted(missing_env)}")
            break
        if any(k in recorded_env for k in absent_env):
            issues.append(f"CSV identity environment must leave entries unset: {sorted(absent_env)}")
            break
        for key, want in [("omp_max_threads", "64"), ("mkl_max_threads", "64"),
                          ("omp_dynamic", "0"), ("mkl_dynamic", "0"),
                          ("omp_proc_bind", "3"), ("omp_num_places", "64")]:
            if single(fields, key) != want:
                issues.append(f"CSV identity {key}={fields.get(key)} (expected {want})")
                break
        if single(fields, "initial_affinity") != "0;" or \
                single(fields, "calling_thread_affinity") != "0;":
            notes.append("CPU affinity in identity is not the historical '0;' value; "
                         "verify the launch mask manually")
    mkl_paths = {r.get("mkl_runtime_path") for r in rows}
    for path in mkl_paths:
        if path and Path(path).is_file() and fingerprint(Path(path)) != \
                {r["mkl_runtime_sha256"] for r in rows}.pop():
            issues.append(f"oneMKL runtime on disk differs from recorded hash: {path}")
    hosts = set()
    for r in rows:
        fields = decode_identity(r["run_identity"])
        hosts.add(single(fields, "host"))
    if len(hosts) != 1:
        issues.append(f"mixed host identities across rows: {sorted(str(h) for h in hosts)}")

    keys = {(r["precision"], int(r["budget"]), int(r["N"])) for r in rows}
    missing = sorted(expected_keys - keys)
    unexpected = sorted(keys - expected_keys)
    if missing:
        issues.append(f"missing campaign configurations: {missing}")
    if unexpected:
        issues.append(f"unexpected campaign configurations: {unexpected}")
    ckpt_keys = set(checkpoints)
    if ckpt_keys != expected_keys:
        issues.append(f"checkpoint set does not equal the {len(expected_keys)} declared configurations: "
                      f"missing={sorted(expected_keys - ckpt_keys)} extra={sorted(ckpt_keys - expected_keys)}")
    if len(rows) != len(expected_keys):
        issues.append(f"expected {len(expected_keys)} rows, found {len(rows)}")
    row_by_key = {}
    for r in rows:
        row_by_key.setdefault((r["precision"], int(r["budget"]), int(r["N"])), r)
    for (p, b, n), c in sorted(checkpoints.items()):
        if c.get("source_id") != SOURCE_ID:
            issues.append(f"checkpoint {p}.{n}.{b}: wrong source_id")
        if c.get("timing_schema") != TIMING_SCHEMA or c.get("measurement_protocol") != MEASUREMENT_PROTOCOL:
            issues.append(f"checkpoint {p}.{n}.{b}: wrong schema/protocol")
        if c.get("complete") is not True or int(c.get("completed_timed_repetitions", -1)) != 10 or \
                int(c.get("requested_repetitions", -1)) != 10:
            issues.append(f"checkpoint {p}.{n}.{b}: not complete with ten timed pairs")
        if c.get("precision") != p or int(c.get("budget", -1)) != b or int(c.get("N", -1)) != n:
            issues.append(f"checkpoint {p}.{n}.{b}: parameters do not match the file name")
        if int(c.get("threads", -1)) != 64 or c.get("distribution") != "uniform":
            issues.append(f"checkpoint {p}.{n}.{b}: wrong threads/distribution")
        if int(c.get("seed", -1)) != SEED_BASE + n:
            issues.append(f"checkpoint {p}.{n}.{b}: unexpected seed {c.get('seed')} "
                          f"(expected {SEED_BASE + n})")
        row = row_by_key.get((p, b, n))
        if row is None:
            continue  # the missing-row issue was already recorded above
        for key in ["driver_source_sha256", "benchmark_executable_sha256", "mkl_runtime_sha256",
                    "run_identity"]:
            if c.get(key) != row[key]:
                issues.append(f"checkpoint {p}.{n}.{b}: {key} differs from its CSV row")
    for r in rows:
        key = (r["precision"], int(r["budget"]), int(r["N"]))
        c = checkpoints.get(key)
        if c is None:
            continue
        if int(r["seed"]) != int(c.get("seed", -1)):
            issues.append(f"{key}: CSV seed differs from checkpoint seed")
        for csv_key, ckpt_key in CSV_TO_CHECKPOINT_RAW:
            row_values = parse_floats(r[csv_key])
            ckpt_values = [float(x) for x in c.get(ckpt_key, [])]
            if len(row_values) != len(ckpt_values) or \
                    any(not math.isclose(a, b, rel_tol=1e-9, abs_tol=0.0)
                        for a, b in zip(row_values, ckpt_values)):
                issues.append(f"{key}: CSV {csv_key} differs from checkpoint {ckpt_key}")


def check_eight_size_coverage(rows, checkpoints):
    report = {}
    ok = True
    for mode in MODES:
        p, b = mode
        row_sizes = {int(r["N"]) for r in rows if r["precision"] == p and int(r["budget"]) == b}
        ckpt_sizes = {n for (cp, cb, n) in checkpoints if (cp, cb) == mode}
        good = row_sizes == set(SIZES) and ckpt_sizes == set(SIZES)
        ok &= good
        report[f"{p}_p{b}"] = {"csv_sizes": sorted(row_sizes),
                               "checkpoint_sizes": sorted(ckpt_sizes), "complete": good}
    return ok, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--require-paper-speedups", action="store_true")
    parser.add_argument("--sizes", help="comma-separated paper sizes (default: all eight)")
    parser.add_argument("--precision", choices=["all", "fp32", "fp64"])
    parser.add_argument("--budgets", "--budget", help="comma-separated product budgets")
    parser.add_argument("--modes", help="comma-separated paper modes, e.g. fp32_p6,fp64_p6")
    parser.add_argument("--expect-cache-bytes", type=int, default=2147483648)
    parser.add_argument("--expect-wait", choices=["passive", "runtime"], default="passive")
    parser.add_argument("--source-policy", choices=["current", "live", "snapshot"], default="current",
                        help="current/live also checks working-tree sources; snapshot requires "
                             "every frozen source snapshot and skips working-tree comparison")
    a = parser.parse_args()
    sizes, modes = declared_scope(parser, a)
    expected_keys = {(p, b, n) for p, b in modes for n in sizes}
    full_scope = sizes == SIZES and modes == MODES
    source_policy = "current" if a.source_policy == "live" else a.source_policy
    required_env = dict(REQUIRED_ENV, OZAMX_WORKSPACE_CACHE_BYTES=str(a.expect_cache_bytes))
    absent_env = []
    if a.expect_wait == "runtime":
        absent_env = ["OMP_WAIT_POLICY", "GOMP_SPINCOUNT"]
        for name in absent_env:
            del required_env[name]
    reference_path = ROOT / "bench/8454h/v3_paper_alignment/paper_reference.json"
    reference = json.loads(reference_path.read_text())
    target = dict(zip(reference["figure7_fp32_speedup"]["sizes"],
                      reference["figure7_fp32_speedup"]["speedup"]))
    rows = list(csv.DictReader(a.csv.open()))
    provenance_path = a.csv.parent / "provenance.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.is_file() else {}
    issues, notes = [], []
    if not full_scope:
        notes.append("Only the explicitly declared subset is validated; this is not full "
                     "40-configuration coverage or an all-eight paper performance result.")
    if not provenance:
        issues.append("Missing campaign provenance")
    checkpoints, ckpt_problems = load_checkpoints(a.csv.parent)
    issues.extend(ckpt_problems)
    if provenance:
        check_identity(rows, checkpoints, provenance, a.csv.parent, issues, notes,
                       expected_keys, required_env, absent_env, source_policy)
    eight_ok, eight_report = check_eight_size_coverage(rows, checkpoints)

    result = []
    keys = set()
    for row in rows:
        key = (row["precision"], int(row["budget"]), int(row["N"]))
        if key in keys:
            issues.append(f"duplicate configuration {key}")
            continue
        keys.add(key)
        precision, budget, n = key
        if row["status"] != "ok":
            issues.append(f"{key}: status is {row['status']!r}, not 'ok'")
            continue
        api = parse_floats(row["raw_api_call_wall_s"])
        mkl = parse_floats(row["raw_mkl_gemm_s"])
        if len(api) != len(mkl) or len(api) != int(row["repetitions"]):
            issues.append(f"{key}: raw vector lengths do not match repetitions")
            continue
        if not all(math.isfinite(t) and t > 0 for t in api + mkl):
            issues.append(f"{key}: non-finite or non-positive raw time")
            continue
        mean, mkl_mean = statistics.mean(api), statistics.mean(mkl)
        speedup = mkl_mean / mean
        gflops = 2 * n ** 3 / mean / 1e9
        for observed, expected in [(float(row["api_call_wall_s_mean"]), mean),
                                   (float(row["mkl_gemm_s"]), mkl_mean),
                                   (float(row["effective_GFLOP_s"]), gflops),
                                   (float(row["api_speedup"]), speedup)]:
            if not math.isclose(observed, expected, rel_tol=2e-10):
                issues.append(f"{key}: CSV field {observed} != recomputed {expected}")
        ef, scaled = float(row["eF_mkl"]), float(row["e_scaled_mkl"])
        if not (math.isfinite(ef) and math.isfinite(scaled)):
            issues.append(f"{key}: non-finite error metrics")
        mode = f"{precision}_p{budget}"
        paper = reference["table4_accuracy"]["values_as_printed_before_scale"].get(str(n), {}).get(mode)
        entry = {"precision": precision, "budget": budget, "N": n, "repetitions": len(api),
                 "api_mean_s": mean, "api_median_s": statistics.median(api),
                 "api_sample_sd_s": statistics.stdev(api) if len(api) > 1 else None,
                 "api_min_s": min(api), "api_max_s": max(api), "mkl_mean_s": mkl_mean,
                 "effective_TFLOP_s": gflops / 1000, "api_speedup": speedup,
                 "eF_mkl": ef, "e_scaled_mkl": scaled,
                 "split_mean_s": float(row["split_s_mean"]), "pack_mean_s": float(row["pack_s_mean"]),
                 "compute_reconstruct_mean_s": float(row["compute_recon_s_mean"])}
        if precision == "fp32" and n in target:
            entry.update(paper_speedup_target=target[n],
                         paper_speedup_target_met=speedup >= target[n])
        if paper:
            scale = reference["table4_modes"][mode]
            entry.update(paper_eF=paper[0] * scale["eF_scale"],
                         eF_over_paper=ef / (paper[0] * scale["eF_scale"]))
        result.append(entry)
        print(f'{precision} p{budget} N={n}: {entry["effective_TFLOP_s"]:.4f} TF/s, '
              f'{speedup:.4f}x MKL, eF={ef:.5g}')

    speeds = [r for r in result if r["precision"] == "fp32" and r["budget"] == 6 and r["N"] in target]
    targets_met = all(r.get("paper_speedup_target_met", False) for r in speeds)
    integrity_ok = not issues and len(result) == len(expected_keys)
    full_coverage = full_scope and integrity_ok and eight_ok and len(result) == 40
    all_targets = full_coverage and len(speeds) == 8 and targets_met
    report = {"csv": str(a.csv.resolve()), "csv_sha256": hashlib.sha256(a.csv.read_bytes()).hexdigest(),
              "reference": str(reference_path), "reference_sha256": fingerprint(reference_path),
              "configurations": len(result), "expected_configurations": len(expected_keys),
              "declared_scope": {"sizes": sizes, "modes": [f"{p}_p{b}" for p, b in modes],
                                 "is_full_paper_scope": full_scope},
              "declared_configuration_coverage": integrity_ok,
              "full_40_configuration_coverage": full_coverage,
              "source_policy": source_policy, "environment_expected": required_env,
              "environment_expected_unset": absent_env,
              "eight_size_coverage_per_mode": eight_report,
              "paper_protocol_and_identity_valid": not issues,
              "protocol_or_identity_issues": issues,
              "paper_fp32_speedup_targets_all_met": all_targets,
              "fp32_speedup_targets": {
                  str(r["N"]): {"observed": r["api_speedup"], "target": r["paper_speedup_target"],
                                "met": r["paper_speedup_target_met"]}
                  for r in speeds},
              "resume_events": [{k: v for k, v in e.items() if k != "environment"}
                                for e in provenance.get("resume_events", [])] if provenance else [],
              "notes": notes, "rows": result,
              "limitations": "Table 4 values are empirical points from different undisclosed random "
                             "inputs; Figure 7 points were measured on a different platform "
                             "(8462Y+/Intel OpenMP/fixed frequency); only descriptive mean comparisons "
                             "are gated and no precision success is inferred from status=ok."}
    temporary = a.out.with_suffix(a.out.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(a.out)
    if not integrity_ok:
        return 2
    if a.require_paper_speedups and not all_targets:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
