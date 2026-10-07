# AI 接手手册 · Kernel Insight

> **2026-10-07 逐页演讲稿与公开复现包**：48 页口语演讲稿已补齐，约 1.08 万汉字，含图表指引、动画操作、过渡和备用问答。演示目录加入公开冻结证据、Kelip 模板与许可证、发布哈希清单及检查器。隔离复制环境中，无原始 `data/` 和工具模板目录仍可重建完全相同的 HTML；没有新增模型或网站验收。GitHub 发布范围为演示包及必要设计/启动文档，私有业务数据与大型内核材料继续留在 Git 忽略目录。

> **2026-10-07 Windows 本地展示与 Slide 整改**：网站已在 `http://127.0.0.1:8787` 启动，入口 `scripts/start-windows-site.ps1`，使用 Git 忽略的独立目录 `data/windows-local/` 和现有 80 条网站案例。导入六份真实实验报告作明确标注的回放，未新增模型调用、未执行网站功能验收、未变更远端服务。讲解稿改为 48 页，实验组改称“模型按需检索 / 自动预检增强”，新增 8 页真实功能界面、科研多面板/配对结果图，以及第 15/19 页可播放流程。详见 `docs/WINDOWS_SITE.md` 与 `deliverables/kernel-insight-system/说明.md`。

> **2026-10-07 网站恢复及 agent 迭代最新验收（覆盖以下停服记录）**：服务器当前发布 `f4648fac616c`，网站 8787、代理 11435 和项目 Supervisor 正常，健康接口 `closed-loop / ollama-native / llmConnected=true`；平台 Ollama/SGLang 未接管。网站仍用 64 例 `openharmony-lkdtm-lab-v1`，旧社区备份与新 stability-v1 均保留。新自检入口 `scripts/run-website-selfcheck.py`：服务器 Node 36/36、Python 29/29、隔离业务 15/15、线上 9/9、匹配源码真实模型 8/8 通过；Linux 6.6.1 真实下载、官方 SHA256、缓存复用与源码读取通过。修复原日志字节损失、debug 首错标题、报告证据格式兼容和 sandbox 执行权限。相同 6 例 log+source 对照：故障代码命中 3/5→5/5，模型请求 21→6，总分析 181.347→95.834 秒；额外 3 例命中 2/3，RCU stall 仍未定位。代码命中不等于独立根因证明，OOM 目标/实际分配量措辞仍需复核。详见 `docs/WEBSITE_SELFCHECK.md`、`docs/website-acceptance-20261007.json`、`docs/agent-iteration-20261007.json`。

> **2026-10-07 约 17:00（北京时间）服务器实查补充**：SSH 已恢复。服务器发布目录仍为 `1ee04edd2ecb`，其中 `app/data/benchmark` 已是 64 例 `openharmony-lkdtm-lab-v1`（43 train / 21 test），与 `$LAB/benchmark/app-format` manifest 相同，64 日志哈希通过；不是旧的 6 例社区集。旧社区集目录 `/opt/kernel-insight/data/backups/benchmark.linux-community-v1.20261007-130120` 与 `$LAB/backups/benchmark.linux-community-v1.20261007-130120.tgz` 均保留，7 个文件一致。`$LAB=/root/gpufree-data/kernel-insight-lab`。新 `stability-v1` 是重新采集并严格校验的独立版本，68 场景中 60 有效（59 故障+健康），423 文件重新深验通过；旧版 64 中有 5 场景在新版排除，新版新增 pressure_oom，不能混算。当前网站 8787、兼容代理 11435 无监听，项目 Supervisor socket 拒绝连接；平台 Ollama 11434、SGLang 30000 模型端点正常。停服原因尚未确认，历史端口占用日志不能作为本次停服根因。本轮仅核查，未重启/替换数据。服务器发布包内 handover 仍为旧版，交接以本文件最新记录为准。v8/v9 完整评测 JSON 和 5 份调用轨迹已取回。详见 `docs/server-dataset-inventory-20261007.json`。

> **2026-10-07 最新优先级覆盖下文旧的“暂停采集”说明**：用户要求先确保日志/产物/源码数据集完备，再重点提升 agent 工具调用、第一现场定界与代码/提交定位。网站功能暂缓扩充。已在服务器重新采集 68 场景，59 故障+1 健康有效、8 排除，运行 GNU Build ID、源码补丁与 423 文件完整性检查通过。目录 `/root/gpufree-data/kernel-insight-lab/datasets/stability-v1`；本地只有证据副本，大型产物仍在服务器。首错提取的 debug/BUG 误匹配已修复并纳入回归，标注版本 v2。新可选工具循环、定位评测和独立机制审核见 `docs/KERNEL_LOCALIZATION_LOOP.md`、`scripts/localization_agent.py`、`scripts/run-localization-benchmark.py`、`scripts/review-localization.py`。代表性真实模型回归已完成：首轮全材料故障代码命中 2/5，后续原生接口复跑锁依赖和原子睡眠成功，OOM 因果代码仍未命中。v9 UAF 日志+源码 3 次请求、53.539 秒，首诊断提取 0.0047 秒；不同版本成绩禁止混算。Python 27/27、Node 31/31 通过。成绩见 `docs/kernel-localization-benchmark-20261007.json`；v8/v9 原始 JSON 与轨迹现已取回（此前 SSH 拒绝连接的缺口已关闭）。新引擎未切换线上。不能用分类正确率替代根因定位准确率；未证明引入提交、未采集 vmcore、未自动验证修复。

更新时间：2026-10-06。项目仓库：https://github.com/YuTaoV5/AI4-Loc 。本文件是后续 AI 的入口，记录用户需求、最终设计和实现边界；历史设计文档冲突时，以最新需求及本文件为准。

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
