# 2026-10-07 接管与验收记录

## 服务恢复

旧网站 PID 776 工作目录为 release d607526437b3；新部署 release 5f5f46116887 的 Supervisor PID 7077 因原有服务占用端口而 FATAL。已在确认无活跃分析任务后，正常终止两个项目 Supervisor，删除重复的 kernel-ollama 服务定义，并以单一 Supervisor 接管。平台 Ollama 和 SGLang 保持运行。

部署现通过 scripts/manage-supervisor.py 精确识别本项目配置进程；不会因 supervisorctl status 非零就删除仍在使用的 socket。维护期间若存在排队/运行任务则拒绝重启。项目服务与兼容适配器统一重启后进行健康检查。

最终发布为 `1ee04edd2ecb`，网站及兼容适配器均 RUNNING，健康接口 llmConnected=true。可复用步骤见 [部署经验流程](DEPLOYMENT_RUNBOOK.md)。

## 已验证

- 网站 8787、兼容接口 11435、SGLang 30000 可用，模型连接正常。
- 接管后任务 09152880-187e-4dd6-aa96-238712cad9e7：231.278 秒、2 次模型工具调用、类别正确，生成 evidence.json。
- 新功能 release 实跑任务 10c154e4-cf62-49bc-8d3b-958f5aef58b7：54.32 秒，schema v2、3 个日志事件、类别正确、待人工审核。
- 本地与服务器均为 Node 31/31、Python 9/9 通过，包含最终新增的配置哈希冲突拒绝转储查询用例。
- 浏览器完成内核 .config 选择和上传提交，收到任务回执，无浏览器错误。
- 材料上传校验 ELF 类型、大小、SHA256、账号归属；材料条件变更不复用原报告。
- 阴性日志拒答、越界路径、原始行号、源码哈希冲突、构建/配置不匹配门禁都有测试。

## 保留的限制

没有真实配套 vmcore，crash/drgn 固定查询只验证了门禁与固定参数。Build ID 一致只说明提交材料之间一致，不能证明来源、根因或修复有效性。rootCauseVerified 与 runtimeMatchVerified 保持 false。压缩 kdump 与自动 KASLR 地址转换未实现。

OpenHarmony 构建仍停在缺少 ccache，未生成 bzImage；故障采集保持暂停。此次未编译、启动或向宿主内核注入故障。

远端结果保存在 /opt/kernel-insight/data/agent-evidence-recovery.json 与 agent-materials-release-smoke.json。业务账号、SSH 凭据、原始私人日志、材料及转储均不进入 Git 或部署包。
