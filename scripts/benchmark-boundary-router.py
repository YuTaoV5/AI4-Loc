"""Paired same-checkpoint finite triage benchmark, randomized order, all test cases."""
import argparse,json,pathlib,random,statistics,sys,time
from boundary_router import decide_boundary,chat_boundary
from decision_plugin import DecisionClient
from localization_agent import Inspector
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools/kernel-lab'))
from dataset_contract import resolve

GOLD={'memory_uaf':'memory_lifetime','memory_oob':'memory_bounds','memory_leak':'memory_leak','lock_order':'locking','atomic_sleep':'locking','hung_task':'blocked_task','watchdog':'watchdog_lockup','rcu_stall':'rcu_progress','oom':'oom','healthy':'other_or_no_fault','usercopy':'memory_bounds'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--base',default='http://127.0.0.1:30000');p.add_argument('--model',default='Qwen3.8-27B-SystemOne');p.add_argument('--repeats',type=int,default=3);a=p.parse_args()
    a.output.mkdir(exist_ok=False,parents=True);m=json.loads((a.dataset/'manifest.json').read_text());cases=[c for c in m['cases'] if c['status']=='ready' and c['split']=='test']
    # Warm both APIs on a synthetic non-benchmark fixture; exclude from reported latency.
    warm=a.output/'warmup';warm.mkdir();(warm/'input.log').write_text('BUG: KASAN: use-after-free in sample+0x1/0x2\n');incident=Inspector(warm).execute('incident',{})
    for mode in ['decision','chat']:
        try:
            if mode=='decision':value=decide_boundary(DecisionClient(a.base,warm),incident)
            else:value=chat_boundary(a.base,a.model,incident)
            (warm/(mode+'.json')).write_text(json.dumps(value))
        except Exception as exc:(warm/(mode+'.json')).write_text(json.dumps({'error':str(exc)}))
    jobs=[(rep,c,mode) for rep in range(a.repeats) for c in cases for mode in ['decision','chat']];random.Random(20261008).shuffle(jobs);rows=[]
    for i,(rep,c,mode) in enumerate(jobs):
        work=a.output/('sample-%03d'%i);work.mkdir();(work/'input.log').write_bytes(resolve(a.dataset,c['files']['agentLog']).read_bytes());incident=Inspector(work).execute('incident',{})
        began=time.monotonic();error=None;value=None
        try:value=decide_boundary(DecisionClient(a.base,work),incident) if mode=='decision' else chat_boundary(a.base,a.model,incident)
        except Exception as exc:error=str(exc)
        (work/'response.json').write_text(json.dumps({'value':value,'error':error},ensure_ascii=False,indent=2))
        gold=GOLD.get(c['family']);rows.append({'caseId':c['id'],'repeat':rep,'mode':mode,'seconds':round(time.monotonic()-began,4),'gold':gold,'family':value.get('family') if value else None,'correct':bool(value and value.get('family')==gold),'error':error,'workspace':work.name})
        result={'schema':'boundary-paired-benchmark/v1','model':a.model,'seed':20261008,'repeats':a.repeats,'labelScope':'family from existing evaluator taxonomy; stage/reporter have no independent manually adjudicated labels','rows':rows,'aggregate':{}}
        for variant in ['decision','chat']:
            group=[r for r in rows if r['mode']==variant];seconds=sorted(r['seconds'] for r in group)
            if group:result['aggregate'][variant]={'total':len(group),'errors':sum(bool(r['error']) for r in group),'accuracy':sum(r['correct'] for r in group)/len(group),'meanSeconds':statistics.mean(seconds),'medianSeconds':statistics.median(seconds),'p95Seconds':seconds[min(len(seconds)-1,int(.95*len(seconds)))],'totalSeconds':sum(seconds)}
        (a.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(i+1,mode,c['id'],rows[-1]['correct'],rows[-1]['seconds'],error,flush=True)
    print(result['aggregate'],flush=True)
if __name__=='__main__':main()
