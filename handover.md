# AI 接手手册 · Kernel Insight

## 并发实测动图与系统Slide整合（2026-10-16；最新交付）

- 原系统演示从48扩展到58页，新增49–58：方法、单步持平、单/四任务八步、无显存收益、顺序/批量、冷/预热、八条件交互、实际并发容量与证据入口。原48页及历史实验口径独立保留；逐页讲稿与目录同步。
- 五个GIF在`deliverables/kernel-insight-system/media/kv/`；交互回放嵌入单文件deck，离线可用，P播放、J/K按结果事件、时间滑块、共同播放速度、换页停止。独立trial以任务放行对齐，同一时间尺；真实单次repeat和5次均值分开。token仅在原生prefill完成结算，新增累计未命中token/s不冒充GPU瞬时吞吐。
- `实验数据与动图说明.md`列全部文件、字段、计时与token公式、代表重复选择、GIF缩放和效度边界。公开token/响应/KV/linear状态/NVML/概率记录及实验源码继续在`research/kv-concurrency-20261016`，校准在`...20261015`，业务原日志留私有归档。
- 分享ZIP由`package_experiment_slides.py`生成，位于`deliverables/releases/AI4Loc_实验动图_Slide与完整公开数据_20261016.zip`；包含完整slide、GIF、58页讲稿、两轮全部公开详细数据、说明、源码和QA，保持相对路径。逐成员核对与SHA见同目录`实验动图与数据包校验_20261016.json`。不含账号、权重、可重新下载的内核源码或私有业务文本。

## Qwen3.8并发、KV缓存与首响应实测（2026-10-16；最新）

- 正式入口 `research/kv-concurrency-20261016/README.md`；完整中文 `REPORT.md` / `report.html`、6组SVG/PNG图、逐HTTP/原生问题/调度边界/监控CSV、冻结协议、执行源码、离线分析与核验程序均保存。文档入口 `docs/SGLang并发决策与KV缓存实测报告_20261016.md`。
- 正式112 trial：80主实验（Decision/Chat×1/4任务×1/8顺序步骤×冷/热×5重复）+20批量8题+12额外观测敏感性；980正式HTTP、1330内部问题，全部成功，1330个内部请求唯一关联，465对完整prompt token SHA一致。4个实际诊断窗口，题干不变、选项不同；不报准确率。2全局预热、125 prime、4 token预检与SGLang启动生成单列；恢复后2次合成验证另列。
- 热条件1×8整批Decision/Chat均值1.365656/1.544334秒（减少11.57%）；4×8为3.634252/4.084956秒（减少11.03%）。单步基本无优势。4×8热条件峰值活跃KV均值916.438/916.250MiB，linear状态16/13槽，不支持Decision节省内存。一次请求批量8题在当前配置更慢。Decision没有文本TTFT，完整概率返回与Chat真实首非空内容分开。
- 发现生产CLI `max-running-requests=4`实际被自动9槽Mamba池限制为1（extra_buffer预算每请求5槽）。正式隔离实例30003使用`mem-fraction-static=0.78 --max-mamba-cache-size=32`，保留FP32状态，实际容量和观测批次4；不是上线改动。测试结束Supervisor已恢复，30003退出，30000原0.70/auto9/实际1配置恢复；Decision与Chat真实合成调用均HTTP200且答案通过。PPLX在本轮开始时未启动，结束保持未启动，不能沿用12日“旁路常驻在线”的旧状态。
- 另保留`research/kv-concurrency-20261015/`完整112-trial启动区段采集校准（980HTTP/1330问题、实际批次1），不并入正式结果。最初窗口缺首诊断，正式轮改窗口并扩池；跨轮存在输入/内存预算混杂。SIGINT取消尝试因nohup继承忽略未生效，校准最终正常完成，说明与证据保留。
- 两轮原始记录在服务器`/opt/kernel-insight/experiments/kv-concurrency-20261015/`及`...20261016/`，本地私有归档在Git忽略的`data/local-archive/kv-concurrency-<日期>/retained-evidence.tgz`。正式54899444字节、1136文件，SHA256 `66374918d1fab184a3a37898008851061e7bde02a9148bcd6c21a728c4660e99`；校准65473358字节、1136文件，SHA256 `342f04e3c42b2e846d3e5b7859f5c2971a9fe3223b96b7dce938bd90cd7b7db1`。归档排除捕获的原进程环境；业务输入不发布到Git。模型服务恢复不代表网站全部功能经过本轮验证。

## 报告修订与中文文档整理（2026-10-12；最新交付状态）

