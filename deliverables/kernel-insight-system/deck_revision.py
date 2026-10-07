"""Readable research narrative, actual Windows UI figures and explicit animations."""
import html
import json
import re
from PIL import Image

def revise(slides, notes, here, h):
    E=html.escape
    svg,box,arrow,text,fig,two,table=(h[k] for k in ['svg','box','arrow','text','fig','two','table'])
    media=here/'media'/'site'
    crops={
        'report-log':('06-report-full.jpg',(250,120,980,820)),
        'report-agent':('06-report-full.jpg',(250,1430,980,2015)),
        'report-review':('06-report-full.jpg',(250,2940,600,3490)),
        'expert-library':('08-experts.jpg',(250,800,980,1690)),
        'expert-content':('09-skill.jpg',(250,100,980,1120)),
        'submission':('11-skill-submit.jpg',(250,80,980,1120)),
        'dashboard':('13-dashboard.jpg',(0,0,991,1000)),
    }
    for name,(src,bounds) in crops.items():
        with Image.open(media/src) as im: im.crop(bounds).save(media/(name+'.jpg'),quality=95)
    (media/'provenance.json').write_text(json.dumps({
        'capturedFrom':'http://127.0.0.1:8787','date':'2026-10-07',
        'method':'CUA browser screenshots; crops preserve original pixels',
        'data':'Public synthetic benchmark and built-in declarative experience only',
        'reports':'Six archived real model runs, explicitly labelled as replay, no new inference',
        'newModelCalls':0,'functionalAcceptanceExecuted':False,'crops':crops,
    },ensure_ascii=False,indent=2),encoding='utf-8')

    def feature(image,label,title,items):
        return '<div class="feature"><div class="screen-card"><img src="media/site/'+image+'" alt="'+E(label)+'"></div><div class="feature-copy"><div class="feature-label">'+E(label)+'</div><div class="feature-title">'+title+'</div>'+''.join('<div class="feature-point"><b>'+a+'</b><p>'+b+'</p></div>' for a,b in items)+'</div></div>'

    # Two animations share manual-by-default controls and stop when leaving a slide.
    def flow(frames,kind='overview'):
        positions=[(30,30),(565,30),(1100,30),(1100,305),(565,305),(30,305)] if kind=='overview' else [(20+i*318,25) for i in range(5)]
        inner=''
        for i,((x,y),f) in enumerate(zip(positions,frames)):
            w=470 if kind=='overview' else 290
            inner+=f'<g class="flow-node" data-step="{i}">'+box(x,y,w,175,f'{i+1:02d}  '+f['title'],f['lines'])+'</g>'
            if i<len(frames)-1:
                nx,ny=positions[i+1]
                if ny==y:
                    inner+=arrow(x+w+10 if nx>x else x-10,y+88,nx-15 if nx>x else nx+w+15,ny+88)
                else: inner+=arrow(x+w/2,y+188,nx+w/2,ny-15)
        if kind=='overview':
            inner+='<path d="M265,500 L265,550 L10,550 L10,270 L800,270 L800,220" fill="none" stroke="#A1A1A6" stroke-width="3" stroke-dasharray="8 6" marker-end="url(#ar)"/>'
            inner+=text(800,590,'退回原因 → 回归样本 / 经验改进 → 冻结数据重新评测',25,'#6E6E73',anchor='middle')
        else:
            inner+=box(20,250,1550,285,'本步观察与证据',[],True)
            inner+='<text class="trace-detail" x="55" y="355" font-size="30" fill="#1D1D1F"></text><text class="trace-detail-2" x="55" y="410" font-size="27" fill="#6E6E73"></text><text class="trace-detail-3" x="55" y="465" font-size="27" fill="#6E6E73"></text>'
        inner+='<circle class="flow-token" r="9" fill="#0071E3" cx="265" cy="218"/>'
        frames=[dict(f,token=[x+(235 if kind=='overview' else 145),y+193]) for (x,y),f in zip(positions,frames)]
        return '<div class="flow-demo" data-flow="'+kind+'"><div class="flow-canvas">'+svg(inner)+'</div><div class="flow-detail" aria-live="polite"></div><div class="flow-controls"><button data-action="prev" aria-label="上一步">← 上一步</button><button data-action="play" aria-label="播放流程">播放流程</button><button data-action="next" aria-label="下一步">下一步 →</button><button data-action="reset" aria-label="从头开始">重置</button><span class="flow-counter"></span><span class="flow-hint">J / K 走步 · P 播放 / 暂停</span></div><script class="flow-data" type="application/json">'+json.dumps(frames,ensure_ascii=False).replace('</',r'<\/')+'</script></div>'

    overview=flow([
        {'title':'提交材料','lines':['日志 / 源码 / 构建产物','记录有与无，保留文件指纹'],'detail':'使用者提供故障实例；缺少材料时，明确限制输出粒度。'},
        {'title':'检查身份','lines':['运行版本与 Build ID','源码 commit + patch'],'detail':'先确认材料属于本次运行；身份不匹配时阻止错误的符号映射。'},
        {'title':'故障定界','lines':['最早有效诊断 + 上下文','阶段 / 检测器 / 涉及组件'],'detail':'保存可观测的错误第一现场，区分检测组件和潜在致错组件。'},
        {'title':'工具取证','lines':['日志检索 → 源码读取','观察不足则继续模型 / 工具'],'detail':'自动预检准备首批证据；模型在只读工具与预算内选择补充观察。'},
        {'title':'生成候选','lines':['文件 / 函数 / 行号区间','校验引用并保存原始轨迹'],'detail':'校验候选在实际读过的范围内；仍将机制与引入提交保持为待验证。'},
        {'title':'专家与评测','lines':['人工确认 / 退回原因','独立评分 → 失败回归'],'detail':'网页支持人工反馈和经验流转；独立机制真值及修复干预仍需补齐。'},
    ])
    trace=flow([
        {'title':'提取诊断','lines':['incident','工具证据 T1'],'detail':'已有 UAF 实验轨迹 · 3 次自动工具检查 + 1 次模型请求 · 总流程 18.166 秒。','detailLines':['日志 L448：KASAN use-after-free in ki_uaf_kmalloc','CPU 1 / PID 1 / init；保留访问、分配与释放上下文','可观测诊断指向运行阶段；KASAN 是检测器。']},
        {'title':'搜索源码','lines':['source_search','工具证据 T2'],'detail':'用真实日志中的栈帧检索；不读取故障标签或注入答案。','detailLines':['查询 ki_uaf_kmalloc，对应 external/ki_bench.c','按实际观察选择候选文件，再读取具体行窗口','通用打印与异常处理函数不应直接当成所有者。']},
        {'title':'读取代码','lines':['source_read','工具证据 T3'],'detail':'读取窗口是后续位置声明的上界；每一行均可回查。','detailLines':['external/ki_bench.c · ki_uaf_kmalloc · 106–114 行','第 111 行 kfree(p)；第 113 行 p[0] = \'X\'','释放后写入与日志中分配 / 释放 / 访问栈相互支持。']},
        {'title':'模型归纳','lines':['结构化候选','本次 1 次模型请求'],'detail':'模型以工具返回的观察生成定界、候选、解释与缺口。','detailLines':['阶段：运行；检测器：KASAN；涉及组件：ki_bench','候选位置引用 T3；第一现场引用 T1','引入提交：未确定；未执行修复重放。']},
        {'title':'独立评价','lines':['位置评分命中','机制审核仍待完成'],'detail':'代码命中来自独立标签评分；不能替代专家机制审核或因果干预。','detailLines':['文件 / 函数 / 与标签区间重叠：命中','保存原轨迹、失败情况、请求与耗时，允许回归比较','本动画按教学节奏播放，未伪造各工具的实测时间。']},
    ],'trace')

    replacements={
        9:('数据与方法','四套数据资产，各有用途且存在重叠',svg(
            box(25,65,440,200,'真实社区报告集',['6 条；训练 3 / 测试 3','保留报告与修复线索','无逐例完整匹配产物'])+
            box(580,65,440,200,'历史故障注入集',['64 条；训练 43 / 测试 21','从 67 个原始场景选入'])+
            arrow(1045,165,1100,165)+box(1125,65,450,200,'网站扩展展示集',['80 条 = 历史 64 + 扩展 16','训练 59 / 测试 21'],True)+
            box(580,355,995,185,'严格定位评测集',['68 个场景中，60 个材料合同通过；8 个排除','有效集：59 故障 + 1 健康；训练 51 / 测试 9'],True)+
            arrow(800,285,800,335)+text(35,400,'重新采集',30)+text(35,450,'共享 59 个有效场景',26,'#6E6E73')+
            text(800,590,'网站新增 16 条均属训练侧；15 条启动日志仅含 9 种签名，不能当作 16 个独立根因',24,'#6E6E73',anchor='middle')),
            '数据数量描述资产规模；备份副本、重采集版本与重复签名不算独立问题。','数据清单与场景谱系',
            '四个版本来自三个主要采集脉络。社区、历史注入、网站扩展和严格集分别对应 linux-community-v1、openharmony-lkdtm-lab-v1、openharmony-lkdtm-lab-v2、stability-v1。严格集与历史集共享59个有效场景，不能合并计算准确率。'),
        13:('数据与方法','材料缺失时，按证据降低输出粒度',fig('input-contract','七种材料组合的能力合同热图'),
            '这是设计约束矩阵，并非七种输入组合的实测成功率；缺日志时拒绝本次故障定位。','输入材料合同',
            '蓝色表示材料允许该类操作或声明，不保证定位正确。产物身份检查不等于有源码映射，更不等于因果正确。没有日志时无法从共享构建唯一识别本次运行事件。历史实验仅部分覆盖组合，完整60×7矩阵尚未执行。'),
        24:('实验结果','固定六例中，命中提高且交互开销降低',fig('result-overview','代码位置命中、模型请求数和定位总时间三个独立量纲的结果图'),
            '按需检索 → 预检增强；代码分母为 5 个故障，请求和时间包含另 1 个健康基线。','固定六例的单次配对试验',
            '代码命中3/5→5/5；报告完成5/6→6/6；请求21→6；耗时181.347→95.834秒；工具25→16。各图使用独立量纲，没有把百分比、次数和秒数放在同一轴。单次、选择样本，不推断泛化或显著性。'),
        34:('讨论与结论','部署可展示，定位效果仍由实验独立评价',two(
            ('当前 Windows 展示环境',[
                '<b>网站已启动 · 本机 8787 端口</b><br>独立本地数据目录；网站载入 80 条案例',
                '<b>六份既有定位报告已回放</b><br>界面标明历史结果，不冒充本机新推理',
                '<b>本次仅为制稿采集界面</b><br>未执行网站功能验收或新增模型实验']),
            ('已有历史验收记录',[
                '<b>36 项 Node / 38 项 Python 检查</b><br>验证代码与数据流程，不作为定位准确率',
                '<b>15 项隔离网站 / 9 项线上检查</b><br>属于此前验收时点',
                '<b>8 项真实模型流程检查</b><br>也不能解释为 8/8 定位准确率'])),
            '本地展示、网站功能验收、Agent 定位质量，分别保留证据与分母。','本地部署记录 / 既有验收记录',
            '按本次要求只启动网站并采集界面，不重跑功能校验与模型。服务使用 data/windows-local，保留独立于私有业务备份的本地状态。归档报告导入时间不是原实验发生时间。此前服务器按用户要求关闭，当前本地启动不代表远端服务器恢复。'),
    }
    screens=[
        ('先登记故障实例，再补齐诊断材料','02-workbench.jpg','本地网站 · 新建分析','一个入口承接多种材料',[
            ('日志输入','支持粘贴、文件与压缩包；按任务保存原始材料。'),('分析选项','选择专家经验组合，补充内核版本、commit 与运行批次。'),('提交后的流转','进入个人任务空间，查看进度、报告与后续审核状态。')],
            '本页只展示输入界面；没有为了截图提交新任务。'),
        ('材料配置把版本与构建身份显式化','03-materials.jpg','本地网站 · 分析选项','定位前先回答“材料是否对应”',[
            ('源码身份','支持版本和 commit；自定义内核需要精确修订状态。'),('诊断产物','可附 vmlinux、模块、ELF vmcore 与内核配置。'),('身份门禁','预期 Build ID 用于匹配；不匹配时停止对应产物查询。')],
            '界面支持上传转储材料，不代表当前数据集具有vmcore或已完成转储实验。未为本页上传文件或下载源码。'),
        ('案例库连接原始日志、来源与复现线索','04-benchmark.jpg','本地网站 · 案例浏览','展示资产规模与问题类型',[
            ('80 条网站案例','属于扩展展示集；不能等同于严格定位集的 60 个有效样本。'),('按异常浏览','聚合日志特征、调用链、来源与修复线索。'),('试跑报告独立保存','个人空间已有六份归档报告；试跑不计入业务解决数。')],
            '网站案例类别与严格数据集的故障族不是同一分类体系。所有80条并非80个独立根因，也不是80条完整材料合同已通过的定位样本。'),
        ('日志报告保留原始行号与异常上下文','report-log.jpg','本地网站 · 既有 UAF 报告回放','从摘要回到可核查的现场',[
            ('第一可观测诊断','保留 KASAN 报告，以及 CPU、任务、分配与释放上下文。'),('关键调用链','展示符号和偏移；没有源码路径时明确保留缺口。'),('可追溯材料','原始日志与报告可查看和导出，便于复核。')],
            '采用增强预检组的UAF既有真实轨迹，耗时18.166秒、1次模型请求、3次自动工具检查。不是此前只用日志的另一份UAF运行。'),
        ('定界、代码候选与因果缺口同时呈现','report-agent.jpg','本地网站 · 问题定位 Agent','让“为什么这样定位”可以被审阅',[
            ('定界字段','运行阶段 / KASAN 检测器 / ki_bench 涉及组件。'),('代码候选','external/ki_bench.c 的函数与行区间，引用工具证据 T3。'),('结论边界','引入提交仍未确定；位置候选不等于根因已经验证。')],
            '报告带有归档回放标记。候选需要实际源码读取支持；工具证据和后续验证建议原样保留，未通过人工确认伪造已解决状态。'),
        ('专家经验沉淀为可复用的排查步骤','expert-content.jpg','本地网站 · 对象生命周期经验','经验正文连接识别、取证与验证',[
            ('结构化经验','异常识别条件、分析建议、定位流程和验证清单。'),('真实来源','社区日志与修复依据可追溯；未本地复现时明确注明。'),('署名与反馈','记录贡献者、使用与验证结果，供后续经验迭代。')],
            '当前展示的是项目内置声明式经验，不是自动执行的脚本。零业务统计保持零，没有为了页面效果新增虚构贡献。'),
        ('经验投稿与手动基准评测约束能力变更','submission.jpg','本地网站 · 经验投稿表单','贡献可审核，合入有门禁',[
            ('先说明变更','记录匹配词、建议步骤、正文与验证依据。'),('冻结评测基准','提交时保存当前案例指纹；手动启动独立类别评测。'),('审核后才合入','无退化门禁保护已有能力；类别 F1 与代码定位命中分开。')],
            '只打开空白投稿表单，未创建投稿、未启动Benchmark。管理员权限在服务端检查。类别F1不能代替Agent位置或机制准确率。'),
        ('业务效能只统计人工确认的真实任务','dashboard.jpg','本地网站 · 效能看板','把研究成绩与业务收益分开记账',[
            ('确认后才算解决','统计提交至人工确认的业务耗时。'),('配对人工基线','仅比较填写了人工基线的同一批真实任务。'),('试跑保持隔离','六份基准回放不进入业务收益；当前业务指标保持为空或零。')],
            '本地新业务状态没有人工确认闭环，因此页面展示零和缺失值。不可用基准定位47.2%的时间下降冒充生产MTTR或人时收益。'),
    ]
    output=[];talk=[];index=[]
    def append(sec,title,body,sub,src,note,visual):
        i=len(output)+1
        output.append(f'<section class="slide" data-sec="{E(sec)}" data-title="{E(re.sub("<[^>]*>","",title))}"><div class="kicker"><b>{i:02d}</b>{E(sec)} · {E(src)}</div><h1>{title}</h1>'+(f'<div class="sub">{sub}</div>' if sub else '')+body+'</section>')
        talk.append(f'## {i:02d} {re.sub("<[^>]*>","",title)}\n\n{note}\n\n来源：{src}。\n')
        index.append((i,sec,re.sub('<[^>]*>','',title),visual))
    for n,(s,note) in enumerate(zip(slides,notes),1):
        if n in [20,21]:
            for title,image,label,ftitle,items,fnote in screens[:4] if n==20 else screens[4:]:
                append('系统与功能展示',title,feature(image,label,ftitle,items),'Windows 本地实拍；既有实验报告以回放方式展示。','本地网站截图',fnote,'真实功能界面与说明')
        elif n in replacements:
            append(*replacements[n],visual='科研图 / 自绘流程 / 实现记录')
        else:
            sec=re.search('data-sec="([^"]+)"',s).group(1)
            title=re.search('<h1>(.*?)</h1>',s,re.S).group(1)
            submatch=re.search('<div class="sub">(.*?)</div>',s,re.S)
            src=re.search('<div class="kicker"><b>.*?</b>(.*?)</div>',s,re.S).group(1).split(' · ',1)[-1]
            body=re.split('</h1>',s,maxsplit=1)[1].removesuffix('</section>')
            if submatch:body=body.replace(submatch.group(0),'',1)
            append(sec,title,body,submatch.group(1) if submatch else '',src,re.sub(r'^## .*?\n\n','',note,flags=re.S).split('\n\n来源：')[0],'统计图 / 系统机制 / 证据表')
        if n==14:
            append('系统与功能展示','全流程：从输入材料到失败回归',overview,'点击播放或按 J 逐步讲解；箭头表示材料与证据流转。','系统实现 · 可交互机制示意',
                '动画不是新增实验轨迹，按教学节奏演示设计。首诊断、取证、候选和反馈为当前工程流程；独立机制评分、引入提交真值和修复干预未完成，不能把最后一步说成自动因果闭环。','六阶段可播放流程动画')
        if n==17:
            append('系统与功能展示','真实 UAF 轨迹：工具如何支撑代码候选',trace,'来自已保存的实验；播放速度为教学节奏，不代表单工具实测耗时。','真实工具轨迹 · 日志 + 源码',
                '按原轨迹的incident→source_search→source_read→模型输出顺序重放观察内容。总定位18.166秒、1次模型请求来自真实记录。不存在完整逐工具时间测量，因此不为工具阶段造时间轴。独立评分命中仍不等于因果证明。','五阶段可播放证据回放')
    assert len(output)==48,len(output)

    # Internal implementation versions belong only in machine-readable provenance.
    substitutions=[
        ('v10 源码预检','自动预检增强'),('v10 迭代','自动预检增强'),('v9 对照','模型按需检索'),
        ('v10','预检增强组'),('v9','按需检索组'),('v6','早期缺失材料试验'),
        ('eagerBoundary','首诊断预检'),('sourceTriage','日志引导的源码预检'),
        ('rootCauseAccuracy=null','独立机制准确率尚无真值'),('firstSceneSeconds','首诊断提取计时'),
        ('ready 样本','有效样本'),('60 ready','60 个有效样本'),('8 excluded','8 个排除场景'),
        ('ready 划分','有效集划分'),('60 个有效样本 ×','60 个有效样本 ×'),
        ('严格 stability-v1','严格定位评测集'),('网站 v2','网站扩展集'),('旧注入 v1','历史注入集'),('社区 v1','社区报告集'),
        ('额外三例在清单中均为train','额外三例在清单中均为训练侧'),
        ('holdout 不代表独立盲测','“额外样本”不代表独立盲测'),
    ]
    def clean(s):
        for a,b in substitutions:s=s.replace(a,b)
        s=s.replace('benchmark-traces-预检增强组.tgz；15 个文件','原始工具轨迹归档；15 个文件')
        s=s.replace('首诊断预检 首诊断预检','首诊断预检').replace('源码预检 日志引导的源码预检','日志引导的源码预检')
        s=s.replace('文件名中的 “额外样本”不代表独立盲测','均为训练侧样本，不属于独立盲测')
        s=s.replace('三例在 manifest 中均为 train；均为训练侧样本，不属于独立盲测','三例在冻结清单中均为训练侧；本次属于额外探索，不属于独立盲测')
        s=s.replace('全量 test','全量独立测试集').replace('冻结 test','冻结测试集')
        s=s.replace('artifacts+source / artifacts / source','产物 + 源码 / 仅产物 / 仅源码')
        return s
    output=[clean(s) for s in output];talk=[clean(s) for s in talk]
    # Replace cryptic source IDs on slides, while retaining file hashes in source notes.
    aliases={'S1':'系统设计文档','S2':'数据资产盘点','S3':'配对实验记录','S4':'历史缺失材料试验','S5':'既有网站验收','S6':'严格集冻结清单','S7':'UAF 冻结标签','S8':'OOM 冻结标签'}
    for i,s in enumerate(output):
        k=re.search('<div class="kicker">.*?</div>',s).group(0)
        for a,b in aliases.items(): k=re.sub(r'\b'+a+r'\b',b,k)
        output[i]=re.sub('<div class="kicker">.*?</div>',lambda m:k,s,count=1)
    # Write the updated storyboard before the HTML is assembled.
    plan='# Kernel Insight 系统设计与实证分析\n\n48 页论文结构网页版讲解稿。正文用“模型按需检索”和“自动预检增强”解释两组方法；原实验标识仅保留在机器可读证据和源文件中。所有结果来自既有真实记录，未新增模型实验。\n\n## 逐页索引\n\n| 页 | 段 | 内容 | 画面 |\n|---:|---|---|---|\n'
    plan+='\n'.join(f'| {i} | {sec} | {clean(t)} | {v} |' for i,sec,t,v in index)
    plan+='''

## 打开与讲解

双击 `deck.html` 可离线打开。方向键翻页，G 目录，数字跳页，F 全屏，C 页码。两张动画页默认静止：J / K 前后走步，P 播放 / 暂停，也可使用页内按钮。动画按教学节奏运行，不暗示各阶段有实测耗时。

Windows 网站：`http://127.0.0.1:8787`。启动命令：`powershell -ExecutionPolicy Bypass -File scripts/start-windows-site.ps1`。网站使用独立目录 `data/windows-local`；本次只采集界面，不执行功能验收。六份原实验报告明确标为历史回放，未连接模型重新推理。

## 图表与证据

`research_figures.py` 从冻结值生成论文风格多面板、配对观测、结果矩阵和精确置信区间。没有为单次耗时伪造方差、误差条或显著性。材料组合图是能力合同，不是七组实验结果。网站截图及裁切来源见 `media/site/provenance.json`；没有私有业务数据。

`analysis-data.json` 与 CSV 保存原数据、哈希及统计口径。`讲稿.md` 解释逐页分母、失败和局限，`资料来源.md` 提供一手文献。当前代码位置命中不等于机制或提交因果正确。

```powershell
python deliverables/kernel-insight-system/build_deck.py
python deliverables/kernel-insight-system/render_preview.py deliverables/kernel-insight-system/deck.html 48 deliverables/kernel-insight-system/rendered 1
python deliverables/kernel-insight-system/verify_deck.py
```

渲染后检查全页预览和关键单页；页面检查仅针对 slide 布局与交互，不是网站功能校验。
'''
    (here/'说明.md').write_text(plan,encoding='utf-8')
    return output,talk

