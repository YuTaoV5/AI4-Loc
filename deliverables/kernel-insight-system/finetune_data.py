"""Frozen 9B training observations and independently clocked inference trials."""
import pathlib,json,csv,gzip,hashlib,statistics,itertools
HERE=pathlib.Path(__file__).resolve().parent
R=HERE.parents[1]/'research/jev-qwen35-9b-20261016'
USED=set()
def read(path):
    p=R/path;USED.add(p)
    if p.suffix=='.csv':return list(csv.DictReader(p.open(encoding='utf-8-sig')))
    if '.jsonl' in p.name:
        op=gzip.open if p.suffix=='.gz' else open
        with op(p,'rt',encoding='utf-8') as f:return [json.loads(x) for x in f]
    return json.loads(p.read_text(encoding='utf-8'))
def build():
    USED.update(R/n for n in ['dataset-frozen.json','training-protocol.json','train.py','REPORT.md','README.md'])
    training=read('training-steps.jsonl');complete=read('training-complete.json')
    env=read('training-environment.json');cal=read('calibration.json')
    pred={k:read(f'tables/{k}-decision-case-predictions.csv') for k in ['base','trained']}
    cases=[]
    for a,b in zip(pred['base'],pred['trained']):
        assert a['case']==b['case']
        cases.append({'label':a['label'],'source':a['source'],'before':a['correct']=='True','after':b['correct']=='True'})
    summary=read('tables/checkpoint-concurrency-summary.csv');scenes={}
    for checkpoint in ['base','trained']:
        trials=read(f'data/{checkpoint}/trials.jsonl');calls=read(f'data/{checkpoint}/calls.jsonl')
        native=read(f'data/{checkpoint}/server-requests.jsonl');obs=read(f'data/{checkpoint}/scheduler.jsonl.gz')
        gpu=read(f'analysis/{checkpoint}/tables/gpu-samples.csv')
        def make(t):
            cs=[x for x in calls if x['trial']==t['trial']]
            ns=[x for x in native if x.get('trial')==t['trial']]
            origin=t['start_mono_ns'];wall=min(x['start_wall_ns']-(x['start_mono_ns']-origin) for x in cs)
            samples=[{'t':(x['mono_ns']-origin)/1e9,'kv':x['pool']['full_num_used']/32,'states':x['pool']['mamba_num_used'],'queued':x['queued']} for x in obs if origin<=x['mono_ns']<=t['end_mono_ns']]
            gs=[{'t':(int(x['wall_ns'])-wall)/1e9,'mib':float(x['memory_used_mib']),'power':float(x['power_w'])} for x in gpu if wall-150e6<=int(x['wall_ns'])<=wall+t['makespan_seconds']*1e9]
            cr=[{'task':x['task'],'start':(x['start_mono_ns']-origin)/1e9,'end':(x['end_mono_ns']-origin)/1e9,'ready':((x['first_content_mono_ns'] if x['arm']=='chat' else x['end_mono_ns'])-origin)/1e9} for x in cs]
            pr=[{'t':(x['prefill_finished_time']*1e9-wall)/1e9,'new':x['prompt_tokens']-x['cached_tokens'],'cached':x['cached_tokens'],'queue_ms':x['queue_time']*1000} for x in ns]
            assert len(pr)==t['questions'] and len(cr)==t['calls'] and samples
            mean=next(s for s in summary if s['checkpoint']==checkpoint and s['mode']=='sequential' and s['cache']==t['cache'] and int(s['concurrency'])==t['concurrency'] and int(s['decisions'])==t['decisions'] and s['arm']==t['arm'] and s['instrumented']=='True')
            return {'trial':t['trial'],'api':t['arm'],'duration':t['makespan_seconds'],'mean':float(mean['makespan_seconds']),'mean_kv':float(mean['peak_active_kv_mib']),'mean_states':float(mean['peak_mamba_states']),'samples':samples,'gpu':gs,'calls':cr,'prefills':pr}
        for c,d,cache in itertools.product([1,4],[1,8],['cold','warm']):
            arms={a:{t['repeat']:t for t in trials if t['arm']==a and t['mode']=='sequential' and t['cache']==cache and t['concurrency']==c and t['decisions']==d and t['instrumented']} for a in ['decision','chat']}
            med={a:statistics.median(t['makespan_seconds'] for t in ts.values()) for a,ts in arms.items()}
            rep=min(range(5),key=lambda k:sum(abs(arms[a][k]['makespan_seconds']-med[a])/med[a] for a in arms))
            aa=[make(arms[a][rep]) for a in ['decision','chat']];end=max(a['duration'] for a in aa)
            key=f'{checkpoint}-{c}x{d}-{cache}'
            scenes[key]={'title':f'{"微调后" if checkpoint=="trained" else "基座"} · {c}任务×{d}步 · {"预热" if cache=="warm" else "冷条件"}','repeat':rep,'tasks':c,'steps':d,'end':end,'arms':aa,'points':sorted(set([0,end]+[x['ready'] for a in aa for x in a['calls']]))}
    result={'schema':'ai4loc-finetune-replay/v1','training':training,'complete':complete,'environment':env,'cases':cases,'calibration':cal,'summary':summary,'agent':read('tables/agent32k-aggregate.csv'),'scenes':scenes}
    out=HERE/'media/finetune';out.mkdir(exist_ok=True)
    (out/'animation-data.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    ledger={'sources':[{'path':p.relative_to(HERE.parents[1]).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(USED)],'selection':'Within each checkpoint/condition, common repeat closest jointly to the two medians; all 5 trials remain in summary. Across checkpoints these are independent trials, never a single synchronized run.','time':'Actual trial clocks aligned at client start. Last observed KV/state/NVML values; unknown before first sample. Native prefill token counts settle at completion, no continuous token interpolation.','training':'396 microstep observations; loss is CE in epoch0 and CE+RLCD thereafter, so not directly comparable across phases. Initial elapsed includes first-step compilation. 343.689s completion includes export, not initial load.','illustrations':'LoRA/RLCD and bar reveals use teaching steps, not measured forward/backward timing.','privacy':'No original log text, credentials, private full payloads or model weights.'}
    (out/'provenance.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
if __name__=='__main__':build()
