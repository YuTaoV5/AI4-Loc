# SGLang 部署 Jev-like 决策模型：配置与操作记录

记录日期：2026-10-09（北京时间）。这里的 Jev-like 指“输入状态和有限问题，输出类型化概率”的接口形态，不等于 TypeSafe Jev 的原始权重，也不代表概率已在内核定位任务上校准。

## 先选对部署路线

|路线|模型文件|API|能否继续 Chat|关键区别|
|---|---|---|---|---|
|通用生成模型做有限决策|完整生成模型、tokenizer、Jinja chat template|`/v1/decisions`；兼容 System One 时也可 `/v1/systemone`|可以|从下一 token 的指定标签概率读出结果，无需专用训练头|
|专用 PPLX-Decider v1/v1.1|checkpoint 原有 config/tokenizer + decision_config.json + readout.safetensors + 完整 backbone|`/v1/systemone`|不能视为有意义的 Chat 模型|使用训练时的专有提示、255 个 answer code 和温度；不能套用通用 A/B 标签格式|
|其他 Jev-like 实现|依其模型卡/参考推理代码|可能是自有接口|依架构|仅有 decision_config.json 不代表 SGLang 已支持；必须确认架构、提示模板、readout 和 token IDs 一致|

[官方 Decision 文档](https://docs.sglang.io/docs/supported-models/decision_models)说明通用路线无需额外启动开关。专用路线请分别按 [PPLX-Decider v1](https://docs.sglang.io/cookbook/autoregressive/Perplexity/PPLX-Decider-v1-27B) 与 [v1.1](https://docs.sglang.io/cookbook/autoregressive/Perplexity/PPLX-Decider-v1.1-27B) 文档检查支持版本。专用支持在 0.5.21 之后合入，不能仅凭当前服务器的 0.5.21 版本号认定支持。

## 当前服务器真实配置

当前保留的服务：

```bash
/root/systemone-venv/bin/python -m sglang.launch_server \
  --model-path /root/gpufree-data/systemone/models/Qwen3.8-27B \
  --served-model-name Qwen3.8-27B-SystemOne \
  --host 127.0.0.1 --port 30000 \
  --dtype bfloat16 --context-length 8192 \
  --mem-fraction-static 0.70 --max-running-requests 4 \
  --mamba-full-memory-ratio 0.6
```

这是通用 Qwen 生成模型的 Decision 接口，别名里的 SystemOne 不是检查点类型证明。模型目录未发现 decision_config.json。当前 `/v1/decisions` 和关闭 thinking 的 `/v1/chat/completions` 均已实际调用成功。GPU 为 A100 80GB，上一轮观察总占用约 79.9GB，包含既有服务；没有足够余量再并列装载一个 BF16 27B。此次未更换权重、升级 SGLang 或重启平台模型。

## 通用生成模型：需要改什么

最小命令仍是 `python -m sglang.launch_server --model-path <完整模型目录> --host 127.0.0.1 --port 30000`。以下是调节项，不是全部必改：

|参数/配置|选择依据|
|---|---|
|`--model-path`|换为支持的完整生成模型目录，固定 Hugging Face revision 或本地文件哈希|
|`--served-model-name`|客户端模型别名；不会把生成模型转换为专用决策头|
|tokenizer/Jinja template|优先使用模型自带模板；必须在答案位置把各标签编码为不同的单 token|
|`--context-length 8192`|包含证据、问题、选项、模板；不能只计算原日志长度。先裁剪证据窗口，不用自动截断删除答案位置|
|`--dtype bfloat16`|当前 A100 使用 BF16；变更量化后重测标签选择和概率漂移|
|`--mem-fraction-static`|按同时运行的模型和实际显存余量设置；0.70 只记录当前值，不是通用推荐|
|`--max-running-requests`|先小并发测 p50/p95，再提高；问题批量也消耗预填充资源|
|`--mamba-full-memory-ratio`|混合线性注意力模型的内存分配选项；纯 Transformer 不照抄|
|thinking|`/v1/decisions` 自动关闭并拒绝重新开启；同服务 Chat 如需关闭，显式传 `chat_template_kwargs: {enable_thinking:false}`|
|缓存与确定性|记录缓存冷热和批次；需要严格重现时单独评估 `--disable-radix-cache` 的速度代价，不直接修改在线服务|

避免 `--skip-tokenizer-init`、`--enable-mis`、`--dllm-algorithm` 和非 Jinja 的内置 conversation template。Decision 服务不设置 `--preferred-sampling-params` 默认 temperature，避免混批影响评分；请求自身的 temperature=1 是标签归一化参数。`--reasoning-parser qwen3` 影响 Chat，不是启用 Decision 的必要开关。

通用接口最小请求：

```bash
curl http://127.0.0.1:30000/v1/decisions \
  -H 'Content-Type: application/json' --data-binary @request.json
```

```json
{
  "input": "BUG: KASAN: use-after-free in worker+0x1/0x20",
  "questions": [{"id":"family","type":"choice","question":"What is the first diagnostic?",
    "options":[{"name":"uaf","description":"Explicit use-after-free"},
               {"name":"unknown","description":"Not enough evidence"}]}],
  "temperature":1,"prompt_format_version":1,"return_prompt_token_ids":true
}
```

choice 为 2–26 项，score 为 2–10 级，yes_no 为两个标签。问题独立评分，不要让后一问依赖前一问的未知输出。响应必须有 completion_tokens=0、概率和约等于 1、选中项属于给定选项；保留 prompt/token IDs、版本、耗时和失败请求。label_mass 是完整词表中标签的概率质量；归一化概率和 label_mass 都不是内核诊断正确率。阈值须用独立开发集校准。

## 专用 Decider：与现有服务不同的部署步骤

1. 使用独立环境或容器，不在现有 0.5.21 环境原地升级。按官方安装指南选择匹配驱动的 CUDA 构建；文档当前提供 nightly/dev 镜像。部署前固定实际 wheel/version/commit 或容器 digest，不能只记录会漂移的 dev 标签。
2. 下载目标检查点的完整固定 revision，保留 decision_config.json、readout.safetensors、模型权重和 tokenizer。不要只拷贝 backbone，也不要自行将通用模型的 architecture 字段改成 Decider。
3. 在有足够空闲显存的 GPU 上启动；BF16 27B 权重约 52GB，另需运行时、激活及状态空间。官方性能数据主要来自 H200/GB300，不能直接移植成 A100 承诺。

示例是待在目标硬件验收的起点，不是本服务器已执行命令：

```bash
/path/to/new-venv/bin/python -m sglang.launch_server \
  --model-path /models/pplx-decider-v1.1-27b \
  --served-model-name kernel-decider \
  --host 127.0.0.1 --port 30001 --dtype bfloat16 \
  --context-length 8192 --max-running-requests 2
```

|模型专有项|v1|v1.1|
|---|---|---|
|接口|System One|System One|
|attention_mode|按原检查点|noncausal_full_attention，由服务读取配置|
|radix/chunked prefill|缓存策略需实测；官方 GB300 unique-state 配方关闭 radix|服务自动关闭两者，不能强开以破坏全提示依赖|
|温度|使用检查点训练/校准值|使用 v1.1 的值，不继承 v1 阈值|
|上下文|先限制训练覆盖的 8192 token|同样先限制 8192，不把更长可运行等同于准确性已验证|
|Chat|另一个生成模型承担|另一个生成模型承担|

在 A100 上不要照搬 GB300 的 TRT-LLM attention、FP8 或 page-size 优化。先跑默认 BF16 和参考实现的概率/选项一致性，再测试替代内核及量化。

System One 请求形状：

```json
{
  "model":"kernel-decider",
  "state":"BUG: KASAN: use-after-free in worker+0x1/0x20",
  "questions": {
    "family":{"type":"choice","instructions":"Classify the first diagnostic",
      "criteria":{"uaf":"Explicit use-after-free","unknown":"Insufficient evidence"}},
    "causal_gap":{"type":"noul","instructions":"Is independent causal verification missing?"}
  }
}
```

发送到 `/v1/systemone`。不要携带 `/v1/decisions` 的 prompt_format_version、temperature 或 return_prompt_token_ids；专用模型没有完整词表 label_mass，不要伪造。API 形状兼容不意味着模型行为或校准可互换。

## AI4Loc 配置与验收清单

通用模型的分层 Agent：

```text
KERNEL_DECISION_BASE_URL=http://127.0.0.1:30000
KERNEL_DECISION_API=decisions
KERNEL_BOUNDARY_ROUTER=decision
```

未来接入已验收的专用检查点时：

```text
KERNEL_DECISION_BASE_URL=http://127.0.0.1:30001
KERNEL_DECISION_API=systemone
KERNEL_DECISION_MODEL=kernel-decider
KERNEL_BOUNDARY_ROUTER=decision
```

Chat 的 KERNEL_AGENT_BASE_URL/MODEL/TRANSPORT 保持独立，承担源码检索、机制分析和证据引用。新的 DecisionClient 显式转换 choice/yes_no/score 到 System One 请求，保留真实原响应；此路径已用现有通用服务验收，**未在专用权重上实测**。

上线前记录：SGLang build、模型 revision/文件哈希、GPU/驱动、全部有效启动参数、模板/答案 token IDs、健康与错误响应、冷热缓存、短长日志、并发 p50/p95、分类命中和拒答率。先用同一个生成检查点比较 Decision/Chat；再单独比较专用小模型，避免把硬件或模型大小差异误归因于 API。API 密钥通过运行环境注入，不提交 GitHub。
