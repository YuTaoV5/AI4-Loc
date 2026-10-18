# Jev实验与开发路线：20页网页Slide

[打开Slide](deck.html) · [逐页讲稿](逐页讲稿.md) · [实验主线通俗解读](../../docs/Jev实验主线与9B分类收益解读_20261018.md) · [微调复现指南](../../docs/决策模型开发与微调复现指南_20261018.md)

面向领导和有开发能力的使用者，建议20–25分钟。沿着“接口 → 资源与引擎 → 公平基线 → 数据微调 → 分类与完整Agent → skill交付”讲清各轮实验。

页码 | 讲什么
---|---
1–3 | 输入、候选概率和定位Agent分工
4 | 四轮实验为何依次开展，哪些对照能够比较
5–6 | thinking / 关闭thinking / 单字母Chat / Decision的前向与输出路径
7–10 | 公平单字母基线、PPLX资源与引擎、KV与并发预算
11–16 | LoRA、33/4/87数据、审核合同、396微步/99更新、RLCD
17 | **旧9B分类优势：66/87→78/87，+13.79个百分点**，按原冻结首诊断标签
18 | 完整Agent：混合流程10→6次HTTP、53.464→29.247s；保留纯Chat23.229s、两侧2/3位置命中的对照
19–20 | 两份skill与可复现开发交付

方向键翻页、数字跳页、G目录；4/5/6/13/16/18页J/K走步、P播放暂停。六个教学GIF在media中，方框宽度与动画节奏不代表实测时长。

9B分类对照保持原87例与原标签，不把规则标签成绩当根因或提交准确率。已知4条标签问题在配套审计中保留；不覆盖历史结果。Decision与单字母Chat均有相同分类提升，训练收益与接口收益分开解释。

[数据skill](../../skills/ai4loc-decision-data/SKILL.md)与[微调skill](../../skills/ai4loc-decision-finetune/SKILL.md)已在本机安装。新L40完成11项CPU合同/计划/协议检查，未占GPU；[详细验收范围](../../research/decision-skills-l40-20261018/README.md)。

```powershell
python deliverables/jev-decision-explained/build.py
python deliverables/jev-decision-explained/render_verify.py
python deliverables/jev-decision-explained/package.py
python deliverables/jev-decision-explained/serve.py --port 8795
```

仅查看可双击HTML；离线图与脚本均在包内。重建需NumPy/Matplotlib/Pillow/Playwright及Windows Chrome/微软雅黑。原28页技术稿保存在deck-technical-28.html，旧16页压缩包保留为历史交付；当前默认20页。
