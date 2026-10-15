#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MKL_ROOT="$ROOT/third_party/code/mkl-2026/venv"
MKL_LIB="$MKL_ROOT/lib"
BIN="${OZAMX_RAW_BF16_BIN:-/tmp/ozamx-raw-bf16}"

# 该脚本只构建并固定亲和性运行 oneMKL 原生 BF16 参考程序。
g++ -std=c++17 -O3 -Wall -Wextra \
  -I"$MKL_ROOT/include" \
  "$ROOT/bench/raw_bf16.cpp" \
  "$MKL_LIB/libmkl_rt.so.3" \
  -Wl,-rpath,"$MKL_LIB" -ldl -o "$BIN"

export MKL_THREADING_LAYER=GNU
export LD_LIBRARY_PATH="$MKL_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec taskset -c 0-63 "$BIN" "$@"
