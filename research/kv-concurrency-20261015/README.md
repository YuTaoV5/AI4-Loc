# 原配置启动区段采集校准（不并入正式故障窗口结果）

2026-10-16跨午夜采集，目录沿用启动日期20261015。完整112个trial、980次HTTP、1330个问题评估全部保存。输入为现有4份日志最初6000字符，主要是启动上下文；不用于问题定位准确性判断。

本轮保留生产内存参数0.70和自动状态池，发现CLI max-running-requests=4最终被9个状态槽、每请求5槽预算限制为实际1。调度观测最大批次也为1。一次SIGINT取消尝试因nohup继承忽略而未生效，最终正常完成；该历史说明与completed状态均保留。之后另起新的正式故障窗口实验，并验证实际容量4。

- [正式研究与完整报告](../kv-concurrency-20261016/README.md)
- [协议](data/protocol.json)、[最终运行参数](data/runtime.json)、[校准归类说明](data/calibration-classification.json)、[计数审计](data/audit.json)
- [条件统计](tables/summary.csv)、[逐调用](tables/calls.csv)、[逐调度边界](tables/scheduler-snapshots.csv)
- [私有归档元数据](archive.json)

本轮与正式轮输入窗口、状态池预算不同，不应把两轮时间差作为扩大状态池的单因素消融。冻结执行源文件保留在本目录；派生分析使用正式研究目录的analyze.py，传入本目录data和输出目录即可。私有完整证据在服务器同名experiments目录及本地Git忽略的data/local-archive同名目录。