- 更新全GPU实测报告，并在此前学术报告加入4节PPLX研究：方法、配对耗时、标签准确性/泄露与部署验证。新版PDF `output/pdf/AI4Loc_Decision_Academic_Report_20261012.pdf` 共25页，11组科研图；旧20261011 PDF保留。网页、Markdown、结构化正文及构建脚本同步；原135次、CPU卸载121次、全GPU121次仍分开，不改冻结数据。
- `docs/`全部27份说明文档改为中文名称，入口 `docs/文档导航.md`，旧名称对照 `docs/文档名称对照.md`。活动引用、打包脚本及对应测试同步；JSON/CSV/图片和历史演示证据不更名。PPLX指南为 `docs/PPLX专用模型下载部署与验收手册.md`，包含官方固定下载链接、30文件校验、环境安装、两种设备放置、命令参数、接口/生命周期验收与恢复。
- 2026-10-12新版常驻部署已通过在线验收（北京时间2026-10-12 07:29:02）：五个部署脚本与仓库521b29c对应字节SHA256一致，30个权重文件重新核验通过；两轮choice/noul/score、项目DecisionClient、422/404负例和推理后停止→启动→再次推理均通过，共4次合成推理，不计入benchmark。PPLX PID1114，通用PID66启动身份未变，两个模型端点健康。当前常驻为CPU卸载并存配置；全GPU121次实验与此次部署验收分别保存。 新版部署证据 `deployment/pplx-decider/validation-20261012/`；私有归档16678字节、27文件，SHA256 `018c2ed719fd6332b3ccdcb9d7cdcfa6f6f9737a05d75aa046b543dcfc2598d6`，归档与逐文件核对通过。
- 更正README及本手册中多抄一字符的归档SHA256，正确值从归档实际内容及audit.json读取；原归档、536文件校验和实验数据未变。历史冻结程序/协议及原始日志继续保留。

## PPLX 全 GPU 分时复用复测（2026-10-12；最新状态）

- 按用户要求先卸载通用模型及PPLX CPU sidecar，让真实PPLX独占同一A100；78次PPLX调用结束并释放显存后，再加载通用模型完成43次调用。正式121次、另2次预热；0接口失败。协议先冻结，SHA256 `e7f831a2caa938ed5be46006b082dcc2d420ec74103993692056f28fc1f7121ab`。旧CPU卸载结果保持独立，不作为全GPU对照。
- PPLX BF16参数共52173271520字节（48.59GiB），逐参数设备只含cuda:0，无CPU/meta参数。研究入口 `research/pplx-timeshare-20261012/README.md`，报告 `REPORT.md` / `report.html`；121次标量/概率、协议、设备与恢复证据、4组科研图及离线复算/独立核对脚本均保留。
- test两端均27/27、唯一案例多数均9/9；25个映射案例repeat=0均23/25。test均值：PPLX 5.672s、通用2.563s，PPLX约慢2.21倍；P95分别6.891s/3.093s。全GPU已消除CPU卸载和同时驻留影响，但PPLX为Transformers/SDPA、通用为SGLang且关闭实验radix缓存，顺序固定PPLX→通用；不能归因纯权重速度。9案例配对探索性p=0.003906，5家族敏感性p=0.0625；不宣称跨机制显著或准确率等效。
- 121匿名隔离/实际请求审计通过，无额外标签/评分/ID字段；自然LKDTM符号仍在63请求、41唯一案例中。test已用于开发，不是盲测。LOOP/SOFTLOCKUP标签构念缺口保留；35未映射案例不评分。未测试完整根因定位或引入提交准确率。
- 首次尝试 `pplx-timeshare-20261011` 的记录代码读取不存在的hf_device_map属性而失败，0正式调用；原服务恢复后修复，用新目录冻结重跑。当前完成状态completed，控制器与独立恢复守护已退出，Supervisor50恢复S。通用模型30000恢复；PPLX CPU sidecar30002恢复，PID5850。恢复后两个Decision端点真实合成UAF均通过，Chat HTTP200；这些验收不计入正式分母。最终GPU70517MiB、余10635MiB。网站8787此前不可用，本次未执行网站恢复。
- 全GPU复测结束当时恢复原通用模型加旧版CPU sidecar；全GPU是已结束的维护实验。之后已部署新版入口，当前状态以上方新版部署验收为准；仓库部署实现已新增full-gpu选项，管理器默认CPU卸载不变。部署手册已补全GPU命令及维护恢复限制，不能照搬固定PID。
- 原始证据服务器 `/opt/kernel-insight/experiments/pplx-timeshare-20261012/retained-evidence.tgz`；本地 `data/local-archive/pplx-timeshare-20261012/retained-evidence.tgz`，624383字节，536证据文件，SHA256 `1e6e699a0bd6fac1b456e71fa51815920300e44f7623151f417a1cc1da6a83b3`。归档与逐文件哈希均核对一致，包含首次失败日志与恢复记录；不含私有进程环境、账号或权重。Git仅发布派生数据、脚本、图及文档。

## PPLX 独立常驻服务与部署手册（2026-10-11；历史部署验收）

