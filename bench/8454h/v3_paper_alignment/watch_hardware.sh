#!/usr/bin/env bash
set -uo pipefail
CAMPAIGN="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUT="$CAMPAIGN/hardware_samples"
LOG="$CAMPAIGN/runner.log"
record() {
  local event="$1" key="$2" stamp file
  stamp="$(date -u +%Y%m%dT%H%M%S.%NUTC)"
  file="$OUT/${stamp}_${event}_${key}.txt"
  {
    printf 'event=%s\nconfig=%s\nutc=%s\n' "$event" "$key" "$stamp"
    echo '[proc_stat_all_cpu_lines]'
    cat /proc/stat
    echo '[cpufreq_cpu0_to_cpu63_scaling_cur_freq_khz]'
    for n in $(seq 0 63); do
      f="/sys/devices/system/cpu/cpu${n}/cpufreq/scaling_cur_freq"
      if [[ -r "$f" ]]; then printf 'cpu%s=' "$n"; cat "$f"; else printf 'cpu%s=unavailable\n' "$n"; fi
    done
    echo '[cpufreq_governor_and_policy]'
    for n in 0 1 2 3; do
      d="/sys/devices/system/cpu/cpu${n}/cpufreq"
      [[ -r "$d/scaling_governor" ]] && printf 'cpu%s_governor=' "$n" && cat "$d/scaling_governor"
      [[ -r "$d/scaling_min_freq" ]] && printf 'cpu%s_min=' "$n" && cat "$d/scaling_min_freq"
      [[ -r "$d/scaling_max_freq" ]] && printf 'cpu%s_max=' "$n" && cat "$d/scaling_max_freq"
    done
  } > "$file"
}
record campaign_midrun_capture current
cursor="$(wc -l < "$LOG" 2>/dev/null || echo 0)"
while :; do
  total="$(wc -l < "$LOG" 2>/dev/null || echo 0)"
  if (( total > cursor )); then
    while IFS= read -r line; do
      kind="${line%% *}"
      rest="${line#* }"
      key="${rest%% *}"
      case "$kind" in START|END) record "$kind" "$key" ;; esac
    done < <(sed -n "$((cursor+1)),${total}p" "$LOG")
    cursor="$total"
  fi
  if rg -q '^CAMPAIGN COMPLETE' "$LOG"; then break; fi
  sleep 0.1
done
record campaign_end complete
