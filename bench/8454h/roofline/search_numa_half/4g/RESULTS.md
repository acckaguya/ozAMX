# NUMA partial-B 4G search

The isolated `OZAMX_NUMA_PARTIAL_B=1` candidate copies only each node's remote packed-B half. On node 0 it copies the second half; on node 1 it copies the first. Compute selects the source by the actual packed offset. This run used the 64-thread pinned setup and paired frozen V2 runs shown in `run_manifest.json`; no measured sample was discarded. All six configurations had exact checksums against frozen V2 (`status=pass`).

| Size | Precision/budget | API wall delta | Compute delta | Copy median (ms) | Peak RSS delta (MiB) | Minor-fault delta |
|---:|---|---:|---:|---:|---:|---:|
| 4096 | fp32 p6 | -0.2% | +0.8% | 1.18 | +99 | +0 |
| 4096 | fp64 p6 | -0.3% | -2.3% | 1.18 | +86 | +0 |
| 4096 | fp64 p21 | +0.5% | -1.3% | 2.63 | +192 | +2664 |
| 8192 | fp32 p6 | -4.6% | -6.9% | 4.42 | +512 | +0 |
| 8192 | fp64 p6 | -0.7% | -2.6% | 4.76 | +512 | +0 |
| 8192 | fp64 p21 | +3.6% | +2.3% | 10.94 | +894 | -64724 |

Across six configurations, paired pooled API wall median delta was -0.24% (4/6 faster); compute median delta was -1.81%. The 2 GiB run's 8192 FP64 p21 samples showed a 20.5% wall regression alongside about 207k additional minor faults, while 4 GiB p21 was +3.6%; this is a noisy capacity/fault-sensitive result, not evidence of a stable slowdown cause. In both capacities partial replication reduced copy time and RSS versus full-replica NUMA-B, but did not establish a general API-throughput win.

Copy time is included in pack time, so the two timing columns are not additive. RSS is process `ru_maxrss` peak, not per-call allocation. Raw repetitions, full checksums, paired comparisons, source/build artifacts, and exact commands are retained here.
