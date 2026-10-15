#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$HERE/../../../../" && pwd)"
FREEZE_MARKER="$REPO_ROOT/bench/8454h/v3_paper_alignment/FROZEN_COMPLETE"
EXPECTED_ARCHIVE_REL="bench/8454h/versions/v3_paper_release"
EXPECTED_LIBRARY_SHA256="73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c"
if [[ ! -f "$FREEZE_MARKER" ]]; then
  echo "refusing to run: frozen V3 completion marker missing: $FREEZE_MARKER" >&2
  exit 2
fi
MARKER_INFO="$(python3 - "$FREEZE_MARKER" "$REPO_ROOT" "$EXPECTED_ARCHIVE_REL" "$EXPECTED_LIBRARY_SHA256" <<'PY'
import json, pathlib, re, sys
path, root_arg, expected_archive_rel, expected_library = sys.argv[1:]
root = pathlib.Path(root_arg).resolve(strict=True)
with open(path, encoding="utf-8") as f:
    marker = json.load(f)
if marker.get("complete") is not True:
    raise SystemExit("FROZEN_COMPLETE must contain complete=true")
if marker.get("configurations") != 66:
    raise SystemExit(f"FROZEN_COMPLETE configurations must be 66, got {marker.get('configurations')!r}")
if marker.get("library_sha256") != expected_library:
    raise SystemExit(f"FROZEN_COMPLETE library hash mismatch: {marker.get('library_sha256')!r}")
archive_rel = marker.get("archive")
if archive_rel != expected_archive_rel:
    raise SystemExit(f"FROZEN_COMPLETE archive path mismatch: {archive_rel!r}")
archive = (root / archive_rel).resolve(strict=True)
expected_archive = (root / expected_archive_rel).resolve(strict=True)
if archive != expected_archive:
    raise SystemExit(f"FROZEN_COMPLETE archive resolves outside the expected release: {archive}")
manifest_hash = marker.get("manifest_sha256")
if not isinstance(manifest_hash, str) or re.fullmatch(r"[0-9a-f]{64}", manifest_hash) is None:
    raise SystemExit("FROZEN_COMPLETE manifest_sha256 must be a lowercase SHA-256")
print(f"{archive}\t{manifest_hash}")
PY
)"
IFS=$'\t' read -r FROZEN_ARCHIVE EXPECTED_MANIFEST_SHA256 <<< "$MARKER_INFO"
ACTUAL_MANIFEST_SHA256="$(sha256sum "$FROZEN_ARCHIVE/MANIFEST.sha256" | awk '{print $1}')"
if [[ "$ACTUAL_MANIFEST_SHA256" != "$EXPECTED_MANIFEST_SHA256" ]]; then
  echo "refusing to run: supplemental archive manifest hash mismatch: $ACTUAL_MANIFEST_SHA256" >&2
  exit 2
fi
V3_LIBRARY="$FROZEN_ARCHIVE/v3_release/artifacts/libozamx_v3.a"
ACTUAL_LIBRARY_SHA256="$(sha256sum "$V3_LIBRARY" | awk '{print $1}')"
if [[ "$ACTUAL_LIBRARY_SHA256" != "$EXPECTED_LIBRARY_SHA256" ]]; then
  echo "refusing to run: supplemental archive V3 library hash mismatch: $ACTUAL_LIBRARY_SHA256" >&2
  exit 2
fi
(cd "$FROZEN_ARCHIVE" && sha256sum --quiet -c MANIFEST.sha256)

BUILD_DIR="${INT8_BUILD_DIR:-/tmp/ozamx-int8-36-build}"
RESULT_ROOT="${INT8_RESULT_DIR:-$HERE/results}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
RESULT_DIR="$RESULT_ROOT/$RUN_ID"
MKL_ROOT="${OZAMX_MKL_ROOT:-$REPO_ROOT/third_party/code/mkl-current}"
mkdir -p "$RESULT_DIR"
exec 9>/tmp/ozamx-perf.lock
flock -x 9

cmake -S "$HERE" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release \
  -DOZAMX_V3_ROOT="$REPO_ROOT" -DOZAMX_V3_LIBRARY="$V3_LIBRARY" \
  -DOZAMX_MKL_ROOT="$MKL_ROOT"
cmake --build "$BUILD_DIR" --target int8_quality_gate int8_benchmark_driver -j8

export LD_LIBRARY_PATH="$MKL_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export MKL_THREADING_LAYER=GNU
export MKL_DYNAMIC=FALSE
export OMP_DYNAMIC=FALSE
export OMP_NUM_THREADS=64
export OMP_PLACES=cores OMP_PROC_BIND=close MKL_NUM_THREADS=64
export OZAMX_WORKSPACE_CACHE_BYTES=2147483648

# Save source, archive, executable, and linked runtime identities with every dataset.
PROV="$RESULT_DIR/provenance.txt"
{
  echo "freeze_marker=$FREEZE_MARKER"
  echo "frozen_archive=$FROZEN_ARCHIVE"
  echo "freeze_marker_sha256=$(sha256sum "$FREEZE_MARKER" | awk '{print $1}')"
  echo "v3_manifest_sha256=$ACTUAL_MANIFEST_SHA256"
  echo "v3_library_sha256=$ACTUAL_LIBRARY_SHA256"
  sha256sum "$FREEZE_MARKER" "$HERE/CMakeLists.txt" "$HERE/int8.cpp" "$HERE/int8.hpp" \
    "$HERE/kernels.S" "$HERE/quality_gate.cpp" "$HERE/benchmark_driver.cpp" \
    "$HERE/run_after_freeze.sh" \
    "$V3_LIBRARY" "$BUILD_DIR/libozamx_int8_36.a" "$BUILD_DIR/int8_quality_gate" \
    "$BUILD_DIR/int8_benchmark_driver" "$MKL_ROOT/lib/libmkl_rt.so.3" \
    "$MKL_ROOT/lib/libmkl_core.so.3"
  echo "--- linked runtime paths ---"
  ldd "$BUILD_DIR/int8_benchmark_driver"
  ldd "$BUILD_DIR/int8_benchmark_driver" | awk '/=> \/\// {print $3} /^\// {print $1}' | sort -u > "$RESULT_DIR/runtime_paths.txt"
  echo "--- linked runtime SHA-256 ---"
  while IFS= read -r runtime_so; do
    [[ -f "$runtime_so" ]] && sha256sum "$runtime_so"
  done < "$RESULT_DIR/runtime_paths.txt"
  echo "--- build identity ---"
  cmake -LA -N "$BUILD_DIR" | rg 'CMAKE_BUILD_TYPE:|OZAMX_I8_B[MNK]:|OZAMX_I8_TILELOAD_HINT:|OZAMX_V3_LIBRARY:|OZAMX_MKL_ROOT:'
} > "$PROV"

# No performance data is collected unless the full binary128/domain gate succeeds.
taskset -c 0-63 "$BUILD_DIR/int8_quality_gate" 64 > "$RESULT_DIR/quality_gate.json" 2> "$RESULT_DIR/quality_gate.stderr.log"

for n in 1024 4096 8192; do
  taskset -c 0-63 "$BUILD_DIR/int8_benchmark_driver" --n "$n" --threads 64 --reps 5 \
    --seed 260904 --output "$RESULT_DIR/matched_n${n}.json" \
    > "$RESULT_DIR/matched_n${n}.stdout.log" 2> "$RESULT_DIR/matched_n${n}.stderr.log"
done
