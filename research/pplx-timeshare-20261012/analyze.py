"""Offline analysis of full-GPU sequential deployments, preserving inference limits."""
import pathlib,json,hashlib,csv,math,itertools,sys
import numpy as np
from scipy.stats import beta,binomtest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
H=pathlib.Path(__file__).resolve().parent;PRIVATE=H.parents[1]/'data/local-archive/pplx-timeshare-20261012';O=H/'results';F=H/'figures';O.mkdir(exist_ok=True);F.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
if '--public' in sys.argv:
 protocol=read(O/'protocol.json');rows=read(O/'trials.json');runtime=read(O/'pplx-runtime.json');completion=read(O/'completion.json');audit=read(O/'audit.json')
else:
 raw=read(PRIVATE/'results.json');assert raw['complete'] and len(raw['rows'])==121;protocol=read(PRIVATE/'protocol.json');assert raw['protocolSha256']==hashlib.sha256((PRIVATE/'protocol.json').read_bytes()).hexdigest()
 runtime=read(PRIVATE/'pplx-runtime.json');completion=read(PRIVATE/'completion.json');assert completion['status']=='completed' and completion['restoration']['restored']
 rows=[];natural_names=0;natural_cases=set();trace_count=0
 for r in raw['rows']:
  trace=read(PRIVATE/'workspaces'/r['workspaceId']/'decision-trace.json');assert len(trace['calls'])==1;call=trace['calls'][0];request=call['request'];assert set(request)=={'model','state','questions'} and set(request['state'])=={'instruction','firstDiagnosticLine','lines','lifetimeEvidence','available'}
  trace_count+=1
  if r['caseId'] in json.dumps(request):natural_names+=1;natural_cases.add(r['caseId'])
  audit_row=r.get('audit',{});safe=audit_row.get('anonymous') is True and not any(audit_row.get(k,True) for k in ['evaluatorVisible','businessVisible','procVisible'])
  row={k:r.get(k) for k in ['caseId','repeat','arm','scored','ordinal','split','injectionFamily','status','seconds','gold','family','correct','inputLogSha256']};row.update(answers=r.get('answers',{}),inputTokens=r.get('usage',{}).get('prompt_tokens'),outputTokens=r.get('usage',{}).get('completion_tokens'),isolationPassed=safe);rows.append(row)
 code={n:hashlib.sha256((PRIVATE/'frozen'/n).read_bytes()).hexdigest()==v for n,v in protocol['code'].items()};experiment_code={n:hashlib.sha256((PRIVATE/n).read_bytes()).hexdigest()==v for n,v in protocol['experimentCode'].items()};assert all(code.values()) and all(experiment_code.values())
 audit={'traceCount':trace_count,'naturalCaseNameTextRequests':natural_names,'naturalCaseNameTextUniqueCases':len(natural_cases),'noAdditionalLabelFields':True,'frozenCodeHashesPassed':code,'experimentCodeHashesPassed':experiment_code,'pplxPhase':read(PRIVATE/'pplx-phase.json'),'genericPhase':read(PRIVATE/'generic-phase.json'),'failedInitialAttempt':read(PRIVATE/'initial-attempt'/'completion.json'),'initialAttemptFormalCalls':0,'archive':read(PRIVATE/'archive.sha256'),'postRestoreSmoke':read(PRIVATE/'post-restore-smoke.json'),'note':'Anonymous paths do not remove natural LKDTM symbols or workload clues. Existing test cases were used in development. No root-cause truth.'}
assert runtime['placement']=='full-gpu' and runtime['parameterDevices']==['cuda:0']
assert len(rows)==121 and len({(r['caseId'],r['arm'],r['repeat']) for r in rows})==121 and all(r['isolationPassed'] for r in rows)
for r,s in zip(sorted(rows,key=lambda x:x['ordinal']),protocol['schedule']):assert all(r[k]==s[k] for k in ['caseId','arm','repeat','scored'])
for r in rows:
 if not r['scored']:assert r['correct'] is None
 if r['status']=='completed':
  assert r['outputTokens']==0
  for answer in r['answers'].values():assert all(math.isfinite(x) and 0<=x<=1 for x in answer['probabilities'].values()) and abs(sum(answer['probabilities'].values())-1)<1e-5
