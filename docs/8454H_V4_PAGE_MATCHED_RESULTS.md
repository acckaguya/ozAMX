# V4 page-layout matched-call results

Campaign `/home/caiweili/ozAMX/bench/8454h/roofline_v4/page_layout_matched_runs/page_matched_runtime_20261014T123536Z` completed 20 matched configurations with 11 alternating pairs each. No additional numerical gate was run: both candidate archives were checked against their exact SHA-256 and the prior full 20-case V3 gate records.

Frozen V3 library SHA-256: `73f0764610072b05a3e50afb8ce312fe6b717c361efef7b94e52f20bde63b42c`. Runtime runner: `/home/caiweili/ozAMX/bench/8454h/roofline_v4/matched_calls/run_matched_runtime.py` (SHA `981787dba57cf8e5d8f6c15b08381c14f0d38c9f289b734bd53ed564d87b1317`); driver source SHA `5cd6bfb93d4c42ef6865c8fbf890927388430c1a231aae08a1a9ce31261ddfac`.
The harness used GNU OpenMP runtime-default wait settings by unsetting `OMP_WAIT_POLICY` and `GOMP_SPINCOUNT`, with its 20 ms parent pause after each API call. Each child reported actual team size 64, and all 64 workers occupied CPUs 0–63 exactly once. For every pair, the deterministic A/B input FNV hashes matched; each final full C buffer had the same byte count and SHA-256 across V3 and candidate. These checks are repeated in each raw journal.

Ratios below are candidate/V3, so values under 1.0 favor the page candidate. `Mean pair ratio` is the arithmetic mean of the 11 individual ratios; `ratio of means` divides the arithmetic mean candidate wall by the arithmetic mean V3 wall. Median, means, per-repetition values, phase timing, order and hashes are retained. No outlier filtering was applied.

| Candidate | Configurations | API paired-call median ratio | API mean paired ratio | API ratio-of-means | Configurations faster by median |
|---|---:|---:|---:|---:|---:|
| `a2m_hint1` | 15 (165 pairs) | 0.9848 | 0.9766 | 0.8558 | 8/15 |
| `a4k_hint1` | 5 (55 pairs) | 0.9647 | 0.9452 | 0.8905 | 4/5 |

## Per-configuration API, phase and order ratios

Times are milliseconds in the JSON raw arrays. `API mean / median ratio` show both center summaries of paired candidate/V3 ratios; `API ratio-of-means` is separate. Order effects report second-position median divided by first-position median for each child.

| Candidate | Workload | N | API mean ratio | API median ratio | API ratio-of-means | Split ratio | Pack ratio | Compute/reconstruct ratio | Profile total ratio | Control second/first | Candidate second/first | Output SHA equal |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `a2m_hint1` | fp32 | 1024 | 1.0640 | 1.0585 | 0.8376 | 1.1958 | 1.6146 | 1.0544 | 1.0652 | -15.7% | -2.4% | yes |
| `a2m_hint1` | fp32 | 4096 | 1.0624 | 1.0783 | 1.0190 | 1.0781 | 1.0237 | 1.0676 | 1.0624 | -10.0% | +38.4% | yes |
| `a2m_hint1` | fp32 | 8192 | 1.0157 | 0.9977 | 0.9919 | 1.2871 | 1.4171 | 0.9959 | 1.0157 | +0.3% | +7.1% | yes |
| `a2m_hint1` | fp64 p6 | 1024 | 1.0080 | 1.0116 | 1.0037 | 0.9722 | 3.5736 | 1.2360 | 1.0081 | -4.4% | -6.6% | yes |
| `a2m_hint1` | fp64 p6 | 4096 | 1.0147 | 1.0189 | 0.9908 | 0.9436 | 0.9716 | 1.0600 | 1.0147 | -0.7% | +3.5% | yes |
| `a2m_hint1` | fp64 p6 | 8192 | 0.9832 | 1.0071 | 0.9502 | 0.9767 | 1.3791 | 1.0023 | 0.9832 | +6.3% | -2.7% | yes |
| `a2m_hint1` | fp64 p10 | 1024 | 0.9735 | 0.9648 | 0.9687 | 0.9786 | 4.3196 | 0.9694 | 0.9735 | -10.2% | -6.5% | yes |
| `a2m_hint1` | fp64 p10 | 4096 | 1.0081 | 1.0089 | 0.9476 | 1.0216 | 1.5671 | 1.0207 | 1.0081 | -0.5% | -3.2% | yes |
| `a2m_hint1` | fp64 p10 | 8192 | 0.8774 | 0.9373 | 0.7226 | 1.0756 | 1.5585 | 0.8617 | 0.8774 | -5.9% | +20.6% | yes |
| `a2m_hint1` | fp64 p15 | 1024 | 0.9477 | 0.9582 | 0.9046 | 0.9662 | 0.7785 | 0.9874 | 0.9477 | -5.8% | +1.2% | yes |
| `a2m_hint1` | fp64 p15 | 4096 | 0.9181 | 0.8778 | 0.8196 | 0.8968 | 0.4455 | 0.9423 | 0.9180 | +23.9% | -3.2% | yes |
| `a2m_hint1` | fp64 p15 | 8192 | 0.9284 | 0.9831 | 0.8439 | 1.1624 | 0.6346 | 0.9066 | 0.9284 | +32.0% | -6.6% | yes |
| `a2m_hint1` | fp64 p21 | 1024 | 1.0735 | 1.0629 | 1.0672 | 1.0660 | 3.5224 | 1.1565 | 1.0736 | +2.1% | -3.9% | yes |
| `a2m_hint1` | fp64 p21 | 4096 | 0.8391 | 0.8352 | 0.6928 | 0.8933 | 0.6350 | 0.8502 | 0.8391 | +64.5% | -43.7% | yes |
| `a2m_hint1` | fp64 p21 | 8192 | 0.9354 | 0.9228 | 0.9259 | 1.0301 | 0.6962 | 0.9278 | 0.9354 | +0.8% | -4.3% | yes |
| `a4k_hint1` | fp32 | 8192 | 0.9396 | 0.9105 | 0.9123 | 0.9218 | 1.2222 | 0.9472 | 0.9396 | -2.4% | -19.7% | yes |
| `a4k_hint1` | fp64 p6 | 8192 | 0.9312 | 0.9380 | 0.9216 | 1.0446 | 0.6237 | 0.9111 | 0.9312 | +12.7% | -0.7% | yes |
| `a4k_hint1` | fp64 p10 | 8192 | 1.0311 | 1.0298 | 1.0291 | 1.0131 | 0.8014 | 1.0382 | 1.0311 | -2.4% | +1.3% | yes |
| `a4k_hint1` | fp64 p15 | 8192 | 0.9409 | 0.9647 | 0.9059 | 1.0361 | 0.9321 | 0.9372 | 0.9409 | +3.9% | -0.5% | yes |
| `a4k_hint1` | fp64 p21 | 8192 | 0.8832 | 0.9075 | 0.7994 | 1.0423 | 0.7317 | 0.8766 | 0.8832 | -1.1% | -5.3% | yes |