- 已部署并保持运行：`/opt/kernel-insight/services/pplx-decider-v1/`，服务 PID2638，loopback `http://127.0.0.1:30002/v1/systemone`，真实 v1 checkpoint；BF16、GPU权重10GiB、CPU权重64GiB、单请求锁。与下方历史实验的临时服务已退出状态区分；本次没有变更历史协议或121次成绩。
- 完整手册 `docs/PPLX专用模型下载部署与验收手册.md`，实现 `deployment/pplx-decider/`，包括官方固定revision链接、镜像与哈希校验、环境复用、参数、Windows隧道、Agent接入、启动/停止/状态/验收脚本。新独立venv复用平台Torch/Transformers，只安装Accelerate；不依赖历史实验venv，但依赖 `/root/systemone-venv` 平台包。
- 30权重相关文件重新校验全通过；4轮合成接口验收共8次真实推理，choice/noul/score、概率和、零输出token、负例422/Chat404、现有DecisionClient均通过；推理后停止→启动→再次真实推理通过。五个部署脚本SHA256与本地/Git文件一致。详见 `deployment/pplx-decider/validation/`。
- 生命周期验证发现CUDA显存释放延迟与退出cmdline清空竞态，均已修复并保留失败记录。start最多等60秒显存≥16000MiB，stop发信号前校验命令/启动tick、发信号后仅等待原启动tick进程退出。最终等待0.045秒，未声称长等待/超时分支已实测。
- 最终GPU占用71149MiB、余10003MiB；原30000模型HTTP200、PID65未变。网站8787此前不可用，本轮未恢复网站或切生产模型。本服务不提供Chat/图像/自动崩溃重启/容器重启自动恢复；需要平台托管时按手册前台命令配置。
- 私有部署归档本地 `data/local-archive/pplx-deployment-20261011/deployment-validation.tgz` 与服务器服务目录同名文件一致，8449字节，SHA256 `6c94eec0d033db11034f41bcf9c6a06536ecafbbd4abf50340005530d7ea6634`。Git只发布合成验收结果、脚本与文档，不发布权重、账号或业务日志。

## PPLX-Decider 专用权重实测（2026-10-11；历史CPU卸载实验）

- 入口 `research/pplx-decider-20261011/README.md`，详细报告 `REPORT.md` / `report.html`，121 次公开派生记录、概率、协议、校验摘要及四组科研图。真实模型 `perplexity-ai/pplx-decider-v1-27b`，revision `b01a5cbaca5391f73bd55103d4f27e8982cd5e60`；30 文件、11 backbone 分片按官方元数据逐一校验，专用 readout / 保存温度实际使用。镜像仅作传输来源。
- 正式121次：9 test×3×2=54，其他16映射 train×1×2=32，35未覆盖家族×1 PPLX=35；另排除2合成预热。0失败、121匿名 worker/轨迹审计通过。两模型 test 均27/27、案例多数均9/9；25例 repeat=0 对照均23/25。未观察提分优势，无显著差异不等于非劣或等效成立。
- LOOP/SOFTLOCKUP 注入标签为 watchdog，但第一诊断为 RCU stall，两端均预测 RCU。保留冻结得分，不能直接称模型错误；见 `docs/首诊断与故障注入标签差异分析_20261011.md`。阶段、reporter、根因机制与引入提交缺独立真值，未报准确率。未覆盖35例 correct=null。
- 在原通用模型继续驻留条件下，PPLX 使用官方参考实现 BF16 CPU 卸载、GPU权重额度10GiB；不是原生 SGLang PPLX。test 平均客户端耗时19.455s，对照1.485s；该差异含 CPU 传输与运行时差异，不能判断同条件全 GPU 速度。没有切生产模型、没有重启 SGLang/Ollama。
- 模型请求无额外标签、评分、案例 ID 或数据集路径字段；但63/121请求、41唯一案例含与案例名重合的自然日志函数名，存在捷径可能。既有 test 参与开发，本轮不宣称去线索盲测或陌生机制泛化。CPU/GPU共享、提示/读出路径不同也限制纯权重因果归因。
- 私有证据服务器 `/opt/kernel-insight/experiments/pplx-decider-20261011/`；本地 `data/local-archive/pplx-decider-20261011/retained-evidence.tgz`，626206字节，SHA256 `0b6b2f6608eae8c819abe173c2ab1dec8319fc17abc23f33721e728131538a61`。归档及518文件哈希一致；账号/完整请求/日志不进 Git。52GB级可重复下载权重仅在服务器缓存，缓存盘余8.3GiB。
- 最新服务观察：测试前及结束后网站8787均不响应，项目Supervisor端口亦曾不可用；上文/下文早先“网站健康”是历史状态。原模型30000仍HTTP200、PID65存活；临时30002已正常退出。当前任务未恢复网站。后续若继续线上功能，先按部署 runbook 检查恢复，不能把模型服务健康当作网站健康。
- 下一步：纠正诊断/注入/因果标签结构；独立GPU同运行时比较专用模型速度；新机制盲测及同Chat/工具预算的完整Agent配对实验。本轮不改历史论文结论，也未证明根因定位提升。

