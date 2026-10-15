# 复现环境记录

本文记录历史 Gold 6430 实验环境。当前机器是 Platinum 8454H，环境、编译选项与性能基线见 [8454H_PERFORMANCE_BASELINE.md](8454H_PERFORMANCE_BASELINE.md)。

## AMX 可用性

本机为 Intel Xeon Gold 6430（Sapphire Rapids），2 路、每路 32 核、每核 2 线程，Linux 报告 128 个逻辑 CPU。`/proc/cpuinfo` 含 `amx_tile`、`amx_bf16`、`avx512_bf16` 及 AVX-512 flags。运行时线程成功申请 `ARCH_REQ_XCOMP_PERM(XFEATURE_XTILEDATA)`；AMX BF16 点积 probe 返回预期值，因此可运行真实 AMX kernel，而非仅凭 CPUID 推断。

从项目根目录复核：

```sh
gcc -O2 -mamx-tile -mamx-bf16 tools/amx_probe.c -o /tmp/ozamx-amx-probe
/tmp/ozamx-amx-probe
```

记录输出：

```text
xcomp_perm_before=0x202e7
AMX_PERM=OK
AMX_EXEC=OK sample_c00=64.0 expected=64.0
```

历史 `ozamx_validation` 在 OpenMP 区域中由 64 个 worker 分别请求 tile permission，并逐线程运行 AMX GEMM；该次验证为 `requested=64, passed=64`。Linux 的 AMX permission 按进程有效，tile 状态缓冲按 task 独立管理；历史逐 worker 请求属于冗余检查。当前实现由调用方确认进程权限，worker 仅配置/释放自己的 tile 状态。规范与本机核验见 [AMX 指令笔记](../third_party/docs/amx-instruction-notes.md)。

## 工具链与 BLAS

- Ubuntu 22.04.5 LTS，Linux `5.15.0-164-generic`，x86_64。
- GCC/G++ 11.4.0，CMake 3.22.1，GCC OpenMP (`libgomp`) 可用；AMX 编译参数 `-mamx-tile -mamx-bf16`。
- Python 3.14.6、NumPy 2.5.2 可导入；当前环境未发现 SciPy、pytest、pybind11。Ninja、Clang 不在 PATH。
- oneMKL 2026 workspace-local 安装在 `third_party/code/mkl-2026/venv`。benchmark 运行时通过 `mkl_get_version_string` 记录版本 `Intel(R) oneAPI Math Kernel Library Version 2026.0-Product Build 20260401 for Intel(R) 64 architecture applications`，并由 `dladdr(cblas_sgemm)` 取得实际加载路径 `third_party/code/mkl-2026/venv/lib/libmkl_rt.so.3`。执行时应将该目录加入 `LD_LIBRARY_PATH`。

## 资源与限制

当前进程 affinity 与 cgroup cpuset 均为 `0-127`。`/proc/meminfo` 在检查时显示总内存 527,985,468 kB、可用 431,801,396 kB。可读取的 cgroup `memory.max` / `cpu.max` 路径未提供值，故不能据此证明没有其他调度或资源配额；全核实验使用 64 个 OpenMP 线程，但机器与论文平台不同。论文平台为 Xeon Platinum 8462Y+、Rocky Linux 9.3、oneAPI 2026.1；本机为 Xeon Gold 6430、Ubuntu 22.04、GCC 11.4、oneMKL 2026.0。

N=32768 时单个 FP64 输入矩阵约 8 GiB；两输入、输出、参考矩阵及组件/打包缓冲会显著增加峰值内存。执行最大阶数前应观察进程实际 RSS；host-wide 可用内存不能代替 job memory limit。

## 可重跑的检查命令

```sh
uname -a
lscpu
awk -F: '/^flags/{print $2; exit}' /proc/cpuinfo
cat /sys/devices/system/cpu/online
cat /sys/fs/cgroup/cpuset.cpus.effective
grep -E '^(NAME|VERSION|VERSION_ID|PRETTY_NAME)=' /etc/os-release
gcc --version
cmake --version
python3 --version
python3 -c 'import numpy; print(numpy.__version__)'
taskset -pc $$
```

本工作区 `.git` 是空目录而非有效 Git repository，因此无法提供 Git revision 或 `git status`；工作目录中的文件状态须通过文件/校验和记录确认。
