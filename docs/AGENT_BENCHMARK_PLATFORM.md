# Agent 定位跑分与个人 Prompt（2026-10-09）

## 用户流程

1. 在个人空间点击“搭配并生成 Prompt”，选择服务端提供的 Agent（Decision 快速定界 + Chat 调查，或纯 Chat 调查）和最多 12 个已启用 Skill，添加调查偏好，生成预览并保存。可设为常用组合。
2. 在新建分析选择常用 Prompt。此时个人组合的冻结 Skill 版本取代临时 Skill 选择；Prompt 实际进入模型消息。组合更新不会改写旧任务。空选项仍采用原有推荐组合。
3. 在社区 Benchmark 点击“一键跑分”，选择个人组合，并选择是否公开用户名、组合名称及汇总分。服务端固定整套测试，提交人不能选有利子集、上传分数、变更模型接口或增加预算。
4. 个人空间和社区展示同一份评测记录，支持排队进度、取消、逐例指标、Prompt 快照和完整 JSON 下载。私人 Prompt、逐例诊断和原始审计仅本人和管理员可访问；公共榜单只有汇总信息。

当前 Agent/Skill 组合是受限调查指令，并非执行用户上传 Python/JavaScript/任意 shell 插件。Skill 的指导文本实际进入模型上下文。Linux 定位模型需要 closed-loop 引擎；Windows 原生 Demo 可管理组合与查看本机历史，完整沙箱评测在 Linux 或 WSL2 中执行，不会返回假成绩。

## 固定计分协议 agent-location-v1

每个样本准确分 A = 10 × 阶段命中 + 20 × 故障类型命中 + 50 × 根因代码命中。三个判定均为 0/1，最高 80 分。套件准确分取所有固定样本的平均值，包括失败和超时。健康负例要求阶段 unknown、类型 none，并且无根因位置、候选符号和故障假设；“未见诊断”不证明系统整体健康。

阶段枚举：boot / runtime / shutdown / build / unknown。故障类型枚举：use_after_free / out_of_bounds / usercopy / lock_dependency / atomic_sleep / hung_task / watchdog / rcu_stall / oom / memory_leak / exception / none / other。以第一条显式诊断为准，后继 panic 不替代首因类型。

代码位置命中要求路径和符号与真值精确相同，行区间与真值重叠，并有实际 source_read 工具证据。最多两个候选位置，每个最多 40 行，防止用整文件或大批候选撞答案。该指标不验证完整机制、不证明某提交引入了缺陷，机制与引入提交准确率保持 null。

仅当一个样本三项准确性全部命中且成本遥测完整时，才获得效率分 E：

| 实测指标 x | 权重 w | 参考量 r | 得分 |
| --- | ---: | ---: | --- |
| 定界耗时 | 4 | 5 秒 | w × r / (r + x) |
| 根因定位耗时 | 6 | 60 秒 | 同上 |
| 报告输出耗时 | 2 | 20 秒 | 同上 |
| 总 Token 数 | 4 | 12000 Token | 同上 |
| 模型 HTTP 请求次数 | 4 | 4 次 | 同上 |

每例总分 A+E，套件分取平均，范围 0–100。参考量是固定工程评分尺度，不是从本次结果拟合的最优参数。准确性优先排序：先比较套件准确分，再比较总分，相同按完成时间早者优先。因此不能通过少做调查、快速答错赚效率分，也不能通过更快但准确分更低超越准确分较高者。每位用户在相同 cohort 中只取最佳公开有效成绩，最多展示 10 位，缺少真实成绩时留空。

### 时间和成本口径

