"""Build a new explanatory deck from frozen public measurements and executed code."""
import pathlib,json,html,hashlib,csv,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];MEDIA=HERE/'media';MEDIA.mkdir(exist_ok=True)
R=ROOT/'research/jev-qwen35-9b-20261016';USED=set()
BLUE='#0071E3';INK='#1D1D1F';GRAY='#6E6E73';PALE='#F5F5F7'
def load(p):
    p=ROOT/p;USED.add(p)
    if p.suffix=='.csv':return list(csv.DictReader(p.open(encoding='utf-8-sig')))
    if p.suffix=='.jsonl':return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
    return json.loads(p.read_text(encoding='utf-8'))
frozen=load('research/jev-qwen35-9b-20261016/dataset-frozen.json')
summ=load('research/jev-qwen35-9b-20261016/summary.json')
cal=load('research/jev-qwen35-9b-20261016/calibration.json')
training=load('research/jev-qwen35-9b-20261016/training-steps.jsonl')
agent=load('research/jev-qwen35-9b-20261016/tables/agent32k-aggregate.csv')
lat=load('research/jev-report-qa-20261018/evidence.json')
stats27=load('research/kv-concurrency-20261016/statistics.json')
for name in ['train.py','prepare-data.py','training-protocol.json','training-environment.json','training-complete.json']:
    USED.add(R/name)
USED.add(ROOT/'docs/Jev决策模型报告答疑与通俗解读_20261018.md')
# A completely synthetic, labelled teaching example; never an alleged training trace.
logits=np.array([.4,-.8,1.8,0,.6]);target=2;sigma=.4
def softmax(x):
    z=x-np.max(x,axis=-1,keepdims=True);v=np.exp(z);return v/v.sum(axis=-1,keepdims=True)
p=softmax(logits);eps=np.random.default_rng(20261018).normal(0,sigma,(4,5));eps-=eps.mean(-1,keepdims=True)
z=logits[None,:]+eps;q=softmax(z)
reward=np.maximum(np.log(np.maximum(q[:,target],1e-12)),-9.21)+.75*q[:,target]/np.linalg.norm(q,axis=-1)
adv=reward-reward.mean();adv/=adv.std(ddof=1)+1e-6
density=-((z-logits)**2).sum(-1)/(2*sigma*sigma)
ce=-np.log(p[target]);loss=ce-np.mean(adv*density)
grad=p.copy();grad[target]-=1;grad-=np.mean(adv[:,None]*(z-logits)/(sigma*sigma),axis=0)
def fixed_loss(x):return -np.log(softmax(x)[target])-np.mean(adv*(-((z-x)**2).sum(-1)/(2*sigma*sigma)))
fd=np.array([(fixed_loss(logits+np.eye(5)[i]*1e-5)-fixed_loss(logits-np.eye(5)[i]*1e-5))/2e-5 for i in range(5)])
assert np.max(np.abs(fd-grad))<1e-7
toy={'scope':'Synthetic teaching example, not recorded training inputs, probabilities or gradients. Gaussian centered noise and fixed z/adv derivative match executed rlcd() math.','logits':logits.tolist(),'target_index':target,'sigma':sigma,'p':p.tolist(),'eps_centered':eps.tolist(),'z':z.tolist(),'q':q.tolist(),'reward':reward.tolist(),'advantage':adv.tolist(),'logdensity_energy':density.tolist(),'CE':float(ce),'loss':float(loss),'gradient_wrt_logits':grad.tolist(),'finite_difference_max_error':float(np.max(np.abs(fd-grad)))}
(HERE/'教学概率与RLCD计算.json').write_text(json.dumps(toy,ensure_ascii=False,indent=2),encoding='utf-8')
bug=[{k:r[k] for k in ['case','source','split','marker','label']} for r in frozen['records'] if r.get('marker') and 'circular' in r['marker'].lower() and r['label']=='rcu_progress']
assert len(bug)==4 and all(r['split']=='test' for r in bug)
(HERE/'旧数据标注规则审计.json').write_text(json.dumps({'finding':"'rcu' in 'possible circular locking dependency' evaluates True before locking branch",'affected_records':bug,'policy':'Frozen labels and scores retained unchanged. Rebuild and re-evaluate under a new dataset version before scientific claims.'},ensure_ascii=False,indent=2),encoding='utf-8')

# Publication-ready data figures, independent of browser rendering.
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':16,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','axes.unicode_minus':False})
def savefig(fig,name):
    fig.savefig(MEDIA/(name+'.svg'),bbox_inches='tight',facecolor='white',metadata={'Date':None});fig.savefig(MEDIA/(name+'.png'),dpi=150,bbox_inches='tight',facecolor='white');plt.close(fig)
fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
def timing27(c,d,cache,arm):return next(r['makespan_seconds'] for r in stats27['summary'] if r['mode']=='sequential' and r['cache']==cache and r['concurrency']==c and r['decisions']==d and r['arm']==arm and r['instrumented'])
for ax,(title,a,b,unit) in zip(axs,[('27B · 单步冷条件',timing27(1,1,'cold','decision'),timing27(1,1,'cold','chat'),'s'),('27B · 四任务八步预热',timing27(4,8,'warm','decision'),timing27(4,8,'warm','chat'),'s'),('微调9B · 四任务八步预热',1.2802849046,1.3876212164,'s')]):
    ax.bar(['Decision','单字母Chat'],[a,b],color=[BLUE,'#AAB2BD'],width=.55);ax.set_ylim(0,max(a,b)*1.32);ax.set_title(title,pad=25);ax.set_ylabel('整批完成时间 / 秒')
    for i,v in enumerate([a,b]):ax.text(i,v+max(a,b)*.05,f'{v:.3f}',ha='center',fontsize=21)
    ax.text(.5,.92,f'耗时减少 {(b-a)/b*100:+.2f}%',transform=ax.transAxes,ha='center',color=GRAY)
savefig(fig,'接口性能对照')
fig,axs=plt.subplots(1,2,figsize=(16,5),layout='constrained')
for ax,(title,vals,lim) in zip(axs,[('首诊断弱标签命中 / 87',[66,78],87),('NLL（越低越好）',[cal[0]['case_nll'],cal[1]['case_nll']],2.1)]):
    ax.bar(['基座9B','微调9B T=1'],vals,color=['#AAB2BD',BLUE],width=.55);ax.set_ylim(0,lim*1.15);ax.set_title(title,pad=20)
    for i,v in enumerate(vals):ax.text(i,v+lim*.035,str(v) if title.startswith('首') else f'{v:.3f}',ha='center',fontsize=25)
