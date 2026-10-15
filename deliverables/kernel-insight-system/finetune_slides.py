"""Append a measured Qwen3.5-9B training/results chapter; keep older studies intact."""
import pathlib,json,html,re
import finetune_data
HERE=pathlib.Path(__file__).resolve().parent
PLAN=[
('只训练0.056%的参数，保留原语言骨干','model','冻结骨干与低秩支路逐步高亮'),
('按机制隔离数据，训练只学习首诊断分类','data','33/4/87的数据流与评测标签隔离'),
('396个微步，逐点回放真实训练过程','training','真实loss、阶段、显存和更新次数'),
('先用交叉熵，再加入扰动奖励学习','objective','RLCD的采样、奖励与反向传播示意'),
('合并LoRA后，Decision直接返回选项概率','inference','同一因果骨干的两条接口路径'),
('首诊断命中66→78，主要改善警告边界','accuracy','87个配对案例与类别统计'),
('分类更准，错误概率却可能更自信','calibration','准确率、NLL、Brier与ECE对比'),
('八步约快7.7%，单步没有稳定优势','runtime','实测请求、prefill结算、KV与功耗时间线'),
('完整矩阵保留冷条件与单步的反例','heatmap','两检查点的八条件速度热力图'),
('微调改变答案，没有减少推理内存','memory','基座与微调后Decision的真实时间对照'),
('完整Agent仍为2/3，混合流程仍更慢','agent','32k独立实验的耗时与调用次数'),
('支持有限分类改进，尚未证明因果定位提升','evidence','证据范围、负结果和复现入口'),
]
NOTES=[
'这里从官方Qwen3.5-9B预训练权重开始，不是随机预训练9B模型。冻结BF16骨干和原有字母LM读出，只训练48处投影上的rank8 LoRA：32个down_proj、8个q_proj、8个v_proj。5,308,416参数占模型总参数9,415,122,160的约0.056%。有效权重W加上2BA。A随机初始化，B为零，所以初始增量为零。这不是新增随机决策头，也没有将Laya的双向BERT结构移植到Qwen。动画只表达依赖关系，不代表实测算子时间。',
'冻结数据集为训练33、开发4、测试87。按规范化注入机制跨两个内核分组，历史测试组不进入训练，脱敏输入哈希也不重叠。测试有20个机制簇，开发者此前已经见过历史测试材料，因此不能叫全新盲测。标签是弱首诊断分类，不是引入提交或因果根因。诊断窗口由规则提取，这也不是无辅助全日志搜索。训练当然需要标签，推理prompt不带gold、split、来源路径与注入命令；评测在worker退出后读取真值。',
'时间轴严格读取396条训练日志，不生成假损失或假梯度。每四个微步累计为一次更新，共99次，三轮各132微步。每例每轮四个选项排列，选项数5、8或12。AdamW学习率1e-4、weight decay0.01、clip1，输入最多2048tokens。第一步约57秒含首次编译，逐步日志到290.764秒，343.689秒是到开发评估、导出与哈希结束的控制器区间，不含前置加载。epoch0和后两轮的目标不同，损失不能跨阶段直接解释为统一收敛指标。峰值torch allocated18.74GiB；实际选择第二轮epoch1，非最后一轮。',
'参考Laya的RLCD思想，在字母logits上采四个高斯扰动，sigma从0.4降至0.15。奖励是带下限的log真类概率加0.75倍spherical分数，优势中心化并标准化，再加交叉熵。数值裁剪后不能宣称全局严格proper或无偏策略梯度；没有做等更新数CE-only与多随机种子消融，因此当前改善不能单独归因RLCD。图中每一步是机制示意，不是保存的逐步梯度值。',
'训练完成后将LoRA合并为BF16权重，在同版本SGLang下对照。固定prompt，取现有LM读出中字母选项logits做归一化，Decision直接回完整概率，不生成解释文字；Chat关闭thinking、最多输出一个字母。八次不同选项仍是八个独立渲染与评分，不是一次prefill共享隐状态。开发集仅4例选出epoch1和温度0.5，合并与适配器的开发top1一致但logit最大漂移3.308，不能声称逐位相同。图是流程示意，不是性能实测。',
'每例三个选项排列多数票，基座66/87，微调78/87，Decision与Chat结果一致。动画按固定公开表的案例顺序揭示配对结果，是统计呈现而不是训练过程。主要来自显式警告类别8/20升为19/20，protection15/16升16/16，RCU1/7升2/7，blocked task从2/2降1/2，locking仍0/2。OOM与watchdog测试支持为零。按机制簇bootstrap的准确率差区间触及或跨越零，不能从这些开发者可见的弱标签样本声称普遍显著泛化。',
'校准按三个排列的概率均值计算。基座T1的NLL0.830，微调T1为1.724，开发选T0.5为1.957，越低越好。Brier与ECE有所改善，但不抵消NLL揭示的错误高置信风险。不能只展示准确率就把输出概率叫可靠置信度，4例开发集的温度选择尤其不稳。动画只是逐列揭示最终统计量，数值是实际计算结果。',
'这是独立9B实验，与49至58页27B实验分开。每个检查点112组trial、980次正式HTTP；主矩阵每格五次重复。默认微调后四任务八步预热，Decision整批均值1.280秒，Chat1.388秒约快7.7%。回放只用联合接近两组中位数的一次实际重复，均值另标。两边独立运行并对齐客户端起点。黑点表示Decision完整概率或Chat首个非空内容，整批结束则按HTTP结束。token在原生prefill完成时结算；排队、KV、状态与NVML为记录的离散观测，不是CUDA精确时刻。可下拉选择两检查点全部16条件。',
'热力图覆盖两个检查点、八种工作量与缓存条件。颜色表示Decision相对Chat整批均值耗时减少百分比，负数就是Decision更慢。单步没有稳定优势，基座冷条件四任务一步约慢11.9%。预热是操作条件，不保证缓存命中。横向基座和微调后同为9B、同配置，但独立实验时段，不能把微小差异说成训练改变调度架构。五次重复与测量开销敏感性都保留在原始研究目录。',
'这页比较同一Decision接口在基座与微调后的独立trial。两端对齐各自起点，选中repeat分别按各自D/Chat联合中位准则选取，不是假装同时驻卡。合并LoRA没有改变网络层数或KV结构，9B每个attention token的KV是32KiB，线性状态另计。四任务八步预热，D与Chat平均活跃KV峰值458.219和458.125MiB、状态16和13槽，接口与微调都没有显示内存节省。NVML约100ms观测、显存因预分配池保持约48GB，不能把两checkpoint相近曲线当逐位等价。功耗只展示观测，不分摊并发单请求能耗。',
'完整Agent另设ctx32768，因为8k输入容不下实际17k至20k token的工具提示。两个检查点采用同一兼容修复和匿名只读沙箱，12/12流程都输出有效报告，三例各流程代码位置命中都2/3。基座纯Chat总23.567秒，混合53.464秒；微调纯Chat23.229秒，混合29.247秒。混合HTTP从10减6，但仍慢于微调纯Chat。这里的条形图是三个串行案例耗时之和，不是并发请求Gantt或单次样本置信区间，也没有引入提交因果真值。',
'结论分层：有限弱标签首诊断分类改善；有限选择接口在八步预热条件有约7.7%的耗时收益；没有KV内存优势；完整定位命中未升，混合Agent仍慢。没有独立盲测、等预算CE-only、多种子、专家因果真值，不能声称通用Jev模型或best-paper级显著因果证据。全部新图读取冻结训练、调用、调度、GPU和准确率文件。可以离线播放，也可逐点复核数据和哈希；私有业务日志与模型权重不进入公开slide包。',
]
CSS='''
.ft-player{flex:1;min-height:0;display:flex;flex-direction:column;gap:12px;margin-top:22px}
.ft-player canvas{width:100%;min-height:0;flex:1;object-fit:contain;background:white;border-radius:22px}
.ft-controls{display:flex;gap:12px;align-items:center}.ft-controls button,.ft-scenes{font:22px var(--font);padding:10px 15px;background:white;border:1px solid var(--line);border-radius:10px;color:var(--ink)}
.ft-controls button[data-ft=play]{background:var(--accent);color:white}.ft-controls input{flex:1;accent-color:var(--accent)}.ft-clock{font:21px var(--mono);min-width:230px;text-align:right}.ft-caption{font-size:21px;color:var(--muted);line-height:1.4;min-height:30px}.ft-slide h1{font-size:62px}.ft-slide .sub{font-size:28px}
'''
def extend(slides,notes,here):
    data=finetune_data.build();esc=html.escape
    # Write the conclusion/visual plan before creating HTML, as required by Kelip.
    with (here/'说明.md').open('a',encoding='utf-8') as f:
        f.write('\n\n## 模型构建、真实微调与对照结果：59–70页\n\n|页|结论|画面|\n|---:|---|---|\n'+'\n'.join(f'|{n}|{title}|{visual}|' for n,(title,kind,visual) in enumerate(PLAN,59))+'\n\n新增动画数据与限制见[模型微调动图与数据说明](模型微调动图与数据说明.md)。\n')
    for n,((title,kind,visual),note) in enumerate(zip(PLAN,NOTES),59):
        sub={'training':'真实396条训练记录 · 横轴为日志elapsed秒；不同阶段loss目标不同','runtime':'同一9B权重、相同prompt · 共同时间尺 · 单次回放与五次均值分开','memory':'两个独立实验起点对齐 · 最新离散观测 · 无逐token时间插值','accuracy':'87例 × 3种选项排列多数票 · 首诊断弱标签，不是因果根因','agent':'独立32k上下文实验 · 三例耗时合计，不是并发时间线'}.get(kind,'Qwen3.5-9B · 冻结公开实测；机制动画与真实时间回放分别标注')
        select=''
        if kind=='runtime':select='<select class="ft-scenes" aria-label="选择9B对照条件">'+''.join(f'<option value="{k}" {"selected" if k=="trained-4x8-warm" else ""}>{esc(v["title"])}</option>' for k,v in data['scenes'].items())+'</select>'
        player=f'<div class="ft-player" data-kind="{kind}">{select}<canvas width="1600" height="590" aria-label="{esc(visual)}"></canvas><div class="ft-controls"><button data-ft="prev">← 事件</button><button data-ft="play">播放演示</button><button data-ft="next">事件 →</button><button data-ft="reset">从头</button><button data-ft="end">到结束</button><input type="range" min="0" max="1" step="0.0001" value="0" aria-label="动画进度"><span class="ft-clock"></span></div><div class="ft-caption"></div></div>'
        slides.append(f'<section class="slide ft-slide" data-sec="9B模型训练与复测" data-title="{esc(title)}"><div class="kicker"><b>{n:02d}</b>2026-10-16 · 模型构建、训练与独立评测</div><h1>{esc(title)}</h1><div class="sub">{esc(sub)}</div>{player}</section>')
        notes.append(f'## {n:02d} {title}\n\n{note}\n\n来源：research/jev-qwen35-9b-20261016；media/finetune/provenance.json。\n')
    speech=here/'逐页演讲稿.md';old=speech.read_text(encoding='utf-8');head,sep,faq=old.partition('## 讲者备用：')
    head=re.split(r'^## 59 ',head,flags=re.M)[0].replace('58 页','70 页').replace('55–70 分钟','70–90 分钟')
    speech.with_suffix('.tmp').write_text(head.rstrip()+'\n\n'+'\n\n'.join(f'## {n:02d} {p[0]}\n\n[按P播放；J/K逐步；说明教学步与实测秒的区别。]\n\n{note}' for n,(p,note) in enumerate(zip(PLAN,NOTES),59))+'\n\n'+sep+faq,encoding='utf-8')
    speech.with_suffix('.tmp').replace(speech)
    return slides,notes,data
def inject(template,data):
    packed=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    template=template.replace('</head>',f'<script id="ft-data" type="application/json">{packed}</script>\n</head>')
    template=template.replace('</style>',CSS+'\n</style>')
    template=template.replace('  let anim=null;',(HERE/'finetune_replay.js').read_text(encoding='utf-8')+'\n  let anim=null;',1)
    template=template.replace("    const kv=sl.querySelector('.kv-player');","    const ft=sl.querySelector('.ft-player');if(ft){anim=window.FTReplay.activate(ft);return;}\n    const kv=sl.querySelector('.kv-player');")
    return template.replace('58页系统设计','70页系统设计').replace('.flow-demo,.kv-player,#nav-panel','.flow-demo,.kv-player,.ft-player,#nav-panel')
