# AI 接手手册 · Kernel Insight

## 插件、Agent、文档与报告完整发布补充（2026-10-09）

- dsh 原生插件 `plugins/kernel-decision/`、共享 Decision 后端、legacy SDK runner、closed-loop Agent、Linux/Windows 部署入口及所有 docs 报告已在此前 GitHub 提交 `d3317aa` / `4c96375` 中。此次重新核对跟踪文件，未遗漏这些功能代码。
- 新增统一入口 `docs/README.md`，区分当前方案、部署、历史实验与数据盘点；包含全部顶层 Markdown/JSON 文档链接及最新逐例 CSV/图表。
- 本轮补交此前未跟踪的 `tools/jev-demos/`、`deliverables/jev-huawei-soc/` 必要源文件/讲稿/来源/完整预览，以及其重建依赖 `tools/kelip-slide/`（保留 MIT 许可证）与项目 `AGENTS.md`。不改演示内容、不新增模型评测；Jev 资料的外部声明以其记录日期为准。
- `.render*` 和单页调试图片属于可再生成临时文件，排除发布。私有模型轨迹、账号和原始业务数据仍不上传；本轮不改生产部署。

## GitHub 功能与评测分析交付（2026-10-09）

- 本轮提交范围：一键 Benchmark、前十用户榜、个人 Agent/Skill Prompt 与分析联动，以及此前尚未提交的 Decision/Chat、标签审计、独立沙箱、Windows/Linux 部署依赖代码和测试。README 已更新当前 closed-loop 运行链路与 42/53 回归计数。
- 详细报告 `docs/AGENT_BENCHMARK_ANALYSIS_20261009.md` 包含实验条件、评分公式、逐例错误、时间/Token/调用分解、历史对照、泄露边界及下一轮可验证方案。`docs/results/agent-benchmark-20261009/` 提供 CSV、统计 JSON、PNG/SVG；`python scripts/summarize-agent-benchmark.py --figures` 从公开摘要重建（绘图需 matplotlib），不调用模型。
- 本轮重新运行 Node 42/42、Python 53/53 通过，并逐项重算得分与累计成本断言。实际模型成绩沿用已保留的九例网站 API 验收，未追加模型跑分或更改生产部署。
- 结论：阶段 7/9、类型 8/9、代码含健康拒答 4/9、故障代码 3/8；34 HTTP、255636 Token、累计定位 248.653 秒。四例 USERCOPY 仍落在检测器；HUNG_TASK 错误拒答。没有同条件提分证据，机制/引入提交准确率仍为 null。
- GitHub 仅发布功能代码、部署说明、测试和脱敏数据。账号、私人 Prompt、原始日志/请求、完整数据集与大归档继续保留在 Git 忽略目录；其他 Jev 演示稿及其示例工具不在本轮功能提交范围内。历史补充 ZIP 的 Git 基线与哈希不改写。

## 网站 Agent 跑分 / 个人 Prompt 交接（2026-10-09；最新状态）

- 用户要求社区一键跑分、用户前十、阶段/故障类型/根因代码准确性和时间/Token/API 效率；个人空间搭配保存 Agent/Skill Prompt，新建分析选择，并联动社区跑分。已实现并部署，完整设计和口径见 docs/AGENT_BENCHMARK_PLATFORM.md，实测汇总 docs/agent-benchmark-platform-results-20261009.json。
- 生产 app -> /opt/kernel-insight/releases/163bdd0af0ec，UTC 2026-10-08 16:57:16 激活（北京时间 10 月 9 日 00:57:16）；8787 模型健康。回滚 5c6791a8f60c；仅重启 kernel-insight，ollama-compat 保持原进程，平台 SGLang/Ollama 未重启。
- 新文件 server/agent-profiles.js、benchmark-score.js、benchmark-service.js；public/agent-lab-ui.js、agent-lab.css；scripts/run-web-benchmark.py、prepare-web-benchmark-labels.py。/api/me 返回 agentProfiles/agentBenchmarkRuns，不覆盖旧 Skill PR benchmarkRuns。普通分析实际传入组合 Prompt，冻结版本/hash 并参与去重。
- 评分 agent-location-v1：阶段10 + 故障类型20 + 根因代码50；三项全对且实测成本完整才获效率20（定界4/定位6/报告2/Token4/API4，w*r/(r+x)）。根因位置最多2候选、每例每处40行以内。先准确分排序，再总分；每用户每 cohort 最佳公开有效成绩，最多10人。机制/引入提交无独立真值，保持null。
- 专用严格数据目录 KERNEL_BENCHMARK_DATASET=/opt/kernel-insight/data/evaluation-datasets/stability-v1；与原 KERNEL_BENCHMARK_DIR 社区浏览目录不同。跨文件系统无法硬链接，最终实际复制（root所有，服务账号只读），未扩大/root权限、未改原始数据。9个 ready test 边界标注来自原始 collector 验证，非独立专家标注。
- 单例 UUID /work、bwrap 无标签/父评测目录/业务数据/proc，只读源码与产物，固定只读工具。共享模型槽、单用户1活跃任务、全站10活跃上限、8 API/240秒单例；进程组超时/取消可终止。自定义组合不执行用户代码；模型访问网络仍开放，依赖固定接口与工具能力限制，不能宣称有网络防火墙。
- 私有验收实例 data/benchmark-acceptance-20261009，实际9/9完成：总分51.6763，阶段7/9，类型8/9，代码4/9（含健康；故障3/8），34 API、255636Token、累计定位248.653s。9/9隔离检查通过、49次源码读、25条生成消息确实含所选Prompt。未证明比旧版提分，USERCOPY和HUNG_TASK仍有缺口。Node42/42、Python53/53通过。
- 自动审批拒绝验收账号向生产公共榜单发布成绩，改为专用私有实例，不向生产植入测试用户/分数；私有结果从榜单排除验证通过。生产榜单目前无用户有效成绩，不能填假前十。另拒绝默认admin凭据登录生产Web；已保留登录页让用户自行登录，不绕过。
- 完整私有证据服务器 /opt/kernel-insight/experiments/agent-benchmark-20261009/ 与 data/benchmark-acceptance-20261009/agent-benchmarks/add670f7-1695-4564-8337-7109e5cae0d2/。本地 retained-evidence.tgz 为653550B、SHA256 0eaea754e219652e25a85b589f6e90f44dd5f8aa63436bee6601833cd071c700，排除账号/口令与可重复取得源码。原始请求、usage、工具轨迹、隔离审计和模型结果保留；私有目录忽略Git。
- Windows原生8788 Demo已启动并验证保存/选择Prompt与展板；不能执行Linux沙箱。生产SSH本机转发localhost:8790 -> 服务器8787（本地独立forward进程依赖当前SSH会话）；用户自行登录后可完整评测。GitHub尚未更新，旧补充ZIP不含本轮内容；保留此前所有未提交修改。


