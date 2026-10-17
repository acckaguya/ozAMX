# 本轮全新独立审计附件

这些程序用于回答“旧测试是否真的测到了完整正确GEMM”，没有复用仓库既有benchmark/test的生成器、计时或oracle。它们只调用公开ozAMX API以及oneMKL原生routine，不替换项目原测试，也不是生产修复。

## 1. 源码与已保存结果

- [independent_gemm_benchmark.cpp](independent_gemm_benchmark.cpp)：N128/1024/4096、dyadic与普通FP32两种输入、三种routine、一次预热和十次正式调用；已运行198次。完整API双墙钟、CPU秒、调用后输入保护、NaN poison、输出扫描/hash，dyadic完整有限域投影，小矩阵全输出整数/longdouble oracle，大矩阵普通输入512点longdouble抽样，两个负控。
- [independent_fp64_numerics.cpp](independent_fp64_numerics.cpp)：三seed、N64、四预算，GCC binary128完整点积参考；独立字面六片/三角选择/FP64重建与native共49,152个输出逐位比较。不测性能，不覆盖跨BK/Wide。
- [analyze_results.py](analyze_results.py)：仅重算已保存CSV、hash关联、挑战二进制区间和分组统计，不运行GEMM。Python标准库即可执行。
- [run_20261016](run_20261016)：原始CSV、挑战、负控、stdout/stderr、外部时间、运行身份及摘要。`checksums.sha256`针对该目录中的其他普通文件，不包含它自身。

协议、代码与结果的分别复核见 [协议](../INDEPENDENT_PROTOCOL_REVIEW.md)、[代码](../INDEPENDENT_HARNESS_REVIEW.md)、[结果](../INDEPENDENT_RESULTS_REVIEW.md)。主报告 [第8与10节](../COMPREHENSIVE_REVIEW.md) 给出结论及限制。

## 2. 编译与运行条件

以下是本次环境的复现命令，工作目录为 `/home/caiweili/ozAMX`。生产静态库在本轮从当前源码构建，SHA与冻结V4相同。`/tmp`中的产物可能随系统清理消失；重编译后应重新记录完整身份。

```bash
g++ -std=c++17 -O3 -march=sapphirerapids -ffp-contract=off -fopenmp \
  -Iinclude -Ithird_party/code/mkl-current/include \
  docs/audit/independent/independent_gemm_benchmark.cpp \
  /tmp/ozamx-audit-20261015-build/libozamx.a \
  third_party/code/mkl-current/lib/libmkl_rt.so.3 \
  -o /tmp/ozamx-audit-20261015-build/independent_gemm_benchmark
```

重跑时使用全新的输出目录，避免覆盖已保存证据。原始运行保存为`run_20261016/results.*`；下面示例改用`/tmp`目录。

```bash
mkdir -p /tmp/ozamx-independent-new-run
env -u MKL_ENABLE_INSTRUCTIONS -u MKL_CBWR -u MKL_VERBOSE -u MKL_INTERFACE_LAYER \
  LD_LIBRARY_PATH=/home/caiweili/ozAMX/third_party/code/mkl-current/lib \
  OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OMP_DYNAMIC=FALSE \
  OMP_WAIT_POLICY=PASSIVE GOMP_SPINCOUNT=0 \
  MKL_NUM_THREADS=64 MKL_DYNAMIC=FALSE MKL_THREADING_LAYER=GNU \
  OZAMX_WORKSPACE_CACHE_BYTES=2147483648 \
  flock /tmp/ozamx-perf.lock taskset -c 0-63 \
  /usr/bin/time -v -o /tmp/ozamx-independent-new-run/outer_time.txt \
  /tmp/ozamx-audit-20261015-build/independent_gemm_benchmark \
  /tmp/ozamx-independent-new-run/results 10 \
  > /tmp/ozamx-independent-new-run/stdout.log \
  2> /tmp/ozamx-independent-new-run/stderr.log
```

FP64数学对照编译用 `-O2`，保持显式类型转换和FP64求和次序：

```bash
g++ -std=c++17 -O2 -ffp-contract=off -fopenmp -Iinclude \
  docs/audit/independent/independent_fp64_numerics.cpp \
  /tmp/ozamx-audit-20261015-build/libozamx.a \
  -o /tmp/ozamx-audit-20261015-build/independent_fp64_numerics
flock /tmp/ozamx-perf.lock taskset -c 0-3 \
  /tmp/ozamx-audit-20261015-build/independent_fp64_numerics \
  > /tmp/ozamx-independent-new-run/fp64_numerics.csv \
  2> /tmp/ozamx-independent-new-run/fp64_numerics.log
```

本轮只做了上述已保存测量。文档中的复现命令不是额外一次运行记录；不应与旧campaign合并统计。

## 3. 解释结果的边界

主吞吐为`2N³/mean(CLOCK_MONOTONIC_RAW秒)/1e12`，是有效数学工作率，没有物理指令计数。两墙钟通常共享底层硬件时钟；CPU秒不是吞吐分母。

dyadic的三个全输出随机挑战有条件性漏检界≤p^-3，并非逐元素确定性证书。普通大矩阵只抽样数值误差；全输出finite和hash不是oracle。两输入族在调用间验证、改变输入和poison改变缓存/等待状态，不能将本轮时间直接拼到历史campaign。N64 FP64逐位相同不能证明大尺寸路径或所有输入正确，范数分解也没有单独隔离double重建舍入。