CSS='''
.feature{display:flex;gap:66px;flex:1;min-height:0;margin-top:34px;align-items:center}
.screen-card{flex:1.22;min-width:0;height:100%;display:flex;align-items:center;justify-content:center}
.screen-card img{display:block;max-width:100%;max-height:100%;object-fit:contain;border-radius:20px;box-shadow:0 14px 48px rgba(0,0,0,.1)}
.feature-copy{flex:1;min-width:0}.feature-label{font-size:22px;color:var(--muted);margin-bottom:18px}
.feature-title{font-size:40px;font-weight:600;line-height:1.35;margin-bottom:24px}
.feature-point{padding:17px 0;border-top:1px solid var(--line)}.feature-point b{font-size:28px;font-weight:600}
.feature-point p{font-size:25px;line-height:1.5;color:var(--muted);margin-top:8px}
.flow-demo{flex:1;min-height:0;display:flex;flex-direction:column;margin-top:32px}
.flow-canvas{flex:1;min-height:0;position:relative}.flow-canvas>.diagbox{position:absolute;inset:0;margin-top:0}
.flow-node{opacity:.58;transition:opacity .35s}.flow-node.done{opacity:.83}.flow-node.current{opacity:1}
.flow-node.current rect{fill:#E8F0FE;stroke:var(--accent);stroke-width:3}.flow-node.current text:first-of-type{fill:var(--accent)}
.flow-token{transition:cx .65s ease-in-out,cy .65s ease-in-out}.flow-detail{font-size:26px;line-height:1.45;color:var(--muted);margin:20px 6px 14px;min-height:76px;display:flex;align-items:center}
.flow-controls{display:flex;align-items:center;gap:18px}.flow-controls button{font:500 23px var(--font);padding:13px 24px;border:1px solid var(--line);border-radius:12px;background:#fff;color:var(--ink);cursor:pointer}
.flow-controls button[data-action=play]{background:var(--accent);color:#fff;border-color:var(--accent);min-width:152px}
.flow-controls button:disabled{opacity:.35;cursor:default}.flow-counter{font-size:24px;margin-left:12px;color:var(--accent)}.flow-hint{margin-left:auto;font-size:22px;color:var(--muted)}
@media(prefers-reduced-motion:reduce){.flow-node,.flow-token{transition:none}}
'''

