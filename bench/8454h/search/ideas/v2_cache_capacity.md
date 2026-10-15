# v2 workspace cache capacity sweep

The selected eager-check v2 candidate was measured at N=8192 with 1, 2, and 4 GiB `OZAMX_WORKSPACE_CACHE_BYTES` caps in a five-pass order: 1G, 2G, 4G, 2G, 1G. Each 1G/2G configuration therefore pools 14 recorded reps; 4G has one 7-rep pass. The five source CSVs and complete split/pack/compute/total/wall/fault summaries are retained in `../v2_cache/`.

Median FP64 whole-call wall for p6 was 360.5 ms at 1G, 290.1 ms at 2G, and 290.2 ms at 4G. For p21 it was 886.3, 735.3, and 734.9 ms. Thus the 2G setting improves these large cases by about 17–20% against 1G, while the single 4G pass is nearly identical to 2G. This is evidence for the proposed 2 GiB default but does not establish behavior at other shapes or concurrency levels. The cap is a workspace cache limit, not a guarantee of resident memory use.
