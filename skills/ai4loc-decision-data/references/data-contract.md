# 数据合同与标注规范

每条JSONL至少包含：

```json
{"id":"sample-01","group":"heap-lifetime-a","source":"linux-build-a","split":"train","input":"BUG: KASAN: use-after-free ...","label":"memory_lifetime","evidence":"BUG: KASAN: use-after-free","reviewed_by":"reviewer-name"}
```

`input`必须是已脱敏、已选定的日志窗口，不放路径、split、答案字段或人工注入命令。`evidence`是输入中连续的首诊断证据，`reviewed_by`标明实际审核者。id/group/source/split/reviewer只进入清单，不拼入模型prompt。无法确定第一诊断时先转人工补证，不用“健康”冒充“未知”。

默认类别：memory_lifetime、memory_bounds、memory_leak、locking、blocked_task、watchdog_lockup、rcu_progress、oom、memory_protection、refcount、explicit_panic_or_warning、other_or_no_fault。

标注要点：

- KASAN/KFENCE之后看use-after-free、double-free、out-of-bounds等具体诊断；不要只凭调用栈出现某个函数就标根因。
- circular/recursive locking、sleeping while atomic等是locking；RCU应匹配`rcu:`、`INFO: rcu_`等明确边界。不能使用无边界`'rcu' in text`判断。
- 首条RCU告警与后续watchdog panic按第一诊断任务处理；注入类别另存，不能当本任务真值。
- 用同一机制在不同内核、读写变体及近似触发器下的所有案例作为同组。先冻结组划分，再做候选排列。
- 审核全部标签，抽查双人一致性；按类报告支持数，训练/开发/测试应覆盖计划交付的任务。脚本校验不是专家审核的替代品。

为训练预留足够开发样本用于选epoch和概率校准；测试不参与改prompt、选温度或改标签。不要把历史33/4/87机械复制为推荐比例。

导出文件与训练衔接：

- `dataset.private.json`：原文+label+group，哈希受冻结清单约束；不上传公开Git。
- `dataset-frozen.json`：classes/question/records/counts/label_counts/private_sha256；原文剔除，仍应按组织数据规定审查元数据。
- `validation.json`：跨集合检查、各类支持和缺类警告。缺类可以用于探索性训练，但不能宣称完整能力。

训练器每例每epoch造4次候选排列，集合大小为5/8/12（自定义类别不足时取可用数），gold在训练候选中且target索引随排列更新。评测用事先固定候选，不能依据答案为测试挑一个特别容易的集合。
