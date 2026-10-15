"""Turn measured requests/allocator observations into offline comparative replays.

No interpolation of token computation. Native prefill-completion counters settle
at their recorded times; KV/state values are last observations, never estimates.
"""
import pathlib,json,gzip,csv,statistics,hashlib,itertools
HERE=pathlib.Path(__file__).resolve().parent
R=HERE.parents[1]/'research/kv-concurrency-20261016'
def load(n):
    op=gzip.open if n.endswith('.gz') else open
    with op(R/'data'/n,'rt',encoding='utf-8') as f:return [json.loads(x) for x in f]
def build():
    trials=load('trials.jsonl');calls=load('calls.jsonl');native=load('server-requests.jsonl');observations=load('scheduler.jsonl.gz')
    gpu=list(csv.DictReader((R/'tables/gpu-samples.csv').open(encoding='utf-8-sig')))
    stats=json.load(open(R/'statistics.json'));summary={(r['mode'],r['cache'],r['concurrency'],r['decisions'],r['arm'],r['instrumented']):r for r in stats['summary']}
    conditions=lambda arm,c,d,cache,mode='sequential':(mode,cache,c,d,arm,True)
    def key(t):return (t['mode'],t['cache'],t['concurrency'],t['decisions'],t['arm'],t['instrumented'])
    by= { (key(t),t['repeat']):t for t in trials }
    def trialdata(t,label):
        cs=[c for c in calls if c['trial']==t['trial']];ns=[n for n in native if n.get('trial')==t['trial']]
        origin=t['start_mono_ns'];wall_origin=min(c['start_wall_ns']-(c['start_mono_ns']-origin) for c in cs)
        samples=[]
        for o in observations:
            if origin<=o['mono_ns']<=t['end_mono_ns']:
                samples.append({'t':(o['mono_ns']-origin)/1e9,'kv':o['pool']['full_num_used']/16,
                    'evictable':o['pool']['full_evictable_size']/16,'states':o['pool']['mamba_num_used'],
                    'cuda_mib':o['torch_allocated_bytes']/2**20,'reserved_mib':o['torch_reserved_bytes']/2**20,
                    'queued':o['queued'],'event':o['event'],'batch':len(o['requests'])})
        req=[]
        for n in ns:
            req.append({'t':(n['prefill_finished_time']*1e9-wall_origin)/1e9,
                        'start':(n['forward_entry_time']*1e9-wall_origin)/1e9,
                        'new':n['prompt_tokens']-n['cached_tokens'],'cached':n['cached_tokens'],
                        'prompt':n['prompt_tokens'],'queue_ms':n['queue_time']*1000,
                        'task':n['task'],'question':n['question_id'],'server_id':n['id']})
        crows=[{'task':c['task'],'start':(c['start_mono_ns']-origin)/1e9,
                'end':(c['end_mono_ns']-origin)/1e9,
                'ready':((c['first_content_mono_ns'] if c['arm']=='chat' else c['end_mono_ns'])-origin)/1e9,
                'questions':len(c['steps']),'output_tokens':c['usage'].get('completion_tokens',0),
                'client_id':c['rid'],'steps':c['steps']} for c in cs]
        gs=[{'t':(int(g['wall_ns'])-wall_origin)/1e9,'mib':float(g['memory_used_mib'])} for g in gpu
            if wall_origin-150e6<=int(g['wall_ns'])<=wall_origin+t['makespan_seconds']*1e9]
        assert len(req)==t['questions'] and len(crows)==t['calls'] and samples
        return {'label':label,'trial':t['trial'],'repeat':t['repeat'],'arm':t['arm'],'cache':t['cache'],'mode':t['mode'],
                'tasks':t['concurrency'],'steps':t['decisions'],'questions':t['questions'],'duration':t['makespan_seconds'],
                'samples':samples,'prefills':sorted(req,key=lambda n:n['t']),'calls':crows,'gpu':gs,
                'mean_duration':summary[key(t)]['makespan_seconds'],'peak_kv':max(s['kv'] for s in samples),
                'peak_states':max(s['states'] for s in samples),'new_tokens':sum(n['new'] for n in req),
                'cached_tokens':sum(n['cached'] for n in req)}
    scenes={}
    def scene(name,left,right,labels,title,meaning):
        # One common repeat index, chosen jointly closest to each arm's median.
        med={k:statistics.median(by[k,r]['makespan_seconds'] for r in range(5)) for k in [left,right]}
        repeat=min(range(5),key=lambda r:sum(abs(by[k,r]['makespan_seconds']-med[k])/med[k] for k in [left,right]))
        arms=[trialdata(by[k,repeat],label) for k,label in zip([left,right],labels)]
        end=max(a['duration'] for a in arms)
        points=sorted(set([0,end]+[a['duration'] for a in arms]+[c['ready'] for a in arms for c in a['calls']]))
        scenes[name]={'id':name,'title':title,'meaning':meaning,'repeat':repeat,'end':end,'points':points,'arms':arms}
    for c,d,cache in itertools.product([1,4],[1,8],['cold','warm']):
        scene(f'dchat-{c}x{d}-{cache}',conditions('decision',c,d,cache),conditions('chat',c,d,cache),
              ['Decision · 完整概率返回','Chat · 首个内容token'],f'{c}任务 × {d}步 · '+('预热条件' if cache=='warm' else '冷条件'),
              '同一权重与相同prompt；Chat关闭thinking、最多输出1 token。')
    scene('seqbatch-4x8-warm',conditions('decision',4,8,'warm'),conditions('decision',4,8,'warm','batch8'),
          ['顺序8次HTTP / 每任务','批量1次HTTP含8题 / 每任务'],'四任务：顺序八步 vs 一次八题',
          '都是32题；批量不是一次prefill，用户要等该HTTP内8题全部完成。')
    scene('coldwarm-d4x8',conditions('decision',4,8,'cold'),conditions('decision',4,8,'warm'),
          ['冷条件 · trial前flush','预热条件 · 不同选项prime'],'四任务八步：冷条件 vs 预热条件',
          '预热操作不保证命中；实际cached/prompt token另行记录。')
    sources={n:hashlib.sha256((R/'data'/n).read_bytes()).hexdigest() for n in ['protocol.json','calls.jsonl','trials.jsonl','server-requests.jsonl','scheduler.jsonl.gz']}
    result={'schema':'ai4loc-measured-replay/v1','sources':sources,'scenes':scenes,
            'gif_scenes':['dchat-1x1-cold','dchat-1x8-warm','dchat-4x8-warm','seqbatch-4x8-warm','coldwarm-d4x8'],
            'clock':'Each independent trial aligns its synchronized client start to t=0; common seconds scale within pair.',
            'token_accounting':'Uncached=request prompt_tokens-cached_tokens; settled only at native prefill_finished_time. Not FLOPs, unique tokens, generated tokens, or continuous per-token timestamps.',
            'memory':'Last scheduler observations; before first observation unknown; after completion hold final observed value, no new samples implied.',
            'summary_unit':'Playback=one jointly selected actual repeat; panel mean=5-trial mean; no averaging traces.',
            'gpu_sampling':'NVML approximately100ms; latest preceding measurement, not instantaneous allocator query.',
            'gif_clock':'80 uniform model-time intervals over 8 seconds display +2 seconds hold. Same speed for both arms; printed t is actual model seconds.'}
    out=HERE/'media/kv';out.mkdir(parents=True,exist_ok=True)
    (out/'animation-data.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (out/'replay-provenance.json').write_text(json.dumps({k:v for k,v in result.items() if k!='scenes'}|{'scene_trials':{k:[a['trial'] for a in v['arms']] for k,v in scenes.items()}},ensure_ascii=False,indent=2),encoding='utf-8')
    print('MEASURED_REPLAYS',len(scenes), 'bytes',(out/'animation-data.json').stat().st_size)
    return result
if __name__=='__main__':build()
