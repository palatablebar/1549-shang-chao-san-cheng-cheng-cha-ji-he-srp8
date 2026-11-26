# 商超散称称差稽核验证目录

AI/ML · 传统ML · 中型

修改业务链路时先检查受影响模块的测试，再运行整套 `pytest`。回归记录须能够定位到具体单据或计算值。

## 功能模块

| 编号 | 功能 | 核对内容 | 核心文件 | 独立测试 |
|---|---|---|---|---|
| M1 | 称重签 | 单据版次与隔离 | `src/weighttally/scale_slips/service.py` | `tests/test_scale_slips.py` |
| M2 | 扣皮版次 | 截止日和成熟标签 | `src/weighttally/tare_versions/service.py` | `tests/test_tare_versions.py` |
| M3 | 称差因素 | 原始数据到特征 | `src/weighttally/variance_context/service.py` | `tests/test_variance_context.py` |
| M4 | 扣皮异常 | 训练及可重复推断 | `src/weighttally/tare_deviation/service.py` | `tests/test_tare_deviation.py` |
| M5 | 称差回放 | 回放误差及可信区间 | `src/weighttally/basket_backtest/service.py` | `tests/test_basket_backtest.py` |
| M6 | 秤台分组 | 差异定位和外推审查 | `src/weighttally/store_mix/service.py` | `tests/test_store_mix.py` |
| M7 | 复秤分派 | 硬规则与额度分配 | `src/weighttally/bench_reweigh/service.py` | `tests/test_bench_reweigh.py` |
| M8 | 称差结算 | 单据及额度证据 | `src/weighttally/weigh_journal/service.py` | `tests/test_weigh_journal.py` |

## 深度登记

| 编号 | 边界 | 判断 | 处理位置 | 测试定位 |
|---|---|---|---|---|
| TRAP-14 | 同版不同读数 | 两条都隔离，换序结论一致 | `src/weighttally/scale_slips/service.py` | `tests/test_scale_slips.py::test_conflicting_same_version_is_order_independent` |
| TRAP-19 | 多个规则或外推标记重叠 | 硬约束优先，保留全部命中码 | `src/weighttally/bench_reweigh/service.py` | `tests/test_bench_reweigh.py::test_hard_rule_precedes_outside_reference` |
| TRAP-23 | 标签落在窗口的终点 | 终点进入隔离段，窗口为半开区间 | `src/weighttally/tare_versions/service.py` | `tests/test_tare_versions.py::test_half_open_days` |
| TRAP-32 | 大偏移细方差与常数列 | 中心化后累加，常数列尺度为一 | `src/weighttally/variance_context/service.py` | `tests/test_variance_context.py::test_cancellation_safe_scaling` |
| TRAP-42 | 拟合窗口后才回传结果 | 依标签成熟时间屏蔽，未来数据不参与拟合 | `src/weighttally/tare_versions/service.py` | `tests/test_tare_versions.py::test_mature_label_cannot_cross_partition` |
| TRAP-43 | 回放没有成熟记录 | 记录未定义状态，避免以零误差替代 | `src/weighttally/basket_backtest/service.py` | `tests/test_basket_backtest.py::test_no_outcome_gets_undefined_metrics` |
| TRAP-44 | 校准样本不足 | 分派前转人工判读并保留原因 | `src/weighttally/basket_backtest/service.py` | `tests/test_basket_backtest.py::test_empty_calibration_requires_review` |
| TRAP-53 | 单条推断与混批 | 复用冻结参数，各条估计完全一致 | `src/weighttally/tare_deviation/service.py` | `tests/test_tare_deviation.py::test_input_batch_invariance` |
| TRAP-54 | 特征版本与模型不配对 | 拒绝继续推断并要求重拟合 | `src/weighttally/tare_deviation/service.py` | `tests/test_tare_deviation.py::test_mismatched_model_input_version_fails` |
