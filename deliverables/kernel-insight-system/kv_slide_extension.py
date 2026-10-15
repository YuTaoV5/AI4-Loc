"""Append measured concurrency replays to the established 48-page Kelip deck."""
import pathlib,json,re,html,shutil
import kv_replay_data
HERE=pathlib.Path(__file__).resolve().parent
PLAN=[
('八步约快11%，单步和显存没有优势','实验协议、计时和两种token口径'),
('单次决策：两条时间线几乎重合','1任务1步冷条件：Decision vs Chat'),
('单任务八步：结果就绪约快11.6%','1任务8步预热：Decision vs Chat'),
('四任务八步：整批完成约快11.0%','4任务8步预热：Decision vs Chat'),
('速度改善，不代表内存下降','活跃KV、线性状态和预分配显存分开'),
('一次提交八题，反而等待更久','4任务8题预热：顺序 vs 批量'),
('相同题干的收益，要看实际缓存命中','4任务8步：冷条件 vs 预热条件'),
('八种工作量与缓存条件，都可以回放','1/4任务×1/8步×冷/预热交互选择'),
('写了四并发，实际可能只有一个','状态池预算、有效容量与恢复边界'),
('动图、逐时间点数据与说明一起交付','公开数据、复现、GIF与论文图入口'),
]
NOTES=[
'这一节补充2026年10月16日的真实服务器实验，不替代前48页的历史定位实验。我们固定同一权重与提示token，对比Decision和关闭thinking、只输出一个字母的Chat。正式112组，980次HTTP，内部评估1330个问题。接下来动画按同一相对秒尺播放真实单次重复；五次均值另外标注。KV和状态是离散观测，token只在原生prefill完成时结算，绝不画成伪造的连续计算进度。Decision不产生文本，所以其结果返回时间不能叫文本首token时间。',
'先看一个没有优势的对照。单任务单步冷条件，五次均值Decision为0.868秒，Chat为0.866秒，几乎相同。按P播放，J/K逐个结果事件前进或后退，滑块可以停在任意相对时间。注意两边时钟一致。计时包含客户端接口等待；Chat首个非空内容是首token观测，Decision黑点则是完整概率已经可用。不能因为结构化接口就预设一定更快。',
'把同一任务拆成八步，日志和题干固定，每一步更换选项。预热条件下，整批均值从Chat的1.544秒变为Decision的1.366秒，约减少11.6%。请看下方实际复用token结算和结果点。两个接口的token数可以完全一致，速度仍可能来自输出与调度路径的小差异；不要把它说成Decision少读了同一输入。预热只是一种操作条件，不保证第一问命中缓存。',
'四个任务同时放行，每任务八步。动画的两个独立trial对齐起点，而非两个模型同驻显卡。五次均值Decision为3.634秒、Chat为4.085秒，约减少11.0%。动画保留一个联合选出的真实repeat，绝不把五条轨迹平均成一条。看结果点先后，也看中部KV和状态曲线；更快完成并不意味着每个时间点使用更少状态。',
'这一页防止把效率结论扩大成内存结论。在四任务八步预热条件下，平均trial峰值活跃KV分别916.438与916.250MiB，Decision并没有更低。线性状态峰值是16与13槽，Decision反而更高。固定attention KV池5.532GiB在两个接口间不变，状态池也不会因为少生成文字而自动释放。我们只能说当前有限选择场景有约11%的时间收益，没有明显显存收益。',
'保持四任务、每任务八题，但右侧一次HTTP携带八个问题。用户需要等这个HTTP内所有题完成才收到概率集合。原生实现每题独立渲染prompt与prefill，所以HTTP减少不等于只计算一次题干。五次均值顺序3.634秒，批量10.286秒。本次批量更慢，动画同时显示内部prefill结算与用户可用结果，帮助分清服务器已经做完一部分与用户已经收到答案。不要从一个硬件配置推导所有模型都应顺序。',
'这次在同一正式配置内比较冷与预热。冷条件每trial先清缓存；预热条件先用另一组选项访问同一题干。两种条件的任务内后续步骤都允许复用缓存，因此冷不等于每一步都重新计算整段日志。四任务八步Decision均值为7.004与3.634秒，但真正解释应看实际cached_tokens，而不是仅看是否执行过预热。tokens在prefill结束时一次结算，不是我们测到了每个token的GPU时间。',
'这是完整主矩阵的探索入口。下拉菜单覆盖1或4任务、1或8步、冷或预热八种工作量，每一种都展示Decision与Chat的一次配对真实回放。不要只选看最快的一格。界面自动停播、重置起点并换入对应数据；从头、到结束、播放速度与时间滑块都能使用。全部5次的原始数值仍在CSV，回放只负责解释过程。',
'我们发现生产CLI虽然写max-running-requests等于4，实际有效容量是1。自动线性状态池9槽，每请求预算5槽，向下取整只够1。隔离实例设32槽并把静态显存比例从0.70提高到0.78，实际容量与观测批次均达到4。这付出了更大持久内存预算，不是Decision接口凭空省内存。原配置校准与正式故障窗口输入不同，不能跨轮把时间差归因成单因素调优。测试结束生产恢复原配置。',
'最后是可复核交付。五个GIF适合快速分享，交互回放可以精确停在某个秒点。原始公开标量、有限概率、服务端时间、调度和显存采样、字段说明、执行源码与校验清单一起提供。完整业务日志仍保存在私有证据归档中，公开包不包含账号或模型权重。这一轮只测有限决策性能，没有证明根因准确率、长篇Chat首token或完整Agent端到端定位速度改善。',
]
CSS='''
.kv-player{flex:1;min-height:0;display:flex;flex-direction:column;margin-top:20px;gap:12px}
.kv-player canvas{display:block;width:100%;height:auto;max-height:572px;background:white;border-radius:20px;min-height:0;flex:1;object-fit:contain}
.kv-controls{display:flex;align-items:center;gap:12px;flex-wrap:nowrap}
.kv-controls button,.kv-controls select,.kv-scenes{font:500 22px var(--font);padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--ink)}
.kv-controls button[data-kv=play]{background:var(--accent);color:white;border-color:var(--accent);min-width:130px}
.kv-controls input{flex:1;min-width:100px;accent-color:var(--accent)}
.kv-clock{font:22px var(--mono);min-width:275px;text-align:right;color:var(--muted)}
.kv-caption{font-size:21px;color:var(--muted);line-height:1.35}
.kv-grid{display:grid;grid-template-columns:1fr 1fr;gap:36px;flex:1;align-items:center;margin-top:38px}
.kv-card{border-radius:24px;background:white;padding:38px}.kv-card h2{font-size:31px;margin-bottom:22px;font-weight:500}.kv-big{font-size:66px;font-weight:600;line-height:1.25;letter-spacing:-.03em}.kv-card p{font-size:27px;color:var(--muted);line-height:1.6;margin-top:25px}
.kv-strip{display:flex;gap:22px;margin-top:42px}.kv-node{background:white;border-radius:20px;padding:28px 22px;flex:1;font-size:28px;line-height:1.5}.kv-node b{display:block;font-size:36px;margin-bottom:15px}.kv-band{font-size:29px;line-height:1.65;background:white;border-radius:22px;padding:30px 36px;margin-top:35px}
.kv-links{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:36px}.kv-links a{display:block;background:white;padding:27px 30px;border-radius:20px;font-size:29px}.kv-links span{display:block;color:var(--muted);font-size:23px;margin-top:9px}
'''
def extend(slides,notes,here):
    replay=kv_replay_data.build();esc=html.escape
    def player(scene,explorer=False):
        select=''
        if explorer:
            select='<select class="kv-scenes" aria-label="选择工作量与缓存条件">'+''.join(f'<option value="{k}">{esc(v["title"])}</option>' for k,v in replay['scenes'].items() if k.startswith('dchat-'))+'</select>'
        return f'<div class="kv-player" data-scene="{scene}">{select}<canvas width="1600" height="550" aria-label="实测KV与token时间回放"></canvas><div class="kv-controls"><button data-kv="prev">← 事件</button><button data-kv="play">播放回放</button><button data-kv="next">事件 →</button><button data-kv="reset">从头</button><button data-kv="end">到结束</button><select class="kv-rate" aria-label="播放速度"><option value="0.25">¼倍速</option><option value="1" selected>1倍速</option><option value="2">2倍速</option></select><input type="range" min="0" max="12" step="0.001" value="0" aria-label="回放时间"><span class="kv-clock"></span></div><div class="kv-caption"></div></div>'
    body=[
        '<div class="kv-strip"><div class="kv-node"><b>112 组</b>冷 / 预热 × 重复</div><div class="kv-node"><b>980 次</b>正式 HTTP 调用</div><div class="kv-node"><b>1330 题</b>服务端逐题时间</div></div><div class="kv-strip"><div class="kv-node">固定日志与题干<br>改变五选项集合</div><div class="kv-node">1 / 4 个并发任务<br>每任务 1 / 8 步</div><div class="kv-node">响应 + KV + 状态<br>token 完成时结算</div></div><div class="kv-band">Decision：完整概率可用时间　·　Chat：首个非空内容 token<br>动画是单次真实重复；均值来自每格 5 次，二者分开标注。</div>',
        player('dchat-1x1-cold'),player('dchat-1x8-warm'),player('dchat-4x8-warm'),
        '<div class="kv-grid"><div class="kv-card"><h2>活跃 attention KV · MiB</h2><div class="kv-big">916.438 <span class="thin">/ 916.250</span></div><p>Decision / Chat，平均 trial 峰值。<br>这一格没有观察到 KV 节省。</p></div><div class="kv-card"><h2>活跃线性状态 · 槽</h2><div class="kv-big">16 <span class="thin">/ 13</span></div><p>Decision 的状态峰值反而更高。<br>两接口固定 KV 池同为 5.532 GiB。</p></div></div>',
        player('seqbatch-4x8-warm'),player('coldwarm-d4x8'),player('dchat-4x8-warm',True),
        '<div class="kv-grid"><div class="kv-card"><h2>生产原配置 · 本轮已恢复</h2><div class="kv-big">9 ÷ 5 → 1</div><p>9 个状态槽，每请求预算 5 槽。<br>CLI 写 4，最终有效容量只有 1。<br>静态显存比例 0.70。</p></div><div class="kv-card"><h2>隔离实验配置 · 验证实际批次 4</h2><div class="kv-big">32 槽 → 4</div><p>固定 FP32 状态，扩大持久池。<br>静态显存比例提高到 0.78。<br>更大预算不是接口本身省内存。</p></div></div>',
        '<div class="kv-links"><a href="../../research/kv-concurrency-20261016/REPORT.md">完整实测报告<span>定义、矩阵、效度边界与复现命令</span></a><a href="../../research/kv-concurrency-20261016/tables/scheduler-snapshots.csv">逐时间点 KV / 状态池<span>4844 个调度边界快照</span></a><a href="../../research/kv-concurrency-20261016/tables/calls.csv">响应、首内容与 token 账本<span>原生排队 / prefill 另有逐问题表</span></a><a href="实验数据与动图说明.md">动图与数据字段说明<span>时间对齐、单次选择、采样与下载入口</span></a></div><div class="kv-band">5 个 GIF + 8 种交互主对照 + 全部公开逐请求数据<br>私有业务日志留在原归档；本轮不评价定位准确率。</div>',
    ]
    for i,((title,visual),content,note) in enumerate(zip(PLAN,body,NOTES),49):
        src='2026-10-16 真实服务器 · 独立试验起点对齐'
        sub={49:'同一 Qwen3.8 权重、相同 prompt token；不为制作动画重新调用模型。',50:'1 任务 × 1 步 · 冷条件 · 五次均值 0.868s / 0.866s',51:'1 任务 × 8 步 · 预热条件 · 五次均值 1.366s / 1.544s',52:'4 任务 × 8 步 · 预热条件 · 五次均值 3.634s / 4.085s',53:'4 任务 × 8 步 · 预热条件；不是整卡显存下降的证据。',54:'同样 32 题 · 五次均值：顺序 3.634s / 批量 10.286s',55:'同一正式配置 · 五次均值：冷 7.004s / 预热 3.634s',56:'P 播放，J/K 事件走步；可拖动时间轴，换条件自动停播。',57:'原配置校准与正式轮输入不同，不作跨轮时延的单因素消融。',58:'轨迹、分母、字段、执行代码和校验清单都保留。'}[i]
        slides.append(f'<section class="slide kv-slide" data-sec="并发与缓存实测" data-title="{esc(title)}"><div class="kicker"><b>{i:02d}</b>{esc(src)}</div><h1>{esc(title)}</h1><div class="sub">{esc(sub)}</div>{content}</section>')
        notes.append(f'## {i:02d} {title}\n\n{note}\n\n来源：research/kv-concurrency-20261016；动画源hash见media/kv/replay-provenance.json。\n')
    plan='\n\n## 2026-10-16 新增：并发与缓存实测\n\n| 页 | 结论 | 画面 |\n|---:|---|---|\n'+'\n'.join(f'| {i} | {title} | {visual} |' for i,(title,visual) in enumerate(PLAN,49))+'\n\n完整字段与时序口径见[实验数据与动图说明](实验数据与动图说明.md)。动画不自动播放，离页自动暂停；GIF使用共同时间压缩/慢放，打印的t为实测秒。\n'
    with (here/'说明.md').open('a',encoding='utf-8') as f:f.write(plan)
    speech=here/'逐页演讲稿.md'
    if speech.exists():
        old=speech.read_text(encoding='utf-8');head,sep,faq=old.partition('## 讲者备用：')
        head=re.split(r'^## 49 ',head,flags=re.M)[0]
        head=head.replace('48 页','58 页').replace('45–55 分钟','55–70 分钟')
        head=head.replace('谢谢大家，欢迎提问。','接下来补充同一模型在并发决策场景下的时延与缓存实测。')
        speech.write_text(head.rstrip()+'\n\n'+'\n\n'.join(f'## {i:02d} {title}\n\n[先指出均值，再播放一次真实重复；P 播放，J/K 走步。]\n\n{note}' for i,((title,_),note) in enumerate(zip(PLAN,NOTES),49))+'\n\n'+sep+faq,encoding='utf-8')
    return slides,notes,replay
def inject(template,replay):
    js=(HERE/'kv_replay.js').read_text(encoding='utf-8')
    data=json.dumps(replay,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    template=template.replace('</head>',f'<script id="kv-replay-data" type="application/json">{data}</script>\n</head>')
    template=template.replace('</style>',CSS+'\n</style>')
    template=template.replace('  let anim=null;',js+'\n  let anim=null;',1)
    template=template.replace("    const root=sl.querySelector('[data-flow]'); if(!root)return;","    const kv=sl.querySelector('.kv-player');if(kv){anim=window.KVReplay.activate(kv);return;}\n    const root=sl.querySelector('[data-flow]'); if(!root)return;")
    template=template.replace("a,button,.flow-demo,#nav-panel", "a,button,input,select,.flow-demo,.kv-player,#nav-panel")
    template=template.replace("addEventListener('keydown',e=>{", "addEventListener('keydown',e=>{\n    if(e.target.closest('input,select'))return;")
    return template.replace('48页系统设计','58页系统设计')