savefig(fig,'分类与概率反例')
fig,ax=plt.subplots(figsize=(16,5),layout='constrained');vals=[float(r['total_localization_seconds']) for r in agent]
labs=['基座 · 纯Chat','基座 · 混合','微调 · 纯Chat','微调 · 混合'];ax.barh(labs,vals,color=['#AAB2BD',BLUE,'#AAB2BD',BLUE]);ax.invert_yaxis();ax.set_xlim(0,72);ax.set_xlabel('三个案例的定位耗时之和 / 秒')
for i,(v,r) in enumerate(zip(vals,agent)):ax.text(v+.8,i,f'{v:.3f}s · {r["model_http_calls"]} HTTP · 2/3命中',va='center',fontsize=19)
savefig(fig,'完整Agent对照')
fig,ax=plt.subplots(figsize=(16,5.4),layout='constrained');xs=[r['elapsed'] for r in training];ys=[r['loss'] for r in training]
for e in range(3):
    rr=[r for r in training if r['epoch']==e];ax.axvspan(0 if e==0 else max(r['elapsed'] for r in training if r['epoch']==e-1),rr[-1]['elapsed'],color=BLUE if e==1 else '#AAB2BD',alpha=.08)
ax.plot(xs,ys,color=BLUE,lw=1.6);ax.set_xlim(0,343.689);ax.set_xlabel('训练日志elapsed / 秒（首步含编译）');ax.set_ylabel('记录的损失值');ax.text(.02,.92,'epoch0: CE → epoch1–2: CE+RLCD；跨阶段损失不能直接比较',transform=ax.transAxes,color=GRAY)
savefig(fig,'真实训练曲线')
names=['生命周期','越界','泄漏','锁','阻塞','watchdog','RCU','OOM','保护','引用计数','警告/panic','其他']
mat=np.array([[frozen['label_counts'][s].get(c,0) for c in frozen['classes']] for s in ['train','dev','test']])
fig,ax=plt.subplots(figsize=(16,4.8),layout='constrained');ax.imshow(mat,cmap='Blues',vmin=0,vmax=20,aspect='auto');ax.set_xticks(range(12),names,rotation=25,ha='right');ax.set_yticks(range(3),['训练33','开发4','测试87'])
for j in range(3):
    for i in range(12):ax.text(i,j,str(mat[j,i]),ha='center',va='center',color='white' if mat[j,i]>12 else INK,fontsize=23)
ax.set_title('冻结数据类别分布（包含已发现的4条规则误标）',pad=20);savefig(fig,'类别覆盖热力图')