for n,obj in [('protocol.json',protocol),('trials.json',rows),('pplx-runtime.json',runtime),('completion.json',completion),('audit.json',audit)]: (O/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
fields=[k for k in rows[0] if k!='answers']
with (O/'trials.csv').open('w',encoding='utf-8',newline='') as file:
 writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in rows)
arms=['generic','pplx'];labels=['Generic Qwen / SGLang','PPLX / Transformers'];colors=['#245fa8','#a84d27'];tests=[c['caseId'] for c in protocol['cases'] if c['split']=='test'];mapped=[c['caseId'] for c in protocol['cases'] if c['family'] in protocol['taxonomy']]
def ci(k,n):return [float(beta.ppf(.025,k,n-k+1)) if k else 0,float(beta.ppf(.975,k+1,n-k)) if k<n else 1]
def summary(rr):
 valid=[r['seconds'] for r in rr if r['status']=='completed'];k=sum(r['correct'] is True for r in rr)
 return {'attempts':len(rr),'correct':k,'agreement':k/len(rr),'failures':sum(r['status']!='completed' for r in rr),'meanSeconds':float(np.mean(valid)),'medianSeconds':float(np.median(valid)),'p95NearestRank':sorted(valid)[math.ceil(.95*len(valid))-1],'inputTokens':sum(r['inputTokens'] or 0 for r in rr),'outputTokens':sum(r['outputTokens'] or 0 for r in rr)}
stats={'formalCalls':121,'warmupsExcluded':2,'uniqueCases':60,'uniqueScoredCases':25,'unsupportedUnscoredCases':35,'primary':{},'secondaryProxy':{},'deploymentCaveat':protocol['runtime'],'orderCaveat':protocol['order'],'primaryCaseLatency':[]}
for arm in arms:
 rr=[r for r in rows if r['arm']==arm and r['split']=='test'];s=summary(rr);k=sum(sum(r['correct'] is True for r in rr if r['caseId']==c)>1 for c in tests);s.update(uniqueCases=len(tests),majorityCorrect=k,majorityCI95=ci(k,len(tests)));stats['primary'][arm]=s
 rr=[r for r in rows if r['arm']==arm and r['scored'] and r['repeat']==0];s=summary(rr);s['proxyCI95']=ci(s['correct'],len(rr));s['multiclassBrier']=float(np.mean([sum((v-int(k==r['gold']))**2 for k,v in r['answers']['family']['probabilities'].items()) for r in rr if r['status']=='completed']));stats['secondaryProxy'][arm]=s
for c in tests:
 rr={a:[r for r in rows if r['arm']==a and r['caseId']==c] for a in arms}
 if all(len(rr[a])==3 and all(r['status']=='completed' for r in rr[a]) for a in arms):stats['primaryCaseLatency'].append({'caseId':c,**{a:float(np.mean([r['seconds'] for r in rr[a]])) for a in arms}})
pairs=stats['primaryCaseLatency'];x=np.array([r['generic'] for r in pairs]);y=np.array([r['pplx'] for r in pairs]);diff=x-y;rng=np.random.default_rng(202610120);boot=np.mean(rng.choice(diff,size=(50000,len(diff)),replace=True),axis=1);observed=abs(float(np.mean(diff)));pval=sum(abs(float(np.mean(diff*np.array(signs))))>=observed-1e-12 for signs in itertools.product([-1,1],repeat=len(diff)))/2**len(diff)
stats['latencyComparison']={'pairedUniqueCases':len(pairs),'genericMinusPplxMeanSeconds':float(np.mean(diff)),'bootstrapCaseCI95':np.quantile(boot,[.025,.975]).tolist(),'exactCaseSignFlipTwoSidedP':pval,'meanReductionFraction':float((np.mean(x)-np.mean(y))/np.mean(x)),'inferenceLimit':'Exploratory on known cases. Sequential order and different runtimes confound interpretation; no model-intrinsic speed or cross-mechanism significance claim.'}
groups={}
for r,d in zip(pairs,diff):
 family=next(x['gold'] for x in rows if x['caseId']==r['caseId']);groups.setdefault(family,[]).append(float(d))
