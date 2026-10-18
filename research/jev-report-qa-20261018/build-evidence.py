"""Collect report Q&A evidence from frozen public results; never call a model."""
import pathlib,json,csv,hashlib
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];used=set()
def read(name):
    p=ROOT/name;used.add(p)
    if p.suffix=='.csv':return list(csv.DictReader(p.open(encoding='utf-8-sig')))
    return json.loads(p.read_text(encoding='utf-8'))
paper=read('research/decision-localization-20261011/results/statistics.json')
cpu=read('research/pplx-decider-20261011/results/statistics.json')
gpu=read('research/pplx-timeshare-20261012/results/statistics.json')
q9=read('research/jev-qwen35-9b-20261016/summary.json')
perf=read('research/jev-qwen35-9b-20261016/tables/checkpoint-concurrency-summary.csv')
q27=read('research/kv-concurrency-20261016/statistics.json')
agent=read('research/jev-qwen35-9b-20261016/tables/agent32k-aggregate.csv')
train=read('research/jev-qwen35-9b-20261016/training-complete.json')
protocol=read('research/jev-qwen35-9b-20261016/training-protocol.json')
env=read('research/jev-qwen35-9b-20261016/training-environment.json')
rows=[]
def pair(study,comparison,a,b,n,scope):
    rows.append(dict(study=study,comparison=comparison,left_seconds=a,right_seconds=b,left_faster_percent=100*(b-a)/b,repeats_per_arm=n,scope=scope))
pair('20261011','Decision3 vs Chat3 JSON',paper['aggregate']['D3-first']['meanSeconds'],paper['aggregate']['C3-first']['meanSeconds'],27,'9 unique cases; thinking disabled; different prompt lengths and output structure')
pair('20261012','generic Decision vs PPLX fullGPU',gpu['primary']['generic']['meanSeconds'],gpu['primary']['pplx']['meanSeconds'],27,'9 unique cases; same A100; different inference engines; fixed stage order')
for cp in ['base','trained']:
    for cache in ['cold','warm']:
        for c,d in [(1,1),(4,1),(1,8),(4,8)]:
            rr=[r for r in perf if r['checkpoint']==cp and r['cache']==cache and r['mode']=='sequential' and int(r['concurrency'])==c and int(r['decisions'])==d and r['instrumented']=='True']
            aa={r['arm']:r for r in rr};assert len(aa)==2
            pair('20261016-9B',f'{cp} {cache} {c}x{d} Decision vs one-token Chat',float(aa['decision']['makespan_seconds']),float(aa['chat']['makespan_seconds']),5,'batch makespan; matched full prompt token IDs; no causal accuracy measured in performance trials')
for cache in ['cold','warm']:
    rr={r['arm']:r for r in q27['summary'] if r['mode']=='sequential' and r['cache']==cache and r['concurrency']==4 and r['decisions']==8 and r['instrumented']}
    pair('20261016-27B',f'{cache} 4x8 Decision vs one-token Chat',rr['decision']['makespan_seconds'],rr['chat']['makespan_seconds'],5,'27B independent experiment; cannot combine with 9B accuracy')
assert train['steps']==396 and train['trainable_parameters']==5308416
assert [(r['correct'],r['cases']) for r in q9['accuracy'] if r['source']=='all' and r['api']=='decision']==[(66,87),(78,87)]
assert all(int(x['cases'])==3 and int(x['code_location_hits'])==2 for x in agent)
result={'date':'2026-10-18','scope':'Offline synthesis of frozen studies; no new inference, deployment or training. Not a current server health check.',
 'latency_pairs':rows,'qwen9_accuracy':q9['accuracy'],'qwen9_calibration':q9['calibration'],
 'agent32k':agent,'training':train,'training_protocol':protocol,'trainable_parameter_fraction':env['trainable_parameters']/env['total_parameters'],
 'pplx_full_gpu_primary':gpu['primary'],'historical_cpu_statistics':cpu,
 'source_files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(used)],
 'external_nanojev_tested_in_this_project':False,'dedicated_typesafe_jev_tested':False,
 'comparability':'Each study retains its own task, input, engine, cache, split and denominator. Differences are not causal attribution to model architecture.'}
(HERE/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
with (HERE/'实验对照汇总.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'passed':True,'source_files':len(used),'paired_conditions':len(rows),'new_model_calls':0},ensure_ascii=False))
