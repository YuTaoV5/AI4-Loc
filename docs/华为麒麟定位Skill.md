# 华为麒麟手机定位 Skill

本次提供的是 DeepSeek Harness 项目 Skill 包，不是 Codex 个人 Skill。压缩包：[huawei-kirin-log-triage-v1.zip](../deliverables/skills/huawei-kirin-log-triage-v1.zip)，源码：[SKILL.md](../tools/harness-skills/huawei-kirin-log-triage/SKILL.md)。

参考适配目标是 **HUAWEI Pura 90 Pro Max / 麒麟 9030S / HarmonyOS 6.1**，来自 [华为官方规格](https://consumer.huawei.com/cn/phones/pura90-pro-max/specs/)。该名称只是研究目标，不能当作用户上传设备的识别结果；未获得该目标的真机完整启动日志、厂商解码器、私有符号或固件源码。

Skill 适用于手机日志取证、启动阶段关联和有证据的初步定位。它不承诺对所有麒麟固件或加密维测格式直接解码。

## 包内内容与行为

- `SKILL.md`：触发词、设备识别、阶段证据、跨启动关联、最早异常与下游症状区分、证据不足和报告要求。
- `scripts/inventory.py`：仅依赖 Python 标准库，只读文件清单及每文件前 256 KiB，最多列 500 个文件；不联网、不调用子进程、不执行材料、不解密。保留实际属性的文件和行号，不复制序列号等无关标识。采样索引不是全量日志扫描或根因结论。
- `references/platform-scope.md`：参考目标、官方来源与不能据此推断的内部细节。
- `references/investigation.md`：命令抓取失败、时间域、源码匹配、加密数据和证据检查表。

用户不用在网页填写内核 commit 或固件版本。Skill 优先从日志中读取身份、构建与时间信息；若有源码缓存和符号，需要核对精确构建后才使用。无法核对就声明代码级定位尚未验证。普通 Linux 输入继续使用调用方既有诊断 JSON，不强制归为手机问题。新 HarmonyOS 输入也不能默认存在 Android logcat / zygote。

## 使用

投稿页上传 ZIP，选择完整 Agent Benchmark。包先保存在私有投稿目录，平台审查与 Benchmark 通过后才可合入公共目录。网站审核的完整 Agent 测试仍是既有内核案例的 baseline/candidate 类别回归，不代表手机机制能力已验证，因此另做私有原生手机场景和真实日志验收。

合入后，新建分析选择 **DeepSeek Harness · Skill 自主定位**，在自定义 Skill 中选择 `huawei-kirin-log-triage`，Prompt 示例：

```text
使用 /huawei-kirin-log-triage 分析这份手机日志。
先确认实际设备、系统和材料覆盖，再关联同一次启动的首个异常与后续症状。
给出文件、实际行号或字节偏移和短原文引文；无法确定的根因请明确列出缺失证据和最小验证步骤。
```

没有该目标真机日志时，可先使用手机样本页的 HUAWEI L29 包。报告必须保留实际观测身份，不得改称 Pura 90。

## 回归与发布原则

除网站原有 Benchmark 外，独立原生候选测试只把待审包的冻结副本装入私有沙箱。测试用本地启用标志不会修改生产投稿状态，也不写公共 Skill 目录。生产发布仍由审核和 Benchmark 门禁控制。

本轮技术审查由 Agent 执行并在网站审查记录中明确标注；不伪称人工厂商认证。若任一必要测试失败，不以手工改分或直接改状态发布。


## 2026-10-26 验收

包 SHA256：`0db2b018f65677cb6514e5e3f784ab50200bfdd5eadce0d57c3681e5dd690275`。上传归档与仓库 ZIP、逐文件源码已核对一致。

- 网站完整 Agent 模式完成 7 例 × baseline/candidate = 14 次真实调查，基线和候选类别得分均为 1.0，0 退化。此项评估旧内核案例的类别兼容性，不是手机根因能力提升。
- 私有原生候选测试 8/8 生成有效报告，受控手机场景 100/100，含加密及缺失材料；与此前无此 Skill 的受控基线同分，不声称提升。
- 真实 HUAWEI L29 包：原生 `/huawei-kirin-log-triage` 由 Harness 的斜杠 Skill 注入生效，执行包内索引工具；报告识别实际 DEL-LX9 / DEL-L29、属性中的 Kirin9030Pro 与 Android release 12，但不把它当成 Pura 90，也不把属性字符串当硬件营销型号认证。正确指出 `Unexpected klogctl return value: -1` 是抓取失败；不宣称根因已验证。引文逐条核对存在于输入。
- 真实验证最初校验器误以为这些 JSON 字段一定是字符串、且必须显式调用 skill 工具；原请求允许嵌套对象，Harness 也支持斜杠注入。校验器按实际字段结构核对相同原始属性，并检查会话中的具名 skill_content，未改动模型报告或金标准。
- 通用平台触发词保留 Skill 调用归属，但在规则分诊中不再覆盖更具体的 KASAN / UAF / hung task / lockdep / RCU / OOM 类别。Node 59/59、Python 71/71 回归通过。

索引是严格 UTF-8 的有限采样，无法识别或采样边界不完整时可标为 opaque；opaque 本身不代表加密，须按 Skill 用额外有界窗口核对。未使用目标机型真机、厂商维测解码器或私有固件符号验证。


已通过网站正式合入接口发布，投稿 ID `7246a41b-ca00-418d-9646-0737619246ee`，状态 `merged`，公共目录为 `data/harness-home/skills/huawei-kirin-log-triage`。14 次网站调查共记录 64 次模型请求；原生手机套件中 6 例生成索引文件，真实包也验证了索引执行。验收摘要见 [kirin-skill-acceptance-20261026.json](kirin-skill-acceptance-20261026.json)。当前部署 release 为 `/opt/kernel-insight/releases/kirin-skill-20261026`。
