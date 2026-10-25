# DeepSeek Harness Skill 自主定位

新建分析的“分析选项”中选择 **DeepSeek Harness · Skill 自主定位**，选择网站 Skill 集合或个人组合，填写本次 Prompt，上传材料即可。每个附件是一个问题；相关文件请先打包。原流程保留可选。

分析选项不再收集压测机器 / 批次、源码仓库、内核版本、Commit 或自动下载开关，相关信息由选定 Skill 在调查中识别和获取。网站源码页面只展示缓存及只读浏览链接，不再提供手动下载参数表单。登录后可通过 `/api/kernels/<key>/files` 浏览缓存目录和普通文件，路径始终限制在该缓存源码根目录内。

Skill 投稿的 Benchmark 可选择“规则分类回归”或“完整 Agent 定位”。前者保留原分类门禁；后者实际调用 closed-loop Chat，比较原集合与候选集合在冻结日志上的类别正确率和退化，保存受权限保护的完整报告。网站一键 Agent 跑分也已去除 Decision 接口依赖。此处的完整 Agent 投稿测试使用 closed-loop；Harness 自由报告暂不混入结构化定位排行榜。具体评分与预算见 [跑分协议](一键跑分平台与评分标准.md)。

## 处理流程

1. 任意扩展名、二进制、kernel 文本、维测加密材料均可上传，不执行日志格式、文本内容或符号匹配校验。沿用每个文件 64 MiB、每次 20 个的上传资源限额。
2. 按账号与原始文件 SHA256 建立 `data/problem-pool/<owner-hash>/<sha256>/`。相同账号的相同字节复用问题目录；不同账号隔离。文件改名仍可去重。SHA256 用于内容身份，不是拒绝材料的格式校验。
3. 保留 `original` 与 `manifest.json`；按内容识别 ZIP、TAR、GZIP 并展开全部普通文件到 `content/`。损坏、加密、未知格式和不能安全展开的压缩包保留原件并记录原因，继续交由 Skill 调查。路径穿越、链接和设备文件不落盘；自动展开上限 512 MiB / 10000 文件，避免写出问题目录或耗尽空间。
4. 每次调查在问题目录内 `runs/<job-id>/` 使用独立 Harness home 和 session。输入副本只读挂载，运行目录可写。所选 Skill 的完整正文、版本和顺序冻结在 `skills.json`；个人组合 Prompt 与本次 Prompt 一起传给 SDK。不经过旧文本分诊、Decision API、固定四次工具调用或旧 JSON 报告约束。
5. `DeepSeekHarness.run()` 调用 OpenAI 兼容 Chat API，自主调用工具完成调查。报告方法、结构与内容由 Skill 指定；`report.md` 是网站收集入口，未写文件时使用最终回复。不伪造解密结果或把服务异常当成功报告。
6. 网站显示净化后的 Markdown、支持下载、人工确认和反馈。工具活动进入任务进度及 API / 工具轨迹。任务按内容、账号、完整 Skill、Prompt、个人组合、引擎代码与模型配置去重。改变 Prompt/Skill 会新建运行但复用原件；失败可重试；强制重跑不复用已完成报告。

## 服务器配置

需要 Python `deepseek-harness-sdk==0.1.5rc1` 及配套 runtime，Linux 必须配置项目 bwrap 沙箱。原网站的 `KERNEL_AGENT_MODE=dsh` 启用模型路径。

| 环境变量 | 用途 |
| --- | --- |
| `KERNEL_HARNESS_BASE_URL` | Chat API 根地址，例如 `https://provider.example/v1` |
| `KERNEL_HARNESS_MODEL` | Chat 模型名；默认继承 `KERNEL_AGENT_MODEL` |
| `KERNEL_HARNESS_API_KEY` | 服务端密钥；默认继承 `KERNEL_AGENT_API_KEY`，不写仓库 |
| `KERNEL_HARNESS_TIMEOUT_SECONDS` | 完整调查超时，默认 1800 秒 |
| `KERNEL_HARNESS_MAX_TOKENS` | 单次生成预算，默认 8192 |
| `KERNEL_AGENT_SANDBOX` | `scripts/agent-sandbox.sh` 的绝对路径 |

现有 Ollama native 配置默认通过 `http://127.0.0.1:11435/v1` 的兼容服务调用 Chat；其他配置默认继承现有 base URL。使用外部 API 时必须明确填写正确的 Chat base URL 和模型。Harness 是 Agent 运行框架，并不要求模型必须来自 DeepSeek。

新问题池、Prompt、会话、报告与密钥均为服务器私有运行数据，不纳入 GitHub。旧个人组合可能只保存 guidance；重新保存组合后才冻结完整 Skill 正文。

## 验证

2026-10-25 用户上传 Skill 专项验收：通过网站 HTTP API 上传两份不同 Markdown 正文的 Skill，执行审核、固定 Benchmark、合入，再上传日志进行真实 MiniMax 模型调查。初测 Harness 三组均通过；closed-loop 两组失败，原因是完整正文虽保存在工作区，但未进入模型请求。已修复 `localization_agent.py` 从冻结的 `skills.json` 读取全部正文；独立跑分 worker 同样传入冻结 Skill 快照。正文不再受简短 Prompt 的 30000 字符截断影响，仍受现有工具和 JSON 报告协议约束。

复测 8/8 检查通过，其中五组真实模型报告验证：Harness 分别选择 A、B；Harness 个人组合 A 覆盖临时 B；closed-loop 直接选择 A；closed-loop 个人组合 A。报告包含正文独有随机标记、日志中的请求编号、2400/1200=2 的实际计算与各 Skill 指定的下一步动作，且未出现未选中 Skill 的标记。未审核草稿不可选也通过验证。新回归含超过 30000 字符的完整正文及评测显式冻结快照，Python 65/65 通过。详见 [逐项记录](skill-selection-acceptance-20261025.json)。测试使用独立数据实例，不向生产 Skill 集合或业务任务写入合成记录。