group_means=np.array([np.mean(v) for v in groups.values()]);group_observed=abs(float(group_means.mean()));group_p=sum(abs(float(np.mean(group_means*np.array(signs))))>=group_observed-1e-12 for signs in itertools.product([-1,1],repeat=len(group_means)))/2**len(group_means)
stats['familySensitivity']={'groups':{k:float(np.mean(v)) for k,v in groups.items()},'equalGroupMeanSeconds':float(group_means.mean()),'exactTwoSidedSignFlipP':group_p,'scope':'Sensitivity to correlated cases in the same injection family. Family groups are not verified independent causal mechanisms.'}
b=c=0
for name in tests:
 hit={arm:sum(r['correct'] is True for r in rows if r['caseId']==name and r['arm']==arm)>1 for arm in arms};b+=hit['generic'] and not hit['pplx'];c+=hit['pplx'] and not hit['generic']
stats['accuracyMcNemar']={'genericOnlyCorrect':b,'pplxOnlyCorrect':c,'exactTwoSidedP':float(binomtest(b,b+c).pvalue) if b+c else 1.0,'noninferiorityProven':False}
stats['mismatches']=[{k:r[k] for k in ['caseId','arm','repeat','split','gold','family']} for r in rows if r['correct'] is False];stats['failures']=[{k:r[k] for k in ['caseId','arm','repeat','status']} for r in rows if r['status']!='completed'];(O/'statistics.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
def save(fig,name):
 fig.savefig(F/(name+'.png'),dpi=200,bbox_inches='tight',facecolor='white');fig.savefig(F/(name+'.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4.4));axis=np.arange(2);w=.32
for i,arm in enumerate(arms):
 primary=stats['primary'][arm];secondary=stats['secondaryProxy'][arm];ys=[primary['majorityCorrect']/9,secondary['agreement']];intervals=[primary['majorityCI95'],secondary['proxyCI95']]
 ax.bar(axis+(i-.5)*w,np.array(ys)*100,width=w,color=colors[i],label=labels[i]);ax.errorbar(axis+(i-.5)*w,np.array(ys)*100,yerr=[[100*(v-z[0]) for v,z in zip(ys,intervals)],[100*(z[1]-v) for v,z in zip(ys,intervals)]],fmt='none',ecolor='#222',capsize=4)
 for j,(v,n) in enumerate(zip(ys,[9,25])):ax.text(axis[j]+(i-.5)*w,v*100+3,f'{round(v*n)}/{n}',ha='center',fontsize=9,zorder=4,bbox={'facecolor':'white','edgecolor':'none','pad':1})
ax.set_xticks(axis,['Existing test / majority of 3','Injection proxy / repeat 0']);ax.set(ylim=(0,117),ylabel='Agreement with frozen labels (%)',title='Full-GPU time-sharing: 95% exact case-level intervals');ax.legend(loc='lower left',fontsize=8);fig.tight_layout();save(fig,'01-accuracy')
names=list(next(r for r in rows if r['status']=='completed')['answers']['family']['probabilities']);display={'memory_lifetime':'lifetime','memory_bounds':'bounds','memory_leak':'leak','locking':'locking','rcu_progress':'RCU','oom':'OOM','other_or_no_fault':'other','blocked_task':'blocked','watchdog_lockup':'watchdog'}
fig,axes=plt.subplots(1,2,figsize=(11,5))
for ax,arm,label in zip(axes,arms,labels):
 matrix=np.zeros((len(names),len(names)),int)
 for r in rows:
  if r['arm']==arm and r['scored'] and r['repeat']==0 and r['family'] in names:matrix[names.index(r['gold']),names.index(r['family'])]+=1
 ax.imshow(matrix,cmap='Blues',vmin=0,vmax=max(1,matrix.max()));ax.set_xticks(range(len(names)),[display[n] for n in names],rotation=55,ha='right');ax.set_yticks(range(len(names)),[display[n] for n in names]);ax.set(xlabel='Predicted first-diagnostic family',ylabel='Mapped injection family',title=label)
 for i,j in itertools.product(range(len(names)),repeat=2):
  if matrix[i,j]:ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>matrix.max()*.55 else 'black')
fig.suptitle('25 proxy-labeled cases / arm; injection and first diagnosis can differ');fig.tight_layout();save(fig,'02-confusion')
fig,ax=plt.subplots(figsize=(9,4.8))
for i,r in enumerate(pairs):ax.plot([r[a] for a in arms],[i,i],color='#b8c3ce');ax.scatter([r[a] for a in arms],[i,i],c=colors,s=34)
ax.set_yticks(range(len(pairs)),[r['caseId'].replace('lkdtm_','') for r in pairs]);ax.invert_yaxis();ax.set_xscale('log');ax.set(xlabel='Mean client-call seconds per case (3 repeats; log scale)',title='Both models fully GPU-resident, measured sequentially\nRuntime/kernel and temporal differences remain');ax.legend(handles=[Line2D([],[],marker='o',linestyle='none',color=c,label=l) for c,l in zip(colors,labels)],loc='upper center',bbox_to_anchor=(.5,-.18),ncol=2,fontsize=8);fig.tight_layout();save(fig,'03-paired-latency')
fig,ax=plt.subplots(figsize=(8,4));ratios=np.array([[np.log2(r['pplx']/r['generic']) for r in pairs]]);bound=max(.25,float(abs(ratios).max()));im=ax.imshow(ratios,cmap='RdBu_r',vmin=-bound,vmax=bound,aspect='auto');ax.set_xticks(range(len(pairs)),[r['caseId'].replace('lkdtm_','') for r in pairs],rotation=55,ha='right',fontsize=8);ax.set_yticks([0],['PPLX / generic']);ax.set_title('Case-wise deployment latency ratio\nNegative: PPLX faster; positive: PPLX slower')
for i,r in enumerate(pairs):ax.text(i,0,f"{r['pplx']/r['generic']:.2f}x",ha='center',va='center',color='white' if abs(ratios[0,i])>bound*.6 else 'black',fontsize=8)
fig.colorbar(im,ax=ax,label='log2 latency ratio',fraction=.045,pad=.03);fig.tight_layout();save(fig,'04-latency-ratio')
g=stats['primary']['generic'];pplx=stats['primary']['pplx'];cmp=stats['latencyComparison'];lines=['# PPLX 全 GPU 分时复用复测报告（2026-10-12）','真实 PPLX v1 专用权重与通用 Qwen 分时使用同一 A100；CPU 卸载旧结果不进入本轮对照分母。', '## 已验证的运行条件',f"PPLX 全部参数位于 `{runtime['parameterDevices']}`，总参数字节 {runtime['parameterBytes']}（{runtime['parameterBytes']/1024**3:.3f} GiB）；device map 为 `{runtime['deviceMap']}`。没有 CPU/meta 参数。固定 checkpoint revision `{protocol['checkpointRevision']}`。",'原通用模型与 PPLX CPU sidecar 在测试时停止；先测 PPLX，再释放显存测通用模型；每阶段都确认另一模型端口及生产30000不响应，并记录GPU快照。两端BF16、相同证据、三个问题、8192上下文、串行客户端；通用实验端关闭radix前缀缓存。PPLX为官方参考Transformers/SDPA，通用为SGLang0.5.21，因此仅移除了CPU卸载/同时驻留差异，运行时、内核、提示与读出仍不同，且顺序没有交叉随机化。','9个既有test案例各3次×2端=54；其他16个映射train案例各1次×2端=32；35个未覆盖案例仅PPLX各1次=35。共121正式调用，另排除2合成预热。未知家族correct=null，未评估源码根因、引入提交或stage/reporter准确率。','## 结果','| 指标 | 通用 Qwen / 全GPU SGLang | PPLX / 全GPU参考实现 |','| --- | --- | --- |',f"| test调用与标签吻合 | {g['correct']}/27 | {pplx['correct']}/27 |",f"| test唯一案例多数正确 | {g['majorityCorrect']}/9 | {pplx['majorityCorrect']}/9 |",f"| test平均客户端秒 | {g['meanSeconds']:.3f} | {pplx['meanSeconds']:.3f} |",f"| test P95秒 | {g['p95NearestRank']:.3f} | {pplx['p95NearestRank']:.3f} |",f"| test API调用数 | {g['attempts']} | {pplx['attempts']} |",f"| test输入token总数 | {g['inputTokens']} | {pplx['inputTokens']} |",f"| test输出token总数 | {g['outputTokens']} | {pplx['outputTokens']} |",f"| 25例注入标签代理吻合 | {stats['secondaryProxy']['generic']['correct']}/25 | {stats['secondaryProxy']['pplx']['correct']}/25 |",'','![标签吻合](figures/01-accuracy.svg)','![混淆矩阵](figures/02-confusion.svg)','![案例级配对耗时](figures/03-paired-latency.svg)','![相对耗时热力图](figures/04-latency-ratio.svg)','## 统计与解释',f"{cmp['pairedUniqueCases']}个唯一test案例取各自3次均值，再做配对。通用减PPLX平均差 {cmp['genericMinusPplxMeanSeconds']:.3f}s；案例bootstrap95%区间 [{cmp['bootstrapCaseCI95'][0]:.3f}, {cmp['bootstrapCaseCI95'][1]:.3f}]s；探索性双侧案例符号置换p={cmp['exactCaseSignFlipTwoSidedP']:.6f}。均值相对减少率（负值表示PPLX更慢）{cmp['meanReductionFraction']*100:.2f}%。重复调用不作为27个独立样本；这些统计不消除运行时/顺序混杂，也不是跨机制显著性或模型本征速度证明。",f"准确率配对McNemar p={stats['accuracyMcNemar']['exactTwoSidedP']:.6f}，非劣/等效未证明。既有test参与开发，不是新机制盲测。25例概率Brier仅对注入代理：通用 {stats['secondaryProxy']['generic']['multiclassBrier']:.4f}，PPLX {stats['secondaryProxy']['pplx']['multiclassBrier']:.4f}；不能声称内核领域已校准。",'## 标签、泄露与失败',f"正式失败 {len(stats['failures'])}；121个匿名隔离审计均通过，{audit['traceCount']}个实际请求无额外标签/案例ID/评分字段。仍有{audit['naturalCaseNameTextRequests']}个请求、{audit['naturalCaseNameTextUniqueCases']}个唯一案例含与案例名重合的自然日志符号，存在捷径，不能称完全去线索盲测。",'注入watchdog的LOOP/SOFTLOCKUP第一诊断为RCU stall；映射目标与提问构念不同。冻结目标不事后重标，返回RCU不能自动算作模型错误。未覆盖35例保留输出但不报准确率。',f"首次启动尝试因记录代码读取不存在的hf_device_map属性失败，0正式调用；已保留该尝试及恢复记录，修复后另起新协议目录。当前最终状态 `{completion['status']}`，原模型与CPU sidecar恢复检查 `{completion['restoration']['restored']}`，Supervisor状态 `{completion['restoration']['supervisorState']}`。",'## 实际结论',f"PPLX已在完整GPU驻留条件下取得本轮数据，平均{pplx['meanSeconds']:.3f}s；通用部署本轮平均{g['meanSeconds']:.3f}s。两者家族成绩分别{pplx['correct']}/27与{g['correct']}/27。此前CPU卸载19.455s不再用于公平速度比较；它只描述另一部署条件。",'完整Agent的根因定位收益仍未测试。若研究目标是纯权重/架构收益，应进一步统一支持专用readout的运行时及核函数，并做AB/BA交叉顺序、独立机制与专家首诊断真值验证。当前数据支持已测部署方案在已知案例上的表现，不能外推至未经测试的配置。','## 保存与复现',f"私有原始归档 {audit['archive']['bytes']} 字节、{audit['archive']['files']} 个证据文件，SHA256 `{audit['archive']['sha256']}`；归档及逐文件哈希在本地复核一致。排除原进程环境、账号、权重与临时制备副本。恢复后两个Decision端点合成UAF家族验收通过；Chat仅验证HTTP200和可返回，不验证生成内容。恢复验收不计入121正式调用。",'公开 `results/trials.csv/json` 包含121次标量、三个问题的选择与概率，完整输入/原始轨迹仅保留私有归档。运行 `python analyze.py --public` 可离线重算本报告与科研图，不调用模型。服务器 `/opt/kernel-insight/experiments/pplx-timeshare-20261012/`；首次失败尝试在相邻20261011目录。恢复与阶段快照、全GPU参数设备断言均可追溯。']
lines+=['## 分析计划与相关案例敏感性',f"运行协议、输入与顺序在正式调用前冻结；本分析脚本在采集期间编写，统计属于探索性。按{len(group_means)}个注入家族分别取案例差值均值，再对家族等权符号置换，p={group_p:.6f}。家族也不等于经过因果验证的独立机制；案例级区间不能被解读为任意新故障的总体区间。"]
lines+=['## 部署验收与文档更新（2026-10-12）','最近已验证：2026-10-11 CPU卸载入口通过choice/noul/score、负例与项目客户端验收；2026-10-12冻结全GPU入口完成78次PPLX正式调用，逐参数cuda:0断言通过。分时对照后恢复原30000及30002服务，并真实执行合成UAF验证。这些部署验收不计入正式121次分母。','2026-10-12新版常驻部署已通过在线验收（北京时间2026-10-12 07:29:02）：五个部署脚本与仓库521b29c对应字节SHA256一致，30个权重文件重新核验通过；两轮choice/noul/score、项目DecisionClient、422/404负例和推理后停止→启动→再次推理均通过，共4次合成推理，不计入benchmark。PPLX PID1114，通用PID66启动身份未变，两个模型端点健康。当前常驻为CPU卸载并存配置；全GPU121次实验与此次部署验收分别保存。 证据见[新版部署验收](../../deployment/pplx-decider/validation-20261012/README.md)。','权重固定下载链接、30文件校验、依赖、CPU卸载与完整GPU命令、参数和恢复步骤见[中文部署手册](../../docs/PPLX专用模型下载部署与验收手册.md)。已更新的[学术报告](../decision-localization-20261011/report.md)与[修订版PDF](../../output/pdf/AI4Loc_Decision_Academic_Report_20261012.pdf)单列本轮全GPU研究。']
text='';previous=''
for line in lines:text+=('' if not text else '\n' if line.startswith('|') and previous.startswith('|') else '\n\n')+line;previous=line
(H/'REPORT.md').write_text(text+'\n',encoding='utf-8')
from markdown_it import MarkdownIt
html=MarkdownIt('commonmark',{'html':False}).enable('table').render(text)
(H/'report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PPLX 全GPU复测</title><style>body{max-width:1050px;margin:40px auto;padding:0 24px;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif;color:#243544}h1,h2{color:#173e62}h2{margin-top:48px}img{width:100%}table{width:100%;border-collapse:collapse;font-size:14px}th,td{border:1px solid #bccbd8;padding:8px}th{background:#edf3f8}code{font-size:.88em;background:#f1f4f7}a{color:#245fa8}</style><main>'+html+'</main></html>',encoding='utf-8');print(json.dumps(stats,ensure_ascii=False,indent=2))
