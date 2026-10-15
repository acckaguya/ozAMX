# Late non-finite check candidate

The variant defers exceptional-value checking until after the common finite-value work. The isolated benchmark sweep and validation artifact are retained, but measured ordinary-workload changes are mixed and do not justify adopting it by themselves. Validation includes the archived non-finite/overflow probes and the frozen-v1 corpus described in `experiment_metadata.json`.

See [late_nonfinite.patch](late_nonfinite.patch), [late_nonfinite_check.md](late_nonfinite_check.md), and the per-config summaries in `comparison.json`.
