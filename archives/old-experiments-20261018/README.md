# Old experiment archive (2026-10-18)

This directory preserves local, ignored experimental artifacts that were not part of the clean source branch. It is intentionally an archive, not active project code.

Source worktree: `/home/caiweili/ozAMX`
Archived from branch context: `codex/strict-clean` / `codex/strict-smalln-c1`

| Archive | Contents |
|---|---|
| `paper-alignment.tar.zst` | `bench/8454h/paper_alignment/` strict campaign logs and checkpoints |
| `versions.tar.zst` | old V1/V2/V3/V4 release and source archives |
| `roofline-v4.tar.zst` | `bench/8454h/roofline_v4/` run directories and driver context |
| `roofline-other.tar.zst` | roofline/mkl diagnostics, local cleanup, V3 paper alignment, P4 microbench |
| `trace-and-audit.tar.zst` | local `trace/` collaboration records and `docs/audit/` leftovers |

`third_party/` is intentionally excluded: the paper and Intel official materials remain in the active clean branch. Teaching-only local files are also excluded.

Extract from repository root with:

```sh
tar --zstd -xf archives/old-experiments-20261018/paper-alignment.tar.zst
```

Verify integrity with:

```sh
(cd archives/old-experiments-20261018 && sha256sum -c SHA256SUMS)
```
