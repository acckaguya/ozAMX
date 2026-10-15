#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/../../.." && pwd)
if (($# == 0)); then
  echo "usage: $0 -DNAME=VALUE [-DNAME=VALUE ...]" >&2
  exit 2
fi
for def in "$@"; do
  [[ $def == -D*=* ]] || { echo "expected -DNAME=VALUE, got: $def" >&2; exit 2; }
done
export OZAMX_CMAKE_DEFINITIONS="$*"
export OZAMX_BUILD_DIR=${OZAMX_BUILD_DIR:-$(mktemp -d /tmp/ozamx-variant.XXXXXX)}
cleanup=0
if [[ -z ${OZAMX_KEEP_VARIANT_BUILD:-} ]]; then cleanup=1; fi
trap 'if ((cleanup)); then rm -rf "$OZAMX_BUILD_DIR"; fi' EXIT
bash "$repo/bench/8454h/run_equivalence.sh"
