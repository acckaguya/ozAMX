# 本次执行的 CPU quota 可见性检查

此检查属于历史 Gold 实验环境，路径和计数器不能代表当前 8454H 会话。当前机器快照与测量条件见 [8454H_PERFORMANCE_BASELINE.md](8454H_PERFORMANCE_BASELINE.md)。

检查日期：2026-10-12 UTC。只读取 cgroup 元数据和计数器，没有运行压力测试，也没有改变线程数、affinity 或基准配置。

## 路径和控制器

本进程 `/proc/self/cgroup` 为 `0::/user.slice/user-19714.slice/session-37530.scope`。环境 worker 报告其 benchmark task 的 cgroup 路径相同；当前容器中看不到该 benchmark 的 host PID，因此只能核对共享路径，不能把以下差值专门归因于 benchmark。

`/proc/self/mountinfo` 显示唯一 CPU cgroup 挂载为 cgroup v2：挂载根 `/`，挂载点 `/sys/fs/cgroup`，当前以只读方式暴露。没有 cgroup v1 CPU/cpuacct 挂载。沿当前 cgroup 到可见根只检查了以下层级：

| 层级 | `cgroup.controllers` | `cpu.max` | `cpu.stat` 节流项 |
|---|---|---|---|
| `/sys/fs/cgroup` | 含 `cpu` | 不可读/不存在于根层 | `nr_periods=0`, `nr_throttled=0`, `throttled_usec=0` |
| `/sys/fs/cgroup/user.slice` | 含 `cpu` | `max 100000`，quota 无限 | `nr_periods=0`, `nr_throttled=0`, `throttled_usec=0` |
| `/sys/fs/cgroup/user.slice/user-19714.slice` | 仅 `memory pids` | 不可读/不存在；本层没有启用 CPU controller | 只有 usage 计数，没有 throttling 字段 |
| `/sys/fs/cgroup/user.slice/user-19714.slice/session-37530.scope` | 仅 `memory pids` | 不可读/不存在；本层没有启用 CPU controller | 只有 usage 计数，没有 throttling 字段 |

以约 10 秒间隔读取 `cpu.stat`，session scope 的 `usage_usec` 从 `26,169,172,743` 增至 `26,917,504,983`，差值为 `748,332,240` µs，折算该 scope 全部任务约 74.83 CPU cores 的平均用量。user slice 的差值为 `748,352,329` µs，约 74.84 cores；可见 cgroup 根及 `/user.slice` 的 `nr_throttled`/`throttled_usec` 均仍为 0。该高用量计数是整个 cgroup 中所有进程的累计，不等于单个 GEMM 的独占用量或可用核数。

## 结论与边界

在可见层级内，`/user.slice` 明确为 `cpu.max=max`，`user-19714.slice` 和 session scope 没有启用 CPU controller，未发现 16-core 或其他有限 CPU quota 的证据；可见的 throttle counters 也没有显示节流。不能据此断言整个宿主机没有更外层配额、虚拟机调度限制或其他资源管理器约束：当前容器只读暴露 cgroup v2 挂载，benchmark host PID 不可见，外部管理器状态不在 `/proc`/该挂载的可见数据中。因此性能报告应把“可见 cgroup 层级无有限 quota 证据”与“宿主机无任何 quota”区分开来。

此前确认的 CPU 0–63 affinity 覆盖 64 个不同物理 core ID；本次没有重新扫描或改变 affinity。cgroup 的 aggregate usage 在采样区间内接近 75 cores，表明共享层级有并发 CPU 活动，不能把 CPU 0–63 理解为基准进程独占的 64 个核心。
