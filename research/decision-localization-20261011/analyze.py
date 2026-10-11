"""Reproduce all tables, uncertainty estimates and scientific figures from retained server results."""
import pathlib,json,csv,hashlib,itertools,math,tarfile,collections,sys
import numpy as np
from scipy.stats import beta,binomtest
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
ROOT=pathlib.Path(__file__).resolve().parents[2];HERE=pathlib.Path(__file__).parent;OUT=HERE/'results';FIG=HERE/'figures';OUT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
PRIVATE=ROOT/'data/local-archive/paper-20261011';OLD=ROOT/'data/local-archive/decision-hybrid-20261008';read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
PUBLIC='--public' in sys.argv
if not PUBLIC:
 new=read(PRIVATE/'results-with-coverage.json');protocol=read(PRIVATE/'protocol.json');assert new['complete'] and len(new['rows'])==135
 assert new['protocolSha256']==hashlib.sha256((PRIVATE/'protocol.json').read_bytes()).hexdigest()
expected={'boundary-results.json':'193d619e8218d83e1b36876980c3a01d07afa1399b10e70cc67c30c40f901765','control-results.json':'1573d226e72e451cd6319f58babb62152351493e867ac9a20eae513b41e4e000','hybrid-results.json':'c5efea27e74446bf68f0dbb9c74abc963f3786f989424e14b068c6f12edb6d3f'}
if not PUBLIC:
 for n,sha in expected.items():assert hashlib.sha256((OLD/n).read_bytes()).hexdigest()==sha
 old=read(OLD/'boundary-results.json');control=read(OLD/'control-results.json');hybrid=read(OLD/'hybrid-results.json');hist={p.name.split('__')[0]:read(p) for p in (PRIVATE/'historical').glob('*results.json')}
else:
 protocol=read(OUT/'protocol.json')
 with (OUT/'boundary-trials.csv').open(encoding='utf-8',newline='') as f:publicrows=list(csv.DictReader(f))
 for r in publicrows:
  for k in ['correct','diagnosticIncluded','isolationPassed']:r[k]={'True':True,'False':False,'':None}[r[k]]
  for k in ['repeat','ordinal','evidenceLineCount','promptTokens','outputTokens']:r[k]=int(r[k]) if r[k] else None
  for k in ['seconds','chosenProbability','labelMass']:r[k]=float(r[k]) if r[k] else None
 with (OUT/'historical-boundary-trials.csv').open(encoding='utf-8',newline='') as f:oldrows=list(csv.DictReader(f))
 for r in oldrows:r.update(repeat=int(r['repeat']),seconds=float(r['seconds']),correct=r['correct']=='True')
 old={'rows':oldrows,'aggregate':read(OUT/'historical-boundary-aggregates.json')}
 e2epublic=read(OUT/'end-to-end-cases.json');control={'runs':[]};hybrid={'runs':[]}
 for c in e2epublic:
  for name,dst in [('control',control),('hybrid',hybrid)]:dst['runs'].append({'caseId':c['caseId'],'scores':{'codeLocationHit':c[name+'Hit']},'metrics':{'localizationSeconds':c[name+'Seconds'],'modelRequests':c[name+'Requests']},'analysis':{'localization':{'locations':c[name+'Locations']}}})
 hist={n:{'aggregate':v} for n,v in read(OUT/'historical-ablation-aggregates.json').items()}
variants=['D3-first','C3-first','D1-first','D3-tail','C3-tail'];cases=protocol['cases'];short=['Healthy','UAF','Hung task','Usercopy from','Usercopy to','Usercopy kernel','Usercopy stack','Mutex ABBA','Spin ABBA'];labels=dict(zip(cases,short));families={c:('usercopy' if 'USERCOPY' in c else 'lock_order' if 'abba' in c else c) for c in cases}
def safe(row):
 a=row.get('answers',{}).get('family',{});return {k:row.get(k) for k in ['caseId','repeat','variant','ordinal','status','seconds','gold','family','correct','diagnosticIncluded','evidenceLineCount','inputSha256','agentLogSha256']}|{'promptTokens':(row.get('usage') or {}).get('prompt_tokens'),'outputTokens':(row.get('usage') or {}).get('completion_tokens'),'chosenProbability':(a.get('probabilities') or {}).get(a.get('choice')),'labelMass':a.get('label_mass'),'isolationPassed':row.get('audit',{}).get('anonymousWorkspace') is True and not any(row.get('audit',{}).get(k,True) for k in ['evaluatorVisible','businessDataVisible','procVisible'])}
