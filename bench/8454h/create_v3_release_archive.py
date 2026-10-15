#!/usr/bin/env python3
"""Create the allowlisted V3 source/results archive after all final gates pass.

This generator is intentionally not run until the V3 campaign owner has finalized
the raw result/provenance/report set. It copies only the production library binary
and refuses to overwrite an existing archive.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "bench/8454h/versions/v3_release"
PROV = ROOT / "bench/8454h/mkl_roofline_v3/provenance.json"
V3 = ROOT / "bench/8454h/mkl_roofline_v3"
V3_LIBRARY = Path("/tmp/ozamx-roofline-production/libozamx.a")
EXPECTED_V3_LIBRARY_SHA256 = "73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
EXPECTED_SOURCE_ID = "mkl-wall-roofline-v3-20261013"
V2_MANIFESTS = {
    "bench/8454h/versions/v2/MANIFEST.sha256": "0811f7ba2169b4ca37de5a3ac670cd54435572cd7d30cf909ae7a6d992c6463e",
    "bench/8454h/versions/v2_release/MANIFEST.sha256": "8b68d0d095b38f117cb10083ae5272847c533821d037fbdba7c091b06e6d950b",
}

# Explicit repository-relative payload allowlist. Do not replace with globbing:
# every raw result and source copied into the archive must be reviewable here.
FILES = (
    "README.md",
    "CMakeLists.txt",
    "include/ozamx/gemm.hpp",
    "src/gemm.cpp", "src/kernels.S", "src/main.cpp", "src/preprocess.hpp",
    "src/runtime.cpp", "src/tuning.hpp",
    "bench/benchmark.cpp", "bench/optimization_benchmark.cpp",
    "bench/run_8454h_baseline.sh", "bench/run_extended_validation.sh",
    "bench/run_packed_panel_audit.sh",
    "bench/8454h/equivalence_driver.cpp", "bench/8454h/run_equivalence.sh",
    "bench/8454h/create_v3_release_archive.py",
    "tests/validation.cpp", "tests/final_late_path_probe.cpp",
    "tests/extended_validation.cpp", "tests/packed_panel_audit.cpp",
    "tests/fp32_packed_panel_audit.cpp",
    "tests/bounded_commit_alias_probe.cpp",
    "tests/bounded_commit_overflow_probe.cpp",
    "tools/amx_probe.c", "tools/platform_baseline.cpp",
    "tools/native_kernel_audit.cpp", "tools/native_alternative_accuracy.cpp",
    "tools/native_signed_shift_accuracy.cpp",
    "tools/roofline_kernels.cpp", "tools/roofline_tileloads.S",
    "tools/roofline_memory.cpp", "tools/plot_roofline_calibration.py",
    "tools/roofline_binary_gate.cpp", "tools/roofline_thp_probe.cpp",
    "bench/8454h/roofline/run_kernel_calibration.sh",
    "bench/8454h/roofline/run_memory_calibration.sh",
    "bench/8454h/roofline/summarize_searches.py",
    "bench/8454h/roofline/search_commands.md",
    "bench/8454h/roofline/calibration/kernels.csv",
    "bench/8454h/roofline/calibration/kernel_metadata.json",
    "bench/8454h/roofline/calibration/kernel_disassembly.txt",
    "bench/8454h/roofline/calibration/kernel_summary.json",
    "bench/8454h/roofline/calibration/summarize_kernels.py",
    "bench/8454h/roofline/memory_calibration_20261013.csv",
    "bench/8454h/roofline/memory_calibration_20261013.json",
    "bench/8454h/roofline/memory_calibration_20261013.disasm.txt",
    "bench/8454h/roofline/traffic_model.json",
    "bench/8454h/roofline/binary_gate.json",
    "bench/8454h/roofline/binary_gate_attempt1.json",
    "bench/8454h/roofline/run_binary_gate.py",
    "bench/8454h/roofline/noomp_gate.json",
    "bench/8454h/roofline/production_validation.json",
    "bench/8454h/roofline/production_native_audit.json",
    "bench/8454h/roofline/extended47_cache_gate.json",
    "bench/8454h/roofline/noomp_build/build_manifest.json",
    "bench/8454h/roofline/noomp_build/ctest.log",
    "bench/8454h/roofline/run_extended47_stream.py",
    "bench/8454h/roofline/ideas/adaptive_block.patch",
    "bench/8454h/roofline/ideas/batch64.md",
    "bench/8454h/roofline/ideas/batch64.patch",
    "bench/8454h/roofline/ideas/hugepages.patch",
    "bench/8454h/roofline/ideas/numa_b.md",
    "bench/8454h/roofline/ideas/numa_b.patch",
    "bench/8454h/roofline/ideas/numa_b_gate.json",
    "bench/8454h/roofline/ideas/numa_b_gate.sh",
    "bench/8454h/roofline/ideas/numa_b_metadata.json",
    "bench/8454h/roofline/ideas/numa_b_trigger_probe.json",
    "bench/8454h/roofline/ideas/numa_partial_b.patch",
    "bench/8454h/roofline/ideas/pad_batch.patch",
    "bench/8454h/roofline/ideas/rectangular_block.patch",
    "bench/8454h/roofline/search_batch64/comparison.json",
    "bench/8454h/roofline/search_batch64/metadata.json",
    "bench/8454h/roofline/search_batch64/runner.sh",
    "bench/8454h/roofline/search_batch64/run01_frozen_before.csv",
    "bench/8454h/roofline/search_batch64/run02_batch1.csv",
    "bench/8454h/roofline/search_batch64/run03_batch2.csv",
    "bench/8454h/roofline/search_batch64/run04_batch4.csv",
    "bench/8454h/roofline/search_batch64/run05_frozen_middle.csv",
    "bench/8454h/roofline/search_batch64/run06_batch4_repeat.csv",
    "bench/8454h/roofline/search_batch64/run07_batch2_repeat.csv",
    "bench/8454h/roofline/search_batch64/run08_frozen_after.csv",
    "bench/8454h/roofline/search_pad/metadata.json",
    "bench/8454h/roofline/search_pad/summary.json",
    "bench/8454h/roofline/search_pad/pass0_frozen.csv",
    "bench/8454h/roofline/search_pad/pass1_p1b1.csv",
    "bench/8454h/roofline/search_pad/pass2_p2b1.csv",
    "bench/8454h/roofline/search_pad/pass3_p3b1.csv",
    "bench/8454h/roofline/search_pad/pass4_p1b2.csv",
    "bench/8454h/roofline/search_pad/pass5_frozen.csv",
    "bench/8454h/roofline/search_pad/pass6_p1b2.csv",
    "bench/8454h/roofline/search_pad/pass7_p1b1.csv",
    "bench/8454h/roofline/search_pad/pass8_frozen.csv",
    "bench/8454h/roofline/search_thp/metadata.json",
    "bench/8454h/roofline/search_thp/summary.json",
    "bench/8454h/roofline/search_thp/probe_hint0.json",
    "bench/8454h/roofline/search_thp/probe_hint1.json",
    "bench/8454h/roofline/search_thp/pass0_frozen.csv",
    "bench/8454h/roofline/search_thp/pass1_h1.csv",
    "bench/8454h/roofline/search_thp/pass2_frozen.csv",
    "bench/8454h/roofline/search_thp/pass3_h1.csv",
    "bench/8454h/roofline/search_thp/pass4_frozen.csv",
    "bench/8454h/roofline/search_rect/metadata.json",
    "bench/8454h/roofline/search_rect/summary.json",
    "bench/8454h/roofline/search_rect/pass0_frozen.csv",
    "bench/8454h/roofline/search_rect/pass1_n256p1.csv",
    "bench/8454h/roofline/search_rect/pass2_n512p1.csv",
    "bench/8454h/roofline/search_rect/pass3_n256p0.csv",
    "bench/8454h/roofline/search_rect/pass4_n256p1b2.csv",
    "bench/8454h/roofline/search_rect/pass5_frozen.csv",
    "bench/8454h/roofline/search_rect/pass6_n256p1.csv",
    "bench/8454h/roofline/search_rect/pass7_n512p1.csv",
    "bench/8454h/roofline/search_rect/pass8_frozen.csv",
    "bench/8454h/roofline/search_adaptive/metadata.json",
    "bench/8454h/roofline/search_adaptive/summary.json",
    "bench/8454h/roofline/search_adaptive/pass0_frozen.csv",
    "bench/8454h/roofline/search_adaptive/pass1_adaptive.csv",
    "bench/8454h/roofline/search_adaptive/pass2_frozen.csv",
    "bench/8454h/roofline/search_adaptive/pass3_adaptive.csv",
    "bench/8454h/roofline/search_adaptive/pass4_frozen.csv",
    "bench/8454h/roofline/search_numa_b/RESULTS.md",
    "bench/8454h/roofline/search_numa_b/run_manifest.json",
    "bench/8454h/roofline/search_numa_b/completion_manifest.json",
    "bench/8454h/roofline/search_numa_b/comparison.json",
    "bench/8454h/roofline/search_numa_b/completed_utc.txt",
    "bench/8454h/roofline/search_numa_b/logs/run_order.log",
    "bench/8454h/roofline/search_numa_b/runner.sh",
    "bench/8454h/roofline/search_numa_b/analyze.py",
    "bench/8454h/roofline/search_numa_b/raw/control0_4g.csv",
    "bench/8454h/roofline/search_numa_b/raw/frozen_4g_a.csv",
    "bench/8454h/roofline/search_numa_b/raw/frozen_4g_b.csv",
    "bench/8454h/roofline/search_numa_b/raw/frozen_4g_c.csv",
    "bench/8454h/roofline/search_numa_b/raw/numa1_4g_a.csv",
    "bench/8454h/roofline/search_numa_b/raw/numa1_4g_b.csv",
    "bench/8454h/roofline/search_numa_half/README.md",
    "bench/8454h/roofline/search_numa_half/2g/RESULTS.md",
    "bench/8454h/roofline/search_numa_half/2g/analyze.py",
    "bench/8454h/roofline/search_numa_half/2g/comparison.json",
    "bench/8454h/roofline/search_numa_half/2g/completion_manifest.json",
    "bench/8454h/roofline/search_numa_half/2g/run_manifest.json",
    "bench/8454h/roofline/search_numa_half/2g/runner.sh",
    "bench/8454h/roofline/search_numa_half/2g/completed_utc.txt",
    "bench/8454h/roofline/search_numa_half/2g/logs/run_order.log",
    "bench/8454h/roofline/search_numa_half/2g/raw/control0_2g.csv",
    "bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_a.csv",
    "bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_b.csv",
    "bench/8454h/roofline/search_numa_half/2g/raw/frozen_2g_c.csv",
    "bench/8454h/roofline/search_numa_half/2g/raw/numa_half_2g_a.csv",
    "bench/8454h/roofline/search_numa_half/2g/raw/numa_half_2g_b.csv",
    "bench/8454h/roofline/search_numa_half/4g/RESULTS.md",
    "bench/8454h/roofline/search_numa_half/4g/analyze.py",
    "bench/8454h/roofline/search_numa_half/4g/comparison.json",
    "bench/8454h/roofline/search_numa_half/4g/completion_manifest.json",
    "bench/8454h/roofline/search_numa_half/4g/run_manifest.json",
    "bench/8454h/roofline/search_numa_half/4g/runner.sh",
    "bench/8454h/roofline/search_numa_half/4g/completed_utc.txt",
    "bench/8454h/roofline/search_numa_half/4g/logs/run_order.log",
    "bench/8454h/roofline/search_numa_half/4g/raw/control0_4g.csv",
    "bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_a.csv",
    "bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_b.csv",
    "bench/8454h/roofline/search_numa_half/4g/raw/frozen_4g_c.csv",
    "bench/8454h/roofline/search_numa_half/4g/raw/numa_half_4g_a.csv",
    "bench/8454h/roofline/search_numa_half/4g/raw/numa_half_4g_b.csv",
    "bench/8454h/mkl_roofline_v3/README.md",
    "bench/8454h/mkl_roofline_v3/benchmark_roofline_v3.cpp",
    "bench/8454h/mkl_roofline_v3/run.sh",
    "bench/8454h/mkl_roofline_v3/run_command.txt",
    "bench/8454h/mkl_roofline_v3/full_roofline_v3.csv",
    "bench/8454h/mkl_roofline_v3/provenance.json",
    "bench/8454h/mkl_roofline_v3/source_hashes.sha256",
    "bench/8454h/mkl_roofline_v3/matched_recheck/README.md",
    "bench/8454h/mkl_roofline_v3/matched_recheck/analyze.py",
    "bench/8454h/mkl_roofline_v3/matched_recheck/comparison.json",
    "bench/8454h/mkl_roofline_v3/matched_recheck/run_matched_recheck.sh",
    "bench/8454h/mkl_roofline_v3/matched_recheck/write_provenance.py",
    "docs/8454H_FINAL_PERFORMANCE_REPORT.md",
    "docs/8454H_ROOFLINE_RESULTS.md",
    "docs/8454H_ROOFLINE_MODEL.md",
    "docs/8454H_ROOFLINE_CALIBRATION.md",
    "docs/8454H_ROOFLINE_SEARCH_LOG.md",
    "docs/8454H_ROOFLINE_TRAFFIC.md",
    "docs/8454H_SEARCH_RESULTS.md",
    "docs/8454H_KERNEL_IDEAS.md",
    "docs/8454H_PERFORMANCE_BASELINE.md",
    "docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.svg",
    "docs/figures/8454H_ROOFLINE_AMX_LOGICAL_AI.png",
    "docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.svg",
    "docs/figures/8454H_ROOFLINE_STAGE_DIAGNOSTIC.png",
    "docs/figures/8454H_ROOFLINE_PLOTS_METADATA.json",
    "third_party/SOURCES.md",
    "third_party/roofline/SOURCES.md",
    "third_party/roofline/study.md",
    "third_party/roofline/ISC18-RooflineAdvisor-final.pdf",
    "bench/8454h/versions/v2/README.md",
    "bench/8454h/versions/v2/MANIFEST.sha256",
    "bench/8454h/versions/v2_release/README.md",
    "bench/8454h/versions/v2_release/MANIFEST.sha256",
)

# Five processes x 16 rows. Keep evidence sources and raw CSV/checkpoints;
# candidate executables and repetitive build/run logs are intentionally omitted.
MATCHED_PROCESSES = ("p1_v2a", "p2_v3a", "p3_v2b", "p4_v3b", "p5_v2c")
MATCHED_CHECKPOINTS = (
    "fp32.1024.6", "fp32.2048.6", "fp32.8192.6",
    "fp64.1024.6", "fp64.1024.10", "fp64.1024.15", "fp64.1024.21",
    "fp64.2048.6", "fp64.2048.10", "fp64.2048.15", "fp64.2048.21",
    "fp64.8192.6", "fp64.8192.10", "fp64.8192.15", "fp64.8192.21",
)
MATCHED_FILES = tuple(
    f"bench/8454h/mkl_roofline_v3/matched_recheck/{process}/{name}"
    for process in MATCHED_PROCESSES
    for name in (
        "benchmark_matched_recheck.cpp", "full.csv", "provenance.json",
        *(f"checkpoint_{process}.{config}.json" for config in MATCHED_CHECKPOINTS),
    )
)

# Preserve one exact, rebuildable production-library artifact for hash auditing.
ARTIFACTS = ((V3_LIBRARY, Path("artifacts/libozamx_v3.a")),)

V3_CHECKPOINTS = (
    "checkpoint_roofline_v3.fp32.256.6.json",
    "checkpoint_roofline_v3.fp32.1024.6.json",
    "checkpoint_roofline_v3.fp32.4096.6.json",
    "checkpoint_roofline_v3.fp32.8192.6.json",
    "checkpoint_roofline_v3.fp64.256.6.json",
    "checkpoint_roofline_v3.fp64.256.10.json",
    "checkpoint_roofline_v3.fp64.256.15.json",
    "checkpoint_roofline_v3.fp64.256.21.json",
    "checkpoint_roofline_v3.fp64.1024.6.json",
    "checkpoint_roofline_v3.fp64.1024.10.json",
    "checkpoint_roofline_v3.fp64.1024.15.json",
    "checkpoint_roofline_v3.fp64.1024.21.json",
    "checkpoint_roofline_v3.fp64.4096.6.json",
    "checkpoint_roofline_v3.fp64.4096.10.json",
    "checkpoint_roofline_v3.fp64.4096.15.json",
    "checkpoint_roofline_v3.fp64.4096.21.json",
    "checkpoint_roofline_v3.fp64.8192.6.json",
    "checkpoint_roofline_v3.fp64.8192.10.json",
    "checkpoint_roofline_v3.fp64.8192.15.json",
    "checkpoint_roofline_v3.fp64.8192.21.json",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_completed_v3() -> dict:
    for rel, expected in V2_MANIFESTS.items():
        manifest = ROOT / rel
        if not manifest.is_file() or sha256(manifest) != expected:
            raise RuntimeError(f"immutable V2 manifest hash changed or is missing: {rel}")
    if not PROV.is_file():
        raise FileNotFoundError(f"final V3 provenance is missing: {PROV}")
    prov = json.loads(PROV.read_text())
    if prov.get("status") != "complete" or prov.get("source_id") != EXPECTED_SOURCE_ID:
        raise RuntimeError("V3 oneMKL provenance status/source_id is not finalized")
    if not V3_LIBRARY.is_file() or sha256(V3_LIBRARY) != EXPECTED_V3_LIBRARY_SHA256:
        raise RuntimeError("current V3 production library is missing or SHA-256 changed")
    if prov.get("library_sha256") != EXPECTED_V3_LIBRARY_SHA256:
        raise RuntimeError("V3 provenance library hash differs from the authorized V3 hash")
    csv_path = V3 / "full_roofline_v3.csv"
    csv_sha = prov.get("raw_csv_sha256", prov.get("outputs", {}).get("csv_sha256"))
    if sha256(csv_path) != csv_sha:
        raise RuntimeError("V3 raw CSV SHA-256 does not match finalized provenance")
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 20 or any(row.get("status") != "ok" for row in rows):
        raise RuntimeError(f"V3 CSV is incomplete or has failed rows: {len(rows)} rows")
    if len({(r["precision"], r["N"], r["budget"]) for r in rows}) != 20:
        raise RuntimeError("V3 CSV does not contain 20 unique configurations")
    if sha256(V3 / "benchmark_roofline_v3.cpp") != prov.get("benchmark_source_sha256"):
        raise RuntimeError("V3 benchmark driver hash mismatch")
    if sha256(V3 / "ozamx_benchmark") != prov.get("benchmark_binary_sha256"):
        raise RuntimeError("V3 benchmark binary does not match provenance; refresh final files first")
    missing = [name for name in V3_CHECKPOINTS if not (V3 / name).is_file()]
    if missing:
        raise FileNotFoundError(f"final V3 checkpoints missing: {missing}")
    recorded = prov.get("measurement", {}).get("checkpoint_hashes",
                                         prov.get("outputs", {}).get("checkpoint_hashes", {}))
    for name in V3_CHECKPOINTS:
        if recorded.get(name) != sha256(V3 / name):
            raise RuntimeError(f"V3 checkpoint hash mismatch: {name}")
    gate_path = ROOT / "bench/8454h/roofline/binary_gate.json"
    gate = json.loads(gate_path.read_text())
    if gate.get("status") != "pass" or gate.get("adaptive_library_sha256") != EXPECTED_V3_LIBRARY_SHA256:
        raise RuntimeError("12-case V3 full-output binary gate is missing or mismatched")
    results = ROOT / "docs/8454H_ROOFLINE_RESULTS.md"
    if not results.is_file():
        raise FileNotFoundError("final V3 interpretation report is missing")
    return {"source_id": prov["source_id"], "library_sha256": prov["library_sha256"],
            "csv_sha256": csv_sha, "csv_rows": len(rows),
            "checkpoint_count": len(V3_CHECKPOINTS), "binary_gate_status": gate["status"],
            "v2_manifest_hashes": V2_MANIFESTS.copy()}


def main() -> None:
    # Do not invoke until the final V3 campaign owner has reported completion.
    # The checks are intentionally strict so an incomplete run cannot be archived.
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite existing release archive: {OUT}")
    verification = verify_completed_v3()
    copied = []
    allowlist = (*FILES, *MATCHED_FILES,
                 *(f"bench/8454h/mkl_roofline_v3/{name}" for name in V3_CHECKPOINTS))
    if len(allowlist) != len(set(allowlist)):
        raise RuntimeError("duplicate entry in explicit V3 archive allowlist")
    missing = [rel for rel in allowlist if not (ROOT / rel).is_file()]
    if missing:
        raise FileNotFoundError(f"allowlisted archive inputs missing: {missing}")
    for rel in allowlist:
        source = ROOT / rel
        target = OUT / "repo" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)

    for source, relative_target in ARTIFACTS:
        if not source.is_file() or sha256(source) != EXPECTED_V3_LIBRARY_SHA256:
            raise RuntimeError(f"authorized production library missing or changed: {source}")
        target = OUT / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)

    readme = f"""# V3 roofline-guided production release archive

