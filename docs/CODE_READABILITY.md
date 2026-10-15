# 代码排版与注释整理

2026年10月14日，对当前工作树的自有代码进行了排版整理，覆盖 `src/`、`include/`、`tests/`、`bench/` 和 `tools/` 中的47个活跃源码与脚本。第三方代码、冻结版本、历史实验数据及生成文件不在本次整理范围内。

C/C++使用4空格缩进、约100列换行，函数、循环和分支展开书写；Python采用相同缩进与行宽；shell使用2空格。汇编保留标签和指令顺序，整理宏体缩进，并说明参数寄存器与tile的用途。三个由shell执行的Python heredoc也按Python风格展开。

新增注释主要解释需要结合算法才能理解的地方：BF16舍入与极小数边界、分片及面板布局、多层分块、FP64逐产品拓宽、工作区复用、AMX权限、计时范围，以及失败时保护输出的规则。注释没有逐行复述指令。

## 如何维护相同风格

根目录的 `.clang-format`、`pyproject.toml` 和 `.editorconfig` 保存了排版约定。本次使用clang-format 18.1.8、Black 24.10.0和shfmt 3.10.0。在根目录执行以下命令可整理活跃代码；命令明确排除了冻结包和实验数据：

```sh
rg --files src include tests bench tools \
  -g '*.cpp' -g '*.hpp' -g '*.h' -g '*.c' \
  -g '!bench/8454h/**' -g '!**/versions/**' -g '!**/build*/**' \
  | xargs -r clang-format -i

for file in tools/*.py; do
  black --config pyproject.toml "$file"
done

shfmt -i 2 -ci -sr -w bench/*.sh
```

汇编和shell内嵌Python需要按各自语言检查，不能把整个文件当作普通C++或Python处理。修改内嵌代码时应保留heredoc定界符、shell变量展开方式及数据字符串。

## 本次核对结果

- 26个C/C++文件的执行token相同；长字符串改成相邻字面量时，拼接后的内容相同。
- 12个Python文件的抽象语法树相同。
- 7个shell脚本通过 `bash -n`；忽略位置和注释后，其语法树相同，内嵌Python按Python语法树核对。
- Release构建成功，基础CTest **3/3通过**。
- OpenMP静态库与整理前已验证的0.4.0库逐字节一致，SHA-256为 `7adcc98996d5a88aa21f74038a42710a28496cf601f2127c016b8e8687801b68`。
- `tools/roofline_tileloads.S`整理前后编译生成的目标文件逐字节一致。

机器可读核对记录见 [readability_checks.json](readability_checks.json)。本次没有重跑性能搜索或论文补测；算法、数值顺序和调度参数均保持原值。格式与注释会改变源码文件的哈希，历史性能报告中的源码哈希仍指当时冻结的文件，不应改写为本次文件身份。项目版本保持0.4.0。
