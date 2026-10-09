# 部署文档、插件与报告索引

发布核对：2026-10-09。本页是仓库导航；历史报告保留各自日期和实验条件。成绩、部署状态冲突时，优先查最新 handover 与详细评测报告，不能跨数据版本合并指标。

## 插件与 Agent 代码

| 内容 | 文件入口 |
| --- | --- |
| 原生 dsh/Cordis 插件、注册与配置 | [插件说明](../plugins/kernel-decision/README.md)、[实现](../plugins/kernel-decision/index.mjs)、[manifest](../plugins/kernel-decision/manifest.json) |
| dsh SDK 任务启动与动态 overlay | [agent-runner.py](../scripts/agent-runner.py) |
| 共享 Decision API 后端 | [decision_plugin.py](../scripts/decision_plugin.py) |
| 快速定界路由 | [boundary_router.py](../scripts/boundary_router.py) |
| closed-loop 工具调用 Agent | [localization_agent.py](../scripts/localization_agent.py)、[网站集成](../server/agent.js) |
| 个人组合、跑分服务与评分 | [组合](../server/agent-profiles.js)、[跑分](../server/benchmark-service.js)、[评分](../server/benchmark-score.js) |
| 独立沙箱评测 | [网站评测器](../scripts/run-web-benchmark.py)、[沙箱驱动](../scripts/run-localization-benchmark.py)、[worker](../scripts/benchmark-worker.py) |

## 当前设计与部署

- [系统方案](SYSTEM_DESIGN.md)
- [Windows / Linux 部署](CROSS_PLATFORM_DEPLOYMENT.md)，[服务配置示例](../deployment/ai4loc.env.example)，[systemd 模板](../deployment/ai4loc.service)
- [原服务器维护与恢复](DEPLOYMENT_RUNBOOK.md)，[远端执行链](REMOTE_AGENT_DEPLOYMENT.md)，[Windows Demo](WINDOWS_SITE.md)
- [SGLang / Jev-like 参数与接口](SGLANG_JEV_LIKE_DEPLOYMENT.md)
- [Decision 插件与定位设计](DECISION_AGENT_DESIGN.md)，[Decision + Chat 分工及实测](DECISION_CHAT_HYBRID_AGENT.md)
- [网站一键跑分、个人 Prompt、评分与隔离](AGENT_BENCHMARK_PLATFORM.md)
- [最新详细评测分析](AGENT_BENCHMARK_ANALYSIS_20261009.md)，[逐例 CSV](results/agent-benchmark-20261009/cases.csv)，[统计 JSON](results/agent-benchmark-20261009/statistics.json)，[PNG](results/agent-benchmark-20261009/benchmark-analysis.png)，[SVG](results/agent-benchmark-20261009/benchmark-analysis.svg)
- [标签泄露审计](BENCHMARK_LABEL_LEAKAGE_AUDIT.md)，[本地数据与私有恢复](LOCAL_DATA_GUIDE.md)，[最新交接](../handover.md)

## 其他技术材料与演示

- [完整系统 48 页演示与逐页演讲稿](../deliverables/kernel-insight-system/README.md)
- [Jev × 手机 SoC 技术汇报、23 页演示、讲稿与资料来源](../deliverables/jev-huawei-soc/说明.md)
- [Jev API 示例与运行方法](../tools/jev-demos/README.md)
- [Kelip 模板、重建工具与许可证](../tools/kelip-slide/README.md)

## 全部顶层说明文档