## Decision 学术研究报告与补充实验（2026-10-11；最新研究状态）

- 交付入口 `research/decision-localization-20261011/README.md`，21 页 PDF 位于 `output/pdf/AI4Loc_Decision_Academic_Report_20261011.pdf`，另有离线 HTML、Markdown、8 组 SVG/PNG、公开派生 CSV、冻结协议与复算脚本。报告包含系统理论约束、DSH/Jev-like 契约、流程图、配对统计、消融、失败机制、泄露和效度边界；不是已投稿或获奖论文。
- 新增真实服务器实验 5 配置×9 案例×3 重复=135 正式调用，另排除 5 合成预热；随机配对块 seed=20261011。D3-first 平均1.145s、C3-first2.075s，客户端调用耗时减少44.8%；两者 family27/27。均值差95%案例bootstrap区间[0.626,1.284]s；三个预指定时延对比案例Holm p=0.011719，但5机制组Holm p=0.1875。不能把重复调用当独立案例，不能宣传跨机制显著或准确率非劣已证明。
- 问题数消融D3→D1平均耗时减少63.2%，同时丢失stage/reporter输出；D3输入token约为Chat3的2.52倍。窗口消融所有family正确，但尾窗口仍有首诊断5/8或其他分类线索，不能证明第一现场不必要。新增实测三问题概率示例保留，stage/reporter没有独立评分。
- 历史18次完整定位保持4/8→4/8、25→34请求、252.946→275.619秒；没有整体提速或提分证据。历史63次早期消融、54次有限分类与本轮135次严格分开。当前通用Qwen的Jev-like接口，不是专用Jev/PPLX权重实验；机制/引入提交准确率没有真值。现有test参与过开发，不是新盲测。
- 服务器 `/opt/kernel-insight/experiments/paper-20261011/` 保留协议、冻结源码、135调用及私有输入/返回/审计。初始化冻结时遇`__pycache__`的失败目录另存，发生于推理前；正式0失败、135/135隔离通过。原始归档3647762字节，SHA256 `78e6c9d997bd69c750ceec8e22ac40842b4daf8d508c7a30725dae5c54cd72ad` 与本地 `data/local-archive/paper-20261011/retained-evidence.tgz` 一致。
- 本轮不改生产代码/模型/配置，不重启服务、不写公共榜单或故障注入。实验后8787健康、llmConnected=true。公开数据独立复算结果与私有原数据统计逐字节一致，SciPy独立精确置换核对三对比通过；PDF已渲染检查。原始日志、完整请求、token ID与账号不提交。
- 后续优先采集新机制独立案例，做错误建议/硬路由/预检/资料缺失的同条件完整流程消融，双人盲标阶段/责任组件/因果机制，补真实引入提交与修复重放；报告提出的120例规模是计划，不是已测数据。

## 服务器部署与可解释调用步骤（2026-10-11；当前状态）

- 正式 app → `/opt/kernel-insight/releases/task-trace-20261011`；旧版 `/opt/kernel-insight/releases/163bdd0af0ec` 可回滚。本轮发现网站与项目 Supervisor 已停止，完成恢复；8787 health.ok/llmConnected=true。平台 SGLang/Ollama PID 70/86 保持不变。
- 轨迹 API v2 与中文逐步展示已部署：实际 Decision 问题/选项/概率/选择，Chat 每次请求的工具或报告选择，自动预检与模型选择的来源，以及有限关键证据。去除原始 JSON、label mass、哈希等中间显示。失败/重复工具请求不伪装执行成功；旧任务缺失的选择和顺序明确标注。
- 本地 Node49/49、Python53/53 通过。服务器独立验收真实 UAF+匹配源码任务 `6ae833d3-9808-4e48-9d7f-f00292028107` 共14步骤：1 Decision、2 Chat、10工具执行+1重复拦截；定界0.328秒、定位24.097秒、21128Token。只验证可观测性，未重跑完整评测或证明提分。
- 私有证据 `/opt/kernel-insight/experiments/task-trace-20261011/` 与 `data/trace-acceptance-20261011/`；配置/状态/账号备份仅存 rollback 私有目录。正式站验证健康、资源和未登录401；鉴权流程在独立实例验收，没有用默认管理员凭据登录正式站。详见 `docs/智能体接口与工具调用轨迹说明.md`。

## 历史初版：任务调用轨迹 Tab（2026-10-11，已由上方新版替代）

