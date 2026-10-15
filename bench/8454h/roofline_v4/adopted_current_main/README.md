# Adopted current main source snapshot

This is a standalone source snapshot of the validated current main candidate. It is kept inside the V4 search experiment archive as an adopted candidate, not as a production-release declaration. Source provenance and guard scope are in `SOURCE_IDENTITY.json` and `guard_domain.json`; exact validated OpenMP and no-OpenMP libraries are in `artifacts/`; test and gate status is in `verification_status.json`. Full raw validation data, build commands and logs remain in the sibling `production_validation_runs/main_current_20261014` source tree in the parent repository and are included separately in the round archive.

Build the OpenMP source with `cmake -S source -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DOZAMX_BUILD_PROBE=OFF`, then `cmake --build build` and `ctest --test-dir build --output-on-failure`. Use `-DOZAMX_ENABLE_OPENMP=OFF` for the no-OpenMP configuration. The optional oneMKL benchmark target requires an externally supplied oneMKL tree through `-DOZAMX_ONEMKL_ROOT`; third-party runtimes are not embedded.

An isolated package-source build check used a separate `/tmp` build tree without oneMKL, built all available targets, passed all three CTests, and reproduced the packaged OpenMP library hash exactly. Commands, compiler database, CMake cache and logs are preserved under `validation/package_build_check/`.
