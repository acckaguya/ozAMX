# Interleaved matched-call benchmark

`run_matched.py` builds the same persistent child driver twice, linking one
binary to each static ozAMX archive. The parent issues one API call at a time
and alternates control-first and candidate-first order for each repetition.
Each child generates the same `std::mt19937_64(260904 + N)` FP32 or FP64
uniform input matrices. API wall time encloses the profiled call, including
workspace allocation and teardown; phase values come from `GemmTimings`.

By default, the runner uses N=1024/4096/8192, one warmup, seven timed calls,
64 threads pinned to CPUs 0–63, and a 2 GiB workspace pool. It sets
`OMP_WAIT_POLICY=PASSIVE` and `GOMP_SPINCOUNT=0` for both children to avoid
idle GNU OpenMP teams spinning between adjacent calls. These settings differ
from earlier GNU OpenMP screens using runtime defaults and are recorded in
`metadata.json`. MKL variables are also recorded and set consistently even
though neither binary uses oneMKL.

Example:

```sh
python3 bench/8454h/roofline_v4/matched_calls/run_matched.py \
  --control-lib bench/8454h/versions/v3_release/artifacts/libozamx_v3.a \
  --candidate-lib /path/to/libozamx_candidate.a --candidate-tag trial-01 \
  --result-dir bench/8454h/roofline_v4/matched_calls/results/trial-01
```

The runner holds `/tmp/ozamx-perf.lock` from before builds through validation
and sampling. It writes atomic per-sample journal checkpoints and refuses to
reuse a result directory unless `--resume` is supplied; resume requires an
identical recorded run configuration and only continues missing samples.
After the timed calls it dumps the complete C buffer from each child to a
temporary binary, streams both files through SHA-256, and requires equal byte
counts and hashes for each configuration. Failure details and compiler logs
are kept under the result directory. Output equality applies to the final
call's C buffer; the API's transaction/error behavior remains covered by the
existing independent validation gate.

For short harness smoke checks, use the V3 library on both sides with a small
N such as 32 and a fresh result directory. A heavy CPU run must hold the same
performance lock.

`run_matched_runtime.py` is a separately hashed follow-up variant for checking
runtime-default GNU OpenMP waiting. It unsets inherited `OMP_WAIT_POLICY` and
`GOMP_SPINCOUNT`, records those unset values, and inserts a 20 ms parent-side
pause after each API call; the pause is outside the child's API wall timer.
Use `--wait-policy runtime` to label that protocol explicitly. Its results do
not alter or replace the passive-wait formal campaign.
