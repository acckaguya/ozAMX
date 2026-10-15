# Partial packed-B replication candidate

The candidate lives in the isolated `/tmp/ozamx-roof-numa-half` clone and adds `OZAMX_NUMA_PARTIAL_B=1`. It mirrors only the remote packed-B half per node and resolves the actual packed offset at each microkernel call. Full-C bitwise equivalence passed the streamed 100-case baseline comparison at 1, 4, and 64 threads; the 47-case extended suite, native AMX audit, and CTests also passed. The 4096x4096 FP64 p6 alias trigger probe matched the control digest and observed 32 copy workers per node with no fallback.

- [4 GiB result](4g/RESULTS.md)
- [2 GiB result](2g/RESULTS.md)
- [Patch against NUMA-B](../ideas/numa_partial_b.patch)

This is an experiment only. Whole-wall medians were close to frozen V2 at 4 GiB and slower at 2 GiB; the repeatable gain is approximately halved replication copy time and lower peak RSS than full NUMA-B replication, not a general throughput win.