## Decision / Chat 分层迭代交接（2026-10-09；优先于后续历史状态）

- 用户本轮要求整理 Jev-like SGLang 部署，构建快速定界与 Chat 根因分析的分层 Agent，并检查标签泄露。文档：docs/SGLANG_JEV_LIKE_DEPLOYMENT.md、docs/DECISION_CHAT_HYBRID_AGENT.md、docs/BENCHMARK_LABEL_LEAKAGE_AUDIT.md；公开汇总 docs/decision-chat-hybrid-results-20261009.json。
- 通用 Qwen 使用 /v1/decisions；专用 PPLX-Decider 使用 /v1/systemone，必须匹配 decision_config/readout 与新版本 SGLang，不能承担 Chat。此次未安装专用权重、升级或重启平台 SGLang/Ollama；当前 0.5.21 不能据版本号宣称支持专用检查点。choice/noul/score 的 System One 转换已在现有通用服务实测，专用权重尚未实测。
- 同 SGLang/Qwen、相同有限问题、9 个 ready test 各重复 3 次并随机交错：两种接口 family 判断均 27/27；Decision 平均 1.2304 秒、Chat 2.0241 秒，但 P95 为 3.0795 vs 2.3113 秒。stage/reporter 没有独立人工标签，不得宣传其准确率 100%。
- 完整隔离定位对照均完成 9/9，控制组和分流组均命中 4/8；请求 25→34，总耗时 252.946→275.619 秒。仅提前定界，没有证明全流程提速或根因提分。USERCOPY 仍易停留在检测器。rootCauseAccuracy=null。
- 已修复 incident 对 usercopy/kernel BUG/invalid opcode 首条诊断的遗漏；API 和生成失败计入预算；Chat 保留源码工具与证据引用，先探索再交付。原生 dsh kernel_boundary 实际调用成功，51 项 Python 与 36 项 Node 检查通过。
- 新 benchmark 采用匿名 UUID 和 bubblewrap 独立进程，无评测父目录、业务数据和 proc 挂载；18 个 worker canary 检查全通过，标签在 worker 退出后读取。60 个 ready 脱敏日志符合契约，历史 63 份工具轨迹未读采集脚本。旧版同进程评测隔离不足，test 已参与开发，合成函数名有捷径，不得对历史结果或预训练污染作绝对无泄露保证。
- 实验完整目录 /opt/kernel-insight/experiments/decision-hybrid-20261008/（开始于北京时间 10 月 8 日，完成于 10 月 9 日）。首轮分类失败、审计换行误报、proc/源码挂载失败、8 轮探索的中断和 System One noul 适配失败都保留。未改原数据或标签。私有本地证据目录 data/local-archive/decision-hybrid-20261008/。
- 新版 release 为 /opt/kernel-insight/releases/5c6791a8f60c，配置 KERNEL_BOUNDARY_ROUTER=decision、KERNEL_DECISION_API=decisions，Chat 继续使用原 Ollama 服务。精确激活、健康与回滚基线见 deployment.json；前版 0d865b1d38ef 和旧 Supervisor 配置保留。平台模型不动，仅维护项目服务。
- 本地审计包 retained-evidence.tgz 为 3,589,542 字节、548 个文件，SHA256 `697b19daac1c41cf5538c4f01a457b9ec5f6c102d7765f5f7aebd50e5dd28f8ad`；下载后已核对。完整服务器实验目录保留，审计包排除全量可再获取源码、缓存、大文件和私有 Supervisor 配置。
- 新代码/数据未上传 GitHub；旧补充 ZIP 不含本轮更新。保留之前工作区修改，禁止无差别 reset/clean/add。后续先改善 owner 源码证据覆盖，再冻结算法，用新采集独立机制样本重测；不能继续把已反复调试的 test 当作盲测。


## Decision 插件迭代交接（2026-10-08；优先于下文旧状态）

