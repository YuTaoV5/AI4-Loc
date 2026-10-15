# Qwen3.5-9B 决策训练与实测

训练与两模型复测均已完成：396微步/99次更新，5,308,416个训练参数，开发NLL选择epoch1，合并权重已导出并生成哈希。每模型112个性能trial及522个分类请求；独立32k兼容修复后两模型共12个完整Agent流程全部输出有效报告。原27B服务已恢复，真实Decision/Chat内容验收通过。完整分析见 [实测报告](REPORT.md)，公开表格/图见 `tables/`、`figures/`，32k闭环证据见 `agent32k/`。

## 模型定义与参考

- 用户确认基座为 [官方 Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B)，固定 revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`。`official-model-metadata.json` 保存独立官方文件大小及 LFS SHA256 / Git blob SHA1。
- 参考 [Laya](https://github.com/NandhaKishorM/laya/tree/4ac226d5ee88ed6df8db288a05c766d7a34ee682) 的类型化概率决策、proper scoring rule、RLCD 与开发集校准流程。它发布的 BERT 编码器及双向决策头不能直接用于 Qwen。本实现是在预训练 Qwen 因果混合注意力骨干上新建、训练零初始化 LoRA，不是从随机参数预训练 9B，也不是 TypeSafe Jev 专有权重的复现。
- 概率接口使用 SGLang 原生 `/v1/decisions`：在单次前向的下一 token logits 中归一化候选字母，不生成文字；8 题仍是 8 个内部评分请求，不声称共享题干只计算一次。训练后的适配器合并成原架构权重，两端均以相同 SGLang 运行，从而避免 BERT/Transformers 与 Qwen/SGLang 的引擎混杂。
- [Microsoft Foundry 概览](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/foundry-models-overview) 提供模型发现、微调、部署和可观测性的一般框架，没有给出 Jev 训练算法；本实验不调用 Azure，也未创建计费云资源。

## 数据与可支持的结论

`prepare-data.py` 从服务器真实 stability 日志及 OpenHarmony 日志构造第一诊断家族任务。源文件先按清单校验，跨内核的同一规范化注入机制归为同组；历史测试组取并集，其他组用固定哈希划分开发/训练。选项置换在划分后发生，不能增加独立样本量。训练前冻结清单；模型只看到诊断窗口、问题和候选项，不能看到 case、split、gold、路径或机制字段。人工注入命令及注入函数名进行遮盖，保留诊断文字和真实栈证据。

冻结数量为训练 33、开发 4、测试 87。标签来自第一诊断的确定性弱监督，不是独立专家根因标注。开发集极小，未覆盖全部类别；部分测试类别未在训练出现；旧测试已被开发者查看，不是全新盲测。必须按家族、机制及内核分别报告，不能用总准确率声称完整根因定位能力提高。自然日志、近重复和预训练污染无法仅凭字段审计排除。

## 执行与文件

服务器研究目录：`/opt/kernel-insight/experiments/jev-qwen35-9b-20261016/`。原始输入、完整请求/SSE、进程环境和权重保留在服务器/本地 Git 忽略目录；公开导出仅含允许字段。

1. `reclaim-inactive-pplx.py`：已获用户清理授权，检查端口、进程 maps/cmdline/fd，逐一 SHA256 核验 11 个固定版本 PPLX 权重分片后删除；保留原代码、tokenizer、配置及恢复元数据。生产 27B 权重、业务状态和数据集不删除。
2. `fetch-checkpoint.py`：带浏览器 User-Agent 经镜像下载固定版本，按独立官方元数据校验；支持断点、重试和磁盘余量检查。
3. `prepare-data.py`：冻结私有输入及公开数据划分/监督依据/排除记录。
4. `train.py`：BF16 骨干、FP32 rank-8 LoRA/优化器，48 处文本投影，3 epoch，每例每 epoch 4 个选项置换。epoch0 用 CE，后续 CE+RLCD；按开发 NLL 选 epoch；温度只用开发集。保存逐步 loss、耗时、显存、适配器和合并权重哈希。
5. `orchestrate.py`：下载完成前生产保持运行；确认无业务任务后分时复用 GPU。核对 PID/启动 tick，独立守护最长 4 小时，异常退出恢复 Supervisor；最后实调原 Decision 和 Chat 验收。
6. `benchmark.py` / `sitecustomize.py`：基座与训练后模型各执行完整 112 trial、980 正式 HTTP、1330 内部评分；同题干、变选项、1/4 任务 × 1/8 决策 × 冷/热 × 5 重复，另有批量8题和观测敏感性。两边实际并发上限必须为4；完整 prompt token 序列逐项核对。
7. `accuracy.py`：87 个测试案例、3 种固定选项置换、Decision 与单 token Chat 两接口分别评估。只将案例/机制作为独立单位；标签在响应之后用于本地评分。这个准确率测试与性能窗口实验分开。
   `agent-check.py` 另用释放后使用、ABBA 锁、hung task 三案例，运行纯 Chat 与 Decision 定界＋Chat 根因流程，两模型各6次。沿用已部署 Agent 的源码、匿名目录与 bubblewrap；初轮仅在冻结副本显式关闭thinking，修复轮另处理`tool_calls:null`，两侧同样设置，不改生产。这个小样本只报告源码位置命中、调用次数、耗时和失败，不能证明根因机制准确率提高。
8. `export.py`：公开逐 HTTP、概率、Chat 内容抵达时间、原生排队/prefill 计时、调度边界 attention KV/linear 状态/torch allocator、100ms NVML 显存和功耗、Prometheus。原生请求按完整 prompt token SHA 与接收时间唯一关联。

## 测量边界

Decision 的指标是完整概率响应时间，没有文本 TTFT；Chat 指标是第一个非空 `delta.content` 抵达时间，不能用响应头、role 或 reasoning 代替。Chat 性能实验仅生成 1 token，不代表完整根因报告耗时。一个非空空白字符串仍算内容，原始 SSE 保留以便重算更严格口径。

排队/prefill 为 SGLang 原生主机时间，调度观察在 run/result 边界，不插入 CUDA 同步；不是逐 kernel CUDA 事件测量。NVML 约100ms，不能观察更短峰值，也不提供逐请求独占功耗。GPU 板级能量按时间积分，只能报告整段/整 trial，不能把并发时每个请求各记一份。预分配 resident 显存、活跃 attention KV、可回收缓存和 linear 状态槽分别报告。9B 每 token 全注意力 KV 为 32KiB（8层×K/V×4头×256维×BF16），与旧27B的64KiB不能混为接口收益。

固定执行顺序为训练→基座→训练后，两模型比较仍可能受温度/时钟/时间趋势影响；同模型内 Decision/Chat 的 trial 随机化。重复是同一4输入的运行重复，不是跨项目普适显著性。

首次启动因新版 tokenizer 的 tokenized chat-template 返回类型不兼容而退出，0 优化步骤，自动恢复原 Decision/Chat 均成功。修正为先渲染字符串再显式编码后，在独立 `...-run2/` 重启；失败目录保留，数据划分未变。正式复测目录为 `/opt/kernel-insight/experiments/jev-qwen35-9b-20261016-run2/`。

## 重新执行

先复制脚本与固定元数据到**新研究目录**，下载并校验权重、冻结输入、安装独立 `deps` 中的 `flash-linear-attention==0.5.2 fla-core==0.5.2`（不修改生产环境）。在维护窗口运行：

```bash
nohup /root/systemone-venv/bin/python orchestrate.py > controller.log 2>&1 < /dev/null &
```

不要对已有 lease/冻结记录重复运行，也不要脱离独立恢复守护直接停止生产。原始数据、训练中间权重和完整请求不能推送 GitHub；共享代码、固定元数据、派生表格及报告即可。

## 推理启动参数与 Agent 接入

以下命令必须在已释放足够GPU显存的维护窗口使用，不能直接与当前60GB的27B常驻实例叠加。本研究控制器完成相应安全检查和自动恢复。

```bash
/root/systemone-venv/bin/python -m sglang.launch_server \
  --model-path /root/gpufree-data/systemone/models/AI4Loc-Jev-Qwen3.5-9B \
  --served-model-name AI4Loc-Qwen9B --host 127.0.0.1 --port 30003 \
  --dtype bfloat16 --context-length 8192 \
  --mem-fraction-static 0.55 --max-running-requests 4 \
  --mamba-full-memory-ratio 0.6 --max-mamba-cache-size 32 \
  --enable-metrics --decode-log-interval 1 \
  --enable-request-time-stats-logging \
  --export-metrics-to-file --export-metrics-to-file-dir ./request-metrics