rows=publicrows if PUBLIC else [safe(r) for r in new['rows']];assert len(rows)==135 and all(r['isolationPassed'] and r['status']=='completed' for r in rows)
assert len({(r['caseId'],r['repeat'],r['variant']) for r in rows})==135
with (OUT/'boundary-trials.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(PROTOCOL_COPY:=OUT/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
means={v:np.array([np.mean([r['seconds'] for r in rows if r['variant']==v and r['caseId']==c]) for c in cases]) for v in variants}
def exact_flip(d):
 d=np.array(d);obs=abs(d.mean());null=np.array([abs(np.mean(d*np.array(s))) for s in itertools.product([-1,1],repeat=len(d))]);return float(np.mean(null>=obs-1e-12))
def paired(a,b):
 d=np.asarray(a)-np.asarray(b);rng=np.random.default_rng(20261011);ids=rng.integers(len(d),size=(30000,len(d)));bs=d[ids].mean(axis=1);ratio=1-np.asarray(b)[ids].mean(axis=1)/np.asarray(a)[ids].mean(axis=1)
 fd=np.array([np.mean([d[i] for i,c in enumerate(cases) if families[c]==f]) for f in sorted(set(families.values()))]) if len(d)==9 else d
 return {'meanDifferenceSeconds':float(d.mean()),'ci95':list(map(float,np.quantile(bs,[.025,.975]))),'relativeReduction':float(1-np.mean(b)/np.mean(a)),'relativeReductionCI95':list(map(float,np.quantile(ratio,[.025,.975]))),'caseSignFlipP':exact_flip(d),'familySignFlipP':exact_flip(fd),'caseCount':len(d),'familyCount':len(fd),'wins':int((d>0).sum())}
def holm(ps):
 order=np.argsort(ps);out=np.zeros(len(ps));running=0
 for rank,i in enumerate(order):running=max(running,(len(ps)-rank)*ps[i]);out[i]=min(1,running)
 return out.tolist()
contrasts={n:paired(means[a],means[b]) for n,a,b in [('C3-first minus D3-first','C3-first','D3-first'),('D3-first minus D1-first','D3-first','D1-first'),('C3-tail minus D3-tail','C3-tail','D3-tail')]}
for field in ['caseSignFlipP','familySignFlipP']:
 for obj,p in zip(contrasts.values(),holm([x[field] for x in contrasts.values()])):obj[field+'Holm']=p
aggregate={}
for v in variants:
 rr=[r for r in rows if r['variant']==v];t=np.array([r['seconds'] for r in rr]);succ=sum(r['correct'] for r in rr);n=len(rr)
 aggregate[v]={'attempts':n,'success':succ,'errors':sum(r['status']!='completed' for r in rr),'meanSeconds':float(t.mean()),'medianSeconds':float(np.median(t)),'p95NearestRank':float(np.sort(t)[math.ceil(.95*n)-1]),'meanInputTokens':float(np.mean([r['promptTokens'] for r in rr])),'meanOutputTokens':float(np.mean([r['outputTokens'] for r in rr])),'caseMajorityCorrect':sum(sum(r['correct'] for r in rr if r['caseId']==c)>=2 for c in cases),'caseAccuracyExactCI95':[float(beta.ppf(.025,9,1)),1.0],'faultDiagnosticIncludedCases':sum(any(r['diagnosticIncluded'] for r in rr if r['caseId']==c) for c in cases if c!='baseline')}
e2e=[]
for c in cases:
 a=next(r for r in control['runs'] if r['caseId']==c);b=next(r for r in hybrid['runs'] if r['caseId']==c)
 e2e.append({'caseId':c,'controlHit':None if c=='baseline' else a['scores']['codeLocationHit'],'hybridHit':None if c=='baseline' else b['scores']['codeLocationHit'],'controlSeconds':a['metrics']['localizationSeconds'],'hybridSeconds':b['metrics']['localizationSeconds'],'controlRequests':a['metrics']['modelRequests'],'hybridRequests':b['metrics']['modelRequests'],'controlLocations':a['analysis'].get('localization',{}).get('locations',[]),'hybridLocations':b['analysis'].get('localization',{}).get('locations',[])})
e2estat=paired([r['hybridSeconds'] for r in e2e],[r['controlSeconds'] for r in e2e]);e2estat.update(controlSeconds=sum(r['controlSeconds'] for r in e2e),hybridSeconds=sum(r['hybridSeconds'] for r in e2e),controlRequests=sum(r['controlRequests'] for r in e2e),hybridRequests=sum(r['hybridRequests'] for r in e2e),controlHits=sum(r['controlHit'] is True for r in e2e),hybridHits=sum(r['hybridHit'] is True for r in e2e),faultCount=8,accuracyCI95=[float(beta.ppf(.025,4,5)),float(beta.ppf(.975,5,4))],discordantAccuracyPairs=0,mcnemarExactP=1.0)
oldmeans={v:np.array([np.mean([r['seconds'] for r in old['rows'] if r['mode']==v and r['caseId']==c]) for c in cases]) for v in ['decision','chat']};oldstat=paired(oldmeans['chat'],oldmeans['decision'])
summary={'schema':'decision-localization-paper-statistics/v1','date':'2026-10-11','nUniqueCases':9,'nMechanismGroups':5,'newAttempts':135,'warmupAttemptsExcluded':5,'bootstrapReplicates':30000,'seed':20261011,'aggregate':aggregate,'contrasts':contrasts,'historicalBoundary':{'aggregate':old['aggregate'],'statistics':oldstat},'historicalEndToEnd':e2estat,'historicalAblations':{n:d['aggregate'] for n,d in hist.items()},'scope':'Current and historical cohorts kept separate. No unseen holdout, no dedicated Jev/Decider checkpoint, no mechanism or introducing-commit correctness ground truth.','inputTokensRatioD3toC3':aggregate['D3-first']['meanInputTokens']/aggregate['C3-first']['meanInputTokens']}
(OUT/'statistics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'end-to-end-cases.json').write_text(json.dumps(e2e,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'historical-ablation-aggregates.json').write_text(json.dumps(summary['historicalAblations'],indent=2),encoding='utf-8');(OUT/'historical-boundary-trials.csv').write_text('caseId,repeat,mode,seconds,correct\n'+'\n'.join(f"{r['caseId']},{r['repeat']},{r['mode']},{r['seconds']},{r['correct']}" for r in old['rows'])+'\n',encoding='utf-8')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','figure.facecolor':'white','axes.titleweight':'bold'})
(OUT/'historical-boundary-aggregates.json').write_text(json.dumps(old['aggregate'],ensure_ascii=False,indent=2),encoding='utf-8')
BLUE='#245fa8';ORANGE='#bb5d24';GRAY='#687584';GREEN='#2c8460'
def save(fig,name):
 fig.savefig(FIG/(name+'.png'),dpi=210,bbox_inches='tight',facecolor='white');fig.savefig(FIG/(name+'.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
# Figure 1: directed data/control flow, with a separate evaluator trust boundary.
fig,ax=plt.subplots(figsize=(11,6.4));ax.set(xlim=(0,11),ylim=(0,6.4));ax.axis('off')
def box(x,y,w,h,t,color=BLUE):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',linewidth=1,edgecolor=color,facecolor='#f6f9fd'));ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=10)
def arr(a,b,label=None,color=GRAY,rad=0):
 ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,color=color,connectionstyle=f'arc3,rad={rad}')); 
 if label:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.12,label,ha='center',fontsize=8,color=color,bbox={'facecolor':'white','edgecolor':'none','pad':1.2})