- 定界耗时：worker 开始到语义分类就绪；Decision 失败时，采用最终 Chat 报告就绪时间，不把失败接口返回当作成功定界。正则第一诊断提取时间另存 firstSceneSeconds，不能冒充语义分类耗时。
- 根因定位耗时：worker 开始到最终位置报告校验完成，包括证据调查与最后报告生成。它表示候选代码位置可供消费的时间，不能声称已经重放验证根因。
- 报告输出耗时：产生最终有效报告的模型请求发起到报告校验完成，为定位耗时的子集，两者不可直接相加。此前失败格式修复的时间已进入总定位耗时和调用成本。
- Token：使用 Ollama prompt_eval_count/eval_count 或 OpenAI 兼容 usage，以及 Decision usage 合计所有实际请求。失败请求缺少 usage 时 tokensComplete=false，totalTokens=null；另存可观测下界。不存在估算 Token 冒充实测。
- API：所有实际尝试的 Chat 和 Decision HTTP 请求均计数，包括失败和格式修复。定界的多个问题仍是一次 HTTP 调用，问题数单列。工具调用数另外记录。
- 排队耗时、套件运行耗时（含准备及验证）单列。缺标签、隔离审计未通过、缺成本遥测的结果保留，但不入榜。失败/取消的套件不入榜。

## 可比性与能力边界

cohort 冻结数据 manifest SHA256、标注 SHA256、Agent 代码、评测/评分实现、模型和接口、硬件标识、预算（单例 8 次模型 API / 240 秒）与运行配置。Prompt / Skill 快照单独冻结，供同 cohort 内比较。模型权重或服务启动配置变更后管理员必须更新 KERNEL_BENCHMARK_HARDWARE_ID 或重启相应版本部署；模型别名相同不自动证明权重相同。硬件标识应同时记录 GPU、驱动与模型检查点摘要。

当前 stability-v1 ready test 为 9 例（8 故障 + 1 健康）。新增边界标注由原始 collector 日志、注入位置和首条检测器签名交叉核对生成，属于 collector_verified，并非独立专家标注。runtime 的定义包括内核完成启动后由用户态 init 触发的工作负载。完整机制仍需独立人工/重放验证。

这是**公开注入集开发练习榜**：test 已用于历史迭代，合成函数名存在捷径，不代表盲测能力。沙箱证明运行期间评测标签未挂载，不能证明模型没有记忆公开答案、用户没有在 Prompt 写答案、或训练数据不存在污染。正式竞赛需另行采集隐藏且独立机制划分的数据，冻结提交后一次性评测、限制 Prompt 答案注入，并做独立专家双人标注。

## 沙箱与保留

每例独立 UUID 工作区，模型只看到固定 /work；只挂载脱敏日志、只读源码和只读匹配 ELF/配置/模块。标签和 manifest 留在父评测器，worker 完成后才加载。原始日志、标签和个人业务状态不挂入 worker；/proc 为空，无 host proc 或评测父目录挂载。canary、宿主根目录、业务状态及 proc 可见性在每例内检查，不通过即失败。仅暴露固定只读工具，无任意 shell、任意 URL 请求或用户代码执行工具。

网络命名空间保持连接以访问固定管理员配置的模型服务。此实现的网络控制依靠受限工具与服务端固定 API，并非独立网络防火墙。匿名目录不能清除日志或源码自身的符号身份。对于将来允许执行用户代码的扩展，必须另外提供网络白名单代理/namespace、防滥用和资源配额，不能复用当前安全结论。

服务端评测器由专用非 root 服务用户运行；模型槽与普通分析共享串行并发控制，每位用户最多一个活跃套件，全站最多 10 个排队/运行套件；运行超时终止整个 worker 进程组。源码和产物只读，标签目录 root 所有且服务账号只读，业务数据与运行输出为私有目录。没有自动降级到同进程、无沙箱的评测路径。

所有实验保留在 KERNEL_INSIGHT_DATA_DIR/agent-benchmarks/<run-id>/：control.json（私有）、evaluator.log、results.json、workspaces/<uuid>/ 的模型请求、工具轨迹、隔离审计、原始模型响应与报告。此目录已加入 .gitignore，不能上传私有 Prompt/用户日志或账号数据到 GitHub。统计摘要与协议可以公开。

## Linux 配置与入口

KERNEL_BENCHMARK_DIR 是原社区浏览目录，**不是**新的严格定位评测数据目录。两者允许同时存在，页面会清楚区分社区案例浏览与固定定位套件。

```bash
export KERNEL_BENCHMARK_DATASET=/opt/kernel-insight/data/evaluation-datasets/stability-v1
export KERNEL_BENCHMARK_HARDWARE_ID='GPU-and-model-checkpoint-config-version'
export KERNEL_DECISION_BASE_URL=http://127.0.0.1:30000
export KERNEL_DECISION_API=decisions
# 其余沿用 closed-loop / Ollama 模型配置
python scripts/prepare-web-benchmark-labels.py "$KERNEL_BENCHMARK_DATASET"
```

