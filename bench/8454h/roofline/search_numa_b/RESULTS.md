# NUMA B replication, 4 GiB workspace

This is the first performance pass for the isolated `OZAMX_NUMA_REPLICATE_B=1` candidate. Production sources were not changed. The frozen reference was the actual `/tmp/ozamx-production-final/ozamx_optimization_benchmark` binary (SHA256 `eece364647b16906862dd0820a46f08ad62b53a0275dde29a9e1fae097d59893`) with its frozen library SHA256 `ddfe885c2ba58089accd4e747aecb53a18422554e06fc409965e2f47b7d92251`. Candidate and macro-off control drivers were both compiled against the isolated clone's `include/ozamx/gemm.hpp`, matching their respective libraries and the added `GemmTimings` fields.

The full locked sequence was frozen A, macro-off control, NUMA A, frozen B, NUMA B, frozen C. Each process ran 4096 and 8192, FP32 and FP64 p6/p21, 64 threads, one warmup and five measured repetitions, with a 4 GiB workspace cache. Launch used `taskset -c 0-63`, `OMP_PLACES=cores`, `OMP_PROC_BIND=close`, and `OMP_DYNAMIC=FALSE`. Every measured row was retained; medians use all five repetitions. The raw CSVs include per-call `getrusage` fault/context-switch/user/system deltas and process high-water RSS. The complete command, environment, file hashes and source hashes are in `run_manifest.json`.

| Shape / precision | API wall delta vs adjacent frozen | Compute delta | Copy median | NUMA vs macro-off wall |
|---|---:|---:|---:|---:|
| 4096 FP32 | +3.1% (+0.64 ms) | -10.8% (-1.88 ms) | 2.53 ms | +4.5% |
| 4096 FP64 p6 | -0.5% (-0.17 ms) | -11.1% (-2.58 ms) | 2.68 ms | +1.6% |
| 4096 FP64 p21 | +13.4% (+10.14 ms) | -2.5% (-1.63 ms) | 5.62 ms | +5.8% |
| 8192 FP32 | -4.6% (-8.49 ms) | -10.7% (-17.99 ms) | 10.73 ms | -5.3% |
| 8192 FP64 p6 | -2.3% (-5.94 ms) | -7.8% (-16.29 ms) | 11.58 ms | -4.0% |
| 8192 FP64 p21 | -5.8% (-35.58 ms) | -10.4% (-59.17 ms) | 22.44 ms | -10.3% |

Across the six configurations, NUMA vs adjacent frozen improved compute time in all six (median -10.55%, median absolute change -9.43 ms), while whole API wall improved in four (median -1.42%, median absolute change -3.05 ms). The 8192 cases all improved in API wall; the 4096 group was mixed, with FP64 p21 regressing materially. Against the macro-off control, pooled NUMA wall median was -1.20% and improved in three of six configurations. The macro-off control itself was +1.25% wall median versus frozen, which is a reminder to use the neighboring frozen runs when reading the small 4096 deltas.

The copy-team stage was consistently placed: all measured calls reported 32 node-0 and 32 node-1 workers, with zero getcpu fallbacks. `replicate_b_s` isolates the copy body; allocation and copy are both included in `pack_s`. The frozen direct split/pack path reports near-zero pack time because its work is in `split_s`, so pack percentage changes are not meaningful. In absolute terms the added pack stage has an across-configuration median of about 8.18 ms, while isolated copy median is 8.18 ms; do not add those two numbers. The compute savings exceed copy cost for the 8192 cases, while 4096 FP32 and p21 do not show a whole-call win.

The candidate's median per-configuration process high-water RSS was 786,572 KiB higher than frozen (about 42%). At 8192 FP64 p21 the recorded peak was about 6220 MiB versus 4301 MiB frozen. This is consistent with retaining the original packed B plus two replicas, on top of input/output and workspace storage. `max_rss_kib` is process-wide `ru_maxrss`, not a per-call RSS delta.

All variant checksums matched exactly across the six configurations (`comparison.json`, zero checksum issues). The initial report is mixed and size-sensitive; it supports a targeted 8192 follow-up, not a claim of a universal win. No 2 GiB run was performed.