- 本轮已按用户要求在服务器构建原生 dsh `kernel_decide` 插件与闭环共享后端，对接现有 SGLang `/v1/decisions`。设计、验证范围及限制见 [Decision 系统设计](docs/DECISION_AGENT_DESIGN.md)，机器可读汇总见 [实测汇总](docs/decision-agent-iteration-20261008.json)。
- 服务器 app 已切到 `/opt/kernel-insight/releases/0d865b1d38ef`，项目 kernel-insight 与 ollama-compat 均 RUNNING，8787 health ok、closed-loop、模型连接正常；平台模型服务未重启。精确激活时间见本地/服务器 deployment.json。旧版 `f4648fac616c` 和原 Supervisor 配置留存，可回滚。
- 回归组原版 7/8 → 按需版 8/8，但规则消融也为 8/8；全 ready test 组原版/新版均为 4/8。Decision 尚未证明额外准确率收益，且全 test 请求 22→25、耗时 198.465→243.124 秒。不要把回归成绩写成全数据集成绩或因果根因准确率。
- 7 组共 63 次执行完整保留服务器 `/opt/kernel-insight/experiments/decision-20261008/`。本地审计归档 `data/local-archive/decision-20261008/retained-evidence.tgz`，SHA256 `9046db45383d5909c36f69e27eb97d04193f62f1a044ffdf80e6f313c26b4412`，含 63 份 localization-trace；排除再获取源码树/缓存/大文件/私有 Supervisor 配置，服务器完整原目录仍在。账号及原数据集未删除。
- 原生 SDK 已实际调用插件成功；该合成日志测试只证明调用链。63 次 benchmark 是离线闭环驱动，不是原生 SDK 沙箱全量验证。Python 45/45、Node 36/36 本地检查通过。
- 新代码、文档和成绩尚未上传 GitHub；旧补充 ZIP 未重做，不含本轮修改。继续保留既有未提交内容，不得无差别 reset/clean/add。后续优先完善未命中的 USER​COPY/HUNG_TASK 输入证据与源码/产物匹配，开展独立重复测试；根因/提交/修复闭环仍未验证。


## 当前交接摘要（2026-10-08，北京时间；优先于下文所有历史记录）

本地项目：`X:\Items\1_AI4-Loc`。仓库：https://github.com/YuTaoV5/AI4-Loc 。本轮用户要求更新交接；只更新本文件并核对现有交付物，未重新部署服务、跑模型评测或上传 GitHub。下文的“当前”“正常”“停服”“优先级最高”等旧措辞均对应当时记录，不能覆盖本节。

### 当前目标和交付状态

- 项目重点是基于真实日志、匹配源码和编译产物的工具调用 Agent：先定界阶段、报错组件和第一现场，再给出有证据的函数/代码候选，记录定位准确性、模型请求数和耗时。网站已有主要业务功能，后续优先完善定位与因果验证闭环。
- 用户要求 Windows 与 Linux 均能部署全量能力。已补跨平台部署入口、Linux 依赖安装/运行时/常驻服务模板与预检；Windows 原生仍为 Demo，完整 Linux 工具和沙箱采用 WSL2。**本机尚未安装 WSL，新 WSL / 空白 Linux 部署尚未完成实机全功能验收。** 模型权重及外部模型服务不在备份或交付包内。
- 48 页 HTML slide、逐页演讲稿及公开复现材料已完成并上传 GitHub；`deliverables/kernel-insight-system/` 是公开演示入口。没有新增真实模型成绩。
- 完整本地主副本约 16.82 GB：实验 5.05 GB、完整恢复包 4.70 GB、额外内核 Git 历史 2.77 GB、源码缓存 1.49 GB、四个数据集及产物 1.25 GB，其余主要是工具/依赖。这些不都是日常部署必需；保留研究与恢复主副本，未因制作精简交付包删除原始资产。

### GitHub 与本地修改

本轮核对本地 HEAD 为 `711319f15b49b9391205aa8e142cbe012688f541`，标题 `Publish research slides, full speaker script and reproducible evidence`；上轮通过 `git ls-remote` 确认其为 GitHub master 已上传版本。**跨平台部署整改、数据备份指南/脚本、补充包制作程序等仍有本地未提交/未上传修改，不能说 GitHub 已包含全部最新实现。** 本次 handover 更新同样仅在本地。

工作区已有修改和未跟踪的用户材料，接手先读 `git status --short`，不要 reset、clean 或整目录无差别提交；`tools/kelip-slide/` 是独立 Git 仓库，不能误提交成父仓库 gitlink。账号、任务、上传材料、模型调用记录和大型数据继续 Git 忽略；无明确授权不得公开上传私有数据。制作/修改 slides 须先读 `tools/kelip-slide/SKILL.md`。

### 服务器与本机运行状态的时间边界

最近 SSH 只读实查为 **2026-10-07 22:18:21 北京时间**，记录在 `docs/deployment-audit-20261007.json`，不是 10 月 8 日实时健康检查：

- 远端 `/opt/kernel-insight/app` 指向 `f4648fac616c`。整改前 51 个运行代码文件与本地全部一致；整改后 49 个一致，`scripts/package-deployment.py`、`scripts/agent-sandbox.sh` 两个本地有意修改，缺失 0。新增部署入口尚未部署远端。
- 当时项目 Supervisor 返回 `unix:///opt/kernel-insight/supervisor.sock refused connection`。不能沿用旧条目宣称网站/代理当前健康；本次未重新确认 8787/11435、平台模型端点或进程存活，也未重启远端服务。恢复前应先确认端口、项目专属 Supervisor 和活跃任务，避免影响平台 Ollama/SGLang。
- 原服务器运行文件对应的 165 个归档文件，本地整改后 78 个原位置一致、81 个在独立 v2 数据集目录一致、6 个有意不同，缺失 0。80 例网站数据没有丢失；根 `data/benchmark/` 保留 6 例社区夹具。
- Windows 网站此前在 `http://127.0.0.1:8787` 运行，独立状态 `data/windows-local/`，导入 6 份注明回放的真实报告；它不是本机新模型推理。本轮未复查该进程是否仍存活。slide 此前通过 `http://127.0.0.1:8793/deck.html` 预览，同样不要假定预览服务一直运行。

