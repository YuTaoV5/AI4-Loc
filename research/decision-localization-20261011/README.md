# AI4Loc Decision 学术研究报告（2026-10-11）

本研究基于服务器实际证据，并新增 **135 次随机配对接口消融**。这是实证技术报告，未冒充已投稿、同行评审或获奖论文。

- [PDF](../../output/pdf/AI4Loc_Decision_Academic_Report_20261011.pdf)：21 页正文、参考文献与附录。
- [离线网页版](report.html)：下载本目录，直接打开；图表使用相对路径，无 CDN。
- [Markdown 正文](report.md)、[结构化正文](manuscript.json)。
- [统计结果](results/statistics.json)、[135 次公开派生记录](results/boundary-trials.csv)、[冻结协议](results/protocol.json)。
- [真实 Decision 返回示例](results/measured-decision-example.json)：保留问题选择与概率，不含原始输入或 token ID。
- [图表](figures/)：8 组可编辑 SVG 与 PNG；[流程图 Mermaid 源](system-flow.mmd)。

核心结论：当前三问题 Decision 平均客户端调用耗时 1.145s，Chat 2.075s，减少 44.8%；仅支持本组有限分类更快。两者 family 均 27/27，只有 9 个唯一案例、5 个机制组；家族级检验不显著。历史完整定位仍为 4/8→4/8，总耗时增加 8.96%，不能声称整体提速或根因提分。当前是通用 Qwen 检查点的 Jev-like 接口，不是专用 Jev 权重评测。

## 无服务器复现

Python 3.12+，安装依赖后在本目录运行：

```shell
python -m pip install -r requirements.txt
python analyze.py --public
python verify.py
python build-report.py
```

`--public` 仅使用已发布的 CSV/JSON 重算统计和全部图表，不访问服务器、不调用模型。已核对其统计 JSON 与私有原始数据路径的输出逐字节一致。`verify.py` 独立使用 SciPy 枚举配对置换，核对协议顺序、重复单位、源码冻结哈希和报告数字。

PDF 在 `../../output/pdf/` 生成。Windows 自动使用系统微软雅黑；Linux 可设置 `AI4LOC_CJK_FONT` 与 `AI4LOC_CJK_BOLD_FONT` 为 ReportLab 支持的 TrueType 中文字体路径，否则使用 STSong-Light（阅读器需支持 CJK 字体）。不分发系统字体文件。PDF 已逐页渲染检查。

## 服务器实验与证据

- 生产代码基线：Git `7e49c6b`，app `/opt/kernel-insight/releases/task-trace-20261011`。
- 新实验原目录：`/opt/kernel-insight/experiments/paper-20261011/`，协议先于正式模型请求写入；135 正式调用 + 5 排除的合成预热。
- 本地私有证据：`data/local-archive/paper-20261011/`。原始请求、输入日志、token ID 及 sandbox 轨迹不上传 GitHub。
- `retained-evidence.tgz` 为 3,647,762 字节，服务器与本地 SHA256 同为 `78e6c9d997bd69c750ceec8e22ac40842b4daf8d508c7a30725dae5c54cd72ad`。
- 历史三份输入与服务器哈希匹配，身份见 [来源清单](results/provenance.json)。历史 54 次分类、18 次完整定位、63 次早期消融分开分析，不拼接独立样本量。
- 初始化时因枚举 `__pycache__` 失败的目录单独保留；发生于正式推理之前，未删除正式失败。正式调用 0 失败、135/135 隔离检查通过。

`run-boundary-ablation.py` 和 `boundary-worker.py` 是实际执行的冻结程序。前者固定实验目录并用 `exist_ok=False` 防止覆盖原始证据。若重新运行，必须另存一个副本并改为新的实验目录；先确认 Linux bubblewrap、项目运行时、已有数据及模型服务，选择维护窗口。脚本等待生产任务队列清空后调用模型；不重启服务、不修改标签、不写公共榜单。实际协议只读接口实验，不是再次故障注入或完整定位实验。

完整系统实现对应仓库的 `scripts/boundary_router.py`、`decision_plugin.py`、`localization_agent.py` 和 `plugins/kernel-decision/`；协议中的冻结源码哈希均匹配本次基线。DSH 插件已有 smoke，但 135 次是独立 API worker，18 次历史定位是 closed-loop，不能冒称原生 DSH 全量跑分。

## 研究边界

阶段与 reporter 没有独立专家真值，机制与引入提交准确率未测。既有 test 已参与开发，不能作为新盲测；匿名目录和标签隔离不能证明预训练无污染。末尾窗口仍保留分类线索；D1 减少问题也减少功能。不同队列、缓存状态与验收数据不能混算。

报告第 17 节给出尚未执行的确认性研究：新机制盲测、责任代码与检测器分离、错误建议/硬路由/预检消融、资料缺失、双人标注、真实引入提交及修复重放。不能把计划的样本量写成已测数据。