E=html.escape
def txt(x,y,s,size=30,color=INK,weight=400,anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{E(str(s))}</text>'
def rect(x,y,w,h,fill=PALE,stroke='none',dash=False):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="2"'+(' stroke-dasharray="8 6"' if dash else '')+'/>'
def box(x,y,w,h,title,lines=(),blue=False,size=29):
    return rect(x,y,w,h,'#E8F3FF' if blue else PALE,BLUE if blue else 'none')+txt(x+22,y+44,title,size,BLUE if blue else INK,600)+''.join(txt(x+22,y+84+i*35,s,24,GRAY) for i,s in enumerate(lines))
def arrow(x,y,xx,yy,color=GRAY,dash=False):
    return f'<path d="M{x},{y} L{xx},{yy}" fill="none" stroke="{color}" stroke-width="3" marker-end="url(#arB)"'+(' stroke-dasharray="8 6"' if dash else '')+'/>'
def path(d,color=BLUE,dash=False):return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3" marker-end="url(#arB)"'+(' stroke-dasharray="8 6"' if dash else '')+'/>'
def group(k,body):return f'<g data-a="{k}">{body}</g>'
def foot(s):return txt(35,554,s,23,GRAY)
DEFS='<defs><marker id="arB" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10z" fill="#0071E3"/></marker></defs>'
slides=[];notes=[];plan=[]
def add(sec,title,sub,body,note,source='项目冻结证据 / 2026-10-18整理',steps=None,figure=None):
    n=len(slides)+1;plan.append((n,sec,title,figure or '自绘SVG'+(' · 分步' if steps else '')))
    if figure:content=f'<div class="fig card"><img src="media/{figure}.svg" alt="{E(title)}"></div>'
    else:
        svg=f'<svg class="sv" viewBox="0 0 1600 580" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">{body}</svg>'
        standalone=svg.replace('>'+body,'>'+DEFS+body).replace('<svg class="sv"','<svg style="font-family:Microsoft YaHei,sans-serif"')
        (MEDIA/f'diagram-{n:02d}.svg').write_text(standalone,encoding='utf-8');content='<div class="art">'+svg+'</div>'
    controls=''
    if steps:
        controls='<div class="walk-controls"><button data-act="prev">← 上一步</button><button data-act="play">播放讲解</button><button data-act="next">下一步 →</button><button data-act="reset">从头</button><span class="walk-caption"></span></div><script type="application/json" class="walk-data">'+json.dumps(steps,ensure_ascii=False)+'</script>'
    slides.append(f'<section class="slide {"walk" if steps else ""}" data-sec="{E(sec)}" data-title="{E(title)}"><div class="kicker"><b>{n:02d}</b>{E(source)}</div><h1>{E(title)}</h1><div class="sub">{E(sub)}</div>{content}{controls}</section>')
    notes.append(f'## {n:02d} {title}\n\n{note}\n\n来源：{source}。\n')

add('问题与计算','Jev到底省了什么，9B又学到了什么？','从输入、KV与输出路径，走到数据、选项概率与RLCD梯度。',
    txt(65,115,'先看计算路径',64,BLUE,600)+txt(65,210,'再看训练证据',64,INK,600)+
    box(65,320,440,150,'输入与缓存',['同一日志，哪些必须重算？'])+arrow(525,395,585,395)+box(605,320,440,150,'类型化输出',['少写文本，是否真的更快？'])+arrow(1065,395,1125,395)+box(1145,320,390,150,'任务微调',['概率如何参与损失？'],True),
    '这是根据报告答疑新做的独立讲解，不是旧70页的追加。机制图只画计算依赖，不将方框长度当实测秒数；数据图读取冻结结果。先弄清接口与模型身份，再区分判断、训练和因果定位。')
add('问题与计算','同一个Decision名字，背后可能是五种实现','接口、架构、训练权重和执行引擎应分别识别。',
    ''.join(box(35+(i%3)*520,40+(i//3)*245,490,200,a,b,i==1,size=30) for i,(a,b) in enumerate([
    ('官方Jev',['TypeSafe专有服务','本项目未直接复测其API']),('SGLang Decision',['聊天骨干 + 字母logit读出','本项目已测27B与9B']),('PPLX-Decider',['真实专门训练的权重','官方参考执行与SGLang分开']),('nanojev',['第三方假设性重建','4B + LoRA + pointer head']),('Laya',['开源编码器决策模型','参考其思想，非官方配方']),('本项目9B微调',['原Qwen骨干 + LoRA','保留原LM字母读出'])])),
    '不要把接口名称当权重身份证。外部nanojev与我们的9B不是同一模型，外部作者成绩不属于本项目内核实验。Laya同名RLCD也不能证明获取了官方Jev完整训练方法。',source='报告答疑 / 官方文档与作者仓库（链接见来源页）')

# Four homologous lanes: widths express computation roles, never elapsed duration.
b=txt(35,35,'输入',25,GRAY)+txt(465,35,'共同前向：处理输入 / 建立KV或状态',25,GRAY)+txt(1050,35,'输出路径',25,GRAY)
for i,(name,out,kvc) in enumerate([('长篇 / thinking Chat','首token → 多步decode','后续输出读回时，KV继续增长'),('关闭thinking的Chat','首token → 答案 / JSON','仍可能有多个输出token'),('单字母Chat','首token即答案 A','max_tokens=1可无后续decode'),('通用Decision','字母候选分数 → 概率','不生成文本；仍计算输入')]):
    y=62+i*112
    b+=group(i,txt(35,y+38,name,28,BLUE if i==3 else INK,600)+rect(355,y,600,76,'#EDF2F7')+txt(380,y+33,'日志 + 问题 + 候选 → prefill',27)+txt(380,y+63,'读完整输入；缓存命中时可复用前缀',21,GRAY)+arrow(965,y+36,1020,y+36)+box(1040,y,510,84,out,[],i==3,size=26)+txt(1045,y+108,kvc,21,GRAY))
b+=foot('机制示意，不是时长比例；通用Decision没有自动变成专有Jev架构。')
add('问题与计算','输出越短，Decision还能省的工作就越少','关闭thinking减少显式思考文本；输入处理与网络前向仍然存在。',b,
    '四条流程从相同材料出发，但完整prompt是否相同要实际检查。长篇Chat会连续写许多token；关闭thinking仍要输出答案；单字母Chat可只用prefill得到的第一个token。通用Decision直接读候选分数，避免自由生成和解析，但不会免除输入前向与缓存需求。此图按语义对齐，不是按秒数绘制。',steps=['长篇输出包含多次后续decode','关闭thinking仍可能输出很多答案token','单字母答案已经省掉几乎所有后续解码','Decision改为概率读出；输入前向仍保留'])
b=group(0,box(45,175,350,155,'同一完整prompt',['日志 / 问题 / A…E'])+arrow(410,252,485,252))+group(1,box(505,175,430,155,'prefill → 最后位置h',['输入KV / 线性状态','原LM读出 → 字母logits'],True))
b+=group(2,arrow(955,252,1020,135)+box(1040,55,510,155,'单字母Chat',['取/采样字母 → SSE内容 A','第一字母可直接来自prefill']))
b+=group(3,arrow(955,252,1020,415)+box(1040,335,510,155,'Decision',['选项logits → softmax → 概率','不经自由文本解码'],True))+foot('不能断言“单字母Chat必比Decision多一次模型前向”；剩余差异需从实际执行与调度测量。')
add('问题与计算','第一个字母，也可以直接来自prefill','只有生成后续token，通常才需要把先前输出再喂回模型。',b,
    '这是最容易讲错的一页。自回归模型处理输入后，最后位置的hidden state就能预测第一个输出token。若max_tokens=1，Chat不一定再进行一个decode前向。Decision与它共享昂贵的输入处理；区别主要是读出、服务流程和返回契约，不应凭接口名称捏造一次前向的节省。',steps=['准备相同prompt，而不只是相同题干','输入前向得到h与候选logits','Chat直接把首字母作为内容返回','Decision直接返回候选条件概率'])
b=txt(50,45,'教学示例：输入S=8个token；右侧只画attention KV槽，线性状态另计',27,GRAY)
for i,(name,count,out) in enumerate([('prefill处理输入',8,'得到输出1；尚未把输出1读回'),('decode读回输出1',9,'得到输出2'),('decode读回输出2',10,'得到输出3'),('decode读回输出3',11,'得到输出4后停止')]):
    y=90+i*104;b+=group(i,txt(45,y+38,name,28,INK,600)+''.join(rect(430+j*62,y,50,46,BLUE if j<8 else '#AAB2BD') for j in range(count))+txt(1150,y+34,out,24,GRAY))
b+=foot('示意：输出4token通常需3次后续decode；Decision与单字母Chat均保留输入成本。缓存收尾因实现而异。')
add('问题与计算','零文本输出，不等于零KV或零输入计算','蓝格是输入KV；灰格是后续读回输出时新增的KV。',b,
    '槽数只用于解释因果注意力计算，不是测得的真实内存时间线。输入8token产生首个输出；再生成3个token通常需要3次后续前向，处理长度依次变9、10、11。最终输出尚未反馈前不一定已经有它的KV。实际混合模型还有线性状态池，不能把所有内存都画成这些格子。',steps=['输入前向已产生KV：不写答案也要读题','继续生成需要读回上一个输出','每个后续前向延长已有KV','减少长输出有潜力，减少一个字母的收益很有限'])
b=''
for i,(a,lines) in enumerate([('HTTP一次放8题',['网络打包：少发请求','内部仍可能有8个独立prompt']),('通用前缀缓存',['相同token前缀已算过 → 复用','选项/模板改动可能改变命中']),('共享状态后分叉',['状态编码一次 → 各题接着计算','需要模型与实现明确支持'])]):
    x=35+i*520;b+=box(x,40,490,155,a,lines,i==2,size=29)
    if i==0:
        for j in range(3):
            yy=230+j*85;b+=rect(x+35,yy,420,65)+txt(x+60,yy+42,f'S + 问题{j+1} → 独立评分',27)
    elif i==1:
        b+=rect(x+40,235,180,160,'#E8F3FF')+txt(x+130,300,'已缓存前缀',25,BLUE,600,'middle')+txt(x+130,350,'KV(S)',28,BLUE,600,'middle')
        for j in range(3):b+=arrow(x+230,315,x+290,245+j*85,dash=True)+rect(x+305,215+j*85,150,60)+txt(x+380,254+j*85,'续算Q'+str(j+1),25,anchor='middle')
    else:
        b+=rect(x+35,265,185,95,'#E8F3FF',BLUE)+txt(x+127,304,'S只编码一次',24,BLUE,600,'middle')+txt(x+127,338,'共享状态',23,GRAY,anchor='middle')
        for j in range(3):b+=arrow(x+230,312,x+290,245+j*85)+rect(x+305,215+j*85,150,60)+txt(x+380,254+j*85,'分叉Q'+str(j+1),25,anchor='middle')
b+=foot('本项目八题实验是独立prompt评分 + 实际前缀复用；未实测nanojev的共享状态分叉路径。')
add('问题与计算','批量、缓存命中与共享状态不是一回事','看实际计算图和cached_tokens，不能只看HTTP请求数。',b,
    '三张图只用于区别概念，不声称实现完全相同。把八题装进一个HTTP不保证只读一次日志；SGLang会处理独立题目的prompt，缓存命中要看实际token前缀。外部nanojev作者描述了状态编码后缓存分叉的路径，但我们没有执行它，因此不能把它的自报加速改写成我们的结论。')
add('实测与模型','八步有小幅收益，单步与冷条件保留反例','不同模型、工作量与缓存条件分开；每格5次trial均值。','',
    '左图27B单步冷条件几乎持平，中图27B四任务八步预热约快11%，右图微调9B同样工作量约快7.74%。这些是不同条件，不能横向当作纯模型尺寸消融。9B四任务八步冷条件Decision还慢约4.1%。图的纵轴都从零起，末任务返回作为整批耗时，不把Decision叫作文本TTFT。',figure='接口性能对照',source='27B / 9B冻结并发矩阵；未新增模型调用')
add('实测与模型','没有观测到KV内存优势','微调9B · 四任务八步预热；峰值是离散采样观测值。',
    box(45,100,730,300,'平均trial峰值 · 活跃attention KV',['Decision       458.219 MiB','单字母Chat     458.125 MiB','两者输入很接近，不支持节省结论'],True,size=32)+box(825,100,730,300,'活跃线性状态 / resident显存',['状态峰值：Decision 16 / Chat 13 槽','NVML resident约48GB；有静态预分配','池容量、活跃量与整卡占用不是一个数'],size=31)+foot('9B每token attention KV=32KiB；旧27B为64KiB，不能把模型结构差异归因为接口。'),
    '不输出长文本可能减少一些后续缓存增长，但本实验Chat也只生成一个字母。固定池不会随接口切换自动释放；Decision的活跃状态峰值反而更高。KV字节公式只覆盖full-attention层，线性状态另计。不能把9B比27B小的KV需求说成Decision节省。',source='9B并发矩阵 / model config / NVML与scheduler冻结观测')
add('实测与模型','PPLX分类持平，已测部署却更慢','完整GPU分时复测：同一A100，仍未统一推理引擎。',
    box(40,60,680,180,'通用Qwen + SGLang',['test：9个唯一案例，各3次均正确','平均2.563秒 · 零文本Decision'],True,size=33)+box(880,60,680,180,'PPLX + Transformers参考路径',['test：同样9例，各3次均正确','平均5.672秒 · 约2.21倍耗时'],size=31)+
    box(40,310,1520,170,'已排除CPU卸载；仍不能把差异全部归因权重',['不同内核、提示编码、批处理与读出；PPLX输入token约多7.5%','旧CPU卸载19.455秒属于另一条件，不混进这轮公平速度比较'],size=31),
    '效果不好这个前提要改成没有显示额外分类优势。有限案例都正确不是等效证明。全GPU排除了CPU搬运，但SGLang与官方Transformers/SDPA运行时不一致，执行顺序固定。因此只能比较已测部署方案，不能断言专用决策训练本身变慢。该轮通用端也是Decision，不是单字母Chat。',source='PPLX全GPU分时复测 / 2026-10-12独立协议')
add('实测与模型','外部nanojev不是本项目的微调9B','两套设计都含任务监督，但不能互换架构、数据或成绩。',
    box(40,55,730,360,'nanojev · 外部作者实现',['Qwen3.5-4B-Base + LoRA','pointer head / 状态缓存分叉','作者自己的训练集与评测','本项目没有执行其内核复测'],size=33)+box(830,55,730,360,'本项目Qwen3.5-9B',['48处LoRA / 原LM字母读出','SGLang中独立prompt评分','33训练 / 4开发 / 87测试','分类66→78；不能冒称nanojev成绩'],True,size=33)+foot('任务适配值得研究；尚无同一新测试上的9B/27B公平完整定位对照。'),
    'nanojev是原作者明确描述的假设性重建，不是官方Jev。我们没有把其代码或权重在本项目数据上跑过，也没有实现其pointer head或共享状态分叉。当前结果支持针对固定任务监督适配，不支持小模型普遍取代大模型。',source='nanojev作者README / 本项目train.py；外部自报不并入本地实验')
add('实测与模型','识别第一声报警，不等于找到因果根因','每个层次都需要对应真值；上层分数不能替代下层验证。',
    ''.join(box(35+i*315,110,290,180,a,[b],i==0,size=29)+ (arrow(330+i*315,195,345+i*315,195) if i<4 else '') for i,(a,b) in enumerate([('首诊断','谁先发出告警？'),('故障家族','属于哪种异常？'),('源码位置','哪段代码相关？'),('因果机制','为何触发故障？'),('引入提交','哪个改动导致？')]))+txt(55,410,'本轮训练监督的是首诊断家族，不是自动找坏提交。',38,BLUE,600)+foot('日志、ELF与源码进入完整Agent；分类训练窗口只使用日志证据。'),
    '例如KASAN报警是现场，内存生命周期是家族，栈帧是相关位置，另一线程提前释放对象才可能是因果机制，某提交改变释放顺序是进一步提交归因。现有位置区间命中也不是因果正确证明。后面的分类准确率只对应弱首诊断标签。')

b=''
for i,(a,lines) in enumerate([('读取与核验',['stability / OpenHarmony','原始文件SHA校验']),('识别首诊断',['正则标记 + 弱标签','窗口：前200 / 共最多5000字符']),('脱敏与去重',['删注入命令、掩码人工符号','按清洗后输入SHA去重']),('按机制划分',['跨内核归一化分组','历史test组并集仍留test']),('训练时造选项',['只从train构造排列','正确类别在训练候选里'])]):
    x=35+(i%3)*520;y=30+(i//3)*260;b+=group(i,box(x,y,490,190,a,lines,i==3,size=29))
    if i%3<2 and i<4:b+=group(i+1,arrow(x+495,y+95,x+515,y+95))
b+=group(4,box(1075,290,490,190,'模型实际看到的内容',['只含日志窗口 / 问题 / 候选','case、split、gold不拼入prompt'],True,size=27))
add('9B数据与训练','先按机制划分，再扩增训练选项','标签用于监督，不作为独立字段泄露给推理模型。',b,
    'prepare-data.py先验证两套日志来源，识别第一诊断并给弱标签。提取窗口、删注入命令并掩码人工注入符号后按输入SHA去重。机制归一化跨内核分组，历史测试组并集留在test，其余按固定hash分train/dev。然后才在训练中造选项。训练实际取清洗窗口的前3000字符，并缩短到完整prompt不超过2048token。模型不看case、split和gold字段，但自然日志线索与历史开发接触仍存在。',source='实际prepare-data.py / train.py / dataset-frozen.json',steps=['核对真实日志来源，不将清单当模型输入','规则选择窗口与弱标签：这一步本身可能犯错','删注入元数据，掩码人工符号并去重','按跨内核机制分组冻结train/dev/test','训练阶段才置换候选；实际prompt截到2048token内'])
add('9B数据与训练','33/4/87，类别覆盖远非均衡','测试87例来自20个机制簇；旧测试已参与开发，不是新盲测。','',
    '热力图来自冻结label_counts。训练仅覆盖六类，测试还有未被训练监督覆盖的类别；OOM和watchdog在测试为零，不能报告这两类能力已经提升。4例开发集很小。图保留旧标签，包含下一页指出的四条RCU规则误标，不事后修改来提高分数。应先修正规则，再冻结新版本盲测。',figure='类别覆盖热力图',source='dataset-frozen.json · 保留原弱标签与原分母')
add('9B数据与训练','circular误命中rcu：四条测试标签需复核','本次制图发现的规则缺陷；冻结标签与历史分数保持不变。',
    box(40,50,730,190,'旧规则分支顺序',["elif 'rcu' in sig: → rcu_progress",'之后才判断 circular locking'],size=31)+box(830,50,730,190,'子串碰撞',["ci + rcu + lar = circular",'四条锁依赖首诊断进入RCU类别'],True,size=31)+
    box(40,300,1520,170,'受影响的冻结test记录',['stability：lock_mutex_abba、lock_spin_abba','OpenHarmony：OHOS-060、OHOS-064；marker均为circular locking dependency'],size=31)+foot('应严格匹配RCU标记、另建版本重标/重训/复测；不能先看答案再改旧分母。'),
    '审计可在不读取私有日志的条件下复现：字符串possible circular locking dependency含连续rcu，prepare-data.py的RCU子串判断位于locking分支之前。冻结清单四条test记录正是这一marker并标为rcu_progress。不能由此直接推断修正后的模型分数；正确流程是修正规则、专家复核并另开新版本实验。现有66/87和78/87只能解释为对带缺陷弱标签的一致性，不能升级为独立根因准确率。',source='本次离线代码/冻结元数据审计 · 旧数据标注规则审计.json')
add('9B数据与训练','模型看题目与候选，正确选项留给训练器','以下是完全合成的讲解样例，不是真实私有日志。',
    box(35,30,1000,430,'送入Qwen的prompt',['日志：BUG: KASAN: use-after-free …（合成）','问题：第一条诊断属于哪个故障家族？','A 越界     B 锁     C 生命周期     D RCU     E 保护','结尾：只回答一个选项字母','训练时：5 / 8 / 12选项；每例每轮4次置换'],True,size=31)+box(1100,100,460,290,'训练器保留',['gold = 生命周期','当前字母 = C','target = 2（从0起）','不把target拼入prompt'],size=30)+foot('候选排列变了，target索引必须一起变化；不能只打乱字母、不更新监督目标。'),
    '这个样例不是保留的服务器输入，不含账号或真实源码。训练中有12个类的全集，每次选5/8/12个候选并包含gold，然后随机排列，target是gold在当前排列中的索引。gold用于造训练候选和计算损失，这是正常监督；评测不能用答案造一个必含正确答案的小集合冒充无标签决策。原性能矩阵部分集合不含真类，所以该矩阵不报准确率。',source='train.py render / 选项构造；合成教学样例')
b=group(0,box(35,45,430,150,'prompt → 最后位置h',['Qwen骨干 + LoRA']))+group(1,arrow(480,120,540,120)+box(560,45,1000,150,'原LM读出：只取A…E五行权重',['ℓ = h · W字母ᵀ；不是新建随机决策头'],True,size=33))
for i,(v,prob) in enumerate(zip(logits,p)):
    x=70+i*310;b+=group(2,box(x,285,270,160,chr(65+i)+f'：logit {v:+.1f}',[f'概率 {prob:.3f}'],i==target,size=27))
b+=group(3,txt(60,510,'p = softmax(ℓ)；这里是候选内的条件分布，不是“根因必然正确率”。',32,BLUE,600))
add('概率与RLCD','先得到logits，再归一化成选项概率','五选项数字是可复算教学例；训练中直接使用可求梯度的张量。',b,
    'logit是还未归一化的分数，不是概率。这里固定教学分数0.4、-0.8、1.8、0、0.6，按softmax得到p。执行代码取最终hidden state，用冻结lm_head中A到E对应行做线性读出，梯度可穿过冻结读出传回h与LoRA。正温度改变概率尖锐程度但不改同一组向量的第一名。',source='train.py forward / 教学概率与RLCD计算.json',steps=['同一prompt处理为最后位置隐藏向量h','用原LM的字母行得到可微logits ℓ','对五个logits做softmax得到条件概率p','正确标签C只在计算监督损失时使用'])
add('9B数据与训练','只训练0.056%参数，推理仍跑完整9B','5,308,416个LoRA参数；冻结骨干与原LM字母读出。',
    box(40,90,420,170,'冻结预训练Qwen',['BF16骨干','不是随机预训练9B'],size=31)+box(600,25,450,170,'原有投影W',['参数冻结，仍参与前向'],size=31)+box(600,295,450,180,'LoRA A → B',['rank8 / alpha16 / scale2','A随机、B初始为0'],True,size=32)+box(1175,170,385,170,'有效W + 2BA',['合并为BF16部署'],size=32)+arrow(475,175,580,110)+arrow(475,175,580,370)+arrow(1065,110,1155,225)+arrow(1065,380,1155,280),
    '48处投影为32个down_proj和8+8个full-attention q/v_proj。A和B用FP32训练。骨干和读出权重冻结不意味着切断计算图：梯度仍可通过这些算子回到LoRA。合并后架构不变，因此不会因为训练参数只有0.056%就把推理内存和计算量缩成0.056%。',source='training-environment.json / train.py LoRA模块')
add('9B数据与训练','396微步、99次更新，损失目标分阶段变化','33例 × 每轮4次排列 × 3轮；每4微步累计一次更新。','',
    '真实曲线来自396条training-steps记录，不是平滑模拟。epoch0用CE，epoch1和2用CE加RLCD，不能把跨阶段曲线下降直接当同一损失的收敛证明。最后微步290.764秒，343.689秒到评估、导出和哈希结束；首步约57秒含首次编译，加载在时钟外。开发仅4例选中epoch1，不保证稳定最优。AdamW学习率1e-4，weight_decay0.01，clip1。',figure='真实训练曲线',source='training-steps.jsonl / training-protocol.json / training-complete.json')

# Exact tensor route of rlcd(logits, target, sigma), not post-hoc API probabilities.
b=group(0,box(40,45,400,150,'输入：ℓ与target y',['ℓ可微；y是当前正确索引'],True,size=31))
b+=group(1,arrow(455,120,515,120)+box(535,45,470,150,'4组中心化高斯扰动',['z = stopgrad(ℓ) + ε'],size=30))
b+=group(2,arrow(1020,120,1080,120)+box(1100,45,450,150,'内部概率q',['q = softmax(z)'],True,size=31))
b+=group(3,path('M1320,210 L1320,280 L900,280 L900,295')+path('M250,210 L250,255 L770,255 L770,295',GRAY,True)+txt(300,245,'正确索引 y（训练监督）',22,GRAY)+box(535,305,470,165,'标签评分 → reward',['按q[y]评分；归一化组内优势A','reward与A停止梯度'],size=28))
b+=group(4,box(40,305,400,165,'损失：CE − mean(A×logdensity)',['logdensity用可微ℓ与固定z','CE直接监督原始ℓ'],True,size=21)+arrow(515,385,460,385))
b+=group(5,box(1100,305,450,165,'backward → LoRA',['优化器不更新冻结骨干'],True,size=30)+path('M240,485 L240,515 L1320,515 L1320,485'))
b+=foot('这是代码中的张量依赖图；RLCD接收logits + target + sigma，q是内部中间量，不是外部API JSON。')
add('概率与RLCD','RLCD接收logits和标签，概率在内部生成','实际函数签名：rlcd(logits, target, sigma)。',b,
    '请按动画看六步。先拿可求梯度的ℓ和当前gold索引y；将ℓ detach后加四组中心化高斯扰动，得到固定采样z，再softmax成q；用真标签概率给各采样评分并得到advantage。这一路奖励不反传。之后用原始可微ℓ构造logdensity项，加CE，损失再回传到LoRA。这不是先调用远程概率接口，再把返回JSON送回训练函数。',source='实际train.py rlcd()，逐行对照',steps=['可微logits ℓ与正确索引y进入函数','detach(ℓ)加四组中心化高斯扰动','在训练内部把z归一化成四份q','用y计算reward与组内优势A，均停梯度','原始ℓ进入logdensity与CE，构成损失','backward只让可训练LoRA参数更新'])

b=txt(40,45,'教学输入 ℓ=[0.4, −0.8, 1.8, 0.0, 0.6]；y=C；σ=0.4',31,BLUE,600)
headers=['采样','q(A)','q(B)','q(C)','q(D)','q(E)','奖励R','优势A'];xs=[65,270,440,610,780,950,1170,1390]
for x,h in zip(xs,headers):b+=txt(x,135,h,27,GRAY)
for i in range(4):
    y=200+i*74;b+=rect(40,y-40,1510,62,'#E8F3FF' if adv[i]>0 else PALE)
    cells=[str(i+1)]+[f'{v:.3f}' for v in q[i]]+[f'{reward[i]:+.3f}',f'{adv[i]:+.3f}']
    for x,v in zip(xs,cells):b+=txt(x,y,v,28,BLUE if x==610 else INK,600 if x==610 else 400)
b+=txt(45,505,'q每行和为1；R由正确项C计算；A比较“这次采样比本组平均好多少”。',29,BLUE,600)
b+=foot('合成数值可复算，不是396步中保存的真实概率；优势标准差按代码使用ddof=1并加1e−6。')
add('概率与RLCD','四次扰动，得到四份候选概率与相对奖励','不是采样四段文字；是在选项logits上做扰动。',b,
    '此表是固定随机种子生成的教学数值，不是实际训练轨迹。每组先从高斯采样五个噪声并减去该组均值，再与stopgrad logits相加。对每行softmax，然后按正确C的log概率加spherical项打分。advantage是四行reward减均值后，除按样本标准差及1e-6。正优势表示相对更好，不意味着已经正确或可以直接自动执行。',source='train.py数学重算 / 教学概率与RLCD计算.json')

b=group(0,box(40,30,1510,120,'先用真标签评分：R = max(log q[y], −9.21) + 0.75 × q[y] / ‖q‖₂',[],False,size=29))
b+=group(1,box(40,210,440,160,'固定z和优势A',['reward / A不反向求导','A=(R−组均值)/(组std+ε)'],size=27)+path('M260,195 L260,175 L1320,175 L1320,195',GRAY,True)+txt(720,199,'固定优势A → 乘到损失',22,GRAY))
b+=group(2,box(590,210,420,160,'logdensity能量项',['− ‖z−ℓ‖² / (2σ²)','原始ℓ仍可微'],True,size=28))
b+=group(3,arrow(1025,290,1095,290)+box(1115,210,440,160,'L = CE − mean(A × logdensity)',['两条损失梯度加到ℓ','代码没有使用部署温度T'],True,size=23))
b+=group(4,path('M1325,385 L1325,440 L800,440 L800,385')+txt(350,505,'梯度 → ℓ → h → LoRA A/B；冻结参数不更新',29,BLUE,600))
b+=foot(f'教学计算：CE={ce:.4f}，总损失={loss:.4f}；用固定z/A的有限差分核对梯度，误差<1e−7。')
add('概率与RLCD','奖励停梯度，更新仍经ℓ回到LoRA','q用于计算奖励；并非把API概率当作可微模型参数。',b,
    '执行代码no_grad包住reward和adv，z也由detach logits采样。因此不能画成reward直接穿过q和z回传。训练信号通过固定采样与原始可微ℓ的logdensity能量项返回，并与CE梯度合并。图中的L完全按代码计算；数值只作教学，有限差分验证时固定z与adv。实际更新的是LoRA矩阵，不是直接把五个logits当独立参数更新。有限扰动、裁剪与优势标准化不构成无偏梯度或全域概率校准证明。',source='train.py rlcd()与backward / 教学数值验证',steps=['用正确标签y计算各采样的奖励R','固定z与A：这一路不走直接反向传播','可微ℓ进入logdensity能量项','和CE一起组成实际损失','梯度经冻结算子回到LoRA；只更新可训练参数'])

add('概率与RLCD','API概率可以作数据，不能直接穿过HTTP反传','“有概率”与“有通向权重的计算图”是两件事。',
    box(40,60,730,340,'本地可微训练',['模型前向 → logits张量 → 损失','计算图保留 → backward → LoRA','需要真标签或明确的奖励定义','本项目rlcd()属于这条路径'],True,size=32)+box(830,60,730,340,'HTTP返回JSON概率',['接口 → 数字列表 → 计算图已断','不能直接loss.backward更新远端权重','可另做软标签蒸馏等训练数据','这不是本轮已经完成的训练方法'],size=32)+foot('黑盒策略优化等另有方法；这里只说明返回JSON不自带跨进程反向传播能力。'),
    '如果只有远程接口返回的概率，客户端拿到的是普通数字，不是能穿过远端模型的autograd张量。可以把它们保存成教师软标签，再训练另一个本地模型，但这是蒸馏，需要另外定义目标和评估；不能宣称把JSON喂给当前rlcd就等价训练。黑盒优化也不是被此图否定，只是不属于这次实现。')
add('概率与RLCD','温度在读出时校准，不是本轮RLCD的输入','训练监督、开发选点与测试评分，应保持职责分离。',
    box(35,70,480,250,'train：更新LoRA',['CE / CE+RLCD','噪声σ=0.4→0.15','不是部署温度T'],True,size=34)+box(560,70,480,250,'dev：选版本与T',['仅4例：选中epoch1','网格选择T=0.5','p部署 = softmax(ℓ/T)'],size=32)+box(1085,70,480,250,'test：固定方案评分',['不用于选epoch或T','T小更尖，正T不改argmax','测试NLL恶化仍要报告'],size=30)+txt(55,440,'σ是训练扰动幅度；T是概率读出温度，不能混为一个参数。',35,BLUE,600),
    '训练rlcd函数的三个参数是logits、target和sigma，没有部署温度T。epoch1用sigma0.4，epoch2用0.15。训练后用四条dev选择正温度，部署Decision再对logits除T。T0.5让概率更尖，不能提升同一向量的第一名准确率；开发集很小，测试NLL反而恶化，不建议把该温度当可靠置信度直接上线。',source='train.py checkpoint_selection / temperature grid / calibration.json')
add('结果与边界','答对更多，仍可能在错题上更自信','原冻结弱标签：66/87→78/87；有4条规则误标，需新版本复测。','',
    '两接口分类都提高13.79个百分点，增益集中在警告与保护边界，不能归因Decision接口独有能力。左图是旧弱标签一致性，不是专家根因真值；新增发现的四例误标尚未重标。右图T1的NLL从0.830升到1.724，T0.5则1.957，更糟。没有等预算CE-only、多种子与新盲测，不能说RLCD比普通微调更好。',figure='分类与概率反例',source='冻结分类/校准结果 + 本次标签规则审计；未重算改标签后的分数')
add('结果与边界','完整Agent仍为2/3，混合流程还更慢','独立32k上下文实验；每条柱为三个案例的耗时之和。','',
    '12个流程都输出有效报告，四组代码位置命中均2/3。微调后混合从10次HTTP变6次，三例耗时从53.464降29.247秒，但纯Chat仍只3次HTTP、23.229秒。图不是并发Gantt，不代表因果根因或引入提交已验证。分类微调效果不能替代完整定位收益。',figure='完整Agent对照',source='独立agent32k / agent32k-aggregate.csv')
add('结果与边界','要知道哪一步有效，必须做独立对照','下面是建议方案，不是已经执行的实验结果。',
    box(40,50,480,350,'训练方法消融',['同样基座 / 数据 / 更新预算','不训练 → 仅CE → CE+RLCD','多个随机种子','盲测准确率与NLL一起报'],True,size=31)+box(560,50,480,350,'模型与接口消融',['同代尺寸尽量可比','小/大模型 × 训练策略','单字母Chat / Decision','输入token、缓存和引擎固定'],size=31)+box(1080,50,480,350,'完整定位验收',['先修复弱标注规则','新机制盲测 + 专家根因真值','规则 / 纯Chat / Decision软路由','位置、机制、提交与总成本'],size=31)+foot('不要从不同试卷的89.66%和9/9，推导“小模型已经胜过27B”。'),
    '优先补规则基线和等预算CE-only，再扩大尺寸对照。现有不同代9B/27B、不同实验条件不能当纯尺寸因果比较。新数据必须修正circular/rcu冲突并独立审核首诊断与根因标签，再预先冻结分组，不反复看test挑模型。')
add('结果与边界','优化有限判断，验证完整根因','接口、概率与任务能力，分别拿证据说话。',
    txt(75,115,'计算：先读输入；少写答案不等于不算KV',43,BLUE,600)+txt(75,225,'训练：logits + 标签 → 奖励与损失 → LoRA',43,INK,600)+txt(75,335,'结论：分类有适配，内存与因果定位未证明提升',43,INK,600)+txt(75,465,'下一步：修正标签，再做新机制盲测与CE-only消融',32,GRAY),
    '报告的核心价值不是宣称某个名字自动带来更强智能，而是把计算依赖、训练监督和完整任务效果分开。本次还发现弱标注规则错误，更说明应该保留负结果、修正数据后另开版本确认。可以将Decision作为有回退的推荐信号，不让未校准概率硬锁死后续调查。')
add('来源与复现','每张图都标明：机制示意、教学计算或实测','相对路径可离线浏览；没有远程字体、脚本或在线模型调用。',
    box(40,40,730,360,'本项目可复核材料',['报告答疑与20个配对条件','train.py / prepare-data.py / frozen清单','训练曲线、分类、校准与32k Agent表','source-provenance.json记录来源SHA'],True,size=31)+box(830,40,730,360,'外部一手资料',['TypeSafe官方Jev介绍','SGLang Decision文档','PPLX原版模型卡','nanojev作者仓库 / Laya固定版本'],size=31)+foot('详细链接、逐页讲稿、图形源文件、教学计算及缺陷审计均随目录保存；私有日志和权重不公开。'),
    '本演示把可执行训练代码与公开冻结标量作为主要依据。外部资料用于核对身份和设计说明，不把作者速度、准确率数字混入本地测量。源文件哈希帮助复核输入身份，但不能证明标签本身没有错误。修正旧规则要创建新数据版本，不改历史文件。',source='资料来源.md / source-provenance.json / 说明.md')

assert len(slides)==28,len(slides)
template=(ROOT/'tools/kelip-slide/assets/deck-template.html').read_text(encoding='utf-8')
start=template.index('<!-- ===== 1 ');end=template.index('<div id="nav-hot"')
template=template[:start]+'\n'.join(slides)+'\n</div>\n'+template[end:]
template=template.replace('【这里写：系列 · 第 N 期 · 主题】','Jev决策模型：计算、数据与RLCD训练')
assert 'id="arB"' in template, 'Kelip global arrow markers must stay outside individual slides'
template=template.replace('"PingFang SC","SF Pro Display"','"PingFang SC","Microsoft YaHei","SF Pro Display"')
css='''
h1{font-size:62px;line-height:1.2}.kicker{letter-spacing:.04em}.sub{font-size:28px;line-height:1.4}
.art{flex:1;min-height:0;margin-top:28px;background:#FFF;border-radius:24px;padding:16px 20px;display:flex;align-items:center;justify-content:center}
.art>svg{width:100%;height:100%;max-height:630px}.sv text{font-family:var(--font)}
.walk-controls{display:flex;gap:12px;margin-top:14px;align-items:center}.walk-controls button{border:1px solid var(--line);background:white;border-radius:10px;padding:11px 17px;font:22px var(--font);color:var(--ink)}
.walk-controls button[data-act=play]{background:var(--accent);color:white;min-width:132px}.walk-caption{font-size:22px;color:var(--muted);line-height:1.35;margin-left:10px;flex:1}
.walk [data-a]{opacity:.18;transition:opacity .18s}.walk [data-a].on{opacity:1}.walk .art{margin-top:20px}
a{color:var(--accent)}
@media print{html,body{height:auto;overflow:visible}#stage{position:static;transform:none!important;height:auto}.slide{display:flex!important;position:relative;width:1920px;height:1080px;break-after:page}#nav-btn,#nav-hot,#nav-panel,#hud,.walk-controls{display:none!important}.walk [data-a]{opacity:1!important}@page{size:1920px 1080px;margin:0}}
'''
template=template.replace('</style>',css+'\n</style>')
a=template.index('  // ---- 分步动画：');b=template.index('  const navBtn=',a)
template=template[:a]+(HERE/'animation.js').read_text(encoding='utf-8')+template[b:]
template=template.replace("if(e.target.closest('a,#nav-panel,#nav-btn,#nav-hot'))", "if(e.target.closest('a,button,.walk-controls,#nav-panel,#nav-btn,#nav-hot'))")
template=template.replace("else if(e.key==='g'||e.key==='G')", "else if(e.key==='p'||e.key==='P'){if(anim)anim.toggle();}\n    else if(e.key==='g'||e.key==='G')")
template=template.replace("addEventListener('keydown',e=>{", "addEventListener('keydown',e=>{\n    if(e.target.closest('button')&&[' ','Enter'].includes(e.key))return;")
(HERE/'deck.html').write_text(template,encoding='utf-8')
(HERE/'逐页讲稿.md').write_text('# Jev决策模型：逐页讲稿\n\n28页，建议25–40分钟。机制图非实测比例；教学数字非保存训练轨迹。按P播放，J/K走步。\n\n'+'\n'.join(notes),encoding='utf-8')
sources=[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(USED)]
for src in sorted(USED):
    dst=HERE/'evidence'/src.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
(HERE/'source-provenance.json').write_text(json.dumps({'date':'2026-10-18','sources':sources,'new_model_calls':0,'synthetic_example':toy['scope'],'label_audit_affected':len(bug),'frozen_labels_changed':False},ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'资料来源.md').write_text('''# 资料来源与科学口径

主要依据：[报告答疑](../../docs/Jev决策模型报告答疑与通俗解读_20261018.md)、[证据索引](../../research/jev-report-qa-20261018/README.md)、[9B执行与实测](../../research/jev-qwen35-9b-20261016/REPORT.md)、[27B并发研究](../../research/kv-concurrency-20261016/REPORT.md)、[PPLX分时复测](../../research/pplx-timeshare-20261012/REPORT.md)。输入源SHA见source-provenance.json。

外部一手来源（此前答疑阶段核对，2026-10-18）：

- [TypeSafe官方Jev介绍](https://typesafe.ai/blog/introducing-system-one-models-and-jev)：厂商模型定位与RLCD名称，不证明本项目复现其专有算法。
- [SGLang Decision文档](https://docs.sglang.io/docs/supported-models/decision_models)：通用模型读选项分数；当前文档不替代冻结执行版本。
- [PPLX原版本模型卡](https://huggingface.co/perplexity-ai/pplx-decider-v1-27b)：身份与参考实现；本项目只测既有固定v1版本。
- [nanojev作者仓库](https://github.com/sshh12/nanojev)：第三方假设性重建，未在本项目内核数据上执行；不引入其自报成绩。
- [Laya固定参考版本](https://github.com/NandhaKishorM/laya/tree/4ac226d5ee88ed6df8db288a05c766d7a34ee682)：思想参考，非官方Jev配方同一性证明。

## 新的标签审计发现

prepare-data.py的`elif 'rcu' in sig`在locking判断前；circular包含连续rcu。冻结test中的lock_mutex_abba、lock_spin_abba、OHOS-060、OHOS-064标记为循环锁依赖却被赋予rcu_progress。旧数据标注规则审计.json保存元数据，无私有日志。原分数和标签保留不变；需新版本修复、审核、重训复测，不能直接宣称新准确率。

## 绘图与训练边界

流程宽度不是时长，S=8的KV格子仅为教学；首输出来自prefill，单字母Chat不一定多一次decode。混合模型线性状态单列。科研条形零基线，27B/9B不同条件不做纯尺寸归因。

教学概率与RLCD计算.json是固定种子的合成数学例，非服务器真实轨迹。q在训练内部由detach logits加中心化噪声的z计算；reward/adv停止梯度。损失通过原始可微logits的logdensity能量项与CE回传；有限差分时固定z/adv。实际更新LoRA，非直接优化五个logits。代码含裁剪、有限采样与标准化，不宣称全域严格恰当性或无偏梯度保证。

训练首步含编译，最后微步290.764s，控制器至评估/导出/哈希343.689s；不把它叫9B随机预训练时间。Dev仅4例，T=0.5未通过测试NLL可靠性验证。分类结果含已知弱标注缺陷，不是专家因果根因真值；87例来自20机制簇，历史已见，不能宣称独立盲测显著泛化。完整Agent三例合计时间与2/3位置命中不等于引入提交证明。
''',encoding='utf-8')
vendor=HERE/'vendor/kelip-slide';vendor.mkdir(parents=True,exist_ok=True)
for name in ['LICENSE']:
    source=ROOT/'tools/kelip-slide'/name
    if source.exists():shutil.copy2(source,vendor/name)
(vendor/'assets').mkdir(exist_ok=True);shutil.copy2(ROOT/'tools/kelip-slide/assets/deck-template.html',vendor/'assets/deck-template.html')
print(json.dumps({'slides':len(slides),'figures':len(list(MEDIA.glob('*.svg'))),'label_audit_cases':len(bug),'toy_gradient_error':toy['finite_difference_max_error']},ensure_ascii=False))

