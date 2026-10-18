# 8454H benchmark support

clean 分支只保留当前 paired benchmark 需要的最小支持文件：

- `machine_metadata.txt`：机器信息；
- `roofline_v4/matched_calls/driver.cpp`：当前 paired benchmark 子进程驱动。

历史 CSV、checkpoint、V1–V4 归档和一次性搜索目录已从该分支移除；对应会话结论保留在 `trace/`。

当前 benchmark 请通过顶层 `bench/benchmark.cpp` 构建 `ozamx_benchmark`，并按照根 `README.md` 中的 64 线程/CPU 0–63 协议运行。

独立 raw oneMKL BF16 headroom 工具保留在 `bench/raw_bf16.cpp`，接口说明见 `bench/raw_bf16_manifest.md`。