- 个人空间任务详细进展新增“API / 工具调用轨迹”，保留原阶段进展。可展示 Decision 问题/选项/概率/label mass、Chat 用量/耗时、closed-loop 工具参数/返回、dsh 通知与 SDK run 事件；运行中每3秒刷新。
- 新 API `/api/jobs/:id/trace` 沿用本人/管理员权限，固定文件白名单、响应无缓存、结果长度限制；不展示完整 Prompt、模型内部推理或认证信息。旧任务回退报告已保留记录，缺失轨迹不补造。详见 `docs/智能体接口与工具调用轨迹说明.md`。
- Node46/46、Python53/53通过；本地8788已启动并验证已有实验回放工具轨迹。未新增模型跑分、未修改远端Linux部署。私有调用文件继续位于Git忽略的任务目录。

## 插件、Agent、文档与报告完整发布补充（2026-10-09）

- dsh 原生插件 `plugins/kernel-decision/`、共享 Decision 后端、legacy SDK runner、closed-loop Agent、Linux/Windows 部署入口及所有 docs 报告已在此前 GitHub 提交 `d3317aa` / `4c96375` 中。此次重新核对跟踪文件，未遗漏这些功能代码。
- 新增统一入口 `docs/文档导航.md`，区分当前方案、部署、历史实验与数据盘点；包含全部顶层 Markdown/JSON 文档链接及最新逐例 CSV/图表。
- 本轮补交此前未跟踪的 `tools/jev-demos/`、`deliverables/jev-huawei-soc/` 必要源文件/讲稿/来源/完整预览，以及其重建依赖 `tools/kelip-slide/`（保留 MIT 许可证）与项目 `AGENTS.md`。不改演示内容、不新增模型评测；Jev 资料的外部声明以其记录日期为准。
- `.render*` 和单页调试图片属于可再生成临时文件，排除发布。私有模型轨迹、账号和原始业务数据仍不上传；本轮不改生产部署。

## GitHub 功能与评测分析交付（2026-10-09）

- 本轮提交范围：一键 Benchmark、前十用户榜、个人 Agent/Skill Prompt 与分析联动，以及此前尚未提交的 Decision/Chat、标签审计、独立沙箱、Windows/Linux 部署依赖代码和测试。README 已更新当前 closed-loop 运行链路与 42/53 回归计数。
- 详细报告 `docs/定位智能体跑分分析报告_20261009.md` 包含实验条件、评分公式、逐例错误、时间/Token/调用分解、历史对照、泄露边界及下一轮可验证方案。`docs/results/agent-benchmark-20261009/` 提供 CSV、统计 JSON、PNG/SVG；`python scripts/summarize-agent-benchmark.py --figures` 从公开摘要重建（绘图需 matplotlib），不调用模型。
- 本轮重新运行 Node 42/42、Python 53/53 通过，并逐项重算得分与累计成本断言。实际模型成绩沿用已保留的九例网站 API 验收，未追加模型跑分或更改生产部署。
- 结论：阶段 7/9、类型 8/9、代码含健康拒答 4/9、故障代码 3/8；34 HTTP、255636 Token、累计定位 248.653 秒。四例 USERCOPY 仍落在检测器；HUNG_TASK 错误拒答。没有同条件提分证据，机制/引入提交准确率仍为 null。
- GitHub 仅发布功能代码、部署说明、测试和脱敏数据。账号、私人 Prompt、原始日志/请求、完整数据集与大归档继续保留在 Git 忽略目录；其他 Jev 演示稿及其示例工具不在本轮功能提交范围内。历史补充 ZIP 的 Git 基线与哈希不改写。

## 网站 Agent 跑分 / 个人 Prompt 交接（2026-10-09；最新状态）

- 用户要求社区一键跑分、用户前十、阶段/故障类型/根因代码准确性和时间/Token/API 效率；个人空间搭配保存 Agent/Skill Prompt，新建分析选择，并联动社区跑分。已实现并部署，完整设计和口径见 docs/一键跑分平台与评分标准.md，实测汇总 docs/agent-benchmark-platform-results-20261009.json。
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

- 用户本轮要求整理 Jev-like SGLang 部署，构建快速定界与 Chat 根因分析的分层 Agent，并检查标签泄露。文档：docs/SGLang决策接口部署与参数指南.md、docs/决策定界与对话根因分析方案.md、docs/评测标签泄露审计.md；公开汇总 docs/decision-chat-hybrid-results-20261009.json。
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

- 本轮已按用户要求在服务器构建原生 dsh `kernel_decide` 插件与闭环共享后端，对接现有 SGLang `/v1/decisions`。设计、验证范围及限制见 [Decision 系统设计](docs/决策模型插件与定位智能体设计.md)，机器可读汇总见 [实测汇总](docs/decision-agent-iteration-20261008.json)。
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

