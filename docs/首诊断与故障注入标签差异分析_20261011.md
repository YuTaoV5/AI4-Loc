# 定界标签与注入类别的差异：PPLX 权重测试发现

2026-10-11，PPLX-Decider 专用权重测试使用现有 `stability-v1`。文件完整性仍按既有契约检查；本记录针对语义真值，不修改原始数据或得分。

## 直接观察

| 案例 | manifest 注入家族 | 工具提取的首条诊断行 | 两个模型返回 |
| --- | --- | --- | --- |
| `lkdtm_LOOP` | `watchdog` | 444：`rcu: INFO: rcu_sched self-detected stall on CPU` | `rcu_progress` |
| `lkdtm_SOFTLOCKUP` | `watchdog` | 443：`rcu: INFO: rcu_sched self-detected stall on CPU` | `rcu_progress` |

接口实际提问是 **Classify the FIRST explicit diagnostic**。因此，以 manifest 的 `watchdog` 注入类别直接评价该问题，会把“回答第一条 RCU 诊断”记为与标签不一致。这两条记录不能直接用来证明模型判断错误。

原始输入来自匿名 worker 的 `input.json`，存于 `/opt/kernel-insight/experiments/pplx-decider-20261011/workspaces/`；报告保留案例、行号和原始输入哈希。不是根据模型输出重新编造标签。

## 本轮处理

- 9 个已有 test 案例使用既有家族口径作主要回归对照。
- 25 个可映射案例的扩展结果明确称为“注入类别代理吻合度”，不冒称独立第一现场准确率。
- 上述不一致保持冻结规则下的原始记录，不事后改标签、删案例或提高分数。
- 35 个 `protection` / `refcount` 案例没有兼容的冻结家族真值，仅采集输出，`correct=null`。
- stage、reporter、因果机制和引入提交没有独立专家真值的部分不报告准确率。

## 建议的下一版标注契约（尚未执行）

将以下对象分别标注：

1. `injectedMechanism`：实验注入的机制及触发条件。
2. `firstDiagnostic`：第一现场的原始行号、agentLog 对应行号、诊断类型、报告组件及执行阶段。
3. `terminalFailure`：后续 panic、watchdog、重启等最终事件。
4. `faultOwner`：责任代码、路径和范围；与检测器位置分开。
5. `causalValidation`：复现、引入提交、修复重放及独立证据。

每条标注应带原始/脱敏日志哈希、标注依据、标注者与裁决状态。规则提取可用于候选标注，不能冒充两名独立专家的一致裁决。采用新评分口径时应新建数据集与评分版本，保留旧版本及旧得分。

这说明“423 项文件契约检查通过”和“所有目标均具有完整语义真值”是不同结论。详细实测与复现见 [PPLX 研究目录](../research/pplx-decider-20261011/)。
