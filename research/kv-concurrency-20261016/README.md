# Qwen3.8 并发决策与 KV cache 实测

2026-10-16，真实服务器 A100 80GB / SGLang 0.5.21。同一 Qwen3.8-27B 实例，对照 Decision 与关闭 thinking、输出单字母的流式 Chat。

- [完整中文报告](REPORT.md) / [离线网页](report.html)：11节方法、结果、原始字段说明、局限与复现步骤，6组SVG/PNG图。
- [逐条件统计](tables/summary.csv)、[逐trial](tables/trials.csv)、[逐调用和TTFT](tables/calls.csv)、[原生服务端请求](tables/server-requests.csv)。
- [每个调度边界的KV/状态池](tables/scheduler-snapshots.csv)、[边界内每个请求](tables/scheduler-requests.csv)、[NVML时间序列](tables/gpu-samples.csv)、[Prometheus时间序列](tables/prometheus-samples.csv)。
- [冻结协议](data/protocol.json)、[运行参数](data/runtime.json)、[输入窗口描述](data/input-profile.json)、[对齐与计数审计](data/audit.json)、[恢复后真实推理验证](post-restoration-validation.json)。
- `data/`保存公开的逐调用概率/内容到达、原生请求时间、压缩调度与监控记录；完整输入和原始日志只在私有归档。

正式112个trial、980次HTTP、1330个内部问题评估；另2个全局预热、125个prime不计入正式分母，4个prompt对齐预检及SGLang启动生成单列。正式1330个内部请求均唯一关联到客户端调用；465对顺序对照的实际完整prompt token SHA256一致；所有HTTP成功。不是准确率实验。

主要结果：单次决策基本没有速度收益。热条件下1任务×8步，Decision/Chat整批均值1.366/1.544s；4任务×8步3.634/4.085s（约11%减少）。后者活跃KV峰值均值916.438/916.250MiB、活跃线性状态16/13槽，未显示内存节省。Decision没有文本TTFT，报告区分完整概率返回与Chat首个非空内容。

一次HTTP批量8题不等于一次prefill，本轮比顺序8步更慢；详见完整表。冷/热仅代表flush/prime操作，实际cache hit另行记录，prime不保证命中。

原服务CLI允许4请求，实际被9个状态槽限制为1。正式隔离实例使用静态比例0.78、32个FP32状态槽，实际容量和观测批次均达到4。生产恢复原0.70/auto9/实际1配置；更大状态池尚未上线。[启动区段采集校准](../kv-concurrency-20261015/README.md)单独保留，不能跨输入窗口/配置做单因素提速归因。

离线复算：Python + NumPy + Matplotlib，在本目录运行 `python analyze.py`、`python build-report.py`。`python verify.py`核验公开数据；本机私有归档存在时也逐文件验SHA256。图表不需要网络或模型调用。

原始证据服务器：`/opt/kernel-insight/experiments/kv-concurrency-20261016/`；本地Git忽略目录：`data/local-archive/kv-concurrency-20261016/retained-evidence.tgz`。大小、SHA256和文件数见 [archive.json](archive.json)。归档排除捕获的原进程环境和恢复lease；不包含账号数据库或权重。公开清单 `data/SHA256.json` 校验采集派生文件，根目录 `SHA256SUMS` 校验此次完整发布材料。
