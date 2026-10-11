# 任务详细进展：API / 工具调用轨迹

更新：2026-10-11。

在个人空间展开任务后，可切换“阶段进展”和“API / 工具调用轨迹”。原阶段时间轴及报告入口保留。轨迹 Tab 在任务运行时每 3 秒读取一次，任务完成后停止自动刷新；支持手动刷新、展开调用详情。切换任务或退出账号会清空上一任务的界面数据及轮询。

## 展示内容

| 调用 | 展示 |
| --- | --- |
| Decision | 问题 ID、类型、问题文本、选项名称及说明、每项概率、选择结果、label mass、耗时、usage 和错误 |
| Chat API | 模型、接口类型、开始时间、状态、HTTP/报告协议失败信息、耗时、实际 usage、请求摘要哈希 |
| closed-loop 工具 | 工具名称、开始时间、耗时、参数及有长度限制的结果；自动预检也保留 |
| 原生 dsh | SDK 工具调用/返回通知及 harness 启动、完成、格式修正记录；通知未提供的参数或输出不会补造 |

Decision 同时兼容 `/v1/decisions` 与 `/v1/systemone` 的已保留格式。概率按接口返回展示；缺失为“未提供”，不从选择结果倒推概率。选项概率和 label mass 都不是经过校准的根因正确率。

dsh harness 一次 `run` 可能包含多次内部模型请求，因此 harness 事件不是 HTTP 次数统计。SDK 内部未开放的逐请求 usage/延迟不做估算。closed-loop Chat 请求使用真实调用记录，包括失败尝试；同一请求的 started/最终状态在界面合并为一条。

## 数据与权限

接口为 `GET /api/jobs/:id/trace`，沿用任务归属中间件：任务本人及管理员可读，其他账号返回 403，未登录返回 401，不存在返回 404。响应 `Cache-Control: no-store`。

仅从任务目录固定文件名读取：`decision-trace.json`、`api-calls.jsonl`、`tool-trace.jsonl`、`dsh-trace.jsonl`。不开放任意路径文件读取。拒绝链接轨迹文件及非规范任务目录，单文件最多 2 MiB，响应最多 300 条调用；嵌套结果、列表和文本也有展示长度限制。JSONL 未完整写入的尾行暂不展示，后续刷新继续读取；JSON 暂时不可读会提示刷新。超限给出缺口提示，不伪装完整轨迹。

不返回完整模型消息、系统/个人 Prompt、Decision input/state、请求头、原始模型响应或内部推理。结构化密钥字段移除，常见 Bearer、密码/API key 字符串脱敏；这是尽力脱敏，不代表能发现任意形式的秘密。工具证据仍是私有数据，不公开上传 GitHub，也不能直接把轨迹 API 当公共接口。前端所有动态字段转义，防止日志、问题或工具输出注入 HTML。

## 记录与历史兼容

- Decision 在请求前持久化 started，结束后原子替换含成功/失败的记录，保留原始问题结构用于跨接口展示。
- closed-loop 每次工具执行结束追加记录；模型请求开始及最终状态追加到私有 JSONL，保留错误与实际 usage。
- 原生 dsh 仅记录明确的工具及 harness 事件，不记录 assistant stream 或内部推理。底层 SDK 通知字段不一致时可能缺少详情。
- 旧任务无 JSONL 时，回退到报告中已有的 `metrics.requests` 和 `evidence.commands`。旧 Decision 文件若仍在任务目录即可展示其问题和概率；未保留原始记录的历史调用无法回填。Windows 导入的实验回放不会被当作本机新推理。

相关代码：`server/agent-trace.js`、`public/task-trace-ui.js`、`scripts/agent-runner.py`、`scripts/localization_agent.py`、`scripts/decision_plugin.py`。部署包自动包含 server/public/scripts；Linux 服务升级后需重启网站进程，浏览器刷新载入前端。新增文件不会替代原模型服务，也无需重启模型。

## 验证与当前部署

本轮本地 Node 46/46、Python 53/53 通过，新增测试覆盖问题/概率投影、凭据排除、请求状态去重、部分 JSONL、旧报告兼容、超限提示、界面转义及任务归属权限。Windows 8788 页面实际验证了 Tab 切换和已有实验回放中的 Chat/工具参数与返回。概率渲染以明确标记的测试夹具验证，未进行新的 Decision 模型推理。

本轮启动现有 Windows Demo 网站供查看，没有更新远端 Linux 部署或重跑 benchmark；此前定位成绩不因可观测性改动而重新计算。
