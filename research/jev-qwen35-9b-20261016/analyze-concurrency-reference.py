"""Offline reconstruction of latency, allocator occupancy, and request timelines."""
import pathlib,json,gzip,csv,collections,statistics,sys,datetime,html,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
E=pathlib.Path(__file__).resolve().parent
D=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else E/'data'
O=pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else E
O.mkdir(exist_ok=True);(O/'figures').mkdir(exist_ok=True);(O/'tables').mkdir(exist_ok=True)
def read(n):return json.load(open(D/n,encoding='utf-8'))
def rows(n):
    op=gzip.open if n.endswith('.gz') else open
    with op(D/n,'rt',encoding='utf-8') as f:return [json.loads(l) for l in f]
def csvout(n,rs):
    if not rs:return
    keys=list(dict.fromkeys(k for r in rs for k in r))
    with (O/'tables'/n).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,keys);w.writeheader()
        for r in rs:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def avg(v):return float(np.mean(v)) if len(v) else None
def q(v,n):return float(np.percentile(v,n)) if len(v) else None
trials=rows('trials.jsonl');calls=rows('calls.jsonl');native=rows('server-requests.jsonl');obs=rows('scheduler.jsonl.gz');prom=rows('prometheus.jsonl.gz')
T={r['trial']:r for r in trials};C={r['rid']:r for r in calls};N=collections.defaultdict(list)
for r in native:
    if 'client_rid' in r:N[r['client_rid']].append(r)