```

8192用于固定接口性能实验；已发现完整Agent的真实prompt达17.7k/20.7k，不能用这个容量宣称完整流程可运行。另用 `orchestrate-agent32k.py` 在独立目录、相同两模型顺序和其他参数下，设置 `--context-length 32768` 重测完整流程；这批数据不能混入8k并发性能分母。SGLang0.5.21从官方chat模板自动识别 `qwen3` reasoning parser 与 `qwen3_coder` tool-call parser；运行日志保留识别结果。Agent Chat请求显式传 `chat_template_kwargs={"enable_thinking":false}`。

首次32k检查还发现既有客户端将 `tool_calls:null` 当列表遍历；该轮受控停止、自动恢复并保留部分失败结果。修复为空列表归一化后，在 `/opt/kernel-insight/experiments/jev-qwen35-9b-20261016-agent32k-fixed/` 对两个模型完整重跑。当前仓库 `scripts/localization_agent.py` 已包含这两处兼容修复，未切换生产权重；不能把上下文或客户端修复当成训练收益。

私有归档保留了3个epoch适配器，可用 `merge-adapter.py --base <固定基座目录> --adapter <adapter-epoch1.pt> --output <全新输出目录>` 重新合并。需要足够显存；原服务器完整合并权重和 `trained-checkpoint-manifest.json` 是发布指纹，跨CUDA/库版本重建不保证逐位相同。

现有项目原生客户端接入为 `KERNEL_DECISION_BASE_URL=http://127.0.0.1:30003 KERNEL_BOUNDARY_ROUTER=decision`，根因Chat为 `--base http://127.0.0.1:30003/v1 --model AI4Loc-Qwen9B --transport openai`。服务接口支持不等于所有题型都被训练；目前训练监督仅涉及第一诊断family的choice，stage/reporter/owner等需独立验证。生产切换不在本轮动作中，不能将训练完成解读为自动上线。
