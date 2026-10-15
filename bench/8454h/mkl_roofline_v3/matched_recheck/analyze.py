#!/usr/bin/env python3
"""Validate and summarize the immutable matched V2/V3 recheck outputs."""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ["p1_v2a", "p2_v3a", "p3_v2b", "p4_v3b", "p5_v2c"]
EXPECTED = {
    "V2": "ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251",
    "V3": "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c",
}

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def arr(text):
    values = [float(x) for x in text.split(";")]
    if len(values) != 7 or not all(math.isfinite(x) and x > 0 for x in values):
        raise ValueError(f"expected seven positive finite samples, got {text!r}")
    return values

def stats(xs):
    return {"samples": xs, "median": statistics.median(xs), "mean": statistics.mean(xs),
            "sd_population": statistics.pstdev(xs)}

def key(row):
    return f"{row['precision']}_p{row['budget']}_N{row['N']}"

runs = {}
reference_keys = None
for name in RUNS:
    d = ROOT / name
    prov = json.loads((d / "provenance.json").read_text())
    variant = prov["library_variant"]
    expected_id = f"mkl-wall-matched-recheck-{name.replace('_','-')}-20261013"
    assert prov["status"] == "complete" and prov["process_name"] == name
    assert prov["source_id"] == expected_id
    assert prov["library_sha256"] == prov["expected_library_sha256"] == EXPECTED[variant]
    csv_path = d / "full.csv"
    assert sha(csv_path) == prov["outputs"]["csv_sha256"]
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 15 == prov["outputs"]["configuration_count"]
    assert prov["outputs"]["checkpoint_count"] == 15
    ids = {key(r) for r in rows}
    assert len(ids) == 15
    if reference_keys is None:
        reference_keys = ids
    assert ids == reference_keys
    for r in rows:
        k = key(r); assert r["status"] == "ok" and int(r["repetitions"]) == 7
        ckpt_name = f"{prov['outputs']['checkpoint_prefix']}.{r['precision']}.{r['N']}.{r['budget']}.json"
        cp = d / ckpt_name
        assert cp.exists() and sha(cp) == prov["outputs"]["checkpoint_hashes"][ckpt_name]
        c = json.loads(cp.read_text())
        assert c["source_id"] == prov["source_id"] and c["complete"]
        assert c["completed_timed_repetitions"] == c["requested_repetitions"] == 7
        assert (c["precision"], str(c["budget"]), str(c["N"])) == (r["precision"], r["budget"], r["N"])
        wall = arr(r["raw_api_call_wall_s"])
        mkl = arr(r["raw_mkl_gemm_s"])
        assert [round(x, 12) for x in wall] == [round(float(x), 12) for x in c["call_wall_seconds"]]
        for field, samples in (("api_wall", wall), ("mkl_gemm", mkl)):
            expected_mean = statistics.mean(samples)
            assert abs(float(r["api_call_wall_s_mean"] if field == "api_wall" else r["mkl_gemm_s"]) - expected_mean) < 2e-9
        row = {"precision": r["precision"], "budget": int(r["budget"]), "N": int(r["N"]),
               "seed": int(r["seed"]), "status": r["status"],
               "api_wall": stats(wall), "split": stats(arr(r["raw_split_s"])),
               "compute_reconstruction": stats(arr(r["raw_compute_recon_s"])),
               "profile_total": stats(arr(r["raw_profile_total_s"])),
               "mkl_gemm": stats(mkl)}
        runs.setdefault(k, {})[name] = row

comparisons = {}
for k in sorted(runs, key=lambda s: (int(s.split("_N")[1]), s.split("_p")[0], int(s.split("_p")[1].split("_N")[0]))):
    by = runs[k]
    vals = {}
    for variant, names in (("V2", RUNS[0::2]), ("V3", RUNS[1::2])):
        vals[variant] = {}
        for metric in ("api_wall", "split", "compute_reconstruction", "profile_total", "mkl_gemm"):
            process = {n: by[n][metric] for n in names}
            medians = [process[n]["median"] for n in names]
            vals[variant][metric] = {
                "processes": process,
                "median_of_process_medians": statistics.median(medians),
                "mean_of_process_means": statistics.mean([process[n]["mean"] for n in names]),
                "mean_of_process_population_sds": statistics.mean([process[n]["sd_population"] for n in names]),
            }
    vals["change_percent_v3_vs_v2_api_median"] = 100 * (1 - vals["V3"]["api_wall"]["median_of_process_medians"] / vals["V2"]["api_wall"]["median_of_process_medians"])
    vals["change_percent_v3_vs_v2_mkl_median"] = 100 * (1 - vals["V3"]["mkl_gemm"]["median_of_process_medians"] / vals["V2"]["mkl_gemm"]["median_of_process_medians"])
    comparisons[k] = vals

out = {"schema": "ozamx-matched-recheck-analysis-v1", "runs": RUNS,
       "validation": {"configuration_count_per_run": 15, "process_count": 5,
                     "sample_count_per_run": 105, "sample_count_total": 525,
                     "all_rows_ok": True, "all_checkpoints_complete_and_hash_matched": True,
                     "library_sha256": EXPECTED,
                     "summary_method": "all process raw samples summarized with median, mean, population SD; primary comparison is median of process medians; means and SDs are separately retained"},
       "comparisons": comparisons}
(ROOT / "comparison.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(f"validated {len(RUNS)} processes x 15 configs x 7 reps = 525 samples")
for k, v in comparisons.items():
    if "N8192" in k or "N1024" in k or "N2048" in k:
        print(k, f"API {v['change_percent_v3_vs_v2_api_median']:+.2f}%", f"MKL {v['change_percent_v3_vs_v2_mkl_median']:+.2f}%")
