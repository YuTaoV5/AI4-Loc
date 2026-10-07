# Kernel Insight

Linux 稳定性分析工作空间：社区案例 Benchmark、精确版本内核源码缓存、专家经验与 Skill 审核、个人任务进度和效能看板。

已有完整本地数据时，使用 [Windows 展示启动指南](docs/WINDOWS_SITE.md) 运行独立状态的网站。系统方案另附 [48 页网页版讲解稿](deliverables/kernel-insight-system/deck.html)，包含真实功能图、科研结果图与可播放流程。

演示材料：[完整逐页演讲稿](deliverables/kernel-insight-system/逐页演讲稿.md)、[离线包与重建说明](deliverables/kernel-insight-system/README.md)。

## 快速启动

需要 Node.js 22.14+ 与系统 `tar`（Windows 自带 bsdtar）。

```powershell
npm ci
npm run setup:diagrams
npm start
```

打开 [本地工作台](http://localhost:8787)。服务默认仅监听 `127.0.0.1:8787`。首次启动创建 `admin / admin` 管理员账号；登录页面不展示默认账号提示。普通注册账号默认为测试人员，管理员在账号管理中设置身份。

`setup:diagrams` 为 Windows 下载并校验本地 Java / PlantUML；其他系统可以通过 `PLANTUML_JAVA` 与 `PLANTUML_JAR` 指定已有运行环境。Markdown 和 Mermaid 使用本地依赖，无需外部 CDN。源码和社区日志采集需要网络。

```powershell
npm test
npm run collect:benchmark
```

当前 28 项自动验收测试全部通过，覆盖账号权限、任务归属、真实进度、分析去重、Benchmark 门禁、源码校验与安全解压、Markdown、PlantUML、模型报告校验和磁盘不足拒收保护。

## 远端模型与定位工具

远端已部署真实 **dsh harness + Qwen** 执行链及 **SGLang 结构化多问题分诊**；本地默认模式保留规则检索。模型调用使用独立任务目录和只读系统沙箱，个人空间可查看工具调用状态，报告含假设、原始行号和验证步骤。默认答案不传给模型，失败不伪装成成功。

- [Windows / Linux 工具手册](docs/KERNEL_TOOLKIT.md)：ripgrep、LLVM ELF / DWARF / PDB 与反汇编，Linux GDB、crash、drgn 等；13 / 14 项实际工具实验。
- [远端部署与恢复](docs/REMOTE_AGENT_DEPLOYMENT.md)：SSH 隧道、模型别名、SGLang 显存、只读沙箱、磁盘迁移与运行边界。
- [模型 Benchmark](docs/agent-benchmark-20261007.json) 与 [首轮原始失败记录](docs/agent-benchmark-first-20261007.json)：真实模型输出与耗时；有限案例的类别得分不是根因准确率。

通过 SSH 隧道访问远端：

```bash
ssh -p 30113 -L 127.0.0.1:8788:127.0.0.1:8787 root@120.209.70.195 -N
```

打开 http://127.0.0.1:8788 。密码只交互输入，不写入代码或 Git。网站及恢复后的模型 API 均以回环地址提供给本次执行链，不直接公开默认账号网站。

## 页面与使用流程

| 页面 | 功能 |
| --- | --- |
| 新建分析 `#/workbench` | 单屏输入与上传，支持最多 20 个文件、每个 64 MB；展开选项选择推荐或指定 Skill、源码参数和重新分析 |
| 个人空间 `#/personal` | 自己的日志任务、社区试跑、跑分历史和 Skill 投稿；顶部三个卡片跳转相应列表，展开任务查看阶段时间轴 |
| 效能看板 `#/overview` | 人工确认解决数、实际耗时、配对人工基线改善率和问题分布 |
| 专家中心 `#/skills` | 从左到右 TOP 1 / 2 / 3，卡片翻转、首席点击烟花；搜索经验，查看贡献者、解决数与满意度 |
| 社区 Benchmark `#/benchmark` | 案例来源、日志、根因摘要与修复依据；就地试跑及查看报告 |
| Skill 合入流程 `#/skills/pulls/` | 投稿、管理员审核、提交者手动测试、无退化合入及活动记录 |
| 账号管理 `#/users` | 仅管理员可见，分配测试人员、专家、领导或管理员身份 |

首次登录按身份进入相应页面；已登录刷新保留当前路由。任务和投稿按服务端用户 ID 隔离。报告记录实际命中的 Skill、版本与贡献者。

## Skill 能力守护

创建投稿时冻结社区案例与一个正常日志负例。审核通过后，提交者手动触发固定 Benchmark；管理员可记录原因并跳过审核，但不能跳过测试。刷新或打开页面不会启动测试，同一时间最多运行一个 Benchmark。

合入要求原本正确的案例不退化、整体类别得分不降低、候选规则有正确命中且没有误匹配。测试后基准 Skill 集合变化会阻止合入，需重新测试。当前评分是有限案例上的类别检索精确率、召回率和 F1，不是完整根因定位准确率。

专家排名按解决能力 50%、真实使用次数 25%、候选 Skill Benchmark F1 25% 计算。社区试跑不计业务贡献；没有已合入贡献者时展示空席位。满意度取人工评价中 4 / 5 星占比，按问题签名去重，没有评价显示 `—`。

## Benchmark 与源码

[data/benchmark](data/benchmark) 包含 6 份真实 syzbot 原始 crash report、4 类异常、3 个测试样本，版本为 `linux-community-v1`。清单保存来源、修复 commit、源码版本 / commit、SHA256 和 train/test 标记。根因摘要依据社区修复说明整理，尚未本地复现。

采集使用官方 syzbot.org；源码优先日志 commit，否则使用准确官方 release，发行版或厂商后缀不会静默降级。支持 Mainline、Stable、Linux-next 对应仓库。官方发布包校验官方 SHA256；commit 快照通过 HTTPS 下载并记录本地 SHA256。两路并发下载、状态持久化和缓存复用；Windows 将安全内核符号链接物化为文件副本或 junction。

## 重复分析与统计

同一账号下，规范化日志、Skill 内容 / 版本 / 顺序、组合、源码条件、下载选项、Benchmark 和分析引擎相同的请求共享任务：运行中跟随进度，完成后复用报告。记录重复提交次数、文件名和机器批次。失败任务不复用；条件改变创建新任务；显式重新分析仅对已完成任务生效。旧任务缺少条件指纹，升级后首次提交会新建一次。

近似问题签名只提供关联提示，不自动复用分析。只有人工确认计入解决数，平均耗时包含提交至确认的等待时间。改善率只使用填写人工基线的配对样本，无样本显示 `—`。

## 数据与实现边界

本地默认仍为确定性规则分诊；远端通过 KERNEL_AGENT_MODE=dsh 启用真实 dsh harness / Qwen 模型与工具分析，并增加 SGLang 结构化分诊。模型只生成待验证假设，不自动证明根因或复现故障。上传 Skill 是声明式文本规则与经验正文，不执行上传脚本。

运行数据保存在 `data/state.json`、`data/accounts.json`、`data/uploads`、`data/reports`、`data/skill-pulls`；源码和图表运行环境为本地缓存。这些目录由 `.gitignore` 排除，GitHub 仅发布代码、公开 Benchmark 与设计文档。测试使用临时独立目录。

## 设计与交接

最新设计使用浅蓝双光束背景、蓝色主操作、高对比度文字，社区摘要为半透明渐变。首页保持单屏，主要页面使用侧栏导航，辅助功能位于底部。

- [handover.md](handover.md)：历次需求 Prompt、设计手册、代码地图、运行与后续注意事项。
- [身份、首页与分析复用](docs/IDENTITY_AND_REUSE.md)
- [专家经验及 Markdown / 图表](docs/EXPERT_EXPERIENCE.md)
- [账号与实时进度](docs/ACCOUNTS_AND_PROGRESS.md)
- [光束视觉设计](docs/AURORA_DESIGN.md)

![专家中心](docs/previews/experts-contrast.jpg)

Kernel 定位 Agent 的证据流程、工具使用边界与后续接口见 [设计手册](docs/KERNEL_AGENT_DESIGN.md)。

新增离线定位闭环：服务器 `stability-v1` 数据集含 59 个有效注入故障和 1 个健康基线，保存完整运行日志、匹配编译产物、源码快照及根因代码；另外 8 个场景明确排除。与网站现有 6 例社区分类守护集分开管理。新 agent 支持第一现场定界、按需工具取证、代码位置候选、实际模型请求/耗时统计及独立机制评审，详见 [定位闭环](docs/KERNEL_LOCALIZATION_LOOP.md) 与 [数据集核验](docs/kernel-dataset-audit-20261007.json)。

### 诊断材料与转储边界

分析选项可附加 vmlinux / ELF 模块、ELF vmcore 和内核 .config，材料按账号隔离并绑定任务。文件 SHA256 与材料编号参与结果追溯和去重。符号和转储的 Build ID、架构与日志版本一致，且无已知配置哈希冲突时，才运行固定的 crash / drgn 只读查询。缺失或不匹配会显示材料缺口；当前不支持压缩 kdump、任意查询脚本或自动 KASLR 地址转换。多异常日志按标题分组，后续 panic 标注为可能连锁反应。

本轮验收为 31 项 Node 测试、9 项 Python 证据测试及远端真实模型单例。没有真实配套 vmcore，不能将门禁测试解释为转储根因已验证。详见 [Agent 设计](docs/KERNEL_AGENT_DESIGN.md) 和 [接管记录](docs/SERVER_STATUS_20261007.md)。

定位闭环本轮验证：Python 27/27、Node 31/31；真实模型各版本成绩、历史超时及 OOM 定位缺口见 [定位评测报告](docs/kernel-localization-benchmark-20261007.json)。新引擎仍为可选实验路径，未切换线上。

服务器网站已恢复并接入新版定位 Agent；当前完整验收为 Node 36/36、Python 29/29、业务与模型自检 32/32。重复执行入口及配对迭代成绩见 [网站自检手册](docs/WEBSITE_SELFCHECK.md)、[验收记录](docs/website-acceptance-20261007.json) 和 [定位迭代数据](docs/agent-iteration-20261007.json)。