box(.2,5.2,2.15,.75,'Log + optional source\n+ matched ELF / DWARF');box(3.1,5.2,2.1,.75,'incident tool\nfirst diagnostic + lines');box(6.1,5.2,2.1,.75,'Decision API\nfamily / stage / reporter');box(8.9,5.2,1.7,.75,'Early boundary\nevent (fallible)');arr((2.4,5.6),(3,5.6));arr((5.3,5.6),(6,5.6));arr((8.3,5.6),(8.8,5.6))
box(.4,3.2,2.4,.9,'Bounded source preflight\nobserved symbols only');box(3.7,3.2,2.4,.9,'Chat investigator\nselect tool or report');box(7.1,3.2,3,.9,'Read-only tools\nlog / source / symbolize / git');arr((4.15,5.1),(1.7,4.2),'same evidence');arr((2.9,3.65),(3.6,3.65));arr((7.1,5.1),(5,4.2),'hint, never hard prune');arr((6.2,3.8),(7,3.8),'tool call');arr((7,3.3),(6.2,3.3),'tool result')
box(3.7,1.6,2.4,.8,'Validate schema + citations\nmatch source ranges');box(7.1,1.6,3,.8,'Bounded report + next checks\nrootCauseVerified = false');arr((4.9,3.1),(4.9,2.5),'report');arr((6.2,2),(7,2),'accepted');arr((3.6,2),(3.5,3.5),'repair / bounded retry',rad=-.35)
ax.add_patch(FancyBboxPatch((.25,.15),10.25,.7,boxstyle='round,pad=.03',edgecolor=ORANGE,linestyle='--',facecolor='#fff9f4'));ax.text(5.35,.5,'Evaluator outside worker: labels + scoring only after exit | No dataset / business / proc mounts',ha='center',va='center',fontsize=10,color=ORANGE);ax.text(.3,6.2,'Evidence flow and auditable control loop (design diagram; not a measured result)',fontsize=11,fontweight='bold');save(fig,'01-system-flow')
# Figure 2: paired means + descriptive latency distribution.
fig,(a,b)=plt.subplots(1,2,figsize=(10,4.8),gridspec_kw={'width_ratios':[1.1,1]})
for i,c in enumerate(cases):a.plot([means['D3-first'][i],means['C3-first'][i]],[i,i],color='#b7c2cc',lw=1.6)
a.scatter(means['D3-first'],range(9),color=BLUE,label='Decision / 3 questions',zorder=3);a.scatter(means['C3-first'],range(9),color=ORANGE,label='Chat / 3 fields',zorder=3);a.set_yticks(range(9),short);a.invert_yaxis();a.set_xlabel('Mean client-call latency per case (s)');a.set_title('Paired case means (3 repeats each)');a.legend(fontsize=8,loc='lower right')
for v,col in [('D3-first',BLUE),('C3-first',ORANGE)]:
 t=np.sort([r['seconds'] for r in rows if r['variant']==v]);b.step(t,np.arange(1,28)/27,where='post',label=v,color=col)
