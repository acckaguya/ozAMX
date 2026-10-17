# 冻结归档完整性核验

本报告只读取归档 README、对应的 `create_*` 生成脚本、顶层清单和归档成员文件；没有执行创建脚本，也没有改动归档内容。清单边界根据 README 的说明和生成器中的目标根目录、allowlist 及 manifest 写入逻辑确定。

## 顶层权威清单

| 归档 | 清单边界与格式 | 条目 | 通过 | 缺失 | 大小/哈希失配 |
|---|---|---:|---:|---:|---:|
| `bench/8454h/versions/v3_release` | README 声明 308 个仓库文件加 README；清单路径相对该归档根目录，清单不含自身 | 309 | 309 | 0 | 0 |
| `bench/8454h/versions/v3_paper_release` | README 和 `create_v3_paper_release.py` 声明 package-root 相对清单，清单不含自身 | 447 | 447 | 0 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1` | README 和 `create_v4_search_archive.py` 声明实验归档；`MANIFEST.json` 路径相对该归档根目录，`self_excluded=true` | 5,073 | 5,073 | 0 | 0 |

V3 manifest SHA-256 为 `bba4aca69c821426d61d529175f7af0738d425446f7ca38c576042b4ce697fcd`；V3 paper supplement manifest SHA-256 为 `cc0e6bab8b5f0d7785988e551d3de2a38ac056e366530b749c06d6394772e0d1`。V4 JSON 清单中的路径、字节数和 SHA-256 全部核对通过；清单外 payload 文件数和清单中不存在的路径数均为 0。V4 `freeze_info.json` 记录的 V3 manifest 与库哈希也分别和正式 V3 归档副本相同。V4 README 将自身定位为搜索实验归档，并明确 `production_release` 为 false。

## 先前 704 条 checksum 失败的归属

此前 `DOCUMENT_COVERAGE.md` 对 23 个 checksum 文件按固定归档根核验，共记录 704 条未通过。核对 README 和生成脚本后，其中 696 条来自被新归档保留为历史参考的嵌套 manifest；这些 manifest 的全部原始 payload 并未随之复制。该结果描述的是嵌套历史清单与外层归档成员边界不同，不代表相应顶层归档清单失败。

| 嵌套历史清单 | 失败条目 | 目标路径缺失 | 在外层新版本根下比较出的表面哈希失配 |
|---|---:|---:|---:|
| `bench/8454h/versions/v2_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` | 8 | 5 | 3 |
| `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2/MANIFEST.sha256` | 12 | 7 | 5 |
| `bench/8454h/versions/v3_release/repo/bench/8454h/versions/v2_release/MANIFEST.sha256` | 69 | 68 | 1 |
| `bench/8454h/versions/v3_paper_release/v3_release/MANIFEST.sha256` | 299 | 299 | 0 |
| `bench/8454h/versions/v4_roofline_search_round1/bench/8454h/versions/v3_release/MANIFEST.sha256` | 308 | 308 | 0 |
| **合计** | **696** | **687** | **9** |

因此，若按失败行字面统计，有 **687 条**指向嵌套清单所列、但没有随该历史包复制的文件；另 **9 条**在缺少对应旧版本 payload 根目录时，落到了外层新版本里同名但版本不同的文件，导致表面哈希失配。这 9 条不能用作旧 V2 快照损坏的证据。

生成方式与 README 支持这种范围区分：`create_v3_release_archive.py` 对嵌入的 V2 与 V2 release 快照仅选入 README 和 manifest；`create_v3_paper_release.py` 仅把 V3 library、选定 core 文件、README 与原 V3 manifest 放到 `v3_release/`，README 也称其为 supplement 并说明仅包含选定 core source；`create_v4_search_archive.py` 只把正式 V3 manifest 与冻结库加入 V4 package，并为 V4 自身另行生成完整的 package-root JSON manifest。

## 其余 8 条辅助哈希记录

另外 8 条并非上述 5 份嵌套旧 manifest 的成员校验：

- 6 条清单路径指向未打包的生成物或依赖：V3 source hash 文件中的 benchmark executable 与 oneMKL runtime 各 1 条；V4 diagnostic mode0–mode3 构建目录中的 `libozamx.a` 各 1 条。生成器的筛选规则排除相应构建树/依赖，V3 README 也说明 release 不包含候选 benchmark binary 和 vendor dependency。
- 2 条是 `diagnostic_src/bench/benchmark.cpp` 的历史哈希值与当前该路径内容不一致，分别记录在 `initial_source_and_freeze.sha256`、`source_and_freeze.sha256`。记录值为 `c50636e4eb5c57d0a6a60352e71697664a7ff93b7ca7f2b8ce91ed4de53913c7`，当前值为 `59a757b819bdc14385f4d9965dbeddb0675b5e7fa0290f2b879df6fdcbae47c0`。此处只记录字节差异，不推断其发生原因。

当前证据支持的结论是：三个指定顶层归档的权威清单全部通过；696 条失败来自嵌套历史 manifest 对未随包复制 payload 的引用或错误版本根上的同名路径比较。剩余 8 条是辅助哈希记录中的缺少目标/字节差异，需按记录用途解释，不据此扩展为顶层归档损坏判断。
