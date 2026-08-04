# Stability Insight 方案与实施计划

## 1. 系统边界

- 前端：Vue 3，负责实时看板、日志/符号表上传、任务队列、Markdown + PlantUML 报告、Skill Market。
- API：Express，统一处理本地文件存储、任务状态、报告读取、Skill 上传。
- 分析编排：上传成功后创建 `analysis_job`；生产环境由 worker 解压、脱敏、调用 Codex SDK，再落盘 `report.md` 与 `evidence.json`。
- 数据存储：原型使用 `data/uploads` 与 `data/reports`；生产建议使用 SQLite/PostgreSQL 保存元数据，文件使用内容寻址目录并保存 SHA-256。

## 2. 分析任务状态机

`queued → unpacking → extracting → agent_running → evaluating → report_ready → review → closed`

失败统一进入 `failed`，记录可重试的阶段、错误码、输入文件 hash 和 worker 版本。日志压缩包是必填；符号表缺失不阻断任务，但证据完整度上限需要下降并在报告中说明。

Agent 请求必须固定：分析协议版本、模型/温度、skill 列表及版本、输入 hash、提示词 hash、时间窗、输出 schema。这样报告和证据评估可以重放。

## 3. 可重复评估算法

`evidence-v1` 对每份报告生成确定性 JSON：

```json
{
  "completeness": 0.35,
  "consistency": 0.35,
  "reproducibility": 0.30,
  "score": 92.4,
  "baselineDelta": 1.8
}
```

- 完整度：问题现象、时间线、根因、影响范围、修复建议、证据引用六项加权。
- 一致性：根因与日志事实、调用链、平台/框架标签之间的规则校验分数。
- 可复现性：证据行号/时间戳/哈希是否能被二次抽取器重新定位。
- 评分器通过 `Evaluator` 接口热替换；版本、配置、seed、输入 hash 必须写入结果，禁止隐式使用当前时间或随机采样。
- Skill 入库门禁：固定 benchmark 上 `score_new >= score_baseline`，且关键类别不能回退超过阈值；再通过 CI、消融实验和管理员审核。

## 4. Skill 治理流程

上传后状态为 `benchmark_pending`，不进入自动分析。流水线执行：病毒/路径检查 → manifest 校验 → benchmark 全量评估 → 与 baseline 对比 → CI（schema、超时、权限、回归）→ 消融实验（移除该 skill、替换同类 skill）→ 管理员审核 → `baseline`。

闲时任务建议由 BullMQ/Redis 或系统级定时器调度，任务结果保存数据集版本、镜像 digest、skill hash 和评估器版本。任何 baseline 更新需要审批、版本化和可回滚。

## 5. 实施阶段

1. **MVP（当前）**：完成 Vue 看板、状态/趋势/矩阵可视化、上传入口、任务队列、报告渲染、PlantUML fenced block、Skill Market 和门禁展示。
2. **分析接入**：新增 worker 服务，接入 Codex SDK；实现解压白名单、敏感字段脱敏、取消/重试、SSE 或 WebSocket 进度推送。
3. **数据与权限**：替换内存数据为数据库；增加用户、管理员 RBAC、审计日志、文件 TTL、限流和病毒扫描。
4. **评估平台**：实现 benchmark runner、`Evaluator` 插件接口、CI pipeline、消融实验和 nightly 调度。
5. **生产化**：容器化、观测指标、备份恢复、模型/skill 回滚、报告签名与安全审计。

## 6. 当前原型的生产接入点

`server/index.js` 中的 `runMockAnalysis` 是 Codex worker 的替换点；`/api/analyze` 已固定必填日志压缩包和可选符号表的接口契约；报告按 job id 存放，前端已经按 Markdown 和 PlantUML fenced code 渲染。生产接入时只需将 mock 定时器替换为真实队列/SDK 调用，并保留同一输出 schema。

## 7. Benchmark 案例结构与验收

当前内置 `benchmark-2026.08`，覆盖 Android/OHOS、Nanchang/Guangzhou/Chengdu/Wuhan、Crash/ANR、启动、内存、丢帧和功耗等类别。每个案例至少包含：

```json
{
  "id": "BM-ANR-001",
  "platform": "Android",
  "version": "Nanchang R12",
  "occurredAt": "2026-07-21 18:42:11",
  "probability": 0.92,
  "resetCause": "watchdog timeout after RenderThread lock contention",
  "falseLogs": ["normal GC pause", "surface reconnect"],
  "rootCause": "BufferQueue lock contention"
}
```

Skill 页面现在可以逐条点击真实门禁按钮：`运行 Benchmark` → `运行 CI` → `运行消融` → `管理员入库`。API 会拒绝跳过前置步骤；未完成全部步骤的 Skill 不会显示为 baseline，也不会参与自动分析。

## 8. 本次验收清单

- 首页可按平台和版本切换，筛选参数传给 `/api/dashboard`。
- 首页显示状态环图、耗时趋势、平台矩阵和定位能力雷达图。
- `/api/benchmark` 返回案例集，Skill 页面显示发生时间、概率、复位原因和虚假日志。
- 分析任务完成后，报告页每 5 秒读取任务最新状态与本地 Markdown。
- PlantUML fenced code 在报告中单独渲染为时序图代码区。
- 上传 Skill 后默认进入 `benchmark_pending`，门禁按钮按顺序推进状态。
