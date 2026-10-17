#!/usr/bin/env python3
"""Negative fixtures for tools/analyze_strict_emulation.py.

Copies a completed (or in-progress) historical campaign directory into a
temporary directory, mutates exactly one thing per fixture, and asserts that the
analyzer refuses the mutated evidence (exit code 2) with the expected issue.
The campaign directory itself is only read, never modified.
"""
import argparse
import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/analyze_strict_emulation.py"


def read_report(out):
    if out.is_file():
        return json.loads(out.read_text())
    return None


def run_analyzer(directory, out):
    process = subprocess.run([sys.executable, str(ANALYZER), str(directory / "results.csv"),
                              "--out", str(out), "--source-policy", "snapshot"],
                             capture_output=True, text=True)
    report = read_report(out)
    issues = report["protocol_or_identity_issues"] if report else []
    return process.returncode, issues, process.stderr


def copy_campaign(source, target):
    shutil.copytree(source, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("resume_*.log", "stdout.log", "stderr.log",
                                                  "outer_time*.txt", "analysis*.json"))


def mutate_identity(directory):
    rows = list(csv.reader((directory / "results.csv").open()))
    index = 3  # a data row
    value = rows[index][-1]
    rows[index][-1] = value[:-1] + ("0" if value[-1] != "0" else "1")
    with (directory / "results.csv").open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    return "Missing or mixed run_identity"


def mutate_incomplete_checkpoint(directory):
    path = directory / "checkpoint.fp32.256.6.json"
    data = json.loads(path.read_text())
    data["complete"] = False
    data["completed_timed_repetitions"] = 9
    path.write_text(json.dumps(data))
    return "not complete with ten timed pairs"


def mutate_truncated_raw(directory):
    rows = list(csv.reader((directory / "results.csv").open()))
    header = rows[0]
    column = header.index("raw_api_call_wall_s")
    rows[3][column] = ";".join(rows[3][column].split(";")[:-1])
    with (directory / "results.csv").open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    return "raw vector lengths do not match repetitions"


def mutate_missing_checkpoint(directory):
    path = directory / "checkpoint.fp64.32768.21.json"
    if not path.is_file():
        path = next(directory.glob("checkpoint.fp64.*.json"))
    path.unlink()
    return "checkpoint set does not equal"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--require-complete-clean", action="store_true",
                        help="also assert the unmutated copy passes the integrity gate "
                             "(use only after the campaign finished)")
    a = parser.parse_args()
    source = a.campaign.resolve()
    fixtures = [("mixed_identity", mutate_identity),
                ("incomplete_checkpoint", mutate_incomplete_checkpoint),
                ("truncated_raw", mutate_truncated_raw),
                ("missing_checkpoint", mutate_missing_checkpoint)]
    failures = []
    with tempfile.TemporaryDirectory(prefix="ozamx-checker-fixtures-") as tmp:
        tmp = Path(tmp)
        if a.require_complete_clean:
            clean = tmp / "clean"
            copy_campaign(source, clean)
            code, issues, stderr = run_analyzer(clean, tmp / "clean.analysis.json")
            report = read_report(tmp / "clean.analysis.json")
            if code != 0 or not report or not report["reference_protocol_and_identity_valid"]:
                failures.append(f"clean campaign failed integrity: rc={code} issues={issues} {stderr[:300]}")
            else:
                print("clean: integrity valid (rc=0)")
        for name, mutate in fixtures:
            directory = tmp / name
            copy_campaign(source, directory)
            expected = mutate(directory)
            code, issues, stderr = run_analyzer(directory, tmp / f"{name}.analysis.json")
            hit = any(expected in issue for issue in issues)
            status = "ok" if (code == 2 and hit) else "FAIL"
            print(f"{name}: rc={code} expected_issue_found={hit} [{status}]")
            if not (code == 2 and hit):
                failures.append(f"{name}: rc={code} issues={issues} stderr={stderr[:300]}")
    if failures:
        print("\nfailures:")
        for failure in failures:
            print(" -", failure)
        return 1
    print("\nall fixtures behaved as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