### 最新交付：GitHub 补充压缩包

用户最新打包要求：排除可重复获取的文件、GitHub 已上传且未修改的文件以及内核源码，并在包内说明怎样与 GitHub 合并。已完成：

| 项目 | 内容 |
| --- | --- |
| 路径 | `data/deployment/AI4Loc-supplement-20261007.zip` |
| 大小 | **665,905,679 字节，约 666 MB** |
| SHA256 | `5ee197eceda89991ab0b8c652374c5380bc6463c3a85d9be25ad9fee72b3adb1` |
| 对应 GitHub 提交 | `711319f15b49b9391205aa8e142cbe012688f541` |
| 清单 | 2,366 个恢复文件，1,061 个去重载荷 |
| 包内入口 | `README-合并与恢复.md`、`MANIFEST.json`、`merge_into_project.py` |
| 外部核验 | 同目录 `.zip.sha256` 和 `.summary.json` |
| 制作程序 | `scripts/package-project-supplement.py` |

包内包含 GitHub 未上传的必要数据集、原始实验/调用轨迹、编译产物、注入源码/补丁、私有业务状态及本地新增/修改文件；不包含已上传且未修改的 slide 等文件、内核源码树/源码包/Git 历史、node_modules、工具下载/运行时/缓存、`.cache` SDK 缓存、整套重复 Linux 恢复归档和编译 `.o/.a` 中间文件。相同内容只存一次，必须通过合并脚本恢复全部路径。

合并流程：先 clone GitHub 并 checkout 上述固定提交，将 ZIP 解压到独立 supplement 目录，再运行 `python supplement/merge_into_project.py <项目目录>`。脚本检查 Git HEAD 与载荷 SHA256，备份已有不同文件后恢复。服务器私有状态放在 `data/restored-server/data/`，不直接覆盖本地演示账号/state；恢复旧业务时显式设置数据目录。服务器配置和源码注册表含旧机器绝对路径，需按本机重新配置和核验。

**补充包的源码边界**：按用户要求，冻结的 `stability-v1/shared/source.tar.gz` 也被排除。因此仅靠补充包恢复后，原始严格数据集完整性检查会报告该文件缺失。OpenHarmony 5.10 源码使用 Gitee `kernel_linux_5.10` 的 `f88704ae607f90518f67aee33790ac06d6ada77d` 和对应补丁恢复；重新制作 tar.gz 不保证原封版哈希一致。逐字节复现须从完整本地主副本另取冻结源码包；新重建材料应另建版本，不能改原 manifest 冒充校验通过。完整主副本和三个恢复包仍保留。

本轮重新计算 ZIP SHA256 与记录一致。此前生成时已逐项读取验证 CRC，并核对排除项、数据集 vmlinux、私有 accounts、新部署入口及合并脚本语法。**该包含私有账号/业务日志，仅作本地受控交付，不上传 GitHub。** 此次 handover 更新发生在打包之后，未回填或重新生成 ZIP，其校验值保持上述版本。

### 部署入口、验证与后续任务

完整说明：`docs/CROSS_PLATFORM_DEPLOYMENT.md`；旧 `/opt/kernel-insight` 升级维护说明：`docs/DEPLOYMENT_RUNBOOK.md`；完整备份恢复：`docs/LOCAL_DATA_GUIDE.md`。

- Windows：`scripts/start-windows-site.ps1 -Mode Demo`；Full 模式需 `-Distribution`、WSL ext4 中的 `-LinuxProject`、实际 `-Model` 和从 WSL 可达的 `-ModelBaseUrl`。不能把 WSL 的 localhost 未经验证当作 Windows 模型地址。
- Linux 新机：管理员运行 `scripts/install-linux-deps.sh`，专用非 root 用户运行 `scripts/setup-linux-runtime.sh`，配置模型后运行 `scripts/start-linux-site.sh`。默认 closed-loop，不依赖旧 dsh；需要旧引擎时初始化加 `--with-dsh`。启动先检查模型与依赖、探测 bubblewrap；失败不回退为 Demo。
- 用户常驻服务模板：`deployment/ai4loc.service`、`deployment/ai4loc.env.example`。旧 `deploy-server.sh` 仍是原服务器专用维护入口，不是通用裸机安装器。模型权重、路由模型、运行时、源码注册表和数据集路径必须按实际机器提供。
- 最近代码验证：Python **40/40**、Node 隔离回归 **36/36**；五个 shell 文件通过 Bash 语法检查，Windows 入口通过 PowerShell 解析。约 2.47 MB 的 `data/deployment/site.tar.gz` 是另一个纯部署代码包，不包含完整大型数据及私有状态，不要和 666 MB 补充包混淆。
- 待办优先级：① 新 WSL / Linux 机安装并完成依赖、业务自检、真实模型三个层次验收；② 按需只读复查远端状态后恢复专属服务；③ 继续完善 RCU stall、OOM 因果措辞、独立机制审核、引入提交真值和修复重跑。尚无配套真实 vmcore，未证明自动引入提交定位或自动修复闭环。
- 定位成绩仍使用已有受限配对实验：5 故障+1 健康，代码命中 **3/5→5/5**、模型请求 **21→6**、总分析时间 **181.347→95.834 秒**；额外 3 例代码命中 **2/3**，RCU 未命中。这不是独立盲测，不是已验证根因率，不能推广成通用准确率。详见 `docs/agent-iteration-20261007.json`。