config=read('model-config.json')['text_config'];runtime=read('runtime.json');audit=read('audit.json')
gpu=[]
with (D/'gpu.csv').open(encoding='utf-8') as f:
    for line in csv.reader(f):
        if len(line)!=9:continue
        at=datetime.datetime.strptime(line[0],'%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        values=[float(v.strip()) for v in line[1:]]
        gpu.append(dict(zip(['wall_ns','memory_used_mib','memory_free_mib','gpu_util_pct','memory_util_pct','temperature_c','power_w','sm_clock_mhz','memory_clock_mhz'],[int(at.timestamp()*1e9),*values])))
csvout('gpu-samples.csv',gpu)
full_layers=sum(t=='full_attention' for t in config['layer_types'])
kvbytes=2*full_layers*config['num_key_value_heads']*config['head_dim']*2
assert kvbytes==32768
flatobs=[];reqobs=[]
for o in obs:
    related={r.get('trial') for r in o['requests'] if r.get('trial',-1)>=0}
    tr=next(iter(related)) if len(related)==1 else None
    flatobs.append({k:v for k,v in o.items() if k not in ['pool','requests']}|o['pool']|{'trial':tr,'batch_requests':len(o['requests']),
                    'active_kv_mib':o['pool']['full_num_used']*kvbytes/2**20,
                    'evictable_kv_mib':o['pool']['full_evictable_size']*kvbytes/2**20})
    for r in o['requests']:reqobs.append({'mono_ns':o['mono_ns'],'event':o['event'],**r})
csvout('scheduler-snapshots.csv',flatobs);csvout('scheduler-requests.csv',reqobs)
for t in trials:
    ss=[s for s in flatobs if t['start_mono_ns']<=s['mono_ns']<=t['end_mono_ns']]
    ns=[r for r in native if r.get('trial')==t['trial']]
    cc=[c for c in calls if c['trial']==t['trial']]
    gw=[g for g in gpu if min(c['start_wall_ns'] for c in cc)<=g['wall_ns']<=max(c['end_wall_ns'] for c in cc)]
    t.update(peak_active_kv_mib=max((s['active_kv_mib'] for s in ss),default=None),
             peak_evictable_kv_mib=max((s['evictable_kv_mib'] for s in ss),default=None),
             peak_mamba_states=max((s['mamba_num_used'] or 0 for s in ss),default=None),
             peak_batch_requests=max((s['batch_requests'] for s in ss),default=None),
             peak_torch_allocated_mib=max((s['torch_allocated_bytes']/2**20 for s in ss),default=None),
             cache_fraction=sum(r['cached_tokens'] for r in ns)/sum(r['prompt_tokens'] for r in ns),
             mean_queue_ms=avg([r['queue_time']*1000 for r in ns]),
             max_queue_ms=max(r['queue_time']*1000 for r in ns),
             mean_call_seconds=avg([c['seconds'] for c in cc]),
             mean_ttft_seconds=avg([c['ttft_seconds'] for c in cc if c['ttft_seconds'] is not None]),
             questions_per_second=t['questions']/t['makespan_seconds'],
             nvml_sample_count=len(gw),nvml_peak_used_mib=max((g['memory_used_mib'] for g in gw),default=None),
             nvml_mean_gpu_util=avg([g['gpu_util_pct'] for g in gw]),nvml_mean_sm_clock_mhz=avg([g['sm_clock_mhz'] for g in gw]))
csvout('trials.csv',trials)
flatcalls=[]
for c in calls:
    rs=N[c['rid']]
    extra={}
    if rs:
        extra={'server_queue_ms_mean':avg([r['queue_time']*1000 for r in rs]),
               'server_prefill_interval_ms_mean':avg([(r['prefill_finished_time']-r['forward_entry_time'])*1000 for r in rs]),
               'server_prompt_tokens':sum(r['prompt_tokens'] for r in rs),
               'server_cached_tokens':sum(r['cached_tokens'] for r in rs),
               'server_ids':[r['id'] for r in rs]}
    flatcalls.append({k:v for k,v in c.items() if k!='usage'}|{'usage_'+k:v for k,v in c['usage'].items()}|extra)
csvout('calls.csv',flatcalls)
csvout('server-requests.csv',[r|{'prefill_interval_ms':(r['prefill_finished_time']-r['forward_entry_time'])*1000} for r in native if 'prefill_finished_time' in r and 'forward_entry_time' in r])
csvout('prometheus-samples.csv',[{k:v for k,v in p.items() if k!='values'}|{k:v for k,v in p['values'].items() if any(x in k.split('{')[0] for x in ['kv_','mamba_','num_running_reqs','num_queue_reqs','num_used_tokens','cache_hit_rate','token_usage'])} for p in prom])
groups=collections.defaultdict(list)
for t in trials:groups[(t['mode'],t['cache'],t['concurrency'],t['decisions'],t['arm'],t['instrumented'])].append(t)
summary=[]
for key,rs in sorted(groups.items()):
    mode,cache,con,d,arm,instrumented=key
    row=dict(mode=mode,cache=cache,concurrency=con,decisions=d,arm=arm,instrumented=instrumented,trials=len(rs))
    for field in ['makespan_seconds','mean_call_seconds','mean_ttft_seconds','peak_active_kv_mib','peak_evictable_kv_mib','peak_mamba_states','peak_torch_allocated_mib','cache_fraction','mean_queue_ms','max_queue_ms','questions_per_second','peak_batch_requests','nvml_peak_used_mib','nvml_mean_gpu_util','nvml_mean_sm_clock_mhz']:
        vv=[r[field] for r in rs if r[field] is not None];row[field]=avg(vv)
        if field in ['makespan_seconds','mean_call_seconds']:row[field+'_p50']=q(vv,50);row[field+'_p95']=q(vv,95)
    summary.append(row)
csvout('summary.csv',summary)
S={(r['mode'],r['cache'],r['concurrency'],r['decisions'],r['arm'],r['instrumented']):r for r in summary}
rng=np.random.default_rng(20261016);comparisons=[]
for cache in ['cold','warm']:
    for con,d in [(1,1),(4,1),(1,8),(4,8)]:
        ds=groups['sequential',cache,con,d,'decision',True];cs=groups['sequential',cache,con,d,'chat',True]
        dp={r['repeat']:r['makespan_seconds'] for r in ds};cp={r['repeat']:r['makespan_seconds'] for r in cs}
        keys=sorted(dp);di=np.array([dp[k] for k in keys]);ch=np.array([cp[k] for k in keys]);idx=rng.integers(0,len(keys),(20000,len(keys)))
        boot=1-di[idx].mean(1)/ch[idx].mean(1)
        comparisons.append({'cache':cache,'concurrency':con,'decisions':d,'paired_repeats':len(keys),
                            'decision_makespan_seconds':float(di.mean()),'chat_makespan_seconds':float(ch.mean()),
                            'decision_makespan_reduction_pct':float((1-di.mean()/ch.mean())*100),
                            'repeat_bootstrap95_low_pct':q(boot*100,2.5),'repeat_bootstrap95_high_pct':q(boot*100,97.5)})
csvout('paired-comparisons.csv',comparisons)
over=[o['observation_us'] for o in obs];poll=[(p['end_mono_ns']-p['start_mono_ns'])/1e6 for p in prom if 'end_mono_ns' in p]
checks={'audit':audit,'kv_bytes_per_token':kvbytes,'scheduler_observations':len(obs),'scheduler_request_observations':len(reqobs),
        'prometheus_samples':len(prom),'observation_us_p50':q(over,50),'observation_us_p95':q(over,95),
        'prometheus_http_ms_p50':q(poll,50),'prometheus_http_ms_p95':q(poll,95),
        'nvml_samples':len(gpu),'nvml_min_used_mib':min(g['memory_used_mib'] for g in gpu),'nvml_max_used_mib':max(g['memory_used_mib'] for g in gpu),
        'nvml_sample_interval_ms_p50':q(np.diff([g['wall_ns'] for g in gpu])/1e6,50),
        'max_observed_batch_requests':max(len(o['requests']) for o in obs),
        'summary':summary,'comparisons':comparisons}
paired_prompts=collections.defaultdict(dict)
for n in native:
    if n.get('trial',-1)<0:continue
    t=T[n['trial']]
    if t['mode']!='sequential':continue
    k=(t['cache'],t['concurrency'],t['decisions'],t['repeat'],t['instrumented'],n['task'],n['question_id'])
    paired_prompts[k][t['arm']]=n['prompt_token_sha256']
assert all(v.get('decision')==v.get('chat') and len(v)==2 for v in paired_prompts.values())
checks['exact_paired_prompt_token_hash_matches']=len(paired_prompts)
(O/'statistics.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'svg.fonttype':'none'})
colors={'decision':'#1768AC','chat':'#DC6B40'}
def savefig(fig,name):
    fig.savefig(O/'figures'/(name+'.svg'),bbox_inches='tight');fig.savefig(O/'figures'/(name+'.png'),bbox_inches='tight');plt.close(fig)
scenarios=[(1,1),(4,1),(1,8),(4,8)];labels=['1 task / 1 step','4 tasks / 1 step','1 task / 8 steps','4 tasks / 8 steps']
fig,axs=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
global_latency_max=max(S['sequential',cache,c,d,a,True]['makespan_seconds'] for cache in ['cold','warm'] for c,d in scenarios for a in ['decision','chat'])
for ax,cache in zip(axs,['cold','warm']):
    mat=np.array([[S['sequential',cache,c,d,a,True]['makespan_seconds'] for a in ['decision','chat']] for c,d in scenarios])
    im=ax.imshow(mat,cmap='Blues',vmin=0,vmax=global_latency_max,aspect='auto');ax.set_xticks([0,1],['Decision\nresult','Chat\none-token completion']);ax.set_yticks(range(4),labels);ax.set_title(cache.title()+' cache: trial makespan (s)')
    for i in range(4):
        for j in range(2):ax.text(j,i,f'{mat[i,j]:.3f}',ha='center',va='center',color='white' if mat[i,j]>global_latency_max*.65 else 'black')
    fig.colorbar(im,ax=ax,shrink=.7,label='seconds')
fig.suptitle('Same prompt tokens, one checkpoint; five repeats per cell');savefig(fig,'01-latency-matrix')
fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
for j,cache in enumerate(['cold','warm']):
    for i,(field,title) in enumerate([('peak_active_kv_mib','Peak active attention KV (MiB)'),('peak_mamba_states','Peak active linear-attention state slots')]):
        ax=axs[i,j];x=np.arange(4)
        for a,offset in [('decision',-.18),('chat',.18)]:
            vals=[S['sequential',cache,c,d,a,True][field] for c,d in scenarios]
            ax.bar(x+offset,vals,width=.34,label=a.title(),color=colors[a])
            for xx,v in zip(x+offset,vals):ax.text(xx,v,f'{v:.1f}',ha='center',va='bottom',fontsize=8)
        ax.set_xticks(x,['1x1','4x1','1x8','4x8']);ax.set_title(cache.title()+': '+title);ax.set_xlabel('tasks x sequential steps');ax.set_ylabel('MiB' if i==0 else 'state slots');ax.margins(y=.18)
for i in range(2):
    limit=max(axs[i,j].get_ylim()[1] for j in range(2))
    for j in range(2):axs[i,j].set_ylim(0,limit)
axs[0,0].legend();fig.suptitle('Logical allocator occupancy; preallocated GPU pools remain resident');savefig(fig,'02-cache-occupancy')
fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
for ax,cache in zip(axs,['cold','warm']):
    for arm in ['decision','chat']:
        selected=[c for c in calls if c['trial']>=0 and (t:=T[c['trial']])['instrumented'] and t['mode']=='sequential' and t['cache']==cache and t['concurrency']==4 and t['decisions']==8 and t['arm']==arm]
        means=[];lo=[];hi=[]
        for step in range(8):
            # Repeat-level averages: four tasks are dependent within a trial.
            vv=[avg([c['seconds'] if arm=='decision' else c['ttft_seconds'] for c in selected if T[c['trial']]['repeat']==r and c['steps']==[step]]) for r in range(5)]
            means.append(avg(vv));lo.append(min(vv));hi.append(max(vv))
        ax.plot(range(1,9),means,'o-',label=arm.title()+(' result' if arm=='decision' else ' TTFT'),color=colors[arm]);ax.fill_between(range(1,9),lo,hi,color=colors[arm],alpha=.12)
    ax.set_title(cache.title()+' cache, four concurrent tasks');ax.set_xlabel('Sequential decision step (changed options)');ax.set_ylabel('Seconds; band = repeat min/max');ax.set_xticks(range(1,9));ax.grid(alpha=.2)
axs[0].legend();savefig(fig,'03-step-response')
fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
for ax,cache in zip(axs,['cold','warm']):
    for arm in ['decision','chat']:
        selected=[n for n in native if n.get('trial',-1)>=0 and (t:=T[n['trial']])['instrumented'] and t['mode']=='sequential' and t['cache']==cache and t['concurrency']==4 and t['decisions']==8 and t['arm']==arm]
        values=[]
        for step in range(8):
            ns=[n for n in selected if n['question_id']=='family'+str(step)]
            values.append(sum(n['cached_tokens'] for n in ns)/sum(n['prompt_tokens'] for n in ns)*100)
        ax.plot(range(1,9),values,'o-' if arm=='decision' else 'x--',label=arm.title(),color=colors[arm],linewidth=3 if arm=='decision' else 1.5)
    ax.set_ylim(0,105);ax.set_xticks(range(1,9));ax.set_xlabel('Decision step');ax.set_ylabel('Cached / prompt tokens (%)');ax.set_title(cache.title()+' condition; realized prefix reuse');ax.grid(alpha=.2)
axs[0].legend();savefig(fig,'06-realized-prefix-hits')
fig,axs=plt.subplots(3,2,figsize=(14,9),layout='constrained')
representatives=[]
for j,arm in enumerate(['decision','chat']):
    candidates=groups['sequential','warm',4,8,arm,True];med=statistics.median(t['makespan_seconds'] for t in candidates);t=min(candidates,key=lambda t:abs(t['makespan_seconds']-med));representatives.append(t['trial'])
    start=t['start_mono_ns'];ss=[o for o in flatobs if start<=o['mono_ns']<=t['end_mono_ns']+50e6]
    xx=[(o['mono_ns']-start)/1e9 for o in ss]
    axs[0,j].step(xx,[o['active_kv_mib'] for o in ss],where='post',label='active KV');axs[0,j].step(xx,[o['evictable_kv_mib'] for o in ss],where='post',label='evictable KV',alpha=.7);axs[0,j].set_ylabel('Attention KV (MiB)');axs[0,j].set_title(f'{arm.title()}: warm 4 tasks x 8 steps, trial {t["trial"]}')
    axs[1,j].step(xx,[o['mamba_num_used'] for o in ss],where='post',label='active state slots',color='#5B8E7D');axs[1,j].set_ylabel('Linear-attention state slots')
    for c in calls:
        if c['trial']!=t['trial']:continue
        a=(c['start_mono_ns']-start)/1e9;b=(c['end_mono_ns']-start)/1e9
        axs[2,j].broken_barh([(a,b-a)],(c['task']-.33,.66),facecolors=colors[arm],alpha=.7)
        marker=c['end_mono_ns'] if arm=='decision' else c['first_content_mono_ns']
        axs[2,j].plot((marker-start)/1e9,c['task'],'k.',ms=3)
    axs[2,j].set_yticks(range(4));axs[2,j].set_ylabel('Task');axs[2,j].set_xlabel('Seconds from synchronized trial start')
    for i in range(3):axs[i,j].grid(alpha=.15);axs[i,j].set_xlim(0,t['makespan_seconds']+.05)
common_end=max(T[i]['makespan_seconds'] for i in representatives)+.05
common_kv=max(max(s['active_kv_mib'],s['evictable_kv_mib']) for s in flatobs if s.get('trial') in representatives)
common_states=max(s['mamba_num_used'] or 0 for s in flatobs if s.get('trial') in representatives)
for j in range(2):
    axs[0,j].set_ylim(0,common_kv*1.08);axs[1,j].set_ylim(0,common_states*1.1)
    for i in range(3):axs[i,j].set_xlim(0,common_end)
axs[0,0].legend();savefig(fig,'04-detailed-timeline')
fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
for ax,cache in zip(axs,['cold','warm']):
    x=np.arange(2)
    for offset,mode in [(-.18,'sequential'),(.18,'batch8')]:
        vals=[S[mode,cache,c,8,'decision',True]['makespan_seconds'] for c in [1,4]]
        ax.bar(x+offset,vals,width=.34,label='8 sequential HTTP calls' if mode=='sequential' else '1 HTTP call, 8 questions',color='#1768AC' if mode=='sequential' else '#5B8E7D')
        for xx,v in zip(x+offset,vals):ax.text(xx,v,f'{v:.3f}s',ha='center',va='bottom')
    ax.set_xticks(x,['1 task','4 concurrent tasks']);ax.set_title(cache.title()+' cache');ax.set_ylabel('Trial makespan (s)');ax.margins(y=.18)
axs[0].legend();fig.suptitle('Batch8 still scores eight independently rendered prompts');savefig(fig,'05-batch-versus-sequential')
checks['representative_timeline_trials']=representatives
(O/'statistics.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps({'trials':len(trials),'formal_calls':audit['formal_http_calls'],'observations':len(obs),'max_actual_batch':checks['max_observed_batch_requests'],'comparisons':comparisons},indent=2))