## Observations

At N=8192, `a4k_hint1` had lower median paired API ratios in 4/5 workloads; p10 was slower (median ratio 1.0298). `a2m_hint1` was faster by per-configuration median in 8/15 configurations across N=1024/4096/8192. This is a provisional pattern for root’s next decision, not evidence to merge.
Across all matched pairs, `a2m_hint1` API median paired ratio / mean paired ratio / ratio-of-means were 0.9848 / 0.9766 / 0.8558; `a4k_hint1` was 0.9647 / 0.9452 / 0.8905. Their ratio-of-means differs materially from paired-call summaries, so it should not stand alone.
Order effects are material, especially for `a2m_hint1`: across its configurations the control’s second/first median ranged from -15.7% to +64.5%, and the candidate ranged from -43.7% to +38.4%. For `a4k_hint1`, the corresponding ranges were -2.4% to +12.7% and -19.7% to +1.3%. Treat individual ratios and aggregate mean/median divergence with that variability in view. The previous screen also had large initial/final control drift; this runtime-default matched run is a separate wait policy and must be interpreted on its own.

The complete per-call phase and API timing vectors and order sequence are in [`summary.json`](summary.json) and each raw `matched_calls.json` journal. This screen is descriptive: `a2m_hint1` covers N=1024/4096/8192 (15 configurations), while `a4k_hint1` covers N=8192 only (5 configurations). The library and previous gate identities are:

- `a2m_hint1`: [`/home/caiweili/ozAMX/bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/libozamx.a`](../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a2m_hint1/libozamx.a), SHA-256 `91ce6bdf48976cc5f9a60db6b15f7861547099060341fc9a57bc6652aa9fbfd4`; prior gate `/home/caiweili/ozAMX/bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a2m_hint1_full.json` SHA `4efa6cc3a6e0ea4789a62c8dda2b306082dd0a4c8c2a9020d9c9d9ea5f749796`, status `pass` with 20/20 cases.
- `a4k_hint1`: [`/home/caiweili/ozAMX/bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/libozamx.a`](../bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/builds/a4k_hint1/libozamx.a), SHA-256 `dbec090534a1c920ebc533e4a5394c1a0a7b83582526ea1d7362f9f43face1af`; prior gate `/home/caiweili/ozAMX/bench/8454h/roofline_v4/search_runs/page_layout_20261014T121831Z/gates/a4k_hint1_full.json` SHA `b497e86e994e34606efea76426ed21ad6722ac67ad5997f5b5b1f395c2d715dc`, status `pass` with 20/20 cases.

The prior short screen showed major initial/final V3 drift, and this runtime-default matched protocol is a distinct wait policy. Interpret results under this exact protocol only. A stable API-wall gain is required before changing the allocator default; this report does not recommend merging a candidate. The run includes no PMU/system traffic attribution. No THP or NUMA system setting was changed.
