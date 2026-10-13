# 公开仓库文件范围

本仓库的可复核提交保留项目源码、测试、构建说明、论文研读与复现规格、正式测量CSV及checkpoint、精度诊断数据、PNG/PDF图表、manifest和必要来源登记。它保留40个主配置、18个线程配置、8个raw BF16配置对应的原始计时CSV与统计；本地诊断导出数据也保留校验和及native结果；这些输入随仓库提供，可在 `bench/diagnostics/*/` 用对应校验文件验证。该发布清单是源码与科学结果的精简包，不是本地运行环境或所有执行产物的完整归档。复跑流程见README与 `bench/` 下脚本。

论文 `third_party/papers/2609.04663v1.pdf` 约247 KB；来源登记记录其 arXiv 页面声明 CC BY 4.0，并保留版本、来源URL和归属信息。Intel ISA手册的来源和许可证说明保留在 `third_party/intel/SOURCES.md`，手册PDF本身不随仓库分发。

公开包不包含本地 `third_party/code/mkl-2026/venv`、PDF工具环境、`build/`、冻结/诊断可执行文件、Python缓存、pilot数据、旧污染数据、运维日志及额度、代理、账号或systemd状态。oneMKL需要依照 `third_party/SOURCES.md` 的版本、来源和安装命令在本机单独取得；PDF检查工具亦需单独安装。benchmark和native诊断可由所含源码与构建命令重新生成。`FULL_SWEEP_MANIFEST.json` 中记录的冻结二进制SHA仅用于说明计时执行文件身份，该二进制不纳入仓库。该manifest还列出本地执行时的日志路径与CTest日志哈希；日志本身因属运行期产物而不上传，测试摘要保留在结果报告。

`REPRODUCTION_TRACE.md`、`CAMPAIGN_STATE.md`、`QUOTA_*`及服务状态文件属于本地恢复/额度操作记录，不是科学复现材料，因此不公开。结果报告只保留必要的方法、计时和数据有效性说明。
