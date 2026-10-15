#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
lock=${OZAMX_PERF_LOCK:-/tmp/ozamx-perf.lock}
summary=${OZAMX_PACKED_AUDIT_SUMMARY:-$repo/bench/8454h/packed_panel_audit_summary.json}
work=$(mktemp -d /tmp/ozamx-packed-audit.XXXXXX)
trap 'rm -rf "$work"' EXIT
if (($#)); then sources=("$@"); else
  sources=("${OZAMX_DIRECTPACK_SOURCE_DIR:-/tmp/ozamx-directpack/src}")
  [[ ! -f /tmp/ozamx-packed-residual/src/preprocess.hpp ]] || sources+=(/tmp/ozamx-packed-residual/src)
fi
exec 9> "$lock"
flock -x 9

results=()
for index in "${!sources[@]}"; do
  source_dir=${sources[$index]}
  header=$source_dir/preprocess.hpp
  [[ -f $header ]] || {
    echo "preprocessing header missing: $header" >&2
    exit 2
  }
  binary=$work/panel-audit-$index
  "${CXX:-g++}" -std=c++17 -O2 -march=sapphirerapids -ffp-contract=off -fopenmp \
    -I"$repo/include" "-DOZAMX_PREPROCESS_HEADER=\"$header\"" \
    "$repo/tests/packed_panel_audit.cpp" -o "$binary"
  if ! "$binary" > "$work/result-$index.jsonl" 2> "$work/result-$index.log"; then
    cat "$work/result-$index.log" >&2
    tail -5 "$work/result-$index.jsonl" >&2 || true
    exit 1
  fi
  results+=("fp64" "$source_dir" "$work/result-$index.jsonl")
done
fp32_source=${OZAMX_FP32_DIRECT_SOURCE_DIR:-/tmp/ozamx-fp32-direct/src}
if [[ -f $fp32_source/preprocess.hpp ]]; then
  binary=$work/fp32-panel-audit
  "${CXX:-g++}" -std=c++17 -O2 -march=sapphirerapids -ffp-contract=off -fopenmp \
    -I"$repo/include" "-DOZAMX_PREPROCESS_HEADER=\"$fp32_source/preprocess.hpp\"" \
    "$repo/tests/fp32_packed_panel_audit.cpp" -o "$binary"
  if ! "$binary" > "$work/fp32-result.jsonl" 2> "$work/fp32-result.log"; then
    cat "$work/fp32-result.log" >&2
    tail -5 "$work/fp32-result.jsonl" >&2 || true
    exit 1
  fi
  results+=("fp32" "$fp32_source" "$work/fp32-result.jsonl")
fi

python3 - "$repo" "$summary" "${results[@]}" << 'PY'
import hashlib, json, pathlib, sys

root = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
docs = []
for i in range(3, len(sys.argv), 3):
    precision = sys.argv[i]
    source = pathlib.Path(sys.argv[i + 1])
    path = pathlib.Path(sys.argv[i + 2])
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    # FP64 覆盖 4 个形状×4 个深度×4 个输入域；FP32 覆盖 3×3。
    expected = 64 if precision == "fp64" else 9
    if len(rows) != expected or any(r.get("status") not in ("pass", "both_rejected") for r in rows):
        raise SystemExit(f"packed panel audit failed or incomplete: {path}")
    if any(r.get("reference_accepted") != r.get("candidate_accepted") for r in rows):
        raise SystemExit(f"legacy/direct accept-reject behavior differs: {path}")
    if any(
        r.get("status") == "both_rejected" and r.get("input") != "max_bf16_boundary" for r in rows
    ):
        raise SystemExit(f"unexpected rejected input domain: {path}")
    docs.append(
        {
            "precision": precision,
            "source_dir": str(source),
            "header_sha256": hashlib.sha256((source / "preprocess.hpp").read_bytes()).hexdigest(),
            "cases": len(rows),
            "both_rejected": sum(r["status"] == "both_rejected" for r in rows),
            "inputs": sorted({r["input"] for r in rows}),
            "depths": sorted({r["depth"] for r in rows}) if precision == "fp64" else [3],
            "shapes": sorted({(r["m"], r["n"], r["k"]) for r in rows}),
            "result_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(
    json.dumps(
        {
            "status": "pass",
            "audits": docs,
            "driver_sha256": hashlib.sha256(
                (root / "tests/packed_panel_audit.cpp").read_bytes()
            ).hexdigest(),
            "fp32_driver_sha256": hashlib.sha256(
                (root / "tests/fp32_packed_panel_audit.cpp").read_bytes()
            ).hexdigest(),
            "runner_sha256": hashlib.sha256(
                (root / "bench/run_packed_panel_audit.sh").read_bytes()
            ).hexdigest(),
            "comparison": "Every uint16 element in each legacy pack_slices A/B panel was compared with split_pack_direct64 output for depths 3/4/5/6; input accept/reject behavior is also compared.",
        },
        indent=2,
    )
    + "\n"
)
print(
    json.dumps(
        {
            "status": "pass",
            "audits": len(docs),
            "cases": [d["cases"] for d in docs],
            "both_rejected": [d["both_rejected"] for d in docs],
        }
    )
)
PY