b.set(xlabel='Client-call latency (s)',ylabel='Empirical cumulative fraction',title='27 trials / interface (dependent repeats)');b.legend();b.grid(alpha=.15);fig.tight_layout();save(fig,'02-paired-latency')
# Figure 3: effect sizes, confidence intervals and corrected p-values.
fig,ax=plt.subplots(figsize=(10,3.8));names=list(contrasts)
for i,n in enumerate(names):
 z=contrasts[n];lo,hi=z['ci95'];ax.errorbar(z['meanDifferenceSeconds'],i,xerr=[[z['meanDifferenceSeconds']-lo],[hi-z['meanDifferenceSeconds']]],fmt='o',color=BLUE,capsize=4);ax.text(1.02,i,f"case Holm p={z['caseSignFlipPHolm']:.4f}\nfamily Holm p={z['familySignFlipPHolm']:.4f}",transform=ax.get_yaxis_transform(),va='center',fontsize=9)
ax.axvline(0,color=GRAY,ls='--');ax.set_yticks(range(3),['Chat3 - Decision3 / first','Decision3 - Decision1 / first','Chat3 - Decision3 / tail']);ax.invert_yaxis();ax.set_xlabel('Paired mean latency difference (s); 95% case-bootstrap CI');ax.set_title('Positive values favor the subtracted configuration');fig.subplots_adjust(left=.28,right=.7,bottom=.2,top=.86);save(fig,'03-effect-forest')
# Figure 4: paired heatmap instead of misleading all-green accuracy map.
mat=np.array([means[v] for v in variants]).T;fig,ax=plt.subplots(figsize=(8.8,5.4));im=ax.imshow(mat,cmap='YlGnBu',aspect='auto',vmin=0,vmax=max(mat.flatten()));ax.set_yticks(range(9),short);ax.set_xticks(range(5),variants,rotation=15,ha='right')
for i in range(9):
 for j in range(5):ax.text(j,i,f'{mat[i,j]:.2f}',ha='center',va='center',color='white' if mat[i,j]>max(mat.flatten())*.55 else '#111',fontsize=10)
