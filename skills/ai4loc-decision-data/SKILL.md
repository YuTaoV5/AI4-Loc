---
name: ai4loc-decision-data
description: Prepare reviewed kernel first-diagnostic decision training data, labels and mechanism-isolated splits for AI4Loc; validate the data contract and export a new training run directory. Use for dataset preparation and label checks before Qwen decision fine-tuning.
---

# 决策数据准备与标签验收

产出可用于Qwen choice训练的新数据版本，而不是只给一份操作建议。先读取[数据合同与标注规范](references/data-contract.md)。

1. 明确问题是“首诊断家族”，不要将故障注入名称、源码根因或引入提交混作同一个标签。优先用人工审核的第一诊断证据，保留reviewer和evidence。
2. 输入采用reviewed JSONL：一个案例一行，`id/group/source/split/input/label/evidence/reviewed_by`；模板见`assets/reviewed-example.jsonl`。模板是合成格式示例，不能当真实能力训练集。
3. 对跨构建的同一故障机制赋相同group，在扩增选项之前划分train/dev/test；同group和同一规范化输入不能跨集合。既有test参与开发时不称新盲测。
4. 运行`python scripts/prepare_dataset.py --input <reviewed.jsonl> --output <全新run目录>`。脚本检查标签、证据、机制组、重复、人工注入元数据和RCU/locking边界；不自动猜标签、不重写旧数据。
5. 检查输出`validation.json`、类别支持与未覆盖类别。交付`dataset.private.json`（本地私有文本）和`dataset-frozen.json`（公开元数据/哈希）给训练skill。公开时排除private文件及敏感原文。

脚本默认12类及首诊断问题，与项目9B实现相容。自定义类别用`--classes <JSON数组>`，仍须符合2–26个字母选项、标签定义与任务一致。补充的根因/提交真值应独立存储，由评测器使用，不混入本训练prompt。

可先`python scripts/prepare_dataset.py --help`；实际文件准备使用用户提供的日志与授权范围，不启动训练或接触生产服务。
