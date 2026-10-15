#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
default_lib=${OZAMX_DEFAULT_LIBRARY:-/tmp/ozamx-optimized-8454h/libozamx.a}
candidate_lib=${OZAMX_CANDIDATE_LIBRARY:-/tmp/ozamx-pipelined/build/libozamx.a}
summary=${OZAMX_EXTENDED_SUMMARY:-$repo/bench/8454h/extended_validation_summary.json}
default_cache_bytes=${OZAMX_DEFAULT_CACHE_BYTES:-2147483648}
for lib in "$default_lib" "$candidate_lib"; do
  [[ -f "$lib" ]] || {
    echo "library not found: $lib" >&2
    exit 2
  }
done
work=$(mktemp -d /tmp/ozamx-extended-validation.XXXXXX)
trap 'rm -rf "$work"' EXIT
exec 9> "${OZAMX_PERF_LOCK:-/tmp/ozamx-perf.lock}"
flock -x 9

flags=(-std=c++17 -O2 -march=sapphirerapids -ffp-contract=off -mamx-tile -mamx-bf16 -fopenmp)
for name in default candidate; do
  if [[ $name == default ]]; then lib=$default_lib; else lib=$candidate_lib; fi
  "${CXX:-g++}" "${flags[@]}" -I"$repo/include" "$repo/tests/extended_validation.cpp" "$lib" -o "$work/$name"
  OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE OZAMX_WORKSPACE_CACHE_BYTES="$default_cache_bytes" "$work/$name" > "$work/${name}-cache.jsonl"
  OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE OZAMX_WORKSPACE_CACHE_BYTES=0 "$work/$name" > "$work/${name}-cache0.jsonl"
done

python3 - "$work" "$summary" "$default_lib" "$candidate_lib" "$repo" << 'PY'
import hashlib, json, pathlib, sys

work = pathlib.Path(sys.argv[1])
summary = pathlib.Path(sys.argv[2])


def compare(a, b):
    count = 0
    slots = 0
    with (work / a).open() as fa, (work / b).open() as fb:
        while True:
            la = fa.readline()
            lb = fb.readline()
            if not la and not lb:
                break
            if not la or not lb:
                raise SystemExit(f"row count differs: {a} vs {b}")
            x = json.loads(la)
            y = json.loads(lb)
            if x.get("case") != y.get("case"):
                raise SystemExit(f"case differs at row {count}")
            for key in ("m", "n", "k", "ldc", "budget", "output_slots"):
                if x.get(key) != y.get(key):
                    raise SystemExit(f"{key} differs for {x['case']}")
            if x.get("guards_ok") is False or y.get("guards_ok") is False:
                raise SystemExit(f"oracle/padding/overflow check failed at {x['case']}")
            if x["case"] == "fp32_overflow_transaction":
                if not (
                    x.get("threw")
                    and x.get("c_unchanged")
                    and y.get("threw")
                    and y.get("c_unchanged")
                ):
                    raise SystemExit("overflow must throw and leave C unchanged")
            # 小矩阵逐项比特串、大矩阵全输出摘要，覆盖不同缓存模式的完整结果。
            if x.get("bits") != y.get("bits") or x.get("output_digest") != y.get("output_digest"):
                raise SystemExit(f"bitwise mismatch: {x['case']}")
            count += 1
            slots += x.get("output_slots", 0)
    if count != 47:
        raise SystemExit(f"expected 47 case records, found {count}")
    return {"cases": count, "compared_slots": slots, "bitwise_mismatches": 0}


# 四组两两比较把缓存开关和库版本的影响分开核对。
checks = {
    "default_cache_vs_cache0": compare("default-cache.jsonl", "default-cache0.jsonl"),
    "candidate_cache_vs_cache0": compare("candidate-cache.jsonl", "candidate-cache0.jsonl"),
    "default_vs_candidate_cache": compare("default-cache.jsonl", "candidate-cache.jsonl"),
    "default_vs_candidate_cache0": compare("default-cache0.jsonl", "candidate-cache0.jsonl"),
}
summary.parent.mkdir(parents=True, exist_ok=True)
summary.write_text(
    json.dumps(
        {
            "status": "pass",
            "seed": "0x8454a11ce",
            "shapes": [
                [1, 17, 31],
                [7, 33, 33],
                [17, 65, 257],
                [65, 129, 65],
                [256, 256, 256],
                [512, 512, 512],
                [256, 512, 256],
                [512, 256, 512],
                [1024, 1024, 1024],
            ],
            "precisions": ["fp32", "fp64-p6", "fp64-p10", "fp64-p15", "fp64-p21"],
            "checks": checks,
            "libraries": {
                "default": {
                    "path": sys.argv[3],
                    "sha256": hashlib.sha256(pathlib.Path(sys.argv[3]).read_bytes()).hexdigest(),
                },
                "candidate": {
                    "path": sys.argv[4],
                    "sha256": hashlib.sha256(pathlib.Path(sys.argv[4]).read_bytes()).hexdigest(),
                },
            },
            "source_sha256": {
                "driver": hashlib.sha256(
                    (pathlib.Path(sys.argv[5]) / "tests/extended_validation.cpp").read_bytes()
                ).hexdigest(),
                "runner": hashlib.sha256(
                    (pathlib.Path(sys.argv[5]) / "bench/run_extended_validation.sh").read_bytes()
                ).hexdigest(),
            },
            "scope": "nine rectangular cases, aligned 256/512 and 1024-cubed boundaries; padded A/B/C strides and tail canaries; full long-double oracle for small cases and 32 sampled C outputs per large case; FP32 overflow and FP64 invalid-input transactional checks; separate default and zero-byte cache processes; 128-bit deterministic digests compare every large-case output slot.",
        },
        indent=2,
    )
    + "\n"
)
print(json.dumps(checks, sort_keys=True))
PY
