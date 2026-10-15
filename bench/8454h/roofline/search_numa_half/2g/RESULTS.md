# NUMA partial-B 2G search

The isolated `OZAMX_NUMA_PARTIAL_B=1` candidate copies only each node's remote packed-B half. On node 0 it copies the second half; on node 1 it copies the first. Compute selects the source by the actual packed offset. This run used the 64-thread pinned setup and paired frozen V2 runs shown in `run_manifest.json`; no measured sample was discarded. All six configurations had exact checksums against frozen V2 (`status=pass`).

| Size | Precision/budget | API wall delta | Compute delta | Copy median (ms) | Peak RSS delta (MiB) | Minor-fault delta |
|---:|---|---:|---:|---:|---:|---:|
| 4096 | fp32 p6 | +4.2% | +1.1% | 1.15 | +99 | +0 |
| 4096 | fp64 p6 | +10.9% | +10.7% | 1.21 | +86 | +0 |
| 4096 | fp64 p21 | -5.1% | -3.1% | 2.47 | +192 | +1675 |
| 8192 | fp32 p6 | +0.8% | -2.9% | 4.41 | +512 | +0 |
| 8192 | fp64 p6 | -1.7% | -5.1% | 4.82 | +508 | +189 |
| 8192 | fp64 p21 | +20.5% | -3.3% | 21.34 | +448 | +206962 |

Across six configurations, paired pooled API wall median delta was +2.50% (2/6 faster); compute median delta was -3.00%. The 2 GiB run's 8192 FP64 p21 samples showed a 20.5% wall regression alongside about 207k additional minor faults, while 4 GiB p21 was +3.6%; this is a noisy capacity/fault-sensitive result, not evidence of a stable slowdown cause. In both capacities partial replication reduced copy time and RSS versus full-replica NUMA-B, but did not establish a general API-throughput win.

Copy time is included in pack time, so the two timing columns are not additive. RSS is process `ru_maxrss` peak, not per-call allocation. Raw repetitions, full checksums, paired comparisons, source/build artifacts, and exact commands are retained here.
