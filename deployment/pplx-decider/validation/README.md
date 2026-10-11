# 2026-10-11 实际部署验收

历史快照：以下PID和脚本哈希对应2026-10-11，不代表当前进程。后续全GPU分时复测与恢复见[2026-10-12报告](../../../research/pplx-timeshare-20261012/REPORT.md)；完整命令见[中文手册](../../../docs/PPLX专用模型下载部署与验收手册.md)。服务器恢复后已补充[2026-10-12新版常驻部署验收](../validation-20261012/README.md)，不覆盖此处历史结果。
最终状态以 `deployment-manifest.json` 的 UTC 时间为准：独立服务 PID 2638，在服务器 `127.0.0.1:30002` 返回真实 PPLX v1 ID/revision，保持运行。原模型30000 HTTP200、PID65仍在。GPU总占用71149MiB、余10003MiB，仅为该时刻快照。

| 验证 | 结果与证据 |
| --- | --- |
| 30个checkpoint文件二次校验 | 全通过，40.778秒，checkpoint-verification.json |
| 首次真实推理、三种类型、概率及DecisionClient | 通过，validation-first.json |
| 首次成功重启后接口 | 通过，validation-after-first-restart.json |
| 修复后的完整推理→停止→启动→真实推理 | 通过，validation-before-final-restart.json、lifecycle-validation-after-inference.json、validation.json |
| 负例 | 缺state、错误model、空choice分别422；Chat路由404 |
| 已部署脚本与Git文件 | 五个SHA256全部一致，deployment-manifest.json |

四轮成功接口验收，每轮一个三类型直接请求和一个现有Agent客户端请求，共8个真实推理请求；均为合成日志，不计入既有121次benchmark，也不是准确率/速度对照试验。中间服务关闭时发生的连接拒绝不冒充推理失败或成功。

曾发现并修复两个生命周期问题：CUDA显存释放延迟导致立即重启被保护门槛拒绝；退出过程中cmdline先清空导致停止等待误判。详见 attempt-notes.json 与 lifecycle-initial-failure.json。最终复验使用修复后源码。最终GPU等待仅0.045秒，不能据此声称已实测长时间等待或超时分支。

原始服务/安装日志与合成调用轨迹仅留私有归档：服务器 `/opt/kernel-insight/services/pplx-decider-v1/deployment-validation.tgz`、本地 `data/local-archive/pplx-deployment-20261011/deployment-validation.tgz`；8449字节，SHA256 `6c94eec0d033db11034f41bcf9c6a06536ecafbbd4abf50340005530d7ea6634`，两端一致。这里公开的请求全为合成内容，不包含用户账号、私有Prompt或业务日志。

本次没有网站任务/榜单写入、没有网站生产模型切换，没有原生SGLang专用模型、全GPU性能、自动重启或重启宿主机后的恢复验收。