ANIM_JS='''
  let anim=null;
  function startAnim(sl){
    if(anim) anim.stop(); anim=null;
    const root=sl.querySelector('[data-flow]'); if(!root)return;
    const frames=JSON.parse(root.querySelector('.flow-data').textContent);
    const fixed=(location.search.match(/[?&]anim=(\\d+)/)||[])[1];
    let k=Math.min(frames.length-1,Math.max(0,Number(fixed||0))),timer=null;
    const play=root.querySelector('[data-action=play]');
    function stop(){if(timer)clearInterval(timer);timer=null;play.textContent='播放流程';play.setAttribute('aria-label','播放流程');root.dataset.playing='false';}
    function apply(){
      root.dataset.step=String(k);
      root.querySelectorAll('.flow-node').forEach((el,i)=>{el.classList.toggle('current',i===k);el.classList.toggle('done',i<k);});
      root.querySelector('.flow-detail').textContent=frames[k].detail;
      root.querySelector('.flow-counter').textContent=`${k+1} / ${frames.length}`;
      root.querySelector('[data-action=prev]').disabled=k===0;
      root.querySelector('[data-action=next]').disabled=k===frames.length-1;
      const dot=root.querySelector('.flow-token');dot.setAttribute('cx',frames[k].token[0]);dot.setAttribute('cy',frames[k].token[1]);
      root.querySelectorAll('[class^=trace-detail]').forEach((el,i)=>el.textContent=(frames[k].detailLines||[])[i]||'');
    }
    function next(){if(k<frames.length-1){k++;apply();}if(k===frames.length-1)stop();}
    function prev(){stop();k=Math.max(0,k-1);apply();}
    function toggle(){if(timer){stop();return;}if(k===frames.length-1)k=0;apply();root.dataset.playing='true';play.textContent='暂停播放';play.setAttribute('aria-label','暂停播放');timer=setInterval(next,2800);}
    root.querySelectorAll('button').forEach(btn=>{btn.onclick=e=>{e.stopPropagation();const a=btn.dataset.action;if(a==='play')toggle();if(a==='prev')prev();if(a==='next'){stop();next();}if(a==='reset'){stop();k=0;apply();}};});
    apply();anim={next(){stop();next();},prev,stop,toggle};
  }
'''
