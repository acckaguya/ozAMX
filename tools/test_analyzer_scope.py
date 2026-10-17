#!/usr/bin/env python3
"""Test declared analyzer scopes using temporary, synthetic campaign copies.

No GEMM or compilation is run. Original campaign evidence and the four legacy
negative fixtures are never changed. The supplied campaign must be a complete
40-configuration baseline that passes the analyzer's default identity checks.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/analyze_paper_alignment.py"
SPEC = importlib.util.spec_from_file_location("paper_analyzer", ANALYZER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SCOPE = ["--sizes", "8192,16384", "--precision", "fp32", "--budget", "6"]
CACHE_2G = 2147483648
CACHE_8G = 8589934592
CAMPAIGN = ROOT / "bench/8454h/paper_alignment/main_passive_2g_20261016"


def encode_identity(fields):
    record = bytearray()
    for key, values in fields.items():
        for value in values:
            for text in (key, value):
                raw = text.encode()
                record.extend(str(len(raw)).encode() + b":" + raw)
    return record.hex()


class ScopeFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ozamx-analyzer-scope-")
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / "campaign"
        shutil.copytree(CAMPAIGN, self.directory,
                        ignore=shutil.ignore_patterns("*.log", "outer_time*.txt", "analysis*.json"))
        with (self.directory / "results.csv").open() as stream:
            reader = csv.DictReader(stream)
            self.header = reader.fieldnames
            self.rows = list(reader)
        self.provenance = json.loads((self.directory / "provenance.json").read_text())

    def save(self):
        with (self.directory / "results.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.header)
            writer.writeheader()
            writer.writerows(self.rows)
        (self.directory / "provenance.json").write_text(json.dumps(self.provenance))

    def partial(self, cache_bytes=CACHE_2G, runtime_wait=False, selected_targets_pass=False):
        self.rows = [r for r in self.rows if r["precision"] == "fp32" and
                     int(r["budget"]) == 6 and int(r["N"]) in (8192, 16384)]
        self.assertEqual(len(self.rows), 2)
        wanted = {f"checkpoint.fp32.{r['N']}.6.json" for r in self.rows}
        for path in self.directory.glob("checkpoint.*.json"):
            if path.name not in wanted:
                path.unlink()
        self.provenance["environment"]["OZAMX_WORKSPACE_CACHE_BYTES"] = str(cache_bytes)
        if runtime_wait:
            for key in ("OMP_WAIT_POLICY", "GOMP_SPINCOUNT"):
                self.provenance["environment"].pop(key, None)
        for row in self.rows:
            fields = MODULE.decode_identity(row["run_identity"])
            environment = dict(v.split("=", 1) for v in fields["environment"])
            environment["OZAMX_WORKSPACE_CACHE_BYTES"] = str(cache_bytes)
            if runtime_wait:
                for key in ("OMP_WAIT_POLICY", "GOMP_SPINCOUNT"):
                    environment.pop(key, None)
            fields["environment"] = [f"{k}={v}" for k, v in sorted(environment.items())]
            row["run_identity"] = encode_identity(fields)
            path = self.directory / f"checkpoint.fp32.{row['N']}.6.json"
            checkpoint = json.loads(path.read_text())
            checkpoint["run_identity"] = row["run_identity"]
            if selected_targets_pass:
                # Synthetic speedups above both selected paper targets, with
                # mutually consistent raw vectors, means, and checkpoints.
                times = [3 * t for t in MODULE.parse_floats(row["raw_api_call_wall_s"])]
                row["raw_mkl_gemm_s"] = ";".join(format(t, ".17g") for t in times)
                row["mkl_gemm_s"] = format(statistics.mean(times), ".17g")
                row["api_speedup"] = "3"
                row["mkl_effective_GFLOP_s"] = str(2 * int(row["N"]) ** 3 /
                                                       statistics.mean(times) / 1e9)
                row["profile_speedup"] = str(statistics.mean(times) /
                                                   float(row["profile_total_s_mean"]))
                checkpoint["mkl_gemm_seconds"] = times
            path.write_text(json.dumps(checkpoint))
        self.save()

    def analyze(self, *arguments):
        out = Path(self.tmp.name) / "report.json"
        out.unlink(missing_ok=True)
        result = subprocess.run([sys.executable, str(ANALYZER),
                                 str(self.directory / "results.csv"), "--out", str(out),
                                 *arguments], capture_output=True, text=True)
        self.assertTrue(out.is_file(), result.stderr)
        return result.returncode, json.loads(out.read_text())

    def assert_rejected(self, arguments, issue):
        code, report = self.analyze(*arguments)
        self.assertEqual(code, 2, report)
        self.assertTrue(any(issue in text for text in report["protocol_or_identity_issues"]), report)
        self.assertFalse(report["declared_configuration_coverage"])
        self.assertFalse(report["full_40_configuration_coverage"])
        self.assertFalse(report["paper_fp32_speedup_targets_all_met"])

    def test_complete_default_unchanged(self):
        code, report = self.analyze()
        self.assertEqual(code, 0, report)
        self.assertTrue(report["declared_configuration_coverage"])
        self.assertTrue(report["full_40_configuration_coverage"])
        self.assertEqual(report["source_policy"], "current")
        self.assertEqual(report["environment_expected"], MODULE.REQUIRED_ENV)
        self.assertEqual(report["expected_configurations"], 40)
        self.assertEqual(report["paper_fp32_speedup_targets_all_met"],
                         all(point["met"] for point in report["fp32_speedup_targets"].values()))

    def test_partial_2g_and_modes_alias(self):
        self.partial()
        for arguments in (SCOPE, ["--sizes", "8192,16384", "--modes", "fp32_p6"]):
            with self.subTest(arguments=arguments):
                code, report = self.analyze(*arguments)
                self.assertEqual(code, 0, report)
                self.assertTrue(report["declared_configuration_coverage"])
                self.assertEqual(report["expected_configurations"], 2)
                self.assertFalse(report["full_40_configuration_coverage"])
                self.assertFalse(report["paper_fp32_speedup_targets_all_met"])

    def test_partial_8g(self):
        self.partial(cache_bytes=CACHE_8G)
        code, report = self.analyze(*SCOPE, "--expect-cache-bytes", str(CACHE_8G))
        self.assertEqual(code, 0, report)
        self.assertTrue(report["declared_configuration_coverage"])
        self.assertEqual(report["environment_expected"]["OZAMX_WORKSPACE_CACHE_BYTES"], str(CACHE_8G))
        self.assertFalse(report["full_40_configuration_coverage"])

    def test_wrong_cache_rejected(self):
        self.partial(cache_bytes=CACHE_8G)
        self.assert_rejected(SCOPE, "environment lacks required entries")

    def test_wrong_scope_rejected(self):
        self.partial()
        self.assert_rejected(["--sizes", "8192", "--modes", "fp32_p6"],
                             "unexpected campaign configurations")

    def test_no_implicit_partial_scope(self):
        self.partial()
        self.assert_rejected([], "missing campaign configurations")

    def test_partial_selected_targets_all_pass_still_not_full_paper_success(self):
        self.partial(selected_targets_pass=True)
        code, report = self.analyze(*SCOPE, "--require-paper-speedups")
        self.assertEqual(code, 1, report)
        self.assertTrue(report["declared_configuration_coverage"])
        self.assertTrue(all(point["met"] for point in report["fp32_speedup_targets"].values()))
        self.assertFalse(report["full_40_configuration_coverage"])
        self.assertFalse(report["paper_fp32_speedup_targets_all_met"])

    def test_runtime_wait_must_be_unset(self):
        self.partial(runtime_wait=True)
        code, report = self.analyze(*SCOPE, "--expect-wait", "runtime")
        self.assertEqual(code, 0, report)
        self.assertEqual(set(report["environment_expected_unset"]),
                         {"OMP_WAIT_POLICY", "GOMP_SPINCOUNT"})
        self.assert_rejected(SCOPE, "environment lacks required entries")

    def test_runtime_rejects_passive_environment(self):
        self.partial()
        self.assert_rejected([*SCOPE, "--expect-wait", "runtime"], "must leave entries unset")

    def test_snapshot_policy_still_requires_all_snapshots(self):
        self.partial()
        (self.directory / "source_snapshot/src/tuning.hpp").unlink()
        self.assert_rejected([*SCOPE, "--source-policy", "snapshot"], "source snapshot missing")

    def test_snapshot_policy_rejects_incomplete_manifest(self):
        self.partial()
        del self.provenance["source_sha256"]["src/tuning.hpp"]
        self.save()
        self.assert_rejected([*SCOPE, "--source-policy", "snapshot"], "manifest is incomplete")

    def test_snapshot_policy_hash_and_current_policy_difference(self):
        self.partial()
        path = self.directory / "source_snapshot/src/tuning.hpp"
        path.write_bytes(path.read_bytes() + b"\n// Synthetic policy fixture only.\n")
        self.assert_rejected([*SCOPE, "--source-policy", "snapshot"], "snapshot differs")
        self.provenance["source_sha256"]["src/tuning.hpp"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.save()
        self.assert_rejected(SCOPE, "working tree source differs")
        code, report = self.analyze(*SCOPE, "--source-policy", "snapshot")
        self.assertEqual(code, 0, report)
        self.assertEqual(report["source_policy"], "snapshot")
        self.assertTrue(report["declared_configuration_coverage"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", nargs="?", type=Path, default=CAMPAIGN)
    args = parser.parse_args()
    CAMPAIGN = args.campaign.resolve()
    unittest.main(argv=[sys.argv[0]])
