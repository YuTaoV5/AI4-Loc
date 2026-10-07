# Windows 本地网站与讲解稿

当前网站地址：<http://127.0.0.1:8787>。该服务用于本地使用与 Slide 功能截图，只监听本机，不改变远端服务器状态。

在项目根目录启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-windows-site.ps1
```

需要已安装 Node.js 和项目依赖。脚本设置独立的 `data/windows-local/` 状态目录，并载入 `data/datasets/openharmony-lkdtm-lab-v2/` 中的 80 条网站案例。该目录已加入 Git 忽略规则。关闭启动终端中的进程会停止服务；下次使用相同命令即可重新启动。

当前默认分析方式为本地确定性分诊；它不是 Linux 服务器上的真实模型推理环境。运行完整工具定位实验仍需匹配的源码工作区、Linux 工具与模型服务。

当前本地状态保留六份已有真实模型实验的报告回放。它们来自 `data/dataset-audit/benchmark-traces-v10.tgz` 中的增强预检实验，报告明确显示“既有实验报告回放（非本机新推理）”，作为 Benchmark 任务保存，不进入业务收益，也未标记为人工确认已解决。导入时间不代表原实验时间。

若在另一个全新本地状态目录重建这些回放，应先启动网站一次生成本地账号，然后停止网站，运行下面的导入程序，再重新启动。不要在网站写入状态时同时导入。

```powershell
python deliverables/kernel-insight-system/prepare_windows_site.py
```

2026-10-07 本次部署只用于打开网站、读取已有报告和采集界面。没有执行网站功能验收、提交分析任务、测试 Skill 或新增模型调用。实际截图与裁切来源见 `deliverables/kernel-insight-system/media/site/provenance.json`。

新版讲解稿为 [48 页 HTML](../deliverables/kernel-insight-system/deck.html)，可以双击离线打开。第 15 页是整体流程动画，第 19 页是 UAF 工具证据回放，第 22–29 页是网站功能图，第 32–37 页为科研统计图。方向键翻页，G 打开目录；动画支持 J/K 走步、P 播放暂停和页内按钮。
