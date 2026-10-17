#!/usr/bin/env python3
"""Lightweight T2 tests: read completed L1 arms and mutate temporary copies only."""
import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/compare_campaigns.py"
SPEC = importlib.util.spec_from_file_location("compare_campaigns", TOOL)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = ROOT / "bench/8454h/paper_alignment/arms/l1_fp32_bracket_20261016"
SOURCES = [BASE / name for name in ("a1_2g", "b_8g", "a2_2g")]


class CampaignComparisons(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ozamx-compare-fixtures-")
        self.addCleanup(self.tmp.cleanup)
        self.arms = [Path(self.tmp.name) / name for name in ("A", "B", "Aprime")]
        for source, arm in zip(SOURCES, self.arms):
            shutil.copytree(source, arm, ignore=shutil.ignore_patterns("*.log", "outer_time*.txt"))

    def run_tool(self, count=3):
        out = Path(self.tmp.name) / "comparison.json"
        process = subprocess.run([sys.executable, "-B", str(TOOL), "--arms",
                                  *(str(p) for p in self.arms[:count]), "--out", str(out)],
                                 capture_output=True, text=True)
        self.assertTrue(out.is_file(), process.stderr)
        return process.returncode, json.loads(out.read_text())

    def assert_invalid(self, expected):
        code, report = self.run_tool()
        self.assertEqual(code, 2, report)
        self.assertEqual(report["status"], "invalid")
        self.assertIn(expected, report["error"])

    def test_valid_bracket_ratios_from_raw_data_not_claimed_means(self):
        path = self.arms[1] / "analysis.json"
        claimed = json.loads(path.read_text())
        for row in claimed["rows"]:
            row["api_mean_s"] = 1234567  # Must never be used as measurement evidence.
        path.write_text(json.dumps(claimed))
        code, report = self.run_tool()
        self.assertEqual(code, 0, report)
        self.assertFalse(report["causal_or_paper_target_success_inferred"])
        self.assertTrue(all(a["revalidated_source_policy"] == "snapshot" for a in report["arms"]))
        for row in report["rows"]:
            raw = []
            for arm in self.arms:
                with (arm / "results.csv").open() as stream:
                    record = next(r for r in csv.DictReader(stream) if int(r["N"]) == row["N"])
                raw.append(statistics.mean(float(t) for t in record["raw_api_call_wall_s"].split(";") if t))
            for name, numerator, denominator in (("B_over_A", 1, 0), ("B_over_A_prime", 1, 2),
                                                  ("A_prime_over_A_drift", 2, 0)):
                self.assertAlmostEqual(row["comparisons"][name]["api_wall_ratio"], raw[numerator] / raw[denominator])
            self.assertAlmostEqual(row["arms"]["B"]["api_mean_s"], raw[1])

    def test_two_arms(self):
        code, report = self.run_tool(count=2)
        self.assertEqual(code, 0, report)
        self.assertEqual(set(report["rows"][0]["comparisons"]), {"B_over_A"})

    def test_wrong_declared_cache(self):
        path = self.arms[1] / "analysis.json"
        claimed = json.loads(path.read_text())
        claimed["environment_expected"]["OZAMX_WORKSPACE_CACHE_BYTES"] = "2147483648"
        path.write_text(json.dumps(claimed))
        self.assert_invalid("fresh analyzer rejected")

    def test_old_pass_report_does_not_hide_incomplete_checkpoint(self):
        path = self.arms[1] / "checkpoint.fp32.8192.6.json"
        checkpoint = json.loads(path.read_text())
        checkpoint["complete"] = False
        path.write_text(json.dumps(checkpoint))
        self.assert_invalid("not complete with ten timed pairs")

    def test_individually_valid_but_different_scope(self):
        arm = self.arms[1]
        path = arm / "results.csv"
        with path.open() as stream:
            reader = csv.DictReader(stream)
            header, rows = reader.fieldnames, [row for row in reader if int(row["N"]) == 8192]
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
        (arm / "checkpoint.fp32.16384.6.json").unlink()
        result = subprocess.run([sys.executable, "-B", str(MODULE.ANALYZER), str(path),
                                 "--out", str(arm / "analysis.json"), "--sizes", "8192",
                                 "--modes", "fp32_p6", "--expect-cache-bytes", "8589934592",
                                 "--source-policy", "snapshot"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_invalid("configuration scopes differ")

    def test_stale_csv_hash(self):
        path = self.arms[1] / "results.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        self.assert_invalid("CSV SHA is stale")

    def test_missing_frozen_snapshot(self):
        (self.arms[1] / "source_snapshot/src/preprocess.hpp").unlink()
        self.assert_invalid("source snapshot missing")


class WelchArithmetic(unittest.TestCase):
    def test_t_critical_table_matches_student_t_density(self):
        # Independently integrate the Student t density (composite Simpson),
        # checking the numeric critical-value table without SciPy dependencies.
        for df, critical in MODULE.T975.items():
            scale = math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi)
            intervals = 2048
            step = critical / intervals
            terms = []
            for i in range(intervals + 1):
                weight = 1 if i in (0, intervals) else (4 if i % 2 else 2)
                terms.append(weight * scale * (1 + (i * step) ** 2 / df) ** (-(df + 1) / 2))
            self.assertAlmostEqual(0.5 + step * sum(terms) / 3, 0.975, places=10)

    def test_equal_variance_and_zero_variance(self):
        denominator = list(range(1, 11))
        numerator = list(range(2, 12))
        interval = MODULE.welch_interval(numerator, denominator)
        se = math.sqrt(2 * statistics.variance(denominator) / 10)
        self.assertAlmostEqual(interval["estimate_s"], 1)
        self.assertAlmostEqual(interval["welch_df"], 18)
        self.assertEqual(interval["critical_df"], 18)
        self.assertAlmostEqual(interval["lower_s"], 1 - 2.1009220402 * se)
        self.assertAlmostEqual(interval["upper_s"], 1 + 2.1009220402 * se)
        flat = MODULE.welch_interval([2] * 10, [1] * 10)
        self.assertEqual((flat["lower_s"], flat["upper_s"]), (1, 1))
        self.assertIsNone(flat["welch_df"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", type=Path, nargs=3, default=SOURCES)
    args = parser.parse_args()
    SOURCES = [p.resolve() for p in args.arms]
    unittest.main(argv=[sys.argv[0]])
