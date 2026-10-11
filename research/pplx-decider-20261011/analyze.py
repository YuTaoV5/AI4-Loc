"""Publish scalar results, exact accuracy comparisons and deployment-specific figures."""
import pathlib,json,csv,math,collections,sys,hashlib
import numpy as np
from scipy.stats import beta,binomtest
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=pathlib.Path(__file__).resolve().parent;ROOT=H.parents[1];PRIVATE=ROOT/'data/local-archive/pplx-decider-20261011';O=H/'results';F=H/'figures';O.mkdir(exist_ok=True);F.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
if '--public' in sys.argv:
 protocol=read(O/'protocol.json');rows=read(O/'trials.json');runtime=read(O/'runtime.json');checkpoint=read(O/'checkpoint.json')
else:
 raw=read(PRIVATE/'results.json');protocol=read(PRIVATE/'protocol.json');assert raw['complete'] and len(raw['rows'])==121
 assert raw['protocolSha256']==hashlib.sha256((PRIVATE/'protocol.json').read_bytes()).hexdigest()
 runtime=read(PRIVATE/'runtime.json');checkpoint=read(PRIVATE/'verified-checkpoint.json');rows=[]
 for r in raw['rows']:
  a=r.get('answers',{});audit=r.get('audit',{});x={k:r.get(k) for k in ['caseId','repeat','arm','scored','ordinal','split','injectionFamily','status','seconds','gold','family','correct','inputLogSha256']}
  x.update(stage=a.get('stage',{}).get('choice'),reporter=a.get('reporter',{}).get('choice'),answers=a,inputTokens=r.get('usage',{}).get('prompt_tokens'),outputTokens=r.get('usage',{}).get('completion_tokens'),isolationPassed=audit.get('anonymous') is True and not any(audit.get(k,True) for k in ['evaluatorVisible','businessVisible','procVisible']))
  rows.append(x)