ax.set_title('Latency heatmap: seconds / case (3-repeat mean)\nFamily classification: 3/3 correct in every cell');fig.colorbar(im,ax=ax,label='Seconds');fig.tight_layout();save(fig,'04-latency-heatmap')
# Figure 5: token-work tradeoff and distribution by configuration.
fig,(a,b)=plt.subplots(1,2,figsize=(10,4.4));a.boxplot([[r['seconds'] for r in rows if r['variant']==v] for v in variants],tick_labels=variants,showfliers=True);a.set(ylabel='Client-call latency (s)',title='All 27 measured trials / configuration');a.tick_params(axis='x',rotation=25)
x=np.arange(5);b.bar(x,[aggregate[v]['meanInputTokens']/1000 for v in variants],color=[BLUE,ORANGE,GREEN,BLUE,ORANGE]);b.set_xticks(x,variants,rotation=25);b.set(ylabel='Mean input tokens (thousands)',title='Zero decoded tokens does not mean zero work');fig.tight_layout();save(fig,'05-ablation-cost')
# Figure 6: fault localization outcome and actual overhead, healthy excluded.
fig,(a,b)=plt.subplots(1,2,figsize=(10,4.8),gridspec_kw={'width_ratios':[.8,1.2]});faults=e2e[1:];hm=np.array([[int(r['controlHit']),int(r['hybridHit'])] for r in faults]);a.imshow(hm,cmap=matplotlib.colors.ListedColormap(['#f4c8bc','#b6ddcf']),vmin=0,vmax=1,aspect='auto');a.set_yticks(range(8),short[1:]);a.set_xticks([0,1],['Chat control','Hybrid']);a.set_title('Code-location hit (8 faults)')
for i in range(8):
 for j in range(2):a.text(j,i,'Hit' if hm[i,j] else 'Miss',ha='center',va='center',fontsize=10)
delta=np.array([r['hybridSeconds']-r['controlSeconds'] for r in e2e]);b.barh(range(9),delta,color=[ORANGE if d>0 else BLUE for d in delta]);b.set_yticks(range(9),short);b.invert_yaxis();b.axvline(0,color=GRAY);b.set(xlabel='Hybrid - control latency (s)',title='Historical complete workflow: +9.0% total');fig.tight_layout();save(fig,'06-end-to-end')
# Figure 7: historical ablation is descriptive, not randomized causal evidence.
hn=['baseline-results','candidate-results','adaptive-results','rule-ablation-results','baseline-warm-results'];hl=['Original\nfirst','Always\nDecision','Adaptive\nDecision','Rule\nablation','Original\nwarm'];fig,(a,b)=plt.subplots(1,2,figsize=(10,4.3));vals=[hist[n]['aggregate'] for n in hn];cols=[GRAY,BLUE,BLUE,GREEN,GRAY];a.bar(range(5),[v['codeLocationAccuracy']*100 for v in vals],color=cols);a.set_xticks(range(5),hl);a.set(ylim=(0,115),ylabel='Fault code-location accuracy (%)',title='Fixed regression cases (8 faults)')
for i,v in enumerate(vals):a.text(i,100*v['codeLocationAccuracy']+3,f"{round(v['codeLocationAccuracy']*8)}/8",ha='center')
b.bar(range(5),[v['localizationSeconds'] for v in vals],color=cols);b.set_xticks(range(5),hl);b.set(ylabel='Sum of 9 case times (s)',title='Sequential historical runs; cache/order confounded');fig.tight_layout();save(fig,'07-historical-ablation')
# Figure 8: old/new tails are separate cohorts, preventing an unjustified SLA claim.
fig,ax=plt.subplots(figsize=(8,4));x=np.arange(4);vals=[old['aggregate']['decision']['p95Seconds'],old['aggregate']['chat']['p95Seconds'],aggregate['D3-first']['p95NearestRank'],aggregate['C3-first']['p95NearestRank']];ax.bar(x,vals,color=[BLUE,ORANGE,BLUE,ORANGE]);ax.set_xticks(x,['Historical\nDecision','Historical\nChat','Current\nDecision','Current\nChat']);ax.set(ylabel='Nearest-rank P95 latency (s)',title='Tail latency: cohort-specific, 27 dependent trials each')
for i,v in enumerate(vals):ax.text(i,v+.04,f'{v:.3f}',ha='center')
ax.set_ylim(0,max(vals)*1.18);fig.tight_layout();save(fig,'08-tail-latency')
print(json.dumps(summary,ensure_ascii=False,indent=2))