2026-10-25 本地 Node 接口回归 50/50、Python 回归 64/64 通过。新增用例覆盖二进制入池、跨账号隔离、重复复用、Prompt 分离、报告净化、ZIP 全格式展开、路径穿越、链接、展开资源限额，以及 Chat 网关的凭据隔离、流式转发和截断流拒绝伪造成功。

真实部署验收见 [记录](harness-minimax-acceptance-20261025.json)：MiniMax-M2.7 + 原生 Harness SDK 在约 55 秒完成合成材料调查，自动展开三份异构文件，工具轨迹、报告回传及重复复用均通过；原 closed-loop Chat 流程也生成报告。这是集成验收，不是实际故障根因能力评测。

## MiniMax 服务器部署（2026-10-25）

当前 release：`/opt/kernel-insight/releases/minimax-harness-20261025`。网站与网关均受项目 Supervisor 管理。容器原有 bootstrap 机制已接入 `scripts/boot-supervisor.sh`，当前运行时重复执行返回成功；未人为重启服务器做整机冷启动验收。

两条定位路径均使用 `MiniMax-M2.7`，通过仅监听 `127.0.0.1:11436` 的 `scripts/chat-gateway.py` 调用 MiniMax 官方 Chat API。服务器的上游地址已实际验证为 `https://api.minimax.cn/v1`。密钥在服务器 `/opt/kernel-insight/services/minimax/credentials.json` 中，以 root 私有目录和 0600 文件权限保存，不进入 Git、任务请求、Agent 环境或沙箱挂载。该配置至少包含 `baseUrl`、`model`、`apiKey` 三个字段；变更后重启网关。

MiniMax 工具流实际返回终止 `finish_reason`，有时省略 `[DONE]`。网关仅在观察到明确终止帧、上游正常结束且未收到 `[DONE]` 时补发结束帧；截断流仍按错误处理。消息、工具历史和推理字段原样转发。

服务器网站仍监听回环 `8787`。从客户端访问：

```bash
ssh -p 30690 -N -L 127.0.0.1:8788:127.0.0.1:8787 root@120.209.70.195
```

然后打开 `http://127.0.0.1:8788`。SSH 密码只交互输入。管理与维护使用原有 Supervisor 配置；`manage-supervisor.py --restart` 现在按已启用的程序及优先级重启，包括 MiniMax 网关，不再强制启动停用的 Ollama 适配器。

SDK 行为参考：[官方 Python SDK 文档](https://deepseek-harness.github.io/deepseek-harness/en/guide/python-sdk)。
MiniMax 协议参考：[官方 OpenAI 兼容 API 文档](https://platform.minimax.cn/docs/api-reference/text-openai-api)。


## Skill 压缩包投稿与原生调用（2026-10-25）

当前生产 release 为 `/opt/kernel-insight/releases/skill-archives-20261025`。

投稿页上传 ZIP / TAR / TGZ / GZIP 压缩包，名称可以省略，贡献者默认当前账号；补充说明可选，保留规则分类 / 完整 Agent 两种 Benchmark 方式。包内至少有一份标准 `SKILL.md`，同时保留 scripts、references 等资源，最多支持 20 份 Skill。示例：

```yaml
---
name: kernel-oops
description: 分析首个内核异常，按正文约定生成报告。
triggers: [KASAN, ovl_inode_upper]
---
```

正文写实际步骤和报告要求。名称必须为英文小写 kebab-case。触发词读取 YAML 的 triggers / keywords / patterns、metadata 下同名字段，或正文“触发词 / Keywords / Triggers”段落；无需网页手填。未声明触发词可使用完整 Agent 测试，规则模式必须有触发词。类别优先读取包内 category，其次按触发词推断，无法识别则标为待专家分析。

上传时展开至 `data/skill-pulls/<id>/package/content`，原包和每个展开文件均封存 SHA256。投稿者和管理员可下载原包审查。包不能跳过人工审核；审核通过后手动运行所选 Benchmark，测试通过仍不立即发布。管理员合入时复核包指纹和基线，才发布到 `data/harness-home/skills/<name>/SKILL.md`。重名拒绝发布，避免覆盖已有 Skill。旧 JSON 投稿 API 继续兼容。

普通任务仅能选择已启用 Skill。Harness 运行时把选中的已发布包复制到任务自身 `dsh-home/skills` 并只读挂载，冻结个人组合保留包指纹。原生 skill registry / filesystem / tool 插件通过 SDK patch 加载，禁止扫描其他默认目录；Prompt 可写 `/kernel-oops`。任务 JSON 只列原生 Skill 名称，模型用 `skill` 工具按需加载正文，再读该包参考资料或调用其辅助脚本。未合入包不会加入普通任务目录。

Benchmark 两种模式的含义保持不变：规则模式检验类别匹配和回归；完整模式用 closed-loop Chat 对照执行 Skill 正文，尚不代表原生 Harness 脚本/资源的逐项验收。两者通过都只能说明相应测试通过，不能当作根因准确率证明。

[独立实例真实验收](skill-archives-acceptance-20261025.json)覆盖上传提取、私有暂存、跳过审核拒绝、过早发布拒绝、规则测试通过后仍私有、合入后资源发布及原生 Prompt 调用。MiniMax-M2.7 实际发起 `skill(name=archive-proof)`，报告包含仅存于 references 文件的随机标记及日志测量值；Skill 正文未直接放入任务 JSON。测试数据保留在服务器独立验收目录，未写入生产投稿或榜单。本地 Node 57/57、Python 66/66 通过。
