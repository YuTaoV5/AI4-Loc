# Kernel Insight 系统设计与实证分析

[打开 48 页 Slide](deck.html) · [逐页演讲稿](逐页演讲稿.md) · [逐页证据说明](讲稿.md) · [资料来源](资料来源.md) · [全页预览](预览-全部页面.png)

下载或克隆仓库后，直接用 Chrome 打开 `deck.html`。CSS、JavaScript 与图片均为本地资源，离线演示无需启动网站或连接模型。只下载 HTML 会缺少图片，请同时保留 `media/`。

方向键/空格翻页，G 目录，数字跳页，F 全屏。第 15 页为整体流程动画，第 19 页为真实 UAF 工具证据回放，支持 J/K 走步、P 播放暂停和页内按钮。

`逐页演讲稿.md` 是对应 48 页的完整口语稿，包含读图指引、动画操作、过渡语与备用问答，适合约 45–55 分钟汇报。`讲稿.md` 另外保留逐页证据口径，不会覆盖手写的演讲正文。

## 文件与复现

| 文件或目录 | 用途 |
|---|---|
| `deck.html`、`media/` | 完整演示页面、科研图、真实功能截图及来源记录 |
| `analysis-data.json`、`*.csv` | 原始结果抽取、统计口径、精确区间与来源哈希 |
| `evidence/` | 重建报告所需的公开冻结清单、结果与标签副本 |
| `build_deck.py`、`research_figures.py`、`deck_revision.py` | 数值抽取、科研绘图与 48 页页面构建 |
| `vendor/kelip-slide/` | 公开模板、规范、参考文件及原 MIT 许可证，不依赖嵌套 Git 仓库 |
| `render_preview.py`、`verify_deck.py` | Chrome 渲染、布局与动画检查 |
| `rendered/`、`预览-全部页面.png`、`qa-report.json`、`render-review.json` | 已保存的逐页预览与检查证据 |
| `发布清单.json` | 发布文件的大小、SHA256 和必要资源完整性记录 |
| `prepare_windows_site.py` | 可选的本地网站历史报告回放导入，需另有本地完整数据 |

在仓库根目录执行：

```powershell
python -m pip install -r deliverables/kernel-insight-system/requirements-render.txt
python deliverables/kernel-insight-system/build_deck.py
python deliverables/kernel-insight-system/render_preview.py deliverables/kernel-insight-system/deck.html 48 deliverables/kernel-insight-system/rendered 1
python deliverables/kernel-insight-system/verify_deck.py
python deliverables/kernel-insight-system/verify_publication.py
```

图表和页面构建优先读取本目录下的 `evidence/`，不要求下载大型内核二进制、源码归档、私有任务状态或模型权重。原始来源路径和所用证据哈希在 `analysis-data.json` 中保留；资产盘点仅公开数据集与检查摘要，排除私有业务备份元数据。该副本不能代替完整数据合同验证，也不能用来直接重跑内核定位实验。

重建脚本按 Windows + 微软雅黑 + 本机 Chrome 配置；其他系统需要相应中文字体及浏览器路径。若仅演示，无需安装上述 Python 依赖。

## 数据边界

所有模型结果来自已保存的真实实验，不为制稿重跑。固定配对试验包含五故障和一个健康基线；代码位置命中不等于机制正确或引入提交已证实。图中 CI 只展示小样本二项模型的不确定性，样本独立同分布条件尚未得到保证。动画按教学节奏播放，不虚构逐工具时间。

网站截图来自独立本地展示状态。六份报告明确标注历史回放，未新增模型推理或业务解决数。本目录不含私有业务账号、访问令牌或服务器完整恢复包。

版式基于 Kelip Slide；本目录 `vendor/kelip-slide/` 保留重建所需的模板、规范、MIT 许可证与作者声明。