## 历史交接记录（以下保留原始记录，状态冲突以上述 2026-10-08 摘要为准）

> **2026-10-07 逐页演讲稿与公开复现包**：48 页口语演讲稿已补齐，约 1.08 万汉字，含图表指引、动画操作、过渡和备用问答。演示目录加入公开冻结证据、Kelip 模板与许可证、发布哈希清单及检查器。隔离复制环境中，无原始 `data/` 和工具模板目录仍可重建完全相同的 HTML；没有新增模型或网站验收。GitHub 发布范围为演示包及必要设计/启动文档，私有业务数据与大型内核材料继续留在 Git 忽略目录。

> **2026-10-07 Windows 本地展示与 Slide 整改**：网站已在 `http://127.0.0.1:8787` 启动，入口 `scripts/start-windows-site.ps1`，使用 Git 忽略的独立目录 `data/windows-local/` 和现有 80 条网站案例。导入六份真实实验报告作明确标注的回放，未新增模型调用、未执行网站功能验收、未变更远端服务。讲解稿改为 48 页，实验组改称“模型按需检索 / 自动预检增强”，新增 8 页真实功能界面、科研多面板/配对结果图，以及第 15/19 页可播放流程。详见 `docs/WINDOWS_SITE.md` 与 `deliverables/kernel-insight-system/说明.md`。

> **2026-10-07 本地完整项目归档与整理已完成**：服务器项目资产已保存至 `X:\Items\1_AI4-Loc`。`data/server-snapshots/20261007-full/` 三个 Linux 恢复包共 4,695,988,355 字节，SHA256 全部通过，包含实验源码/构建/启动阶段/评测，以及用户明确授权的账号、任务和私有业务状态；私有状态文件哈希一致。`data/datasets/` 独立保留社区 6 例、旧注入 64 例、启动扩增 v2 80 例、stability-v1 68 场景（60 ready、8 excluded）；后者 423 合同文件深验零错误。启动、旧评测与原始证据展开于 `data/experiments/kernel-lab/`；Linux 链接与重复大产物仍保留在恢复包，冻结源码使用数据集 `shared/source.tar.gz`。大型及私有数据均 Git 忽略。删除约 490 MB 失败下载与可再生文件，保留内核 Git 历史、演示稿和失败证据；未启动或重部署网站。新增完整方案 `docs/SYSTEM_DESIGN.md`、本地指南 `docs/LOCAL_DATA_GUIDE.md` 和库存 `docs/project-data-inventory-20261007.json`。本轮 Node 36/36、Python 38/38、隔离业务 15/15 通过，真实模型成绩未重跑。