This archive freezes the current V3 source, build/test drivers, calibration evidence, roofline search results, final oneMKL comparison and interpretation report. The explicit repository-relative allowlist and generator are at `repo/bench/8454h/create_v3_release_archive.py`. Generated archive includes {len(copied)} repository payload files plus this README; `MANIFEST.sha256` covers the README and every copied file. The archive contains source, compact raw result files, metadata, plots, and one verified production-library binary. It excludes candidate benchmark binaries, build trees, vendor dependencies, and large diagnostic logs.

## Verified final experiment

- V3 source ID: `{verification['source_id']}`.
- Production library SHA-256: `{verification['library_sha256']}` (verified against the final oneMKL provenance and root's current authorized V3 library).
- oneMKL CSV: {verification['csv_rows']} successful configurations; SHA-256 `{verification['csv_sha256']}`.
- Complete per-configuration checkpoint count: {verification['checkpoint_count']}.
- Full-output binary gate: `{verification['binary_gate_status']}` for 12 large/representative cases.
- Immutable V2 manifest hashes: `{json.dumps(verification['v2_manifest_hashes'], sort_keys=True)}`.

The original immutable [V2 source snapshot](../v2/README.md) and its [release evidence archive](../v2_release/README.md) remain separate and unchanged. They are linked for comparison, not copied or rewritten here. All source and result files under `repo/` retain their repository-relative paths.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    files = [OUT / "README.md", *copied]
    entries = [f"{sha256(path)}  {path.relative_to(OUT).as_posix()}" for path in sorted(files)]
    (OUT / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")
    print(f"archive={OUT}")
    print(f"payload_files={len(files)} manifest_entries={len(entries)}")
    print(f"payload_bytes={sum(p.stat().st_size for p in files)}")


if __name__ == "__main__":
    main()
