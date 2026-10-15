#!/usr/bin/env bash
# Historical Gold campaign maintenance; paths and result names are archival.
# Current 8454H measurements use run_8454h_baseline.sh and bench/8454h/.
set -euo pipefail
cd /data/home/caiwl/ozAMX

if [[ "${OZAMX_FINALIZE_WAIT:-0}" == 1 ]]; then
  echo "$(date -u +%FT%TZ) WAITING_FOR_CAMPAIGN" >> docs/trace/finalize.log
  while systemctl --user is-active --quiet ozamx-campaign.service; do
    sleep 30
  done
elif systemctl --user is-active --quiet ozamx-campaign.service; then
  echo "campaign service is still active; finalization is deferred" >&2
  exit 73
fi
exec 9> bench/campaign.lock
if ! flock -n 9; then
  echo "campaign/finalization lock is held; refusing to overlap." >&2
  exit 73
fi
mkdir -p docs/trace bench/diagnostics

# Gate on all raw CSV/checkpoint coverage before any diagnostic, compiler, or plot work.
python3 tools/finalize_campaign_data.py --validate-only
python3 tools/finalize_campaign_data.py --merge-only

python3 tools/diagnose_fp64_alternative.py --self-test
if [[ ! -s bench/diagnostics/alt_256/alternative_report.json || ! -s bench/diagnostics/alt_256/metadata.json ]]; then
  alt_stage="bench/diagnostics/alt_256.stage.$$"
  alt_report_tmp="$alt_stage/alternative_report.json.tmp"
  alt_validation_tmp="$alt_stage/alternative_validation.json.tmp"
  mkdir -p "$alt_stage"
  python3 tools/diagnose_fp64_alternative.py --sizes 256 --seed 20261012 \
    --export-dir "$alt_stage" > "$alt_report_tmp"
  (cd "$alt_stage" && sha256sum -c checksums.sha256)
  python3 tools/validate_native_alternative.py --alternate-json "$alt_report_tmp" \
    > "$alt_validation_tmp"
  mv "$alt_report_tmp" "$alt_stage/alternative_report.json"
  mv "$alt_validation_tmp" "$alt_stage/alternative_validation.json"
  if [[ -e bench/diagnostics/alt_256 ]]; then
    echo "destination already exists but lacks validated alternate artifacts; refusing overwrite" >&2
    exit 73
  fi
  mv "$alt_stage" bench/diagnostics/alt_256
fi
(cd bench/diagnostics/alt_256 && sha256sum -c checksums.sha256)
python3 tools/validate_native_alternative.py \
  --alternate-json bench/diagnostics/alt_256/alternative_report.json \
  > bench/diagnostics/alt_256/alternative_validation.json.tmp.$$
mv bench/diagnostics/alt_256/alternative_validation.json.tmp.$$ \
  bench/diagnostics/alt_256/alternative_validation.json

if [[ ! -x bench/diagnostics/alt_256/native_alternative_accuracy ]]; then
  native_bin_tmp="bench/diagnostics/alt_256/native_alternative_accuracy.tmp.$$"
  g++ -std=c++17 -O3 -Wall -Wextra -march=sapphirerapids -ffp-contract=off -fopenmp \
    -Iinclude tools/native_alternative_accuracy.cpp src/runtime.cpp src/kernels.S \
    -o "$native_bin_tmp"
  mv "$native_bin_tmp" bench/diagnostics/alt_256/native_alternative_accuracy
fi
if [[ ! -s bench/diagnostics/alt_256/native_results.csv ]]; then
  native_csv_tmp="bench/diagnostics/alt_256/native_results.csv.tmp.$$"
  OMP_NUM_THREADS=64 bench/diagnostics/alt_256/native_alternative_accuracy \
    bench/diagnostics/alt_256 > "$native_csv_tmp"
  python3 tools/validate_native_alternative.py --native-csv "$native_csv_tmp" > /dev/null
  mv "$native_csv_tmp" bench/diagnostics/alt_256/native_results.csv
fi
native_validation_tmp="bench/diagnostics/alt_256/native_validation.json.tmp.$$"
python3 tools/validate_native_alternative.py \
  --native-csv bench/diagnostics/alt_256/native_results.csv > "$native_validation_tmp"
mv "$native_validation_tmp" bench/diagnostics/alt_256/native_validation.json

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DOZAMX_ENABLE_OPENMP=ON
cmake --build build -j8
OMP_NUM_THREADS=64 ctest --test-dir build --output-on-failure 2>&1 | tee docs/trace/ctest.log
grep -q '100% tests passed' docs/trace/ctest.log

# Both commands must be run with the scientific Python in the launcher PATH.
export MPLCONFIGDIR=/tmp/ozamx-mplconfig
/data/home/caiwl/miniconda3/envs/tilelang/bin/python tools/plot_campaign.py
python3 tools/finalize_campaign_data.py
echo "$(date -u +%FT%TZ) FINALIZE_COMPLETE" >> docs/trace/finalize.log