assert len(rows)==121 and len({(r['caseId'],r['repeat'],r['arm']) for r in rows})==121
for r,s in zip(sorted(rows,key=lambda r:r['ordinal']),protocol['schedule']):assert all(r[k]==s[k] for k in ['caseId','repeat','arm','scored'])
assert all(r['isolationPassed'] for r in rows)
for n,obj in [('protocol.json',protocol),('trials.json',rows),('runtime.json',runtime),('checkpoint.json',checkpoint)]: (O/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
fields=[k for k in rows[0] if k!='answers']
with (O/'trials.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows)
arms=['generic','pplx'];testcases=[c['caseId'] for c in protocol['cases'] if c['split']=='test'];scoredcases=[c['caseId'] for c in protocol['cases'] if c['family'] in protocol['taxonomy']]
def interval(k,n):return [float(beta.ppf(.025,k,n-k+1)) if k else 0,float(beta.ppf(.975,k+1,n-k)) if k<n else 1]
def summarize(rr):
 n=len(rr);k=sum(r['correct'] is True for r in rr);valid=[r['seconds'] for r in rr if r['status']=='completed' and r['seconds'] is not None]
 return {'attempts':n,'success':k,'accuracy':k/n,'accuracyCI95':interval(k,n),'failures':sum(r['status']!='completed' for r in rr),'meanSeconds':float(np.mean(valid)) if valid else None,'medianSeconds':float(np.median(valid)) if valid else None,'p95NearestRank':float(sorted(valid)[math.ceil(.95*len(valid))-1]) if valid else None,'inputTokens':sum(r['inputTokens'] or 0 for r in rr),'outputTokens':sum(r['outputTokens'] or 0 for r in rr)}
def majority(arm,c):
 rr=[r for r in rows if r['arm']==arm and r['caseId']==c];return sum(r['correct'] is True for r in rr)>len(rr)/2
def mcnemar(cases,repeat0=False):
 def hit(a,c):return next(r for r in rows if r['arm']==a and r['caseId']==c and r['repeat']==0)['correct'] is True if repeat0 else majority(a,c)
 b=sum(hit('generic',c) and not hit('pplx',c) for c in cases);c=sum(hit('pplx',c) and not hit('generic',c) for c in cases);return {'genericOnlyCorrect':b,'pplxOnlyCorrect':c,'exactTwoSidedP':float(binomtest(b,b+c,.5).pvalue) if b+c else 1.0,'scope':'Exploratory paired accuracy comparison; not a noninferiority test'}
stats={'schema':'pplx-weight-evaluation/v1','model':checkpoint['model'],'revision':checkpoint['revision'],'formalAttempts':len(rows),'uniquePplxCases':60,'uniqueScoredCases':25,'unsupportedUnscoredCases':35,'primary':{},'secondarySingleRepeat25':{},'runtimeCaveat':'PPLX uses BF16 CPU offload in Transformers; generic uses SGLang fully GPU. Latency describes these deployments, not an intrinsic or native-SGLang model comparison.','primaryMcNemar':mcnemar(testcases),'secondaryMcNemar':mcnemar(scoredcases,True),'confidenceScope':'Finite class probabilities; calibration only against mapped injection family, not root-cause truth; small mixed train/test sample.'}
for arm in arms:
 rr=[r for r in rows if r['arm']==arm and r['split']=='test'];s=summarize(rr);s.pop('accuracyCI95');k=sum(majority(arm,c) for c in testcases);s.update(uniqueCases=9,majorityCorrect=k,majorityAccuracyCI95=interval(k,9),trialAccuracyInference='Three dependent repeats per case; no independent-trial interval');stats['primary'][arm]=s
 rr=[r for r in rows if r['arm']==arm and r['scored'] and r['repeat']==0];stats['secondarySingleRepeat25'][arm]=summarize(rr)
 train=[r for r in rr if r['split']=='train'];stats['secondarySingleRepeat25'][arm]['trainOnly']=summarize(train)
 vals=[];conf=[];correct=[];class_names=list(next(r for r in rr if r.get('answers'))['answers']['family']['probabilities'])
 for r in rr:
  probs=r.get('answers',{}).get('family',{}).get('probabilities')
  if probs is None:continue
  vals.append(sum((probs[k]-int(k==r['gold']))**2 for k in class_names));conf.append(max(probs.values()));correct.append(r['correct'] is True)
 bins=[];ece=0
 for i in range(5):
  ids=[j for j,v in enumerate(conf) if i/5<=v<=(i+1)/5 and (i==0 or v>i/5)]
  if ids:
   mean=float(np.mean([conf[j] for j in ids]));acc=float(np.mean([correct[j] for j in ids]));ece+=len(ids)/len(conf)*abs(mean-acc);bins.append({'lower':i/5,'upper':(i+1)/5,'n':len(ids),'meanConfidence':mean,'accuracy':acc})
 stats['secondarySingleRepeat25'][arm]['multiclassBrier']=float(np.mean(vals));stats['secondarySingleRepeat25'][arm]['ece5Bins']=ece;stats['secondarySingleRepeat25'][arm]['reliabilityBins']=bins
stats['failures']=[{k:r[k] for k in ['caseId','arm','repeat','status']} for r in rows if r['status']!='completed'];stats['mismatches']=[{k:r[k] for k in ['caseId','split','arm','repeat','injectionFamily','gold','family']} for r in rows if r['correct'] is False]
(O/'statistics.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'});cols=['#245fa8','#a84d27'];labels=['Generic Qwen / SGLang','PPLX / CPU offload']
def save(fig,n):
 fig.savefig(F/(n+'.png'),dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(F/(n+'.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
fig,ax=plt.subplots(figsize=(8.5,4.5));x=np.arange(2);w=.32
for i,arm in enumerate(arms):
 ss=[stats['primary'][arm],stats['secondarySingleRepeat25'][arm]];ys=[ss[0]['majorityCorrect']/9,ss[1]['accuracy']];ci=[ss[0]['majorityAccuracyCI95'],ss[1]['accuracyCI95']]
 ax.bar(x+(i-.5)*w,np.array(ys)*100,width=w,color=cols[i],label=labels[i]);ax.errorbar(x+(i-.5)*w,np.array(ys)*100,yerr=[[100*(v-z[0]) for v,z in zip(ys,ci)],[100*(z[1]-v) for v,z in zip(ys,ci)]],fmt='none',ecolor='#222',capsize=4)
 for j,(v,n) in enumerate(zip(ys,[9,25])):ax.text(x[j]+(i-.5)*w,v*100+3,f'{round(v*n)}/{n}',ha='center',fontsize=9,zorder=4,bbox={'facecolor':'white','edgecolor':'none','pad':1})
ax.set_xticks(x,['Existing test / majority of 3','Injection proxy / repeat 0']);ax.set(ylim=(0,117),ylabel='Agreement with frozen labels (%)',title='Independent-case binomial intervals; secondary labels are proxies');ax.legend(loc='lower left',fontsize=8);fig.tight_layout();save(fig,'01-accuracy')
fig,axes=plt.subplots(1,2,figsize=(11,5.2));display=['lifetime','bounds','leak','locking','RCU','OOM','other','blocked','watchdog']
for ax,arm in zip(axes,arms):
 mat=np.zeros((9,9),int)
 for r in rows:
  if r['arm']==arm and r['scored'] and r['repeat']==0 and r['family'] in class_names:mat[class_names.index(r['gold']),class_names.index(r['family'])]+=1
 im=ax.imshow(mat,cmap='Blues',vmin=0,vmax=max(1,mat.max()));ax.set_xticks(range(9),display,rotation=55,ha='right');ax.set_yticks(range(9),display);ax.set(xlabel='Predicted family',ylabel='Mapped injection family',title=labels[arms.index(arm)])
 for i in range(9):
  for j in range(9):
   if mat[i,j]:ax.text(j,i,str(mat[i,j]),ha='center',va='center',color='white' if mat[i,j]>mat.max()*.55 else 'black')
fig.suptitle('25 injection-proxy cases / arm; not independent first-report labels');fig.tight_layout();save(fig,'02-confusion')
fig,ax=plt.subplots(figsize=(10,5.4));names=[]
for i,c in enumerate(scoredcases):
 rr=[next(r for r in rows if r['arm']==arm and r['caseId']==c and r['repeat']==0) for arm in arms];t=[r['seconds'] for r in rr];ax.plot(t,[i,i],color='#c0c9d3');ax.scatter(t,[i,i],c=cols,s=22);names.append(c.replace('lkdtm_','').replace('corrupt_',''))
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([],[],marker='o',linestyle='none',color=c,label=l) for c,l in zip(cols,labels)],loc='upper center',bbox_to_anchor=(.5,-.15),ncol=2,fontsize=8)
ax.set_yticks(range(len(names)),names,fontsize=7);ax.invert_yaxis();ax.set_xscale('log');ax.set(xlabel='Client-call seconds (log scale)',title='Deployment latency: PPLX includes CPU weight transfers\nThese are not equal-runtime or native-SGLang speed results');fig.tight_layout();save(fig,'03-latency')
fig,axes=plt.subplots(1,2,figsize=(9,4.2))
for ax,arm in zip(axes,arms):
 b=stats['secondarySingleRepeat25'][arm]['reliabilityBins'];ax.plot([0,1],[0,1],ls='--',color='#888');ax.scatter([z['meanConfidence'] for z in b],[z['accuracy'] for z in b],s=[z['n']*14 for z in b],color=cols[arms.index(arm)])
 for z in b:ax.annotate('n='+str(z['n']),(z['meanConfidence'],z['accuracy']),xytext=(-8,-16),textcoords='offset points',fontsize=8)
 ax.set(xlim=(-.03,1.05),ylim=(-.03,1.05),xlabel='Mean top-option probability',ylabel='Agreement with injection proxy',title=labels[arms.index(arm)]);ax.grid(alpha=.15)
fig.suptitle('Exploratory reliability: 25 cases, five fixed bins\nTraining temperature calibration does not guarantee kernel calibration');fig.tight_layout();save(fig,'04-reliability')
def fmt(x):return f'{x:.3f}'
parts=['# PPLX-Decider 专用权重实测报告（2026-10-11）','本报告测试真实专用权重，而非更改通用模型别名。实验、失败、概率及输入哈希全部保留。',f"模型：`{checkpoint['model']}`；固定 revision：`{checkpoint['revision']}`。30 个文件按官方元数据校验，所有 11 个权重分片 SHA256 通过；使用专用 readout 和保存的 temperature={runtime['temperature']:.9f}。",'## 实验条件与可解释范围','单张 A100-SXM4-80GB，原有通用 Qwen/SGLang 继续驻留。专用模型采用官方参考 prepare/forward、BF16、Accelerate CPU 卸载，GPU 权重额度 10 GiB；仅改变放置方式，未替换权重、答案读出或温度。运行时为 Torch 2.13.0、Transformers 5.12.1、Accelerate 1.15.0。原版构造器的整模型 .to(cuda) 由显式分层放置替代。**该条件验证权重、接口与有限分类能力；耗时包含 CPU 权重传输，不能推断全 GPU PPLX 或原生 SGLang 的速度。**','两端均通过 `/v1/systemone`，相同日志状态、三个固定问题与选项；每个 worker 为匿名 UUID `/work`，无评测父目录、业务数据或 proc 挂载。协议与随机顺序在正式调用之前冻结，seed=20261011。模型侧不接收独立的案例 ID、注入类别、标签或评分字段；自然日志中的函数名与工作负载线索保留。','9 个已有 test 案例各 3 次×2 模型=54；16 个其他可映射 train 案例各 1 次×2=32；35 个 protection/refcount 案例仅 PPLX 各 1 次=35。共 121 正式调用，另排除 2 次合成预热。后 35 例无兼容家族真值，准确率为空。材料均为现有脱敏日志；未测源码根因或提交定位。','## 实际结果','| 指标 | 通用 Qwen / SGLang | PPLX / CPU 卸载 |','| --- | --- | --- |']
for label,fun in [('test 正确调用/27',lambda s:f"{s['success']}/27"),('test 唯一案例多数正确/9',lambda s:f"{s['majorityCorrect']}/9"),('test 平均客户端秒',lambda s:fmt(s['meanSeconds'])),('test P95 秒',lambda s:fmt(s['p95NearestRank'])),('test 输入 token 总数',lambda s:str(s['inputTokens'])),('test 输出 token 总数',lambda s:str(s['outputTokens']))]:parts.append('| '+label+' | '+' | '.join(fun(stats['primary'][arm]) for arm in arms)+' |')
for label,key in [('25 例注入类别代理吻合（repeat=0）','secondarySingleRepeat25')]:parts.append('| '+label+' | '+' | '.join(f"{stats[key][arm]['success']}/25" for arm in arms)+' |')
parts+=['','![准确率及独立案例区间](figures/01-accuracy.svg)','![家族混淆热力图](figures/02-confusion.svg)','![部署耗时](figures/03-latency.svg)','## 统计与概率分析',f"test 案例级配对 McNemar：通用独对 {stats['primaryMcNemar']['genericOnlyCorrect']}、PPLX 独对 {stats['primaryMcNemar']['pplxOnlyCorrect']}，双侧精确 p={stats['primaryMcNemar']['exactTwoSidedP']:.6f}。25 例 repeat=0 对照 p={stats['secondaryMcNemar']['exactTwoSidedP']:.6f}。这是探索性准确率比较，不是预设非劣/等效证明；重复调用不是新的独立案例。",'| 概率诊断（25例 repeat=0） | 通用 | PPLX |','| --- | --- | --- |']
for title,key in [('多类 Brier（越低越好）','multiclassBrier'),('5固定分箱 ECE（描述性）','ece5Bins')]:parts.append('| '+title+' | '+' | '.join(fmt(stats['secondarySingleRepeat25'][arm][key]) for arm in arms)+' |')
parts+=['','![探索性可靠性图](figures/04-reliability.svg)','分箱和 Brier 使用冻结映射后的注入家族作为目标，仅 25 个既有案例且包含 train；不能声称完成独立领域概率校准，更不能把高概率等同根因正确率。阶段和 reporter 的实际选项/概率已保留，但没有独立专家真值，未给出其准确率。','## 标签不一致与未评分案例']
if stats['mismatches']:
 parts+=['| 案例 | split | 模型 | repeat | 目标家族 | 返回 |','| --- | --- | --- | --- | --- | --- |']+['| '+' | '.join(str(r[k]) for k in ['caseId','split','arm','repeat','gold','family'])+' |' for r in stats['mismatches']]
else:parts.append('可映射家族的正式调用未观察到与冻结标签不一致的输出。这不证明陌生故障或因果定位的准确率。')
parts+=['35 个 protection/refcount 案例的 family/stage/reporter 输出位于公开派生表，correct=null；没有把未知真值强制映射为“其他”凑准确率。所有正式失败也保留在分母。重要的构念差异：secondary 的目标来自注入家族，而提问要求识别第一条诊断，二者可能不同。例如 lkdtm_LOOP 标为 watchdog，但实际首条诊断是 RCU stall，两模型都选择 rcu_progress。因此上述不一致不能自动称为模型错误；原始标签得分不事后改写，需独立诊断标注后再评价首现场准确率。','## 结论与后续验证',f"在现有 test 上，PPLX 多数正确 {stats['primary']['pplx']['majorityCorrect']}/9，通用模型 {stats['primary']['generic']['majorityCorrect']}/9；25 例单次对照为 {stats['secondarySingleRepeat25']['pplx']['success']}/25 与 {stats['secondarySingleRepeat25']['generic']['success']}/25。结论只适用于这个已知回归集合。",'专用模型已实际接入现有 DecisionClient 的 System One 适配，并返回三个问题的选择及有限分布；接口名称相同不意味着已测原生 dsh SDK 全流程。本轮没有更换网站的生产模型，也没有重启 SGLang/Ollama。','若要判断专用权重是否提速，需要独立 GPU，或在已批准维护窗口中卸载当前通用模型、使用支持专用 checkpoint 的 SGLang 版本，以一致 BF16、上下文、并发和缓存条件重测。本轮 CPU 卸载耗时不能替代这一结论。是否提升根因定位还须在同一 Chat/源码工具/预算下做完整 Agent 对照及新机制盲测。','## 数据、来源与复现','- `results/trials.csv`、`trials.json`：121 次派生数据与选项概率；无原始输入/Prompt/账号/token ID。\n- `results/protocol.json`、`runtime.json`、`checkpoint.json`：冻结协议、实际放置与官方校验摘要。\n- `python analyze.py --public`：离线重算统计及四组 SVG/PNG，不调用模型。\n- 私有服务器目录 `/opt/kernel-insight/experiments/pplx-decider-20261011/`；本地 `data/local-archive/pplx-decider-20261011/`。','官方模型与许可证：[Hugging Face](https://huggingface.co/perplexity-ai/pplx-decider-v1-27b)。[SGLang 部署说明](https://docs.sglang.io/cookbook/autoregressive/Perplexity/PPLX-Decider-v1-27B)。源代码和权重校验来自官方模型仓库固定 revision；镜像仅作传输，不作为模型身份依据。']
audit_path=O/'evidence-audit.json'
if audit_path.exists():
 audit=read(audit_path)
 parts+=['## 完整性、泄露复核与服务状态',f"121/121 调用成功，121/121 匿名 worker 检查通过，121/121 实际请求轨迹通过字段复核，冻结源码哈希一致。完整私有归档 {audit['archive']['bytes']} 字节，SHA256 `{audit['archive']['sha256']}`；本地归档及其中 518 个文件逐一核验一致。",'模型请求没有 caseId、gold、injectionFamily、评测结果或数据集路径字段；但保留了自然日志中的 LKDTM 函数名和工作负载线索。63/121 次请求（41 个唯一案例）包含与案例名重合的日志文本。这不属于父进程额外传入标签，但可能形成捷径；本轮不能宣称完全去线索盲测或泛化能力已被证明。匿名目录不能消除日志内容本身的线索。','测试结束临时参考服务已关闭，原通用模型接口 HTTP 200、原进程 PID 65 仍在。8787 网站端口在本次测试前及结束后均不响应；本轮没有恢复网站，不能以模型接口正常代替网站健康。服务器模型缓存盘剩余约 8.3 GiB；完整 checkpoint 缓存保留，未上传 GitHub。']
parts.insert(1,'2026-10-12更新：本页保留CPU卸载历史条件与冻结数据。最新[全GPU分时复测](../pplx-timeshare-20261012/REPORT.md)已完成，两端test均27/27，PPLX均值5.672s、通用2.563s；旧CPU速度不作公平对照。部署步骤见[中文手册](../../docs/PPLX专用模型下载部署与验收手册.md)。')
text='';previous=''
for part in parts:
 text+=('' if not text else '\n' if part.startswith('|') and previous.startswith('|') else '\n\n')+part;previous=part
(H/'REPORT.md').write_text(text+'\n',encoding='utf-8')
try:
 from markdown_it import MarkdownIt
 rendered=MarkdownIt('commonmark',{'html':False}).enable('table').render(text)
 (H/'report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PPLX-Decider 专用权重实测</title><style>body{max-width:1050px;margin:48px auto;padding:0 24px;font:17px/1.85 system-ui,"Microsoft YaHei",sans-serif;color:#1d2d3b}h1,h2{color:#183d60;line-height:1.4}h2{margin-top:48px}table{border-collapse:collapse;width:100%;font-size:14px;margin:24px 0}th,td{border:1px solid #bdcbd8;padding:8px;overflow-wrap:anywhere}th{background:#edf3f8}img{width:100%;height:auto;border:1px solid #edf0f4}a{color:#245fa8}code{font-size:.88em;background:#f0f4f7;padding:2px 4px}strong{color:#8b3d20}@media print{body{font-size:10pt;margin:0}img,table{break-inside:avoid}}</style><main>'+rendered+'</main></html>',encoding='utf-8')
except ImportError:print('Optional markdown-it-py missing; Markdown and scientific figures generated.',file=sys.stderr)
print(json.dumps(stats,ensure_ascii=False,indent=2))