完整说明：`docs/Windows与Linux完整部署指南.md`；旧 `/opt/kernel-insight` 升级维护说明：`docs/服务器部署维护与故障恢复手册.md`；完整备份恢复：`docs/本地项目数据与备份恢复指南.md`。

- Windows：`scripts/start-windows-site.ps1 -Mode Demo`；Full 模式需 `-Distribution`、WSL ext4 中的 `-LinuxProject`、实际 `-Model` 和从 WSL 可达的 `-ModelBaseUrl`。不能把 WSL 的 localhost 未经验证当作 Windows 模型地址。
- Linux 新机：管理员运行 `scripts/install-linux-deps.sh`，专用非 root 用户运行 `scripts/setup-linux-runtime.sh`，配置模型后运行 `scripts/start-linux-site.sh`。默认 closed-loop，不依赖旧 dsh；需要旧引擎时初始化加 `--with-dsh`。启动先检查模型与依赖、探测 bubblewrap；失败不回退为 Demo。
- 用户常驻服务模板：`deployment/ai4loc.service`、`deployment/ai4loc.env.example`。旧 `deploy-server.sh` 仍是原服务器专用维护入口，不是通用裸机安装器。模型权重、路由模型、运行时、源码注册表和数据集路径必须按实际机器提供。
- 最近代码验证：Python **40/40**、Node 隔离回归 **36/36**；五个 shell 文件通过 Bash 语法检查，Windows 入口通过 PowerShell 解析。约 2.47 MB 的 `data/deployment/site.tar.gz` 是另一个纯部署代码包，不包含完整大型数据及私有状态，不要和 666 MB 补充包混淆。
- 待办优先级：① 新 WSL / Linux 机安装并完成依赖、业务自检、真实模型三个层次验收；② 按需只读复查远端状态后恢复专属服务；③ 继续完善 RCU stall、OOM 因果措辞、独立机制审核、引入提交真值和修复重跑。尚无配套真实 vmcore，未证明自动引入提交定位或自动修复闭环。
- 定位成绩仍使用已有受限配对实验：5 故障+1 健康，代码命中 **3/5→5/5**、模型请求 **21→6**、总分析时间 **181.347→95.834 秒**；额外 3 例代码命中 **2/3**，RCU 未命中。这不是独立盲测，不是已验证根因率，不能推广成通用准确率。详见 `docs/agent-iteration-20261007.json`。

## 历史交接记录（以下保留原始记录，状态冲突以上述 2026-10-08 摘要为准）

> **2026-10-07 逐页演讲稿与公开复现包**：48 页口语演讲稿已补齐，约 1.08 万汉字，含图表指引、动画操作、过渡和备用问答。演示目录加入公开冻结证据、Kelip 模板与许可证、发布哈希清单及检查器。隔离复制环境中，无原始 `data/` 和工具模板目录仍可重建完全相同的 HTML；没有新增模型或网站验收。GitHub 发布范围为演示包及必要设计/启动文档，私有业务数据与大型内核材料继续留在 Git 忽略目录。

> **2026-10-07 Windows 本地展示与 Slide 整改**：网站已在 `http://127.0.0.1:8787` 启动，入口 `scripts/start-windows-site.ps1`，使用 Git 忽略的独立目录 `data/windows-local/` 和现有 80 条网站案例。导入六份真实实验报告作明确标注的回放，未新增模型调用、未执行网站功能验收、未变更远端服务。讲解稿改为 48 页，实验组改称“模型按需检索 / 自动预检增强”，新增 8 页真实功能界面、科研多面板/配对结果图，以及第 15/19 页可播放流程。详见 `docs/Windows本地网站启动指南.md` 与 `deliverables/kernel-insight-system/说明.md`。

> **2026-10-07 本地完整项目归档与整理已完成**：服务器项目资产已保存至 `X:\Items\1_AI4-Loc`。`data/server-snapshots/20261007-full/` 三个 Linux 恢复包共 4,695,988,355 字节，SHA256 全部通过，包含实验源码/构建/启动阶段/评测，以及用户明确授权的账号、任务和私有业务状态；私有状态文件哈希一致。`data/datasets/` 独立保留社区 6 例、旧注入 64 例、启动扩增 v2 80 例、stability-v1 68 场景（60 ready、8 excluded）；后者 423 合同文件深验零错误。启动、旧评测与原始证据展开于 `data/experiments/kernel-lab/`；Linux 链接与重复大产物仍保留在恢复包，冻结源码使用数据集 `shared/source.tar.gz`。大型及私有数据均 Git 忽略。删除约 490 MB 失败下载与可再生文件，保留内核 Git 历史、演示稿和失败证据；未启动或重部署网站。新增完整方案 `docs/问题定位系统完整设计方案.md`、本地指南 `docs/本地项目数据与备份恢复指南.md` 和库存 `docs/project-data-inventory-20261007.json`。本轮 Node 36/36、Python 38/38、隔离业务 15/15 通过，真实模型成绩未重跑。

