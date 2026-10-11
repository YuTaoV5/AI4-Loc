# 任务详细进展：API / 工具调用轨迹

更新：2026-10-11。服务器当前使用 closed-loop Agent，按真实执行记录展示可解释步骤。

## 用户看到的流程

个人空间 → 日志任务 → 展开分析进度 → API / 工具调用轨迹。原阶段进展与报告入口保留。运行中每 3 秒刷新，结束后停止轮询，可手动刷新；切换任务或退出账号清空上一任务数据。

1. 输入检查：日志、源码、编译产物是否实际可用，第一条明确异常的原始日志行。
2. Decision 定界：故障类别、执行阶段、报告组件的问题、全部选项概率和实际选择。内置问题提供中文解释，可展开接口问题原文。
3. 自动源码预检：从日志符号寻找候选，读取实际源码。与 Chat 自主选择明确区分。
4. Chat 调查：记录每次真实 HTTP 请求选择工具还是输出报告，随后展示对应工具结果。
5. 报告交付：仅在格式及证据引用检查通过后显示报告摘要和已保留的代码候选；候选不是已验证根因。

步骤仅描述可观察动作，不生成模型思维链或虚构选择理由。旧任务缺少时间戳时，编号只是阅读顺序，不宣称完整执行顺序。旧调用未记录的选择无法补造。

## Decision 格式与含义

兼容 `/v1/decisions` 的 `input + questions[]` 与 `/v1/systemone` 的 `state + questions{}`。展示层保留原始问题结构，读取接口实际返回的答案：

| 类型 | 输入 | 页面输出 |
| --- | --- | --- |
| choice | 问题和有名称的 options / criteria | 全部选项概率、明确返回的 choice |
| yes_no / noul | 二元问题 | yes/no 概率；System One noul 表示“是”的概率，不凭空构造 choice |
| score | 有顺序的 levels / criteria | 等级分布、明确返回的 score |

显示百分比保留四位小数；缺失概率标为未记录。概率是有限选项之间的相对偏好，未做根因正确率校准。已保留原始记录中的 label mass、请求哈希、原始 JSON、调试 token ID 不再投影到页面。已知协议校验失败同时显示错误，不当作成功调用。

## 调用记录与统计

`localization_agent.py` 在请求开始、解析出工具/报告选择及最终结束时持久化 `api-calls.jsonl`。同一请求 index 在展示时合并。工具记录 origin（自动预检或 Chat）及 modelRequestIndex；重复、超预算、参数格式错误的工具请求也记录为失败尝试，不执行工具。

执行次数与尝试次数不同：例如本次验收的 11 条工具活动包含 10 次执行和 1 次重复拦截，metrics.toolCalls 仍为 10。Decision/Chat 每次尝试的 HTTP 请求均计数。原生 DSH SDK run 可能包含多次内部请求，harness 启动/结束事件不能作为 HTTP 次数。

`server/trace-presentation.js` 把允许的工具结果转换为中文动作和有限证据：第一现场一行、搜索最多 8 条匹配、读源码最多 12 行；完整私有审计文件仍保留。失败工具不推断输入缺失或系统健康。最终代码位置经过现有源码引用检查，但独立因果验证仍需复现等证据。

## 权限与保留边界

`GET /api/jobs/:id/trace` 返回 `agent-call-trace/v2`。仅任务本人及管理员可读；未登录 401、其他用户 403、任务不存在 404，响应 no-store。只读任务目录固定文件名，拒绝符号链接与非规范目录；单文件最多 2 MiB，最多 300 条记录，超限提示缺口。不完整 JSONL 尾行暂不展示。

原始文件：decision-trace.json、api-calls.jsonl、tool-trace.jsonl、dsh-trace.jsonl。旧任务回退报告中已保留的 metrics.requests 和 evidence.commands。

API 不返回原始工具参数/结果、完整 Prompt、Decision input/state、请求头、模型原始回复或内部推理。受控证据片段仍需脱敏，动态字段一律 HTML 转义。密钥字段和常见字符串尽力脱敏，不宣称识别所有形式的秘密。原始日志、账号、模型请求及业务状态保留在私有 Git 忽略目录，不上传 GitHub。

## 实测与部署

本地 Node 49/49、Python 53/53 通过。覆盖权限隔离、输入转义、不同 Decision 类型、真实模型动作持久化、部分文件、历史兼容及失败工具不产生虚假观察。

Linux 独立验收实例 8789 实际调用现有 SGLang 与 Ollama。完整源码样本任务 `6ae833d3-9808-4e48-9d7f-f00292028107`：14 步；Decision 1 次、Chat 2 次、工具执行 10 次、重复拦截 1 次；Decision 0.3032 秒，定界 0.328 秒，定位 24.097 秒，21128 Token。浏览器核对真实问题、概率、自动预检和 Chat 动作。另保留日志单输入运行及初次验收路径配置失败，未把失败历史抹去。本轮不是完整 benchmark，不据此声称准确率改善。

2026-10-11 13:00:58 UTC 切换正式 release `/opt/kernel-insight/releases/task-trace-20261011`，恢复项目 Supervisor 与网站 8787；health.ok/llmConnected 均 true，模型 PID 70/86 未改变。回滚版本 `/opt/kernel-insight/releases/163bdd0af0ec`。正式站只验证健康、静态资源、未登录轨迹 401；鉴权完整流程在独立验收站完成，没有用默认凭据登录正式站。

服务器私有证据：`/opt/kernel-insight/experiments/task-trace-20261011/` 和 `/opt/kernel-insight/data/trace-acceptance-20261011/`。备份 config/state/accounts 位于实验目录 rollback（目录 0700、文件 0600）。运行配置、数据集和现有模型保持原设置。浏览器刷新后载入新版页面。
