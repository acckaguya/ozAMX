#!/usr/bin/env python3
"""Normalize malformed V4 diagnostic CSV endings and analyze existing records only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3"
NORMALIZED = BATCH / "normalized_csv"
REPORT = ROOT / "docs/8454H_V4_DIAGNOSTIC_RESULTS.md"
LABELS = (
    "frozen_v3_initial",
    "mode0_control",
    "mode1_diagnostic_plain_nf",
    "mode2_diagnostic_no_reconstruction",
    "mode3_candidate_late32_unvalidated",
    "frozen_v3_final",
)
SIZES = (1024, 4096, 8192)
BUDGETS = (6, 10, 15, 21)
MODES = (("fp32", 6), ("fp64", 6), ("fp64", 10), ("fp64", 15), ("fp64", 21))
MODE_SOURCE_ID = {
    "frozen_v3_initial": "mkl-wall-roofline-v4-mode0-control",
    "mode0_control": "mkl-wall-roofline-v4-mode0-control",
    "mode1_diagnostic_plain_nf": "mkl-wall-roofline-v4-mode1-diagnostic-plain-nf",
    "mode2_diagnostic_no_reconstruction": "mkl-wall-roofline-v4-mode2-diagnostic-no-reconstruction",
    "mode3_candidate_late32_unvalidated": "mkl-wall-roofline-v4-mode3-candidate-late32-unvalidated",
    "frozen_v3_final": "mkl-wall-roofline-v4-mode0-control",
}
CSV_TO_CHECKPOINT = {
    "raw_split_s": "split_seconds",
    "raw_pack_s": "pack_seconds",
    "raw_compute_recon_s": "compute_reconstruction_seconds",
    "raw_profile_total_s": "total_seconds",
    "raw_api_call_wall_s": "call_wall_seconds",
}
MEAN_FIELDS = {
    "split_s_mean": "split_seconds",
    "pack_s_mean": "pack_seconds",
    "compute_recon_s_mean": "compute_reconstruction_seconds",
    "profile_total_s_mean": "total_seconds",
    "api_call_wall_s_mean": "call_wall_seconds",
}
V3_SHA = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def near(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=2e-7, abs_tol=5e-10)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, strict=True)
        if reader.fieldnames is None:
            raise ValueError(f"missing header: {path}")
        rows = list(reader)
    return reader.fieldnames, rows


def parse_vector(row: dict[str, str], key: str) -> list[float]:
    raw = row.get(key, "")
    if not raw:
        raise ValueError(f"empty sample vector {key}")
    values = [float(x) for x in raw.split(";")]
    if len(values) != 5 or any(not math.isfinite(x) for x in values):
        raise ValueError(f"{key} must contain five finite values")
    return values


def cp_path(label: str, precision: str, n: int, budget: int) -> Path:
    return BATCH / f"checkpoint_{label}.{precision}.{n}.{budget}.json"


def repair_one(source: Path, destination: Path) -> dict:
    original = source.read_bytes()
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite normalized file: {destination}")
    lines = original.splitlines(keepends=True)
    if len(lines) != 16:
        raise ValueError(
            f"{source.name}: expected 1 header + 15 physical data lines, found {len(lines)}"
        )
    fixed = [lines[0]]
    appended = []
    for index, raw in enumerate(lines[1:], start=2):
        body = raw.rstrip(b"\r\n")
        eol = raw[len(body) :]
        if body.endswith(b'"'):
            fixed.append(raw)
            continue
        if body.count(b'"') % 2 != 1:
            raise ValueError(
                f"{source.name}:{index}: missing final quote is not the sole detectable defect"
            )
        candidate = body + b'"' + eol
        # Validate this repaired physical record in isolation before accepting the change.
        parsed = list(csv.reader([candidate.decode("utf-8")], strict=True))
        if len(parsed) != 1:
            raise ValueError(f"{source.name}:{index}: repaired physical line is not one CSV row")
        fixed.append(candidate)
        appended.append(index)
    if len(appended) != 15:
        raise ValueError(
            f"{source.name}: expected to append exactly one terminal quote to each of 15 data rows; did {len(appended)}"
        )
    normalized = b"".join(fixed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(normalized)
    headers, rows = read_rows(destination)
    with destination.open(newline="", encoding="utf-8") as f:
        parsed_rows = list(csv.reader(f, strict=True))
    if len(headers) != 36 or len(rows) != 15 or any(len(r) != len(headers) for r in parsed_rows):
        raise ValueError(f"{source.name}: normalized strict CSV dimensions invalid")
    return {
        "original_path": str(source.relative_to(ROOT)),
        "normalized_path": str(destination.relative_to(ROOT)),
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "normalized_sha256": digest(destination),
        "physical_lines": 16,
        "data_rows": 15,
        "header_columns": 36,
        "strict_csv": True,
        "repaired_data_lines_1_based": appended,
        "repair": "Appended exactly one missing closing double quote at the end of each affected physical data line; no field content, delimiters, samples, means, source CSV, or checkpoints were otherwise changed.",
    }


def validate_label(label: str, csv_path: Path) -> tuple[list[dict], dict]:
    headers, rows = read_rows(csv_path)
    if len(headers) != 36 or len(rows) != 15:
        raise ValueError(f"{label}: expected 36 columns and 15 records")
    expected_keys = {(p, n, b) for n in SIZES for p, b in MODES}
    got_keys = set()
    output = []
    checks = []
    for row in rows:
        precision = row["precision"]
        n = int(row["N"])
        budget = int(row["budget"])
        threads = int(row["threads"])
        seed = int(row["seed"])
        key = (precision, n, budget)
        if key not in expected_keys or key in got_keys:
            raise ValueError(f"{label}: unexpected/duplicate configuration {key}")
        got_keys.add(key)
        if (
            n not in SIZES
            or threads != 64
            or seed != 260904 + n
            or row["distribution"] != "uniform"
            or int(row["repetitions"]) != 5
        ):
            raise ValueError(f"{label}: incorrect protocol fields for {key}")
        checkpoint = cp_path(label, precision, n, budget)
        cp = json.loads(checkpoint.read_text())
        cp_expected = {
            "source_id": MODE_SOURCE_ID[label],
            "precision": precision,
            "distribution": "uniform",
            "budget": budget,
            "N": n,
            "threads": 64,
            "seed": seed,
            "requested_repetitions": 5,
            "completed_timed_repetitions": 5,
            "complete": True,
        }
        for field, value in cp_expected.items():
            if cp.get(field) != value:
                raise ValueError(
                    f"{label} {key}: checkpoint {field}={cp.get(field)!r}, expected {value!r}"
                )
        config_checks = []
        for csv_vec, cp_vec in CSV_TO_CHECKPOINT.items():
            observed = parse_vector(row, csv_vec)
            reference = cp.get(cp_vec)
            if not isinstance(reference, list) or len(reference) != 5:
                raise ValueError(
                    f"{label} {key}: checkpoint {cp_vec} does not contain five samples"
                )
            if any(not near(x, float(y)) for x, y in zip(observed, reference)):
                raise ValueError(f"{label} {key}: CSV {csv_vec} differs from checkpoint {cp_vec}")
            config_checks.append(
                {"csv_vector": csv_vec, "checkpoint_vector": cp_vec, "entries": 5, "matches": True}
            )
        sample_means = {}
        for csv_mean, cp_vec in MEAN_FIELDS.items():
            values = cp[cp_vec]
            mean = statistics.fmean(float(x) for x in values)
            recorded = float(row[csv_mean])
            if not near(mean, recorded):
                raise ValueError(
                    f"{label} {key}: {csv_mean} {recorded} differs from five-sample checkpoint mean {mean}"
                )
            sample_means[csv_mean] = mean
        status = row["status"]
        if (
            label
            in (
                "frozen_v3_initial",
                "mode0_control",
                "frozen_v3_final",
                "mode3_candidate_late32_unvalidated",
            )
            and status != "ok"
        ):
            raise ValueError(f"{label} {key}: unexpected status {status!r}")
        if (
            label == "mode1_diagnostic_plain_nf"
            and status != "diagnostic_only_accuracy_unvalidated"
        ):
            raise ValueError(f"mode1 {key}: unexpected status {status!r}")
        if (
            label == "mode2_diagnostic_no_reconstruction"
            and status != "diagnostic_no_reconstruction_non_numeric"
        ):
            raise ValueError(f"mode2 {key}: unexpected status {status!r}")
        result = {
            "label": label,
            "diagnostic_mode": row["diagnostic_mode"],
            "precision": precision,
            "budget": budget,
            "N": n,
            "threads": threads,
            "seed": seed,
            "repetitions": 5,
            "status": status,
            "accuracy_scope": row["accuracy_scope"],
            "hp_scope": row["hp_scope"],
            "mkl_gemm_s_mean": float(row["mkl_gemm_s"]),
            "eF_mkl": numeric_or_none(row["eF_mkl"]),
            "e_scaled_mkl": numeric_or_none(row["e_scaled_mkl"]),
            "phase_means_seconds": {
                "split": sample_means["split_s_mean"],
                "pack": sample_means["pack_s_mean"],
                "compute_reconstruct": sample_means["compute_recon_s_mean"],
                "profile_total": sample_means["profile_total_s_mean"],
                "api_call_wall": sample_means["api_call_wall_s_mean"],
            },
            "api_call_wall_all_five_samples_seconds": cp["call_wall_seconds"],
            "phase_compute_all_five_samples_seconds": cp["compute_reconstruction_seconds"],
            "product_equivalent_TFLOP_s": (
                2.0 * budget * n**3 / sample_means["compute_recon_s_mean"] / 1e12
                if label == "mode2_diagnostic_no_reconstruction"
                else None
            ),
            "checkpoint_path": str(checkpoint.relative_to(ROOT)),
            "checkpoint_vector_matches": config_checks,
        }
        output.append(result)
        checks.append(
            {
                "precision": precision,
                "budget": budget,
                "N": n,
                "checkpoint": str(checkpoint.relative_to(ROOT)),
                "mean_checks": "5/5 pass",
                "sample_vectors": "5 vectors × 5 entries match",
            }
        )
    if got_keys != expected_keys:
        raise ValueError(f"{label}: missing configurations {sorted(expected_keys-got_keys)}")
    return output, {
        "configurations": len(rows),
        "all_repetitions": 5,
        "checkpoint_validations": checks,
    }


def numeric_or_none(value: str) -> float | None:
    if value in ("NA", "", "nan", "NaN"):
        return None
    x = float(value)
    return x if math.isfinite(x) else None


def analyze_binary_gates() -> dict:
    out = {}
    for mode in (0, 3):
        p = BATCH / f"binary_gate_mode{mode}.json"
        gate = json.loads(p.read_text())
        cases = gate.get("cases", [])
        out[str(mode)] = {
            "status": gate.get("status"),
            "case_count": len(cases),
            "passed_cases": sum(c.get("pass") is True for c in cases),
            "all_pass": bool(cases) and all(c.get("pass") is True for c in cases),
            "candidate_library_sha256": gate.get("candidate_library_sha256"),
            "frozen_library_sha256": gate.get("frozen_library_sha256"),
            "json_path": str(p.relative_to(ROOT)),
        }
        if (
            gate.get("status") != "pass"
            or len(cases) != 18
            or not all(c.get("pass") is True for c in cases)
        ):
            raise ValueError(f"mode {mode} binary gate does not show all 18 cases passing")
        if gate.get("frozen_library_sha256") != V3_SHA:
            raise ValueError(f"mode {mode} gate does not reference the frozen V3 library")
        log = BATCH / f"ctest_mode{mode}.log"
        txt = log.read_text()
        ctest_ok = "100% tests passed, 0 tests failed out of 3" in txt
        out[str(mode)]["ctest_3_of_3_passed"] = ctest_ok
        out[str(mode)]["ctest_log"] = str(log.relative_to(ROOT))
        if not ctest_ok:
            raise ValueError(f"mode {mode} CTest log does not show 3/3 pass")
    return out


def build_report(analysis: dict) -> str:
    results = analysis["records"]
    by_key = {(r["label"], r["precision"], r["budget"], r["N"]): r for r in results}
    compare_modes = LABELS[1:-1]
    lines = [
        "# 8454H V4 diagnostic campaign results",
        "",
        "This is an offline analysis of the six-label, 90-configuration diagnostic run `20261014T091717Z-3`. It does not promote any diagnostic mode to a production GEMM. The malformed original CSV files remain unchanged. Their only parse repair is represented by six normalized copies, each with one missing terminal CSV quote appended to each of its 15 physical data lines.",
        "",
        "## Protocol and record integrity",
        "",
        "Each label covers N=1024/4096/8192 and FP32 p6 plus FP64 p6/p10/p15/p21. Each configuration has one warmup and five timed repetitions. The analysis retains every timed value, removes no outliers, and verifies each of the five CSV timing vectors against the corresponding checkpoint vector; each checkpoint reports `complete=true`, five requested and five completed repetitions. Strict parsing after normalization confirms 36 header columns and 15 records per CSV.",
        "",
        "The only CSV correction is a final closing double quote where the driver omitted it. Original files, checkpoints, and source files were read only. Original and normalized SHA-256 values for all six pairs are in `bench/8454h/roofline_v4/diagnostic_src/results/20261014T091717Z-3/analysis.json`.",
        "",
        "The initial and final controls both reference frozen V3 static library SHA-256 `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`. Mode 0 passed an 18-case full-output binary gate and 3/3 CTests; mode 3 also passed its 18-case gate and 3/3 CTests. Those tests establish the recorded gate behavior for their test cases, while the mode3 timing CSV still labels its numeric gate pending. Mode 1 is explicitly a plain finite-input diagnostic without the final non-finite guard, so its reported accuracy fields are not an accuracy pass. Mode 2 omits reconstruction and is non-numeric; its NA fields are preserved as such.",
        "",
        "## Full API wall and compute-phase comparisons",
        "",
        "The tables below summarize descriptive medians over the 15 configuration means in each label. Ratios are V3 baseline time divided by the mode time; values above one indicate a lower recorded time for that diagnostic mode. `compute` is the driver's combined compute/reconstruction phase. API wall encloses the complete call. The five individual repetitions remain in the analysis JSON and normalized CSVs; these medians do not delete or replace them.",
        "",
        "| Diagnostic label | Compute speed ratio vs initial V3 | API-wall speed ratio vs initial V3 | Compute speed ratio vs final V3 | API-wall speed ratio vs final V3 |",
        "|---|---:|---:|---:|---:|",
    ]
    initial_label, final_label = LABELS[0], LABELS[-1]
    for label in compare_modes:
        compute_i, api_i, compute_f, api_f = [], [], [], []
        for precision, budget in MODES:
            for n in SIZES:
                cand = by_key[(label, precision, budget, n)]
                ini = by_key[(initial_label, precision, budget, n)]
                fin = by_key[(final_label, precision, budget, n)]
                compute_i.append(
                    ini["phase_means_seconds"]["compute_reconstruct"]
                    / cand["phase_means_seconds"]["compute_reconstruct"]
                )
                api_i.append(
                    ini["phase_means_seconds"]["api_call_wall"]
                    / cand["phase_means_seconds"]["api_call_wall"]
                )
                compute_f.append(
                    fin["phase_means_seconds"]["compute_reconstruct"]
                    / cand["phase_means_seconds"]["compute_reconstruct"]
                )
                api_f.append(
                    fin["phase_means_seconds"]["api_call_wall"]
                    / cand["phase_means_seconds"]["api_call_wall"]
                )
        fmt = lambda xs: f"{statistics.median(xs):.3f}×"
        lines.append(
            f"| `{label}` | {fmt(compute_i)} | {fmt(api_i)} | {fmt(compute_f)} | {fmt(api_f)} |"
        )
    lines += [
        "",
        "These aggregates mix five matrix/product shapes and should be read alongside the per-configuration records in `analysis.json`; do not treat a cross-case median as a single workload result. OneMKL `mkl_gemm_s` is retained separately in every normalized row and has not been folded into the diagnostic timings.",
        "",
        "## Mode 2: no-reconstruction product-equivalent rate",
        "",
        "Mode 2 executes the AMX component-product path but omits product accumulation/reconstruction, leaving a non-numeric result. The following `2 × products × N³ / compute_phase_time` rate is an operation-equivalent diagnostic for the component products, not a valid GEMM throughput or end-to-end performance result. Its phases still include the V4 call's tile, scheduling, scratch, result-copy and related overheads; they are not an ideal hot-register benchmark.",
        "",
        "| N | FP32 p6 | FP64 p6 | FP64 p10 | FP64 p15 | FP64 p21 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for n in SIZES:
        cells = []
        for precision, budget in MODES:
            r = by_key[("mode2_diagnostic_no_reconstruction", precision, budget, n)]
            cells.append(f"{r['product_equivalent_TFLOP_s']:.2f} TFLOP/s")
        lines.append(f"| {n} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "For scope only, the earlier 64-thread register-resident AMX microbenchmark reported 161.034 ± 0.236 TFLOP/s with input tiles already in tile registers. The mode-2 rates include the actual benchmark's panel/compute path and other in-phase overheads; the comparison is not an attainable bound test and does not identify cache level or external-memory traffic. The current campaign collected no PMU cache/DRAM traffic counters, so these data do not establish a physical DRAM roofline.",
        "",
        "## Diagnostic interpretation and limits",
        "",
        "- Mode 0 is an isolated V3-equivalent control and its full-buffer comparison passed for 18 cases. Initial/final controls bracket the four mode measurements and both use the same frozen V3 library SHA.",
        "- Mode 1 omits eager FP32 non-finite checks on accumulated intermediate results. Treat timing as a finite-input diagnostic only; its accuracy scope explicitly says unvalidated.",
        "- Mode 2 intentionally returns no numeric GEMM result. Only its component-product-equivalent timing is useful, with the scope limits above.",
        "- Mode 3 selects the late FP32 check for K≥4096 while retaining eager handling below that. Its 18-case full-buffer gate and three CTests passed, but the performance-run rows keep `numeric_gate_pending`; this remains a candidate diagnostic, not a release claim.",
        "- The local machine/compiler/runtime and frequency conditions are those recorded in the result batch and V4 source preparation. The run uses five samples per configuration, all retained; the table uses arithmetic means per configuration then a median across 15 configurations. It is not a statistical confidence interval.",
        "- OneMKL timing is a GEMM-only baseline retained as a separate column. Modes 1–3 alter safety or numeric work, so their MKL ratios do not represent equivalent numerical GEMM performance.",
        "",
        "Exact raw configuration values, vectors, checkpoints, original/normalized hashes, test gate summaries, and validation details are in the batch `analysis.json`. The normalized CSVs are under `normalized_csv/`; the six original CSVs are unchanged.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    global BATCH, NORMALIZED, REPORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, default=BATCH)
    args = parser.parse_args()
    BATCH = args.batch.resolve()
    NORMALIZED = BATCH / "normalized_csv"
    if NORMALIZED.exists():
        raise FileExistsError(f"refusing to overwrite normalized directory: {NORMALIZED}")
    if (BATCH / "analysis.json").exists() or REPORT.exists():
        raise FileExistsError("refusing to overwrite existing analysis or report")
    normalized_tmp = BATCH / ".normalized_csv.stage"
    if normalized_tmp.exists():
        raise FileExistsError(f"temporary normalized directory already exists: {normalized_tmp}")
    normalized_tmp.mkdir()
    file_checks = []
    all_records = []
    label_summaries = {}
    try:
        for label in LABELS:
            source = BATCH / f"{label}.csv"
            destination = normalized_tmp / source.name
            repair = repair_one(source, destination)
            # The file is built in a staging directory and published by rename;
            # record the stable published path in the analysis manifest.
            repair["normalized_path"] = str((NORMALIZED / source.name).relative_to(ROOT))
            records, summary = validate_label(label, destination)
            repair.update(summary)
            sidecar = BATCH / f"{label}.sha256"
            original_sidecar = sidecar.read_text().splitlines()[0].split()[0]
            if original_sidecar != repair["original_sha256"]:
                raise ValueError(f"{label}: original CSV SHA differs from retained .sha256 record")
            repair["original_sidecar_sha256_matches"] = True
            file_checks.append(repair)
            label_summaries[label] = summary
            all_records.extend(records)
        gate_summary = analyze_binary_gates()
        if len(all_records) != 90:
            raise ValueError(f"expected 90 normalized configurations, got {len(all_records)}")
        # Controls' before/after CSV checksums and sidecars must agree with the V3 library identity.
        bracket_integrity = {}
        for label in ("frozen_v3_initial", "frozen_v3_final"):
            lines = (BATCH / f"{label}.sha256").read_text().splitlines()
            lib_hash = lines[2].split()[0]
            if lib_hash != V3_SHA:
                raise ValueError(f"{label}: V3 static library SHA mismatch")
            bracket_integrity[label] = {
                "library_sha256": lib_hash,
                "matches_frozen_v3": True,
                "csv_sha256": file_checks[LABELS.index(label)]["original_sha256"],
            }

        # Add mode ratios for every N/precision/budget; preserve all original oneMKL means.
        by_key = {(r["label"], r["precision"], r["budget"], r["N"]): r for r in all_records}
        comparisons = []
        for precision, budget in MODES:
            for n in SIZES:
                initial = by_key[("frozen_v3_initial", precision, budget, n)]
                final = by_key[("frozen_v3_final", precision, budget, n)]
                for label in LABELS[1:-1]:
                    r = by_key[(label, precision, budget, n)]
                    r["comparison_vs_brackets"] = {
                        "compute_time_ratio_initial_over_mode": initial["phase_means_seconds"][
                            "compute_reconstruct"
                        ]
                        / r["phase_means_seconds"]["compute_reconstruct"],
                        "api_wall_ratio_initial_over_mode": initial["phase_means_seconds"][
                            "api_call_wall"
                        ]
                        / r["phase_means_seconds"]["api_call_wall"],
                        "compute_time_ratio_final_over_mode": final["phase_means_seconds"][
                            "compute_reconstruct"
                        ]
                        / r["phase_means_seconds"]["compute_reconstruct"],
                        "api_wall_ratio_final_over_mode": final["phase_means_seconds"][
                            "api_call_wall"
                        ]
                        / r["phase_means_seconds"]["api_call_wall"],
                        "mkl_gemm_s_mean_preserved": r["mkl_gemm_s_mean"],
                    }
                    comparisons.append(
                        {
                            "label": label,
                            "precision": precision,
                            "budget": budget,
                            "N": n,
                            **r["comparison_vs_brackets"],
                        }
                    )
        report = {
            "schema": "ozamx_v4_offline_diagnostic_analysis_v1",
            "batch_id": BATCH.name,
            "diagnostic_only": True,
            "production_release_claim": False,
            "configurations": 90,
            "expected_configurations": {
                "labels": 6,
                "per_label": 15,
                "sizes": list(SIZES),
                "timed_repetitions": 5,
            },
            "columns": 36,
            "physical_lines_per_original_csv": 16,
            "normalization": {
                "output_dir": str(NORMALIZED.relative_to(ROOT)),
                "all_six_csvs_strictly_valid": True,
                "repair_rule": "append one closing double quote to a physical data line only when terminal quote is missing and its quote count is odd; no other modification",
                "original_csv_files_modified": False,
                "per_file": file_checks,
            },
            "repetition_policy": "All five timed values retained per configuration; no outliers removed.",
            "checkpoint_validation": label_summaries,
            "v3_bracket_integrity": bracket_integrity,
            "binary_gates": gate_summary,
            "records": all_records,
            "comparisons": comparisons,
            "limitations": [
                "Diagnostic modes are not production-release GEMM claims.",
                "Mode 1 omits eager FP32 non-finite checks; its accuracy scope is unvalidated.",
                "Mode 2 omits accumulation/reconstruction and produces no numeric result; its product-equivalent rate is not GEMM throughput.",
                "Mode 3's binary gate and CTests passed, but its campaign rows keep numeric_gate_pending.",
                "OneMKL values are GEMM-only and remain distinct from full API wall time.",
                "No cache/DRAM PMU traffic was measured; do not interpret these records as physical DRAM roofline points.",
            ],
        }
        # A rename publishes the normalized set as one complete unit; refuse if target appeared meanwhile.
        if NORMALIZED.exists():
            raise FileExistsError(f"refusing to overwrite normalized directory: {NORMALIZED}")
        normalized_tmp.rename(NORMALIZED)
        report["normalization"]["output_dir"] = str(NORMALIZED.relative_to(ROOT))
        analysis_path = BATCH / "analysis.json"
        analysis_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        REPORT.write_text(build_report(report))
        print(
            json.dumps(
                {
                    "configurations": 90,
                    "labels": len(file_checks),
                    "columns": 36,
                    "rows_per_label": 15,
                    "five_reps_checkpoint_validated": True,
                    "normalized_dir": str(NORMALIZED),
                    "analysis": str(analysis_path),
                    "report": str(REPORT),
                },
                indent=2,
            )
        )
    except Exception:
        if normalized_tmp.exists():
            import shutil

            shutil.rmtree(normalized_tmp)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
