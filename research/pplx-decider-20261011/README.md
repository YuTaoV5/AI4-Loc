# PPLX-Decider 专用权重实测

本目录独立于此前通用模型 Decision/Chat 报告。真实 checkpoint 为 `perplexity-ai/pplx-decider-v1-27b`，固定 revision `b01a5cbaca5391f73bd55103d4f27e8982cd5e60`。结果以 [REPORT.md](REPORT.md) 与 `results/statistics.json` 为准。

## 范围

121 次正式调用：9 个既有 test 案例×3 次×2 模型，16 个其他可映射 train 案例×1 次×2 模型，35 个未覆盖家族×1 次 PPLX。另有两次不计分合成预热。模型只收到第一现场日志状态与三个有限选项问题；本轮不评估源码、引入提交或根因定位，不把无真值案例算入准确率。

现有 A100 同时保留生产通用模型；PPLX 通过官方参考代码、专用 readout 和保存温度执行 BF16 CPU 卸载，GPU 权重额度 10 GiB。通用模型使用 SGLang 全 GPU。因此耗时仅描述实际部署，不能证明 PPLX 原生全 GPU 或 SGLang 性能优劣。GPU 共享及不同提示/读出路径也阻止对纯权重收益作因果归因。

## 离线复现公开分析

```sh
python -m pip install -r requirements-analysis.txt
python analyze.py --public
python verify.py
```

不需要模型或服务器；从公开派生结果重新计算统计、四组 PNG/SVG 和 `report.html`。公开表不包含完整原始日志、Prompt、账号或 token ID；保留案例名用于追溯，模型没有收到单独的案例 ID 字段，但自然日志中部分 LKDTM 函数名与案例名重合。审计发现 63/121 次请求、41 个唯一案例存在这类文本，不能宣称完全去线索盲测。

## 执行脚本与环境

- `fetch-checkpoint.py`：读取官方元数据，固定 revision 下载，逐文件大小、LFS SHA256 或 Git blob SHA1 校验。镜像仅作传输，身份以官方元数据为准。
- `serve-reference.py`：调用 checkpoint 的官方 prepare/forward/answer，使用分层放置替代构造器整模型 `.to(cuda)`，以 `/v1/systemone` 提供兼容接口。绑定 loopback；实验完成关闭。
- `boundary-worker.py`：调用现有 DecisionClient，记录三个问题的选项概率及用量。
- `run-benchmark.py`：冻结协议、代码哈希、随机顺序；匿名 bwrap worker；父进程在调用结束后评分。
- `run-experiment.py`：等待下载、空任务队列及可用显存，管理临时服务，最终只关闭自身模型进程。

这些脚本保存当次实际执行的固定路径，用于审计，**不是可无条件重复运行的生产部署入口**。重跑需另建实验目录、冻结新协议，核验磁盘/内存/GPU及任务队列；不能覆盖本次工件。

实际环境：Python 3.12，Torch 2.13.0+cu130，Transformers 5.12.1，SGLang 0.5.21；隔离虚拟环境添加 Accelerate 1.15.0。复用了已有 Torch 等依赖，没有升级生产环境。CPU cgroup 内存上限 120 GiB、12 核 quota。完整 device map、加载时间、温度与 checkpoint 哈希见 `results/`。

## 保存与标签限制

服务器：`/opt/kernel-insight/experiments/pplx-decider-20261011/`。

私有完整证据：本地 `data/local-archive/pplx-decider-20261011/retained-evidence.tgz`，含逐次输入、响应、调用轨迹、匿名隔离审计、冻结源码及执行日志。Git 只保存脱敏派生表、协议、校验摘要、分析与实验脚本。大型权重可重复下载，保留服务器缓存而不进 Git。

注入家族不必等于日志第一条诊断；LOOP/SOFTLOCKUP 的第一诊断为 RCU stall，原始注入标签为 watchdog。保留冻结映射得分，另见 [数据标注缺口](../../docs/DATASET_DIAGNOSTIC_LABEL_GAP_20261011.md)。既有 test 已参与项目开发，不能称新机制盲测。无显著差异不构成等效或非劣证明。

官方来源：[模型、源代码及许可证](https://huggingface.co/perplexity-ai/pplx-decider-v1-27b)、[SGLang 说明](https://docs.sglang.io/cookbook/autoregressive/Perplexity/PPLX-Decider-v1-27B)。本仓库不复制第三方权重或官方源码；请按原仓库许可证取得。
