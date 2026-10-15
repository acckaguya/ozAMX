# 非有限检查位置实验

假设：每个AMX组件还原时的非有限分类、mask归约和标量bad依赖链占用大量指令；将检查延后到完整输出块可减少这些指令。候选不改变TDP、K块或浮点加法顺序。

依据：在当前纯加法还原中，组件的Inf或NaN一旦进入累加器，后续加法不能恢复有限值；因此最终输出块的isfinite检查仍能发现组件/还原溢出。输入非法值检查仍全部保留。需用NaN/Inf、组件overflow、抵消overflow以及C错误时不变的case验证这一推理，而不是只看随机输入checksum。

实现：隔离源树 /tmp/ozamx-late-check，用constexpr late_check=true去掉每micro/component检查，在copy到私有result前SIMD扫描完整输出块。工作树搜索参数空间不变。

验证：CTest、native审计通过；对frozen v1的100case、2322780个C槽逐位相等；额外4个FP32/FP64组件overflow与overflow后抵消case均拒绝且C不变。

测量：`../late_check/{eager_before,late,eager_after}.csv`，64核、1GiB缓存、7次重复，前后默认夹住候选。4096真call wall中位数（毫秒）：

|精度|默认前|late|默认后|
|---|---:|---:|---:|
|FP32|24.45|21.61|25.62|
|FP64 p6|47.25|44.37|44.25|
|FP64 p10|59.27|53.14|56.20|
|FP64 p15|81.01|86.41|85.19|
|FP64 p21|113.69|102.42|106.97|

分析：FP32值得复测；FP64收益不稳定，p15退化。不据单次结果全局采用。主搜索工作树未修改。可重建diff：`late_nonfinite.patch`（相对本轮参数化默认源码）。
