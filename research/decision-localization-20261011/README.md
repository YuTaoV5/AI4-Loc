# AI4Loc Decision 学术研究报告（2026-10-12 修订）

本研究基于服务器实际证据，并新增 **135 次随机配对接口消融**。这是实证技术报告，未冒充已投稿、同行评审或获奖论文。

- [修订版PDF](../../output/pdf/AI4Loc_Decision_Academic_Report_20261012.pdf)：25页，新增真实PPLX完整GPU研究；[2026-10-11历史PDF](../../output/pdf/AI4Loc_Decision_Academic_Report_20261011.pdf)保留。
- [离线网页版](report.html)：下载本目录，直接打开；图表使用相对路径，无 CDN。
- [Markdown 正文](report.md)、[结构化正文](manuscript.json)。
- [统计结果](results/statistics.json)、[135 次公开派生记录](results/boundary-trials.csv)、[冻结协议](results/protocol.json)。
- [真实 Decision 返回示例](results/measured-decision-example.json)：保留问题选择与概率，不含原始输入或 token ID。
- [图表](figures/)：11组SVG/PNG，含专用权重配对耗时、混淆与比率热力图；[流程图 Mermaid 源](system-flow.mmd)。

新增独立研究见[全GPU实测报告](../pplx-timeshare-20261012/REPORT.md)。121正式调用、2预热排除：test两端均27/27，PPLX均值5.672s、通用2.563s；PPLX全部参数cuda:0。原CPU卸载121次和原135次接口消融不混算。专用参考部署当前未提速，完整根因定位收益仍未测。第17至20节完整说明协议、统计、标签线索、失败与服务恢复。

原主实验结论：通用Qwen三问题Decision平均1.145s，Chat2.075s，减少44.8%；仅支持该有限分类更快。两者family均27/27，9唯一案例、5机制组，家族级检验不显著。历史完整定位4/8→4/8、耗时增加8.96%，不能声称整体提速或根因提分。新增PPLX结果不改变这135次主实验的权重身份。

## 无服务器复现

Python 3.12+，安装依赖后在本目录运行：

```shell
python -m pip install -r requirements.txt
python analyze.py --public
python verify.py
python build-report.py
```

`--public` 仅使用已发布的 CSV/JSON 重算统计和全部图表，不访问服务器、不调用模型。已核对其统计 JSON 与私有原始数据路径的输出逐字节一致。`verify.py` 独立使用 SciPy 枚举配对置换，核对协议顺序、重复单位、源码冻结哈希和报告数字。

PDF 在 `../../output/pdf/` 生成。构建还读取相邻 `pplx-timeshare-20261012/results/` 和 `figures/`，离线分享时保留两个研究目录。Windows 自动使用微软雅黑；Linux可设置 `AI4LOC_CJK_FONT` 与 `AI4LOC_CJK_BOLD_FONT`，否则使用STSong-Light。不分发字体文件。修订版PDF已逐页渲染检查。

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

报告第21节给出尚未执行的确认性研究。新版部署命令与权重链接见[中文部署手册](../../docs/PPLX专用模型下载部署与验收手册.md)。服务器恢复后已完成新版常驻部署与真实接口/重启验收，见[验收证据](../../deployment/pplx-decider/validation-20261012/README.md)。本次4次合成推理不计入benchmark。