- [ACCOUNTS_AND_PROGRESS](ACCOUNTS_AND_PROGRESS.md)
- [AGENT_BENCHMARK_ANALYSIS_20261009](AGENT_BENCHMARK_ANALYSIS_20261009.md)
- [AGENT_BENCHMARK_PLATFORM](AGENT_BENCHMARK_PLATFORM.md)
- [AURORA_DESIGN](AURORA_DESIGN.md)
- [BENCHMARK_LABEL_LEAKAGE_AUDIT](BENCHMARK_LABEL_LEAKAGE_AUDIT.md)
- [CROSS_PLATFORM_DEPLOYMENT](CROSS_PLATFORM_DEPLOYMENT.md)
- [DECISION_AGENT_DESIGN](DECISION_AGENT_DESIGN.md)
- [DECISION_CHAT_HYBRID_AGENT](DECISION_CHAT_HYBRID_AGENT.md)
- [DEPLOYMENT_RUNBOOK](DEPLOYMENT_RUNBOOK.md)
- [EXPERT_EXPERIENCE](EXPERT_EXPERIENCE.md)
- [IDENTITY_AND_REUSE](IDENTITY_AND_REUSE.md)
- [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md)
- [KERNEL_AGENT_DESIGN](KERNEL_AGENT_DESIGN.md)
- [KERNEL_LOCALIZATION_LOOP](KERNEL_LOCALIZATION_LOOP.md)
- [KERNEL_TOOLKIT](KERNEL_TOOLKIT.md)
- [LOCAL_DATA_GUIDE](LOCAL_DATA_GUIDE.md)
- [REMOTE_AGENT_DEPLOYMENT](REMOTE_AGENT_DEPLOYMENT.md)
- [SERVER_STATUS_20261007](SERVER_STATUS_20261007.md)
- [SGLANG_JEV_LIKE_DEPLOYMENT](SGLANG_JEV_LIKE_DEPLOYMENT.md)
- [SYSTEM_DESIGN](SYSTEM_DESIGN.md)
- [WEBSITE_SELFCHECK](WEBSITE_SELFCHECK.md)
- [WINDOWS_SITE](WINDOWS_SITE.md)
- [WORKSPACE_DESIGN](WORKSPACE_DESIGN.md)

## 全部顶层机器可读报告

- [agent-benchmark-20261007.json](agent-benchmark-20261007.json)
- [agent-benchmark-first-20261007.json](agent-benchmark-first-20261007.json)
- [agent-benchmark-platform-results-20261009.json](agent-benchmark-platform-results-20261009.json)
- [agent-evidence-smoke-20261007.json](agent-evidence-smoke-20261007.json)
- [agent-iteration-20261007.json](agent-iteration-20261007.json)
- [benchmark-leakage-audit-20261009.json](benchmark-leakage-audit-20261009.json)
- [decision-agent-iteration-20261008.json](decision-agent-iteration-20261008.json)
- [decision-chat-hybrid-results-20261009.json](decision-chat-hybrid-results-20261009.json)
- [deployment-audit-20261007.json](deployment-audit-20261007.json)
- [exact-source-download-20261007.json](exact-source-download-20261007.json)
- [kernel-dataset-audit-20261007.json](kernel-dataset-audit-20261007.json)
- [kernel-localization-benchmark-20261007.json](kernel-localization-benchmark-20261007.json)
- [linux-tool-experiments.json](linux-tool-experiments.json)
- [localization-review-template.json](localization-review-template.json)
- [project-cleanup-20261007.json](project-cleanup-20261007.json)
- [project-data-inventory-20261007.json](project-data-inventory-20261007.json)
- [server-dataset-inventory-20261007.json](server-dataset-inventory-20261007.json)
- [sglang-routing-20261007.json](sglang-routing-20261007.json)
- [website-acceptance-20261007.json](website-acceptance-20261007.json)
- [windows-tool-experiments.json](windows-tool-experiments.json)

## 发布与复现边界

代码、部署脚本、公开夹具、脱敏结果及说明文档进入 Git；数据集大产物、模型权重、账号、私有 Prompt、原始请求和业务日志不随仓库公开。完整数据保留在受控本地/服务器目录。下载仓库不等于已恢复大型材料或已安装模型服务。

历史展示中的模型价格、版本及外部评测以材料注明的日期为准，本次仅补齐发布文件，没有重新核验外部服务或重跑那些实验。Windows 原生 Demo 不提供 Linux 工具与隔离的全部执行能力；完整运行需 Linux/WSL2 及真实模型配置。