> **2026-10-07 晚（北京时间）OpenHarmony 启动阶段（boot-stage）故障数据集扩增已完成（本块优先级最高，覆盖下文“暂停 OpenHarmony 故障采集”的旧措辞）**：按用户“不影响其他进程、针对不同启动阶段构建错误”的要求，在 `$LAB/bootstages/`（`$LAB=/root/gpufree-data/kernel-insight-lab`）用 QEMU TCG（`nice -n 19`、`taskset -c 96-111`）跑通 19 个启动场景，得 **15 条有效真实内核日志 / 9 类不同签名**（另有 `bs_init_segv` 与 `bs_init_exit_false` 签名相同，记为重复不计）。覆盖：早期内存（`alloc_low_pages` / `kasan_populate_shadow` / 实模式 trampoline，均在 console 就绪前 panic）、console 未就绪日志截断、rootfs 挂载失败（garbage/empty/noinit/`initcall_blacklist=populate_rootfs`/rdinit 缺失/root 缺失/rootfstype 未知）、init 失败（`No working init found`、`Attempted to kill init! exitcode=0x00000000`）与两类无 panic 的启动挂起（`Waiting for root device`、init 常驻）。另完成一项**配置驱动**故障：`CONFIG_BLK_DEV_INITRD=n`（需先给 OH 源码 `include/linux/initrd.h` 补上缺失的 `_LINUX_INITRD_H` include guard 才能编译，源补丁已做并保留 `.orig`），新 bzImage 23,135,744 B；即便 `-initrd` 提供镜像也被忽略，内核 `panic: VFS: Unable to mount root fs on unknown-block(0,0)`。**已将这 16 条（15 启动 + 1 配置）按应用 schema 并入线上数据集**：`openharmony-lkdtm-lab-v1`（64 例）→ **`openharmony-lkdtm-lab-v2`（80 例，新增 `OHOS-065..080`，全部 `category=待专家分析`、`split=train`）**，位于 `/opt/kernel-insight/app/data/benchmark/`；sha256+bytes 逐条校验 0 不符、80 个 ID 唯一无重复；写入前已备份 `/opt/kernel-insight/data/backups/benchmark.openharmony-lkdtm-lab-v1.20261007-185249.tgz`（并复制到 `$LAB/backups/`）。边界：新增 16 例均为本地注入的**真实内核输出**（非社区报单、无编造文本），标注方式与既有 LKDTM 集一致；这 16 例不等于“50 份真实社区样本”，不要把构造注入日志计入社区样本数。8787 应用服务按用户要求保持关闭（仅改文件，未重启）。证据：`$LAB/bootstages/notes/bs_manifest.json`、`bs_notes_README.md`、`runs/*.log`；本地脚本 `C:\Users\YuTao\AppData\Local\Temp\opencode\kernel-bench\`（`patch_build_c1.py`、`run_c1.py`、`bs_app_cases.json`、`_remote_install.py`、`verify_install.py`）。

> **2026-10-07 网站恢复及 agent 迭代最新验收（覆盖以下停服记录）**：服务器当前发布 `f4648fac616c`，网站 8787、代理 11435 和项目 Supervisor 正常，健康接口 `closed-loop / ollama-native / llmConnected=true`；平台 Ollama/SGLang 未接管。网站仍用 64 例 `openharmony-lkdtm-lab-v1`，旧社区备份与新 stability-v1 均保留。新自检入口 `scripts/run-website-selfcheck.py`：服务器 Node 36/36、Python 29/29、隔离业务 15/15、线上 9/9、匹配源码真实模型 8/8 通过；Linux 6.6.1 真实下载、官方 SHA256、缓存复用与源码读取通过。修复原日志字节损失、debug 首错标题、报告证据格式兼容和 sandbox 执行权限。相同 6 例 log+source 对照：故障代码命中 3/5→5/5，模型请求 21→6，总分析 181.347→95.834 秒；额外 3 例命中 2/3，RCU stall 仍未定位。代码命中不等于独立根因证明，OOM 目标/实际分配量措辞仍需复核。详见 `docs/WEBSITE_SELFCHECK.md`、`docs/website-acceptance-20261007.json`、`docs/agent-iteration-20261007.json`。

> **2026-10-07 约 17:00（北京时间）服务器实查补充**：SSH 已恢复。服务器发布目录仍为 `1ee04edd2ecb`，其中 `app/data/benchmark` 已是 64 例 `openharmony-lkdtm-lab-v1`（43 train / 21 test），与 `$LAB/benchmark/app-format` manifest 相同，64 日志哈希通过；不是旧的 6 例社区集。旧社区集目录 `/opt/kernel-insight/data/backups/benchmark.linux-community-v1.20261007-130120` 与 `$LAB/backups/benchmark.linux-community-v1.20261007-130120.tgz` 均保留，7 个文件一致。`$LAB=/root/gpufree-data/kernel-insight-lab`。新 `stability-v1` 是重新采集并严格校验的独立版本，68 场景中 60 有效（59 故障+健康），423 文件重新深验通过；旧版 64 中有 5 场景在新版排除，新版新增 pressure_oom，不能混算。当前网站 8787、兼容代理 11435 无监听，项目 Supervisor socket 拒绝连接；平台 Ollama 11434、SGLang 30000 模型端点正常。停服原因尚未确认，历史端口占用日志不能作为本次停服根因。本轮仅核查，未重启/替换数据。服务器发布包内 handover 仍为旧版，交接以本文件最新记录为准。v8/v9 完整评测 JSON 和 5 份调用轨迹已取回。详见 `docs/server-dataset-inventory-20261007.json`。

> **2026-10-07 最新优先级覆盖下文旧的“暂停采集”说明**：用户要求先确保日志/产物/源码数据集完备，再重点提升 agent 工具调用、第一现场定界与代码/提交定位。网站功能暂缓扩充。已在服务器重新采集 68 场景，59 故障+1 健康有效、8 排除，运行 GNU Build ID、源码补丁与 423 文件完整性检查通过。目录 `/root/gpufree-data/kernel-insight-lab/datasets/stability-v1`；本地只有证据副本，大型产物仍在服务器。首错提取的 debug/BUG 误匹配已修复并纳入回归，标注版本 v2。新可选工具循环、定位评测和独立机制审核见 `docs/KERNEL_LOCALIZATION_LOOP.md`、`scripts/localization_agent.py`、`scripts/run-localization-benchmark.py`、`scripts/review-localization.py`。代表性真实模型回归已完成：首轮全材料故障代码命中 2/5，后续原生接口复跑锁依赖和原子睡眠成功，OOM 因果代码仍未命中。v9 UAF 日志+源码 3 次请求、53.539 秒，首诊断提取 0.0047 秒；不同版本成绩禁止混算。Python 27/27、Node 31/31 通过。成绩见 `docs/kernel-localization-benchmark-20261007.json`；v8/v9 原始 JSON 与轨迹现已取回（此前 SSH 拒绝连接的缺口已关闭）。新引擎未切换线上。不能用分类正确率替代根因定位准确率；未证明引入提交、未采集 vmcore、未自动验证修复。

历史正文初始更新时间：2026-10-06；本文件最新交接更新：2026-10-08。项目仓库：https://github.com/YuTaoV5/AI4-Loc 。本文件是后续 AI 的入口，记录用户需求、最终设计和实现边界；历史设计文档冲突时，以最新需求及本文件顶部当前交接摘要为准。

## 用户 Prompt 与需求演进

以下是本轮会话用户需求的整理，不包含系统或工具内部提示。

1. **初始项目目标**：收集 Linux 社区稳定性问题日志及根因作为 Benchmark；自动下载对应版本源码；领导关注解决数与耗时改善，专家关注 Skill 贡献价值，测试人员需要大量压测日志快速定位。
2. **Skill 投稿**：“像 github 里面 pr 合入一样”，先管理员审核，再由提交者手动触发固定 Benchmark；未审核不许测试以减轻压力，管理员可以跳过审核；保证原集合不退化。分析可选推荐组合或指定 Skill。前三名按解决能力、使用次数、测试跑分排名，第一名有动画。
3. **工作空间布局**：Benchmark 试跑不应跳回工作台；上传界面“像 codex 界面一样一个输入行，上传按钮等等”；个人空间集中分析、跑分与投稿，删除工作台任务队列；主要导航突出，辅助页面在侧栏底部用图标。
4. **账号和进度**：首席点击烟花，专家悬停翻转展示解决问题与调用次数；默认创建 admin/admin；个人任务展开时间轴与当前阶段，显示真实执行状态。
5. **经验阅读**：点经验卡片进入正文；支持 Markdown 和 PlantUML 等插件；卡片展示解决数、满意度；移除登录页默认管理员提示等无必要注释。
6. **视觉风格**：浅色轻快、重点功能亮色、图标不重复，使用原始 logo.png。主标题大号粗体紧凑字距，副标题较大正常粗细。左右光束宽 60%、高 80%，从顶部原点分别旋转 20 / -20 度，浅蓝 #a0cdff 75% → #4687eb 40% → 85% 透明并模糊，内容后延迟 0.5 秒亮起。元素淡入上移依次进入；曾要求底部 Mockup 3D Tilt。
7. **最新布局约束**：删除首页工作流卡片，首页单屏无需上下滚动；统一 Benchmark 字色；不在公开页面展示三类用户视角切换，由管理员账号管理设置身份，首次登录进入对应页面；阅读按钮固定经验卡片右下角，支持搜索，防重复分析。
8. **此次更新**：“6 社区案例 4 异常类型 3 测试样本 linux-community-v1” 摘要背景要与渐变一致；专家从左到右 1、2、3；确保全站卡片文字与背景区分明显；上传 GitHub，更新 README，并添加本 handover.md。

**需求覆盖顺序**：后来的“删除首页工作流卡片”取代旧 Mockup 展示要求，因此当前首页没有 Mockup，Tilt 绑定在无目标时不执行。不要重新加入公开身份切换器、首页队列或默认账号登录提示。

## 设计手册

- 页面背景 #f6f9ff，正文 #172b4d，辅助正文 #465d7c，标题 #193760，主操作 #2563eb。卡片为半透明浅色，信息优先于装饰。
- 双光束在固定背景层，主内容透明，保持光效透出；表单浮层保留不透明浅色以便阅读。
- 社区摘要使用 `rgba(160,205,255,.48)` 至 `rgba(70,135,235,.19)` 的渐变、柔和边框和 blur，数字 / 版本号深蓝，不能回到纯白条。
- 专家桌面三列从左到右 1 / 2 / 3，第一列稍宽；窄屏按 1 / 2 / 3 向下排列。首席深蓝背景，标题纯白、辅助字近白；普通卡片深色字。首席点击烟花和卡片翻转保留。
- 效能看板主指标使用较深蓝渐变，白色标签；浅卡片的版本、说明、时间等辅助字不可过浅。状态标签使用有区分度的绿、蓝、黄、紫、红。
- 首页主输入与上传在一屏内，额外设置通过可关闭浮层展开，长选项只在浮层内部滚动。个人空间顶部卡片实际切换列表 tab。
- 经验卡片 footer 使用 flex；“阅读经验”靠右且在底部。搜索名称、专家、团队、类别、匹配词和建议，每次 12 个，加载更多。
- 内容动画采用淡入上移和错峰，尊重 prefers-reduced-motion；5 秒轮询不能反复播放进场。动画 fill 使用 backwards，避免 transform 形成固定定位浮层的包含块。
- 图标使用项目内 SVG，logo 使用根目录 logo.png 的原文件副本 public/logo.png，不改造品牌。
- **CSS 顺序陷阱**：kernel.css 为旧基础布局，aurora.css 最后加载；旧后代选择器可能覆盖父级颜色。此次新增末尾对比度规则明确覆盖 chief h2、说明与状态颜色。改背景必须同时检查子元素计算色和 hover / 翻转背面，不能只设置父 color。

## 代码地图

| 文件 | 职责 |
| --- | --- |
| public/kernel-app.js | 全局状态、导航、工作台、报告、Benchmark、看板 |
| public/aurora.css | 最新主题、响应式、光束和对比度，最后加载 |
| public/kernel.css | 基础组件与历史布局 |
| public/skill-ui.js | Skill 选择、TOP 3、投稿 / 审核 / 测试、经验卡片 |
| public/workspace-ui.js | 简洁输入和个人空间 tab |
| public/account-ui.js / admin-ui.js | 登录与身份、专家交互、管理员账号管理 |
| public/experience-ui.js / motion-ui.js | 经验正文、搜索；路由进场和交互动效 |
| server/index.js | API、任务创建 / 去重 / 执行、静态资源、持久化 |
| server/analyzer.js / catalog.js | 真实日志解析、声明式规则、内置 Skill 与指标 |
| server/accounts.js / task-progress.js | 密码哈希、会话、权限；真实阶段与 SSE |
| server/skill-workflow.js | 固定快照、审核门禁、无退化测试、合入与排名 |
| server/kernels.js | 精确 release / commit 下载、校验、缓存、安全解压 |
| server/experience.js | Markdown 安全渲染、图表、经验与满意度 |
| data/benchmark/ | 6 份公开 crash report 与来源清单 |
| scripts/ | 社区采集、校验并安装本地图表运行环境 |
| tests/platform.test.js | 24 项接口 / 数据 / 安全与行为验收 |

## 运行与验证

Node.js 22.14+：`npm ci` → `npm run setup:diagrams` → `npm start`。地址 http://localhost:8787 ，默认仅绑定本机。首次启动自动创建 admin/admin；注册默认 tester，admin 可设置 expert / leader / admin。首次登录按身份跳转，已登录刷新保留深链接。

前端静态文件修改后刷新即可；服务端修改后需要重启 Node。图表 setup 脚本默认支持 Windows；其他系统配置 PLANTUML_JAVA / PLANTUML_JAR。不提交 Java、PlantUML jar 或内核缓存。

本次 `npm test`：24 / 24 通过。浏览器验证社区摘要、专家顺序、首席文字和响应式布局，截图见 docs/previews/benchmark-contrast.jpg 与 experts-contrast.jpg。自动测试使用独立临时目录，不计入真实业务指标。

## 必须保留的实现约束

1. 本地默认“agent”仍为确定性流程；远端已通过 dsh SDK 接入 Qwen、工具调用及 SGLang 分诊，真实任务进度来自执行事件。不得在 UI 或文档宣称自动根因证明、自动复现或通用定位准确率。
2. 六个案例是真实社区 crash report，不是完整 console log，根因摘要来自关联补丁。固定 Benchmark 为类别检索守护，包含正常日志负例；有限案例不代表任意日志无退化。源码优先 commit，不能把厂商内核静默当官方基础版本。
3. 审核门禁必须在服务端执行。管理员可跳过审核但需记录原因；Benchmark 只能提交者或管理员手动触发，不能靠刷新自动启动。合入必须确认基准集合未变。
4. 任务 / 投稿归属按服务端用户 ID 校验。非管理员不能管理账号，最后一个管理员不能被降级。注册不能自选身份。
5. 相同条件分析共享进行中的任务，完成后复用报告；指纹含用户、日志、Skill 快照 / 顺序、源码、Benchmark 和 analyzer.js 文件哈希。失败不复用，force 只重跑已完成任务。近似签名关联不是自动免分析依据；旧任务缺完整指纹，升级首次会新建。
6. 解决数、满意度、使用和排行来自实际业务，试跑不计入。没有评价 / 人工基线显示 —，没有投稿贡献者显示空席位。不要填充虚构专家和收益。
7. Markdown 禁原始 HTML并净化，链接协议受限；Mermaid strict；PlantUML 本地沙箱、并发 / 时间 / 内存限制并禁外部引用。不得直接执行用户上传脚本。
8. Git 排除账号文件、admin-key、任务 state、上传 / 报告 / 投稿快照、源码、Java / 图表缓存、node_modules。根目录 kernel_linux_6.6 是下载验证用的本地源码，不应上传。工作区 deliverables 与 tools 含独立演示文稿素材，本次网站发布不纳入这些无关文件。

## 后续改进建议（尚未实现）

领导：区分独立故障和多机器重复发生次数，同时显示复用节省的分析量。专家：类别筛选、按满意度 / 解决数排序、经验版本演进。测试人员：任务关联机器与批次，区分故障复发和重复上传，批量反馈及更大规模检索。扩充真实社区样本并引入独立根因评估之后，再讨论完整智能诊断指标。

## 2026-10-07 Agent 设计更新
用户最新 prompt：暂时不需要做日志收集，重点根据之前收集的工具设计 kernel 稳定性问题定位 Agent。暂停 OpenHarmony 故障采集，构建曾停在缺少 ccache；不得宣称已启动该内核或已有 50 份样本。新增 kernel_triage.py 固定工具证据层、dsh 紧凑证据输入、实际阶段事件和报告证据展开。设计与实现边界见 docs/KERNEL_AGENT_DESIGN.md；缺少 vmcore/匹配符号时不得宣称根因已验证。

## 2026-10-07 服务器接管与材料链更新

用户要求执行状态核查后的修复与后续实现。发现旧网站进程停留在 d607526437b3，另一个 Supervisor 因端口占用 FATAL；已关闭两个项目 Supervisor 后以单一实例接管 5f5f46116887，保留平台 Ollama/SGLang。新 scripts/manage-supervisor.py 按精确配置定位进程、拒绝在活跃分析期间维护，部署不再因 status 非零删除仍在使用的 socket。

接管后真实单例任务 09152880-187e-4dd6-aa96-238712cad9e7 完成（231.278 秒，类别正确，2 次模型工具调用），生成新版 evidence.json；结果位于服务器 data/agent-evidence-recovery.json。这是单例分类验证，不是根因证明。

本轮新增：账号隔离的符号/ELF vmcore/.config 材料上传与任务绑定，SHA256 和材料指纹；多故障事件分组与可能 panic 连锁标注；Build ID/架构/版本门禁下的固定 crash sys/bt 和 drgn 任务摘要。构建不匹配或缺证据时停止查询。原日志和附件在沙箱只读挂载。没有真实配套 vmcore，因此固定查询的门禁测试不能替代真实转储验证；不支持压缩 kdump，未开放任意脚本或地址自动转换。

本地验收：Node 31 / 31、Python 9 / 9 通过；浏览器完成 .config 附件选择及提交并显示任务回执。当前设计细节见 docs/KERNEL_AGENT_DESIGN.md；日志采集保持暂停。

部署验收：新版实跑任务 10c154e4-cf62-49bc-8d3b-958f5aef58b7 在 54.32 秒完成，schema v2、3 个事件、类别正确、rootCauseVerified=false，保存在 data/agent-materials-release-smoke.json。服务器 Node 31 / 31、Python 证据测试通过；配置哈希冲突另加了拒绝转储查询测试。所有结果仍待人工根因验证。