> **2026-10-07 晚（北京时间）OpenHarmony 启动阶段（boot-stage）故障数据集扩增已完成（本块优先级最高，覆盖下文“暂停 OpenHarmony 故障采集”的旧措辞）**：按用户“不影响其他进程、针对不同启动阶段构建错误”的要求，在 `$LAB/bootstages/`（`$LAB=/root/gpufree-data/kernel-insight-lab`）用 QEMU TCG（`nice -n 19`、`taskset -c 96-111`）跑通 19 个启动场景，得 **15 条有效真实内核日志 / 9 类不同签名**（另有 `bs_init_segv` 与 `bs_init_exit_false` 签名相同，记为重复不计）。覆盖：早期内存（`alloc_low_pages` / `kasan_populate_shadow` / 实模式 trampoline，均在 console 就绪前 panic）、console 未就绪日志截断、rootfs 挂载失败（garbage/empty/noinit/`initcall_blacklist=populate_rootfs`/rdinit 缺失/root 缺失/rootfstype 未知）、init 失败（`No working init found`、`Attempted to kill init! exitcode=0x00000000`）与两类无 panic 的启动挂起（`Waiting for root device`、init 常驻）。另完成一项**配置驱动**故障：`CONFIG_BLK_DEV_INITRD=n`（需先给 OH 源码 `include/linux/initrd.h` 补上缺失的 `_LINUX_INITRD_H` include guard 才能编译，源补丁已做并保留 `.orig`），新 bzImage 23,135,744 B；即便 `-initrd` 提供镜像也被忽略，内核 `panic: VFS: Unable to mount root fs on unknown-block(0,0)`。**已将这 16 条（15 启动 + 1 配置）按应用 schema 并入线上数据集**：`openharmony-lkdtm-lab-v1`（64 例）→ **`openharmony-lkdtm-lab-v2`（80 例，新增 `OHOS-065..080`，全部 `category=待专家分析`、`split=train`）**，位于 `/opt/kernel-insight/app/data/benchmark/`；sha256+bytes 逐条校验 0 不符、80 个 ID 唯一无重复；写入前已备份 `/opt/kernel-insight/data/backups/benchmark.openharmony-lkdtm-lab-v1.20261007-185249.tgz`（并复制到 `$LAB/backups/`）。边界：新增 16 例均为本地注入的**真实内核输出**（非社区报单、无编造文本），标注方式与既有 LKDTM 集一致；这 16 例不等于“50 份真实社区样本”，不要把构造注入日志计入社区样本数。8787 应用服务按用户要求保持关闭（仅改文件，未重启）。证据：`$LAB/bootstages/notes/bs_manifest.json`、`bs_notes_README.md`、`runs/*.log`；本地脚本 `C:\Users\YuTao\AppData\Local\Temp\opencode\kernel-bench\`（`patch_build_c1.py`、`run_c1.py`、`bs_app_cases.json`、`_remote_install.py`、`verify_install.py`）。

> **2026-10-07 网站恢复及 agent 迭代最新验收（覆盖以下停服记录）**：服务器当前发布 `f4648fac616c`，网站 8787、代理 11435 和项目 Supervisor 正常，健康接口 `closed-loop / ollama-native / llmConnected=true`；平台 Ollama/SGLang 未接管。网站仍用 64 例 `openharmony-lkdtm-lab-v1`，旧社区备份与新 stability-v1 均保留。新自检入口 `scripts/run-website-selfcheck.py`：服务器 Node 36/36、Python 29/29、隔离业务 15/15、线上 9/9、匹配源码真实模型 8/8 通过；Linux 6.6.1 真实下载、官方 SHA256、缓存复用与源码读取通过。修复原日志字节损失、debug 首错标题、报告证据格式兼容和 sandbox 执行权限。相同 6 例 log+source 对照：故障代码命中 3/5→5/5，模型请求 21→6，总分析 181.347→95.834 秒；额外 3 例命中 2/3，RCU stall 仍未定位。代码命中不等于独立根因证明，OOM 目标/实际分配量措辞仍需复核。详见 `docs/网站功能自动自检手册.md`、`docs/website-acceptance-20261007.json`、`docs/agent-iteration-20261007.json`。

> **2026-10-07 约 17:00（北京时间）服务器实查补充**：SSH 已恢复。服务器发布目录仍为 `1ee04edd2ecb`，其中 `app/data/benchmark` 已是 64 例 `openharmony-lkdtm-lab-v1`（43 train / 21 test），与 `$LAB/benchmark/app-format` manifest 相同，64 日志哈希通过；不是旧的 6 例社区集。旧社区集目录 `/opt/kernel-insight/data/backups/benchmark.linux-community-v1.20261007-130120` 与 `$LAB/backups/benchmark.linux-community-v1.20261007-130120.tgz` 均保留，7 个文件一致。`$LAB=/root/gpufree-data/kernel-insight-lab`。新 `stability-v1` 是重新采集并严格校验的独立版本，68 场景中 60 有效（59 故障+健康），423 文件重新深验通过；旧版 64 中有 5 场景在新版排除，新版新增 pressure_oom，不能混算。当前网站 8787、兼容代理 11435 无监听，项目 Supervisor socket 拒绝连接；平台 Ollama 11434、SGLang 30000 模型端点正常。停服原因尚未确认，历史端口占用日志不能作为本次停服根因。本轮仅核查，未重启/替换数据。服务器发布包内 handover 仍为旧版，交接以本文件最新记录为准。v8/v9 完整评测 JSON 和 5 份调用轨迹已取回。详见 `docs/server-dataset-inventory-20261007.json`。

> **2026-10-07 最新优先级覆盖下文旧的“暂停采集”说明**：用户要求先确保日志/产物/源码数据集完备，再重点提升 agent 工具调用、第一现场定界与代码/提交定位。网站功能暂缓扩充。已在服务器重新采集 68 场景，59 故障+1 健康有效、8 排除，运行 GNU Build ID、源码补丁与 423 文件完整性检查通过。目录 `/root/gpufree-data/kernel-insight-lab/datasets/stability-v1`；本地只有证据副本，大型产物仍在服务器。首错提取的 debug/BUG 误匹配已修复并纳入回归，标注版本 v2。新可选工具循环、定位评测和独立机制审核见 `docs/内核定位闭环与数据集说明.md`、`scripts/localization_agent.py`、`scripts/run-localization-benchmark.py`、`scripts/review-localization.py`。代表性真实模型回归已完成：首轮全材料故障代码命中 2/5，后续原生接口复跑锁依赖和原子睡眠成功，OOM 因果代码仍未命中。v9 UAF 日志+源码 3 次请求、53.539 秒，首诊断提取 0.0047 秒；不同版本成绩禁止混算。Python 27/27、Node 31/31 通过。成绩见 `docs/kernel-localization-benchmark-20261007.json`；v8/v9 原始 JSON 与轨迹现已取回（此前 SSH 拒绝连接的缺口已关闭）。新引擎未切换线上。不能用分类正确率替代根因定位准确率；未证明引入提交、未采集 vmcore、未自动验证修复。

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
用户最新 prompt：暂时不需要做日志收集，重点根据之前收集的工具设计 kernel 稳定性问题定位 Agent。暂停 OpenHarmony 故障采集，构建曾停在缺少 ccache；不得宣称已启动该内核或已有 50 份样本。新增 kernel_triage.py 固定工具证据层、dsh 紧凑证据输入、实际阶段事件和报告证据展开。设计与实现边界见 docs/内核问题定位智能体设计.md；缺少 vmcore/匹配符号时不得宣称根因已验证。

## 2026-10-07 服务器接管与材料链更新

用户要求执行状态核查后的修复与后续实现。发现旧网站进程停留在 d607526437b3，另一个 Supervisor 因端口占用 FATAL；已关闭两个项目 Supervisor 后以单一实例接管 5f5f46116887，保留平台 Ollama/SGLang。新 scripts/manage-supervisor.py 按精确配置定位进程、拒绝在活跃分析期间维护，部署不再因 status 非零删除仍在使用的 socket。

接管后真实单例任务 09152880-187e-4dd6-aa96-238712cad9e7 完成（231.278 秒，类别正确，2 次模型工具调用），生成新版 evidence.json；结果位于服务器 data/agent-evidence-recovery.json。这是单例分类验证，不是根因证明。

本轮新增：账号隔离的符号/ELF vmcore/.config 材料上传与任务绑定，SHA256 和材料指纹；多故障事件分组与可能 panic 连锁标注；Build ID/架构/版本门禁下的固定 crash sys/bt 和 drgn 任务摘要。构建不匹配或缺证据时停止查询。原日志和附件在沙箱只读挂载。没有真实配套 vmcore，因此固定查询的门禁测试不能替代真实转储验证；不支持压缩 kdump，未开放任意脚本或地址自动转换。

本地验收：Node 31 / 31、Python 9 / 9 通过；浏览器完成 .config 附件选择及提交并显示任务回执。当前设计细节见 docs/内核问题定位智能体设计.md；日志采集保持暂停。

部署验收：新版实跑任务 10c154e4-cf62-49bc-8d3b-958f5aef58b7 在 54.32 秒完成，schema v2、3 个事件、类别正确、rootCauseVerified=false，保存在 data/agent-materials-release-smoke.json。服务器 Node 31 / 31、Python 证据测试通过；配置哈希冲突另加了拒绝转储查询测试。所有结果仍待人工根因验证。
