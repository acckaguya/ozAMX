# 8454H 优化与机器基线工件

报告见 [8454H_PERFORMANCE_BASELINE.md](../../docs/8454H_PERFORMANCE_BASELINE.md)。这些数据属于当前 Platinum 8454H，与仓库原 Gold 6430 的论文 campaign 分开保存。

| 文件 | 含义 |
|---|---|
| `before/` | 优化前核心源和公共头文件的冻结快照 |
| `final_before.csv` / `final_optimized.csv` | 同驱动、同输入、64 物理核的 256/1024/4096 匹配测试 |
| `final_before_8192.csv` / `final_optimized_8192.csv` | 同协议的 8192 扩展；含较大离散样本，未删减 |
| `supplemental_default_8192.csv` / `supplemental_cache4g_8192.csv` | 新版自身的 1 GiB/4 GiB 工作区容量比较 |
| `platform_baseline.csv` | 校正并经反汇编验证的 AVX-512、AMX、内存微基线 |
| `platform_instruction_audit.txt` | 真实循环指令数、编译命令和计数定义 |
| `final_run_metadata.txt` / `machine_metadata.txt` | 测量命令、源码指纹和机器信息 |
| `validation_results.json` | CTest、原生组件审计、旧版/新版逐位比较记录 |
| `baseline_original.csv` | 最初使用不同输入重复的历史采集；不得与固定输入结果相除 |

从仓库根目录重新测量（结果写入新的时间戳目录）：

```sh
bash bench/run_8454h_baseline.sh --sizes 256,1024,4096 \
  --threads 64 --reps 5 --budgets 6,10,15,21
bash bench/run_8454h_baseline.sh --hardware
OZAMX_WORKSPACE_CACHE_BYTES=4294967296 bash bench/run_8454h_baseline.sh \
  --sizes 8192 --threads 64 --reps 5 --budgets 6,10,15,21
```

所有构建和测量由 `/tmp/ozamx-perf.lock` 串行保护。默认 CPU 0–63 在本机对应 64 个物理核，换机器时须重新核对，并用 `OZAMX_CPUSET` 指定。锁不能保证宿主机独占。

独立复现逐位等价性（自动从冻结源构建旧版、临时构建新版）：

```sh
bash bench/8454h/run_equivalence.sh
```

基准 CSV 的 `warmup` 是配置首轮，不能等同于冷进程；五条 `rep` 才进入 summary。标准差为总体标准差，`sum(C)` 只用于配对复核。逐元素正确性由单独的 100 case 验证驱动覆盖，包含带符号零及 C padding。
