#!/usr/bin/env python3
"""Compare 2--3 T1-validated campaigns after fresh snapshot-policy validation.

API wall means are primary; MKL ratios are auxiliary descriptions. Intervals
describe within-process timing samples, not independent host replications.
Exit 0 means analysis completed, never a causal or paper-target success claim.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/analyze_paper_alignment.py"
WAIT_KEYS = {"OMP_WAIT_POLICY", "GOMP_SPINCOUNT"}
# Two-sided 95% Student t critical values. Ten samples per arm constrain Welch
# degrees of freedom to [9, 18]. Flooring df gives a conservative critical value.
T975 = {9: 2.2621571629, 10: 2.2281388520, 11: 2.2009851601,
        12: 2.1788128297, 13: 2.1603686565, 14: 2.1447866879,
        15: 2.1314495456, 16: 2.1199052992, 17: 2.1098155778, 18: 2.1009220402}
INTERVAL_LIMITATION = (
    "Welch-Satterthwaite approximate two-sided 95% interval for the difference "
    "of API sample means (numerator minus denominator, seconds); Student t "
    "critical value uses conservatively floored degrees of freedom. Nominal "
    "coverage assumes independent, stationary, approximately normal samples. "
    "The ten sequential timings in each process may be correlated and are not "
    "ten independent host/process replications. This sample-level descriptive "
    "interval does not establish host-level uncertainty, causality, or paper success.")


def welch_interval(numerator, denominator):
    if len(numerator) != 10 or len(denominator) != 10:
        raise ValueError("Welch interval requires ten samples in each arm")
    delta = statistics.mean(numerator) - statistics.mean(denominator)
    terms = [statistics.variance(values) / len(values) for values in (numerator, denominator)]
    se2 = sum(terms)
    df = se2 ** 2 / sum(term ** 2 / 9 for term in terms) if se2 else None
    critical_df = max(9, min(18, math.floor(df + 1e-10))) if df is not None else None
    critical = T975[critical_df] if critical_df is not None else None
    margin = critical * math.sqrt(se2) if se2 else 0.0
    return {"estimate_s": delta, "lower_s": delta - margin, "upper_s": delta + margin,
            "standard_error_s": math.sqrt(se2), "welch_df": df,
            "critical_df": critical_df, "t_critical": critical}


def validate_arm(directory, label, temporary):
    claimed = json.loads((directory / "analysis.json").read_text())
    scope, env = claimed["declared_scope"], claimed["environment_expected"]
    if claimed.get("source_policy") not in ("current", "live", "snapshot"):
        raise ValueError(f"{label}: missing or invalid declared source_policy")
    absent = claimed["environment_expected_unset"]
    if not WAIT_KEYS.intersection(env) and set(absent) == WAIT_KEYS:
        wait = "runtime"
    elif env.get("OMP_WAIT_POLICY") == "PASSIVE" and env.get("GOMP_SPINCOUNT") == "0" and not absent:
        wait = "passive"
    else:
        raise ValueError(f"{label}: inconsistent declared wait policy")
    raw = (directory / "results.csv").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if claimed.get("csv_sha256") != digest:
        raise ValueError(f"{label}: analysis.json CSV SHA is stale or incorrect")
    out = temporary / f"{label}.revalidated.json"
    command = [sys.executable, "-B", str(ANALYZER), str(directory / "results.csv"),
               "--out", str(out), "--sizes", ",".join(str(n) for n in scope["sizes"]),
               "--modes", ",".join(scope["modes"]), "--expect-cache-bytes",
               str(int(env["OZAMX_WORKSPACE_CACHE_BYTES"])), "--expect-wait", wait,
               "--source-policy", "snapshot"]
    process = subprocess.run(command, capture_output=True, text=True)
    fresh = json.loads(out.read_text()) if out.is_file() else {}
    if process.returncode != 0 or not fresh.get("declared_configuration_coverage") or \
            not fresh.get("paper_protocol_and_identity_valid"):
        raise ValueError(f"{label}: fresh analyzer rejected evidence: "
                         f"{fresh.get('protocol_or_identity_issues', [])} {process.stderr[:500]}")
    if fresh["csv_sha256"] != digest or \
            hashlib.sha256((directory / "results.csv").read_bytes()).hexdigest() != digest:
        raise ValueError(f"{label}: CSV changed during validation")
    for field in ("declared_scope", "environment_expected", "environment_expected_unset", "reference_sha256"):
        if fresh[field] != claimed[field]:
            raise ValueError(f"{label}: fresh validation contradicts declared {field}")
    values = {}
    for row in csv.DictReader(io.StringIO(raw.decode())):
        key = (row["precision"], int(row["budget"]), int(row["N"]))
        values[key] = {"api": [float(t) for t in row["raw_api_call_wall_s"].split(";") if t],
                       "mkl": [float(t) for t in row["raw_mkl_gemm_s"].split(";") if t]}
    provenance = json.loads((directory / "provenance.json").read_text())
    evidence = {"label": label, "directory": str(directory), "csv_sha256": digest,
                "declared_scope": fresh["declared_scope"], "environment_expected": fresh["environment_expected"],
                "environment_expected_unset": fresh["environment_expected_unset"],
                "claimed_source_policy": claimed["source_policy"], "revalidated_source_policy": "snapshot",
                "source_sha256": provenance["source_sha256"], "artifact_sha256": provenance["artifact_sha256"],
                "full_40_configuration_coverage": fresh["full_40_configuration_coverage"]}
    return values, evidence


def compare(numerator, denominator, numerator_label, denominator_label):
    api_num, api_den = statistics.mean(numerator["api"]), statistics.mean(denominator["api"])
    mkl_num, mkl_den = statistics.mean(numerator["mkl"]), statistics.mean(denominator["mkl"])
    return {"numerator": numerator_label, "denominator": denominator_label,
            "api_wall_ratio": api_num / api_den, "mkl_wall_ratio_auxiliary": mkl_num / mkl_den,
            "mkl_normalized_speedup_ratio_auxiliary": (mkl_num / api_num) / (mkl_den / api_den),
            "api_mean_difference_sample_welch_95pct": welch_interval(numerator["api"], denominator["api"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", type=Path, required=True)
    parser.add_argument("--labels", help="comma-separated labels (default: A,B[,A_prime])")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    labels = args.labels.split(",") if args.labels is not None else ["A", "B", "A_prime"][:len(args.arms)]
    if len(args.arms) not in (2, 3) or len(labels) != len(args.arms) or \
            len(set(labels)) != len(labels) or any(not label or not all(c.isalnum() or c in "_-" for c in label)
                                                      for label in labels):
        parser.error("supply two or three arms and equally many distinct alphanumeric/_/- labels")
    arms = [p.resolve() for p in args.arms]
    if len(set(arms)) != len(arms):
        parser.error("arm directories must be distinct")
    if any(args.out.resolve().is_relative_to(arm) for arm in arms):
        parser.error("--out must be outside the input arm directories")
    try:
        with tempfile.TemporaryDirectory(prefix="ozamx-compare-") as tmp:
            validated = [validate_arm(p, label, Path(tmp)) for p, label in zip(arms, labels)]
        scope = validated[0][1]["declared_scope"]
        if any(evidence["declared_scope"] != scope for _, evidence in validated):
            raise ValueError("arm configuration scopes differ; sizes, precisions and budgets must match exactly")
        keys = set(validated[0][0])
        if any(set(values) != keys for values, _ in validated):
            raise ValueError("arm configuration keys differ")
        pairs = [(1, 0, "B_over_A")]
        if len(arms) == 3:
            pairs += [(1, 2, "B_over_A_prime"), (2, 0, "A_prime_over_A_drift")]
        rows = []
        for key in sorted(keys):
            arm_stats = {}
            for (values, _), label in zip(validated, labels):
                api, mkl = values[key]["api"], values[key]["mkl"]
                arm_stats[label] = {"samples": len(api), "api_mean_s": statistics.mean(api),
                                    "api_sample_sd_s": statistics.stdev(api), "mkl_mean_s": statistics.mean(mkl),
                                    "mkl_sample_sd_s": statistics.stdev(mkl),
                                    "api_speedup": statistics.mean(mkl) / statistics.mean(api)}
            rows.append({"precision": key[0], "budget": key[1], "N": key[2], "arms": arm_stats,
                         "comparisons": {name: compare(validated[n][0][key], validated[d][0][key], labels[n], labels[d])
                                         for n, d, name in pairs}})
        report = {"status": "analysis_completed", "analyzer_sha256": hashlib.sha256(ANALYZER.read_bytes()).hexdigest(),
                  "declared_scope": scope, "arms": [evidence for _, evidence in validated], "rows": rows,
                  "ratio_convention": "API/MKL wall ratios below 1 mean less wall time in the numerator; "
                                      "the auxiliary normalized speedup ratio above 1 means higher MKL/API speedup.",
                  "interval_method_and_limits": INTERVAL_LIMITATION,
                  "causal_or_paper_target_success_inferred": False}
        code = 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        report, code = {"status": "invalid", "error": str(error)}, 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    temporary.replace(args.out)
    print(json.dumps({"status": report["status"], "out": str(args.out), "error": report.get("error")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
