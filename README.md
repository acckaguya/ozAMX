# Intel AMX 上的 FP32/FP64 GEMM 组件积复现

本项目是对论文《BF16 Component-Product Emulation of FP32 and FP64 GEMM on Intel AMX》的独立实现与实验复现，不是作者代码的移植。它使用 Intel AMX BF16 点积实现 FP32，以及可选 6/10/15/21 个 BF16 组件积的 FP64 近似 GEMM。

## 环境

当前记录的环境支持真实 AMX tile/BF16 指令；运行探针与每线程 permission 验证见 [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)。算法及论文证据见 [docs/PAPER_STUDY.md](docs/PAPER_STUDY.md)，实现边界与复现约定见 [docs/REPRODUCTION_SPEC.md](docs/REPRODUCTION_SPEC.md)。

## 构建与验证

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DOZAMX_ENABLE_OPENMP=ON
cmake --build build -j8
OMP_NUM_THREADS=64 ctest --test-dir build --output-on-failure
```

验证覆盖真实 AMX GEMM、FP32/FP64 精度预算、尺寸边界、异常输入域及各 OpenMP worker 的 tile permission。使用本机 BLAS benchmark 时，运行 oneMKL workspace 库：

```sh
export LD_LIBRARY_PATH="$PWD/third_party/code/mkl-2026/venv/lib:${LD_LIBRARY_PATH:-}"
OMP_NUM_THREADS=64 MKL_THREADING_LAYER=GNU OMP_PLACES=cores OMP_PROC_BIND=close \
taskset -c 0-63 build/ozamx_benchmark \
  --sizes 256,512,1024,2048,4096,8192,16384,32768 \
  --threads 64 --reps 10 --precision all --distribution uniform \
  --seed 260904 --output bench/rerun_main_40.csv
```

`--reps 10` 对每个配置执行十次计时，程序另先做一次 warm-up。最大尺寸需要大量输入、输出及 BF16 临时缓冲；跑全阶数前请确认作业实际内存限制。benchmark 会将 oneMKL 的 SGEMM/DGEMM 作为参考，并记录 AMX 分段时间、端到端时间和精度指标。正式复现实验使用 [bench/run_remaining_campaign.sh](bench/run_remaining_campaign.sh)，按配置串行、设置 4 小时单配置硬超时、保留 per-repetition JSON checkpoint，并以 `bench/campaign.lock` 防止多个队列同时运行。首次运行前按上述命令在 workspace 内构建；脚本也可通过 `OZAMX_BENCH=/path/to/ozamx_benchmark` 指定等价构建。

上面的直接运行示例使用独立的 `bench/rerun_main_40.csv`，不会覆盖正式原始结果。正式实验的历史 CSV 与 checkpoint 仅供复核；若要重跑正式campaign，使用带锁的runner并设置新的输出前缀，避免覆盖或混入已记录样本。

## 目前实验状态

已完成 64 个线程的 AMX 功能验证、Table 4 的 40 个配置、FP32 线程伸缩 18 个配置及 raw BF16 的 8 个阶数；每个正式配置均通过 1 次 warm-up 和 10 次计时校验。完整原始结果、统计、论文逐项覆盖状态、误差差异与图表见 [docs/REPRODUCTION_RESULTS.md](docs/REPRODUCTION_RESULTS.md)。本机实测 AMX 端到端与 MKL GEMM-only 的比较采用不同计时范围，并按结果逐项报告，不宣称数值或性能完全匹配论文。公开包的文件选择、许可与可重算项见 [docs/PUBLICATION_PACKAGE.md](docs/PUBLICATION_PACKAGE.md)。
