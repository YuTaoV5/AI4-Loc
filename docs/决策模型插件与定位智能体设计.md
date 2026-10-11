# Decision 工具插件与定位 Agent 迭代（2026-10-08）

## 问题与设计

目标是从实际日志定界阶段、组件和第一现场，再在可用源码/编译产物中寻找有引用支持的函数或代码段。日志、源码和产物允许缺失；缺少证据时返回不确定，不能用评测标签补全输入。当前评测验证代码位置命中，不等同于验证引入提交或修复因果。

依据 [SGLang Decision API](https://docs.sglang.io/docs/supported-models/decision_models)：`/v1/decisions` 一次预填充可批量计算 choice、yes_no、score 问题，无生成 token。选项概率是标签间归一化概率，label_mass 是标签在完整词表中的概率质量，二者均不是校准后的定位正确率。请求保留 prompt_token_ids、label_token_ids、温度和版本，支持复核接口输入。

架构：实际日志 → incident 工具提取第一现场 → source_triage 搜索/读取实际源码 → 检查 RIP/PC 对应函数是否已覆盖 → 必要时 Decision 对有限候选排序 → source_read 获取候选完整窗口 → 生成模型调用工具并输出有引用的定位结论。Decision 不负责生成诊断，也不把选项选择当作根因证明。

候选只来自日志中实际出现的栈帧、故障位置和生命周期证据。实际 RIP/PC 优先，推测栈帧降权；候选经 source_search 验证函数定义后读取源码。保留“证据不足”选项，不使用武断的概率阈值。源码缺失时不得捏造源码定位。

## 插件实现与边界

- `plugins/kernel-decision/index.mjs` 是原生 dsh/Cordis 工具插件，注册 `kernel_decide`，固定空参数 schema。Python、桥接程序、workspace 和 URL 均来自可信配置，不接受模型传入任意命令或路径。
- `scripts/decision_plugin.py` 是共享后端，检查响应概率、选项集合、版本和零生成 token，并记录失败请求。完整 HTTP 请求/响应和 token ID 写入私有 decision-trace.json，不把访问密钥写入轨迹。
- 原生 dsh SDK 通过 patches 加载插件；闭环 Agent 复用同一后端。Linux 沙箱只读挂载插件和脚本。生成请求和 Decision 请求共用 8 次上限，失败 HTTP 尝试也计数。
- 配置 `KERNEL_DECISION_BASE_URL=http://127.0.0.1:30000` 启用网站闭环的 adaptive 策略；移除此变量回到既有分支。实验支持 `decision`、`adaptive`、`adaptive-rule`，规则消融不调用 Decision。
- 缓存身份包含插件代码和端点，避免把旧缓存当作新模型成绩。

服务器已有 SGLang 0.5.21 接口可用，未升级或重启平台模型。模型别名 Qwen3.8-27B-SystemOne 的目录未发现 decision_config.json；这是已支持接口的生成模型部署，不能宣称换上了专门训练的 Decision 检查点。

## 实测结果

每个配置 9 个 log+source 案例，8 个故障、1 个健康案例。分母排除健康案例。请求数包括生成与 Decision 的实际 HTTP 尝试；耗时为案例时间之和。固定回归组混合已有训练/测试案例；全 test 组也不是新采集的盲测集，两组有重叠。共 7 组、63 次执行，不能当作 63 个独立案例。

|评测组/配置|代码定位命中|模型请求数|总耗时秒|
|---|---:|---:|---:|
|回归：原版首次|7/8|12|169.234|
|回归：总是 Decision|8/8|24|226.881|
|回归：按需 Decision|8/8|14|165.325|
|回归：规则消融|8/8|12|117.366|
|回归：原版暖机复测|7/8|12|107.367|
|全 test：原版|4/8|22|198.465|
|全 test：按需 Decision|4/8|25|243.124|

回归组改善来自更完整的源码证据选择：规则消融同样达到 8/8，当前实验没有证明 Decision 相对规则的准确率增益。暖机原版比按需版快，不能拿冷启动的 169 秒宣称速度改善。全 test 准确率未提升，Decision 增加了请求和时间；现阶段其价值是可审计的候选决策接口，而非已经证实的整体提分。单次顺序测试受缓存和顺序影响，样本较小，没有显著性结论。

引入提交、根因机制和修复重放缺少完整真值，本次 rootCauseAccuracy 保持 null。下一步优先检查 USER​COPY/HUNG_TASK 等未命中案例的输入可辨识性、源码版本/产物对齐和证据工具覆盖，使用独立新样本及重复、随机顺序评测后再调整路由。

## 验证与留存

本地 Python 45 项、Node 36 项检查通过。原生 dsh SDK 0.1.5rc1 实际调用 kernel_decide 成功，完成事件、插件审计和 Decision 轨迹均留存。该原生接口测试使用明确标记的合成日志，仅验证加载和调用；benchmark 使用离线闭环驱动，不能混称为原生 SDK 全量沙箱测试。最初 SGLang 生成接口的 SDK 请求失败记录也保留，成功调用采用 Ollama 兼容生成接口、SGLang Decision 接口。

服务器实验目录：`/opt/kernel-insight/experiments/decision-20261008/`。包含冻结原版/首轮/最终源码、各组完整结果、逐例工具轨迹、模型输出、接口 token ID、环境、日志、原生插件测试及部署记录。原始完整目录留在服务器；本地审计归档 `data/local-archive/decision-20261008/retained-evidence.tgz` 排除可再获取源码树、缓存、超 10MB 文件和私有 Supervisor 配置，不能冒充整目录镜像。摘要见 `decision-agent-iteration-20261008.json`。私有轨迹不公开上传 GitHub。

部署版本：`/opt/kernel-insight/releases/0d865b1d38ef`；旧版本 `f4648fac616c` 保留。启用前检查无活动任务，仅启动项目 Supervisor 两项服务。8787 健康接口 ok、closed-loop、ollama-native、llmConnected=true；平台 SGLang/Ollama 未重启。回滚时先确认无活动任务，恢复实验目录中的 supervisord.conf.before 和旧 app 软链接，再执行旧版本 scripts/manage-supervisor.py --restart，只操作项目服务。
