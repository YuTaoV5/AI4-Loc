"""Paired checkpoint/endpoint analysis. Requires only public exports."""
import pathlib,json,csv,subprocess,sys,collections,math,statistics,gzip
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
E=pathlib.Path(__file__).resolve().parent
def csvrows(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def outcsv(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def records(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def compressed(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:return [json.loads(x) for x in f]
def save(fig,name):
    fig.savefig(E/'figures'/(name+'.svg'),bbox_inches='tight');fig.savefig(E/'figures'/(name+'.png'),dpi=170,bbox_inches='tight');plt.close(fig)
def main():
    (E/'figures').mkdir(exist_ok=True);(E/'tables').mkdir(exist_ok=True)
    results=[];acc=[];trials=[]
    for model in ['base','trained']:
        folder=E/'analysis'/model;folder.mkdir(parents=True,exist_ok=True)
        subprocess.run([sys.executable,str(E/'analyze-concurrency-reference.py'),str(E/'data'/model),str(folder)],check=True)
        calls_table=csvrows(folder/'tables'/'calls.csv')
        arrivals={r['rid']:r for r in records(E/'data'/model/'answers-and-arrivals.jsonl')}
        for r in calls_table:
            events=arrivals[r['rid']]['arrivals']
            last=max((x['mono_ns'] for x in events),default=None)
            r['decision_last_probability_body_seconds']=(last-int(r['start_mono_ns']))/1e9 if r['arm']=='decision' and last else None
            r['decision_body_to_validation_end_ms']=(int(r['end_mono_ns'])-last)/1e6 if r['arm']=='decision' and last else None
        outcsv(folder/'tables'/'calls.csv',calls_table)
        for r in csvrows(folder/'tables'/'summary.csv'):results.append({'checkpoint':model,**r})
        for r in records(E/'data'/model/'accuracy.jsonl'):acc.append({'checkpoint':model,**r})
        # Board energy is integrated once per trial, never allocated repeatedly to concurrent requests.
        gpu=csvrows(folder/'tables'/'gpu-samples.csv')
        calls=records(E/'data'/model/'calls.jsonl')
        for t in records(E/'data'/model/'trials.jsonl'):
            cc=[c for c in calls if c['trial']==t['trial']];a=min(c['start_wall_ns'] for c in cc);b=max(c['end_wall_ns'] for c in cc)
            gs=[g for g in gpu if a<=int(g['wall_ns'])<=b]
            # Interior-sample trapezoid is a partial-window observation, not extrapolated full-trial energy.
            joules=sum((int(y['wall_ns'])-int(x['wall_ns']))/1e9*(float(x['power_w'])+float(y['power_w']))/2 for x,y in zip(gs,gs[1:]))
            trials.append({'checkpoint':model,**{k:t[k] for k in ['trial','arm','concurrency','decisions','cache','mode','repeat','instrumented','makespan_seconds']},
                           'power_samples':len(gs),'mean_sampled_power_w':statistics.mean(float(g['power_w']) for g in gs) if gs else None,
                           'observed_board_energy_j':joules if len(gs)>=2 else None,
                           'covered_seconds':(int(gs[-1]['wall_ns'])-int(gs[0]['wall_ns']))/1e9 if len(gs)>=2 else None})
    outcsv(E/'tables'/'checkpoint-concurrency-summary.csv',results);outcsv(E/'tables'/'trial-power-energy.csv',trials)
    frozen=json.loads((E/'dataset-frozen.json').read_text(encoding='utf-8'));classes=frozen['classes']
    count=[];matrices={};cal=[];casepred={}
    temperature=json.loads((E/'training-complete.json').read_text())['temperature']
    for model in ['base','trained']:
        for api in ['decision','chat']:
            rr=[r for r in acc if r['checkpoint']==model and r['api']==api]
            # Majority per original case; repeated option permutations are dependent.
            groups=collections.defaultdict(list)
            for r in rr:groups[r['source'],r['case']].append(r)
            cases=[]
            for (source,case),rs in groups.items():
                pred=collections.Counter(r['prediction'] for r in rs).most_common(1)[0][0]
                cases.append({'case':case,'source':source,'group':rs[0]['group'],'label':rs[0]['label'],'prediction':pred,'correct':pred==rs[0]['label']})
            matrix=np.zeros((len(classes),len(classes)+1),dtype=int)
            for r in cases:matrix[classes.index(r['label']),classes.index(r['prediction']) if r['prediction'] in classes else len(classes)]+=1
            matrices[model,api]=matrix
            casepred[model,api]=cases
            for source in ['all','stability','openharmony']:
                selected=[r for r in cases if source=='all' or r['source']==source]
                count.append({'checkpoint':model,'api':api,'source':source,'cases':len(selected),'correct':sum(r['correct'] for r in selected),'accuracy':sum(r['correct'] for r in selected)/len(selected)})
            outcsv(E/'tables'/f'{model}-{api}-case-predictions.csv',cases)
            if api=='decision':
                for temp in ([1.,temperature] if model=='trained' and temperature!=1 else [1.]):
                    # Select canonical case-level mean probabilities, then calculate calibration.
                    nll=[];brier=[];conf=[];correct=[]
                    for rs in groups.values():
                        pp=[]
                        for r in rs:
                            p=np.array([r['probabilities'][c] for c in classes]);p=np.exp(np.log(np.clip(p,1e-12,1))/temp);p/=p.sum();pp.append(p)
                        p=np.mean(pp,axis=0);y=classes.index(rs[0]['label']);nll.append(-np.log(max(p[y],1e-12)));brier.append(float(np.sum((p-np.eye(len(classes))[y])**2)));conf.append(float(p.max()));correct.append(p.argmax()==y)
                    bins=[];ece=0
                    for j in range(10):
                        ids=[i for i,c in enumerate(conf) if j/10<=c<((j+1)/10) or (j==9 and c==1)]
                        if ids:
                            c=float(np.mean([conf[i] for i in ids]));a=float(np.mean([correct[i] for i in ids]));ece+=len(ids)/len(conf)*abs(a-c);bins.append({'bin':j,'cases':len(ids),'mean_confidence':c,'accuracy':a})
                    cal.append({'checkpoint':model,'temperature':temp,'case_nll':float(np.mean(nll)),'case_brier':float(np.mean(brier)),'ece10':ece,'bins':bins})
    outcsv(E/'tables'/'accuracy-by-kernel.csv',count);(E/'calibration.json').write_text(json.dumps(cal,indent=2))
    fig,axs=plt.subplots(2,2,figsize=(16,13),layout='constrained')
    for ax,((model,api),m) in zip(axs.flat,matrices.items()):
        denominator=m.sum(1,keepdims=True);norm=np.divide(m,denominator,out=np.zeros_like(m,dtype=float),where=denominator!=0)
        masked=np.ma.masked_where(np.broadcast_to(denominator==0,m.shape),norm);cmap=plt.colormaps['Blues'].copy();cmap.set_bad('#e5e5e5')
        im=ax.imshow(masked,vmin=0,vmax=1,cmap=cmap);ax.set_xticks(range(len(classes)+1),[c.replace('_','\n') for c in classes]+['invalid'],rotation=65,fontsize=7);ax.set_yticks(range(len(classes)),[f'{c} (n={int(denominator[i,0])})' for i,c in enumerate(classes)],fontsize=8)
        for i,j in zip(*np.nonzero(m)):ax.text(j,i,str(m[i,j]),ha='center',va='center',color='white' if norm[i,j]>.6 else 'black',fontsize=8)
        ax.set_title(f'{model}: {api}; first-diagnostic weak labels');ax.set_ylabel('Reference');ax.set_xlabel('Case-majority prediction')
    fig.colorbar(im,ax=axs.ravel().tolist(),shrink=.5,label='row fraction; text = case count');save(fig,'accuracy-confusion')
    plt.rcParams.update({'font.size':10})
    scenarios=[(1,1),(4,1),(1,8),(4,8)]
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,cache in zip(axs,['cold','warm']):
        rows=[]
        for c,d in scenarios:
            values=[]
            for model in ['base','trained']:
                for api in ['decision','chat']:
                    r=next(r for r in results if r['checkpoint']==model and r['arm']==api and r['mode']=='sequential' and r['cache']==cache and r['concurrency']==str(c) and r['decisions']==str(d) and r['instrumented']=='True');values.append(float(r['makespan_seconds']))
            rows.append(values)
        m=np.array(rows);im=ax.imshow(m,cmap='Blues',aspect='auto');ax.set_xticks(range(4),['base\nDecision','base\nChat','trained\nDecision','trained\nChat']);ax.set_yticks(range(4),[f'{c} tasks x {d} steps' for c,d in scenarios]);ax.set_title(cache+' cache; trial makespan seconds')
        for i in range(4):
            for j in range(4):ax.text(j,i,f'{m[i,j]:.3f}',ha='center',va='center',color='white' if m[i,j]>.65*m.max() else 'black')
        fig.colorbar(im,ax=ax,shrink=.7)
    save(fig,'checkpoint-latency-heatmap')
    fig,axs=plt.subplots(3,2,figsize=(13,9),layout='constrained');timeline_selection=[];maxend=0
    for col,model in enumerate(['base','trained']):
        tt=records(E/'data'/model/'trials.jsonl');cc=records(E/'data'/model/'calls.jsonl');ss=compressed(E/'data'/model/'scheduler.jsonl.gz')
        gpu=csvrows(E/'analysis'/model/'tables/gpu-samples.csv')
        candidates=[t for t in tt if t['mode']=='sequential' and t['cache']=='warm' and t['concurrency']==4 and t['decisions']==8 and t['instrumented']]
        med={api:statistics.median(t['makespan_seconds'] for t in candidates if t['arm']==api) for api in ['decision','chat']}
        repeat=min(range(5),key=lambda r:sum(abs(t['makespan_seconds']/med[t['arm']]-1) for t in candidates if t['repeat']==r))
        for api,color in [('decision','#1768AC'),('chat','#D07A39')]:
            t=next(t for t in candidates if t['repeat']==repeat and t['arm']==api);maxend=max(maxend,t['makespan_seconds'])
            req=[c for c in cc if c['trial']==t['trial']];first=min(req,key=lambda c:c['start_mono_ns'])
            wall=first['start_wall_ns']-(first['start_mono_ns']-t['start_mono_ns'])
            snapshots=[s for s in ss if t['start_mono_ns']<=s['mono_ns']<=t['end_mono_ns']]
            x=[(s['mono_ns']-t['start_mono_ns'])/1e9 for s in snapshots]
            axs[0,col].step(x,[s['pool']['full_num_used']*.03125 for s in snapshots],where='post',color=color,label=api)
            samples=[g for g in gpu if wall<=int(g['wall_ns'])<=wall+t['makespan_seconds']*1e9]
            for row,field in [(1,'memory_used_mib'),(2,'power_w')]:
                axs[row,col].step([(int(g['wall_ns'])-wall)/1e9 for g in samples],[float(g[field]) for g in samples],where='post',color=color,label=api)
            timeline_selection.append({'checkpoint':model,'api':api,'trial':t['trial'],'repeat':repeat,'selection':'joint closest to Decision/Chat median within this checkpoint; same repeat for endpoints'})
        axs[0,col].set_title(model+'; warm 4 tasks x 8 steps');axs[2,col].set_xlabel('Seconds from trial release')
    for row,label in enumerate(['Active attention KV (MiB)','NVML resident memory (MiB)','NVML board power (W)']):
        low=min(a.get_ylim()[0] for a in axs[row]);high=max(a.get_ylim()[1] for a in axs[row])
        for ax in axs[row]:ax.set_ylabel(label);ax.set_ylim(0 if row==1 else low,high);ax.set_xlim(0,maxend+.05);ax.grid(alpha=.2)
    axs[0,0].legend();save(fig,'gpu-kv-power-timeline');(E/'timeline-selection.json').write_text(json.dumps(timeline_selection,indent=2))
    comparisons=[];rng=np.random.default_rng(20261016)
    for api in ['decision','chat']:
        baseline={(r['source'],r['case']):r for r in casepred['base',api]}
        candidate={(r['source'],r['case']):r for r in casepred['trained',api]}
        assert set(baseline)==set(candidate)
        clusters=collections.defaultdict(list)
        for key,r in baseline.items():clusters[r['group']].append(int(candidate[key]['correct'])-int(r['correct']))
        groups=list(clusters);bootstrap=[]
        for _ in range(10000):
            selected=rng.integers(0,len(groups),len(groups));values=[v for i in selected for v in clusters[groups[i]]];bootstrap.append(np.mean(values))
        comparisons.append({'api':api,'cases':len(baseline),'mechanism_clusters':len(groups),'trained_minus_base_accuracy':float(np.mean([v for vs in clusters.values() for v in vs])),
                            'cluster_bootstrap95':np.percentile(bootstrap,[2.5,97.5]).tolist(),'exploratory':True})
    steps=records(E/'training-steps.jsonl');fig,axs=plt.subplots(1,3,figsize=(15,4.2),layout='constrained')
    for epoch,color in [(0,'#1768AC'),(1,'#5B8E7D'),(2,'#D07A39')]:
        group=[r for r in steps if r['epoch']==epoch];axs[0].plot([r['step'] for r in group],[r['loss'] for r in group],color=color,label=f'epoch{epoch}: '+('CE' if epoch==0 else 'CE+RLCD'),linewidth=1)
    axs[0].set_yscale('symlog',linthresh=1e-5);axs[0].set_xlabel('Training microstep');axs[0].set_ylabel('Recorded objective (symlog)');axs[0].set_title('Different objectives across phases');axs[0].legend(fontsize=8)
    for r in cal:
        b=r['bins'];axs[1].plot([v['mean_confidence'] for v in b],[v['accuracy'] for v in b],'o-',label=f"{r['checkpoint']}, T={r['temperature']}")
    axs[1].plot([0,1],[0,1],'k:',linewidth=1);axs[1].set_xlim(0,1);axs[1].set_ylim(0,1.04);axs[1].set_xlabel('Case mean confidence');axs[1].set_ylabel('Observed accuracy');axs[1].set_title('Reliability; 87 cases, 20 mechanisms');axs[1].legend(fontsize=8)
    axs[2].bar(range(len(cal)),[r['case_nll'] for r in cal],color=['#1768AC','#5B8E7D','#D07A39']);axs[2].set_xticks(range(len(cal)),[f"{r['checkpoint']}\nT={r['temperature']}" for r in cal]);axs[2].set_ylabel('Case NLL (lower is better)');axs[2].set_title('Accuracy gain does not ensure calibration')
    for i,r in enumerate(cal):axs[2].text(i,r['case_nll'],f"{r['case_nll']:.3f}",ha='center',va='bottom')
    for a in axs:a.grid(alpha=.15)
    save(fig,'training-and-calibration')
    (E/'summary.json').write_text(json.dumps({'accuracy':count,'calibration':cal,'paired_accuracy':comparisons,'checkpoint_concurrency_summary':results,'test_cases':87,'independent_units':'mechanism clusters; kernels and option permutations within a group are dependent','test_is_blind':False,'label_basis':'weak first diagnostic, not root cause','temperature':temperature},indent=2))
    print('ANALYSIS_COMPLETE',flush=True)
if __name__=='__main__':main()