服务账号必须能只读遍历数据集路径，shared/source-tree 为匹配源码。不要扩大 /root 权限或向 worker 暴露父数据目录；复制/硬链接数据到专用 root 所有的只读目录。硬链接副本共享 inode：只能读取，不能修改已有文件；本次新增 benchmark-annotations.json 是新独立文件，不会改写原始标签。跨文件系统需复制。每轮正式跑分首先执行完整 dataset_contract 哈希验证。

API：GET /api/agent-presets；GET/POST /api/me/agent-profiles；PUT/DELETE /api/me/agent-profiles/:id；POST /api/agent-profiles/preview；GET /api/benchmark/suite；POST/GET /api/benchmark/runs；GET /api/benchmark/runs/:id（本人/管理员）；POST /api/benchmark/runs/:id/cancel；GET /api/benchmark/runs/:id/export；GET /api/benchmark/leaderboard。/api/me 同时返回 agentProfiles 和 agentBenchmarkRuns，原 Skill PR benchmarkRuns 保留。


## 本轮完整实测验收

生产 release：/opt/kernel-insight/releases/163bdd0af0ec，于 UTC 2026-10-08 16:57:16（北京时间 10 月 9 日 00:57:16）激活。网站与原模型连接健康，仅重启项目网站；SGLang / Ollama 未重启。回滚基线 5c6791a8f60c，原 Supervisor 配置和私有业务 state 已备份。

同一生产代码、模型和数据，在专用私有验收实例中通过真实网站 API 提交组合和整套评测；没有向生产账号、生产跑分记录或生产公共榜单植入测试成绩。9/9 样本完成，9/9 隔离 canary 检查通过，49 次源码读取仅涉及实施源码路径；25 条生成请求消息确认实际包含用户选择的调查 Prompt。私有结果出现在该实例个人空间，公共榜单仍为空，验证隐私联动。

| 指标 | 实测 |
| --- | ---: |
| 总分 | 51.6763 / 100 |
| 准确分 / 效率分 | 47.7778 / 3.8986 |
| 阶段准确率 | 7/9（77.78%） |
| 故障类型准确率 | 8/9（88.89%） |
| 根因代码定位（含健康拒答） | 4/9（44.44%） |
| 故障样本代码定位（不含健康） | 3/8（37.50%） |
| 累计语义定界耗时 | 9.6335 秒 |
| 累计定位报告就绪耗时 | 248.653 秒 |
| 累计报告输出耗时（定位子集） | 155.2847 秒 |
| Token / 模型 API | 255636 / 34 |
| Token 遥测完整率 | 9/9 |
| 本地回归 | Node 42/42；Python 53/53 |

这是平台闭环的功能与计量验收，没有证明 Agent 相比此前准确率提升。组合指导文本和评分口径均有变化，不能直接当作以前 4/8 的同条件回归对照。USERCOPY 仍经常落在检测器，HUNG_TASK 在本次连阶段/类型也未命中；健康样本类型与拒答正确，但阶段误报。后续应在开发集改善责任组件证据覆盖，并用新冻结隐藏集检验泛化。根因机制/引入提交准确率仍为 null。

机器可读摘要：docs/agent-benchmark-platform-results-20261009.json；详细分析：[评测报告](AGENT_BENCHMARK_ANALYSIS_20261009.md)。功能代码、公开协议和脱敏分析纳入 GitHub 发布。私有完整证据：data/local-archive/agent-benchmark-20261009/retained-evidence.tgz，653550 字节，SHA256 0eaea754e219652e25a85b589f6e90f44dd5f88aa63436bee6601833cd071c700。原始完整运行保留服务器 data/benchmark-acceptance-20261009/agent-benchmarks/add670f7-1695-4564-8337-7109e5cae0d2/，不上传 GitHub。

自动审批拒绝了以验收账号公开发布社区成绩，已改为独立实例私有验收；另拒绝使用代码默认凭据登录生产 Web 管理员，生产页面停留登录页交由用户自行登录。没有通过其他账号或接口绕过这两项拒绝。
