#!/usr/bin/env python3
"""Summarize the frozen roofline-kernel calibration CSV without running it."""
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CAL = ROOT / "bench/8454h/roofline/calibration"
CSV = CAL / "kernels.csv"
META = CAL / "kernel_metadata.json"
DISASM = CAL / "kernel_disassembly.txt"
OUT = CAL / "kernel_summary.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def num(row, name):
    return float(row[name])


def stats(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return {"n": 0, "median": None, "mean": None, "sample_sd": None, "raw": values}
    return {
        "n": len(valid),
        "median": statistics.median(valid),
        "mean": statistics.mean(valid),
        "sample_sd": statistics.stdev(valid) if len(valid) > 1 else 0.0,
        "raw": values,
    }


def total_flops(row):
    amx = num(row, "amx_or_add_ops")
    kernel = row["kernel"]
    units = int(row["units"])
    if kernel in ("p6_with_reconstruct", "p21_with_reconstruct"):
        depth = 6 if kernel.startswith("p6") else 21
        return amx + units * depth * 1024
    if kernel == "fp32_six_with_reconstruct":
        return amx + units * 1024
    return amx


def main():
    rows = list(csv.DictReader(CSV.open(newline="", encoding="utf-8")))
    metadata = json.loads(META.read_text(encoding="utf-8"))
    groups = defaultdict(list)
    warmups = 0
    for row in rows:
        if row["record"] == "warmup":
            warmups += 1
            continue
        groups[(row["kernel"], int(row["threads"]), int(row["worker_input_bytes"]), int(row["stride_elements"]))].append(row)

    configurations = []
    for key in sorted(groups):
        kernel, threads, input_bytes, stride = key
        samples = groups[key]
        fields = {
            "elapsed_s": [num(r, "elapsed_s") for r in samples],
            "amx_or_add_ops_per_s": [num(r, "ops_per_s") for r in samples],
            "logical_B_per_s": [num(r, "logical_B_per_s") for r in samples],
            "units_per_s": [int(r["units"]) / num(r, "elapsed_s") for r in samples],
            "total_ops_per_s": [total_flops(r) / num(r, "elapsed_s") for r in samples],
            "logical_arithmetic_intensity_ops_per_byte": [
                total_flops(r) / num(r, "logical_bytes") if num(r, "logical_bytes") else None
                for r in samples
            ],
        }
        metrics = {name: stats(values) for name, values in fields.items()}

        configurations.append({
            "kernel": kernel,
            "threads": threads,
            "worker_input_bytes": input_bytes,
            "total_input_bytes": input_bytes * threads,
            "stride_elements": stride,
            "timed_samples": len(samples),
            "validation": sorted(set(r["validation"] for r in samples)),
            "raw_samples": [
                {"rep": int(r["rep"]), "elapsed_s": num(r, "elapsed_s"),
                 "units": int(r["units"]), "reported_ops": num(r, "amx_or_add_ops"),
                 "derived_total_ops": total_flops(r), "logical_bytes": num(r, "logical_bytes"),
                 "reported_ops_per_s": num(r, "ops_per_s"), "logical_B_per_s": num(r, "logical_B_per_s"),
                 "checksum": num(r, "checksum"), "validation": r["validation"]}
                for r in samples
            ],
            "metrics": metrics,
        })

    hash_audit = {}
    for rel, expected in metadata["source_hashes"].items():
        path = ROOT / rel
        actual = sha(path) if path.exists() else None
        hash_audit[rel] = {"expected": expected, "actual": actual, "match": actual == expected}
    actual_csv_sha = sha(CSV)
    actual_lib_sha = sha(Path("/tmp/ozamx-production-final/libozamx.a")) if Path("/tmp/ozamx-production-final/libozamx.a").exists() else None
    actual_disasm_sha = sha(DISASM)
    binary_path = Path("/tmp/ozamx-roof-kernels/roofline_kernels")
    actual_binary_sha = sha(binary_path) if binary_path.exists() else None
    old_mem_path = ROOT / "bench/8454h/platform_baseline.csv"
    old_mem_rows = list(csv.DictReader(old_mem_path.open(newline="", encoding="utf-8")))
    old_mem_groups = defaultdict(list)
    for row in old_mem_rows:
        if row["benchmark"] == "memory_triad":
            old_mem_groups[int(row["threads"])].append(float(row["rate_per_s"]))
    new_mem_path = ROOT / "bench/8454h/roofline/memory_calibration_20261013.csv"
    new_mem_rows = list(csv.DictReader(new_mem_path.open(newline="", encoding="utf-8"))) if new_mem_path.exists() else []
    new_mem_groups = defaultdict(list)
    for row in new_mem_rows:
        if row["level"] == "DRAM_footprint" and row["record_type"] == "timed":
            new_mem_groups[int(row["threads"])].append(float(row["logical_B_per_s"]))
    counts = {"raw_rows": len(rows), "warmup_rows": warmups,
              "timed_rows": sum(len(v) for v in groups.values()), "configurations": len(groups),
              "timed_reps_per_configuration": sorted(set(len(v) for v in groups.values()))}
    payload = {
        "schema": "ozamx-roofline-kernel-summary-v1",
        "source_artifacts": {
            "raw_csv": str(CSV.relative_to(ROOT)), "raw_csv_sha256": actual_csv_sha,
            "raw_csv_matches_metadata": actual_csv_sha == metadata["raw_csv_sha256"],
            "input_metadata": str(META.relative_to(ROOT)), "input_metadata_sha256": sha(META),
            "disassembly": str(DISASM.relative_to(ROOT)), "disassembly_sha256": actual_disasm_sha,
            "source_hash_audit": hash_audit,
            "linked_library_expected_sha256": metadata["linked_frozen_library_sha256"],
            "linked_library_actual_sha256": actual_lib_sha,
            "linked_library_hash_matches": actual_lib_sha == metadata["linked_frozen_library_sha256"],
            "benchmark_binary_expected_sha256": metadata["binary_sha256"],
            "benchmark_binary_path": str(binary_path),
            "benchmark_binary_actual_sha256": actual_binary_sha,
            "benchmark_binary_hash_matches": actual_binary_sha == metadata["binary_sha256"],
            "saved_disassembly_expected_hash_not_in_input_metadata": True,
        },
        "contextual_memory_references": {
            "legacy_platform_triad": {
                "path": str(old_mem_path.relative_to(ROOT)),
                "sha256": sha(old_mem_path),
                "definition": "three 256 MiB float arrays (768 MiB aggregate footprint), static OpenMP initialization and 50 ms minimum pass batches; logical bytes include 2 reads + 1 write",
                "logical_GB_per_s_by_threads": {str(t): stats(v) for t, v in sorted(old_mem_groups.items())},
            },
            "new_memory_calibration_dram_footprint": {
                "path": str(new_mem_path.relative_to(ROOT)) if new_mem_path.exists() else None,
                "sha256": sha(new_mem_path) if new_mem_path.exists() else None,
                "definition": "three independent 8 MiB double arrays per worker (24 MiB/worker; 1.5 GiB total at 64), per-worker static first-touch, fixed calibrated passes >=0.1 s",
                "logical_GB_per_s_by_threads": {str(t): stats(v) for t, v in sorted(new_mem_groups.items())},
                "comparison_warning": "This is a distinct probe with different type, working-set partitioning, runtime/timer protocol and first-touch placement. Its rate must not replace the legacy 768 MiB platform triad baseline without an explicit reconciliation.",
            },
        },
        "counts": counts,
        "interpretation": {
            "sd": "sample standard deviation (n-1), over the three timed reps; warmup excluded",
            "timer_scope": metadata["time_scope"],
            "worker_input_footprint_scope": metadata["working_set_scope"],
            "logical_payload_scope": metadata["logical_payload"],
            "physical_traffic_warning": "logical_bytes / logical_B_per_s are instruction-payload accounting; no PMU cache misses or physical DRAM traffic were measured",
            "no_reconstruct_warning": metadata["diagnostic_no_reconstruct"],
            "amx_permission": metadata["amx_guard"],
            "reconstruction_ops": "For mixed P6/P21, derived total_ops adds 1024 FP64 additions per component-product output; CSV's reported amx_or_add_ops_per_s counts AMX work only. FP32 six-mix adds 1024 reconstruction additions once per six-product unit.",
            "local_stack": "Local reserves 4 KiB micro + 36 KiB FP64 block + 18 KiB FP32 block = 58 KiB per worker (plus ABI/compiler stack state). Active FP64 reconstruction touches 4 KiB micro and 8 KiB C; active FP32 reconstruction touches 4 KiB micro and 4 KiB C. The 196608-byte P6/P21 worker_input_bytes excludes these local arrays.",
        },
        "configurations": configurations,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {counts}")
    print(f"raw_csv_hash_match={payload['source_artifacts']['raw_csv_matches_metadata']} linked_library_hash_match={payload['source_artifacts']['linked_library_hash_matches']} source_hash_mismatches={sum(not x['match'] for x in hash_audit.values())}")


if __name__ == "__main__":
    main()
