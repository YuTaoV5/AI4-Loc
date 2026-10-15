# Kernel Insight 系统设计与实证分析

[打开70页Slide](deck.html) · [逐页演讲稿](逐页演讲稿.md) · [逐页证据说明](讲稿.md) · [资料来源](资料来源.md) · [全页预览](预览-全部页面.png)

最新59–70页：[模型微调动图与数据说明](模型微调动图与数据说明.md)；[9B完整实测数据](../../research/jev-qwen35-9b-20261016/README.md)。新版[70页Slide、14个GIF与完整公开数据包](../releases/AI4Loc_模型微调动图_Slide与完整公开数据_20261016.zip)保留三份研究的独立范围。

2026-10-16新增49–58页：五组实测时间流程动图、八种工作量／缓存条件交互回放，展示响应、KV、线性状态、prefill与复用token。详见[实验数据与动图说明](实验数据与动图说明.md)，[完整公开数据](../../research/kv-concurrency-20261016/README.md)和[打包分享文件](../releases/AI4Loc_实验动图_Slide与完整公开数据_20261016.zip)。

五个可单独分享的GIF：[单步几乎持平](media/kv/dchat-1x1-cold.gif) · [单任务八步](media/kv/dchat-1x8-warm.gif) · [四任务八步](media/kv/dchat-4x8-warm.gif) · [顺序与批量](media/kv/seqbatch-4x8-warm.gif) · [冷与预热](media/kv/coldwarm-d4x8.gif)。两边按共同实测时间尺播放；五次均值与真实单次重复分开，内存不节省的结果同样展示。

下载或克隆仓库后，直接用 Chrome 打开 `deck.html`。CSS、JavaScript 与图片均为本地资源，离线演示无需启动网站或连接模型。只下载 HTML 会缺少图片，请同时保留 `media/`。

方向键/空格翻页，G 目录，数字跳页，F 全屏。第 15 页为整体流程动画，第 19 页为真实 UAF 工具证据回放，支持 J/K 走步、P 播放暂停和页内按钮。

`逐页演讲稿.md` 是对应70页的完整口语稿，包含读图指引、动画操作、过渡语与备用问答，适合约70–90分钟汇报。59–70页新增Qwen3.5-9B模型构建、真实396微步训练、概率校准、并发响应与完整Agent对照；[动图与数据说明](模型微调动图与数据说明.md)。9个新GIF在`media/finetune/`，原5个并发GIF在`media/kv/`。`讲稿.md`另外保留逐页证据口径。

## 文件与复现

| 文件或目录 | 用途 |
|---|---|
| `deck.html`、`media/` | 完整演示页面、科研图、真实功能截图及来源记录 |
| `analysis-data.json`、`*.csv` | 原始结果抽取、统计口径、精确区间与来源哈希 |
| `evidence/` | 重建报告所需的公开冻结清单、结果与标签副本 |
| `build_deck.py`、`research_figures.py`、`deck_revision.py`、`kv_slide_extension.py`、`finetune_slides.py` | 数值抽取、科研绘图与70页页面构建 |
| `finetune_data.py`、`finetune_replay.js`、`render_finetune_replays.py` | 9B训练、分类、概率与并发动画，16种实测条件与交互核验 |
| `kv_replay_data.py`、`kv_replay.js`、`media/kv/` | 实测时序回放、源数据映射和五个GIF |
| `实验数据与动图说明.md`、`kv-data-qa.json`、`kv-animation-qa.json` | 字段与时钟口径、token账本和新回放交互核验 |
| `package_experiment_slides.py`、`serve_deck.py` | 包含全部公开详细数据的分享包、本机只读预览 |
| `vendor/kelip-slide/` | 公开模板、规范、参考文件及原 MIT 许可证，不依赖嵌套 Git 仓库 |
| `render_preview.py`、`verify_deck.py` | Chrome 渲染、布局与动画检查 |
| `rendered/`、`预览-全部页面.png`、`qa-report.json`、`render-review.json` | 已保存的逐页预览与检查证据 |
| `发布清单.json` | 发布文件的大小、SHA256 和必要资源完整性记录 |
| `prepare_windows_site.py` | 可选的本地网站历史报告回放导入，需另有本地完整数据 |

在仓库根目录执行：

```powershell
python -m pip install -r deliverables/kernel-insight-system/requirements-render.txt
python deliverables/kernel-insight-system/build_deck.py
python deliverables/kernel-insight-system/render_finetune_replays.py
python deliverables/kernel-insight-system/render_kv_replays.py --verify-only
python deliverables/kernel-insight-system/verify_deck.py
python deliverables/kernel-insight-system/verify_kv_data.py
python deliverables/kernel-insight-system/verify_publication.py
```

图表和页面构建优先读取本目录下的 `evidence/`，不要求下载大型内核二进制、源码归档、私有任务状态或模型权重。原始来源路径和所用证据哈希在 `analysis-data.json` 中保留；资产盘点仅公开数据集与检查摘要，排除私有业务备份元数据。该副本不能代替完整数据合同验证，也不能用来直接重跑内核定位实验。

重建脚本按 Windows + 微软雅黑 + 本机 Chrome 配置；其他系统需要相应中文字体及浏览器路径。若仅演示，无需安装上述 Python 依赖。

## 数据边界

所有模型结果来自已保存的真实实验，不为制稿重跑。基础48页固定配对试验包含五故障和一个健康基线；代码位置命中不等于机制正确或引入提交已证实。图中 CI 只展示小样本二项模型的不确定性，样本独立同分布条件尚未得到保证。原15/19页机制动画按教学节奏播放，不虚构逐工具时间。新增49–58页使用2026-10-16并发研究的原生时间与池观测，按真实单次重复回放，不并入旧定位准确率；GIF统一时间缩放，token只在prefill完成时结算。

网站截图来自独立本地展示状态。六份报告明确标注历史回放，未新增模型推理或业务解决数。本目录不含私有业务账号、访问令牌或服务器完整恢复包。

版式基于 Kelip Slide；本目录 `vendor/kelip-slide/` 保留重建所需的模板、规范、MIT 许可证与作者声明。
