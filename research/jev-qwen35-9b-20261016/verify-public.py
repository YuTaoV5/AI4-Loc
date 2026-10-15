"""Offline checks independent of the figure/report rendering."""
import pathlib,json,gzip,hashlib,collections,sys,math
E=pathlib.Path(__file__).resolve().parent
def lines(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',encoding='utf-8') as f:return [json.loads(x) for x in f]
frozen=json.loads((E/'dataset-frozen.json').read_text(encoding='utf-8'))
for field in ['group','input_sha256']:
    sets={s:{r[field] for r in frozen['records'] if r['split']==s} for s in ['train','dev','test']}
    assert all(not sets[a]&sets[b] for a in sets for b in sets if a!=b),field
result={'split_disjoint':True,'arms':{}}
for manifest,folder in [('PUBLIC_ROOT_SHA256.json',E),('agent32k/SHA256.json',E/'agent32k')]:
    for name,digest in json.loads((E/manifest).read_text()).items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest,name
for arm in ['base','trained']:
    d=E/'data'/arm
    for path,digest in json.loads((d/'SHA256.json').read_text()).items():assert hashlib.sha256((d/path).read_bytes()).hexdigest()==digest,path
    trials=lines(d/'trials.jsonl');calls=lines(d/'calls.jsonl');native=lines(d/'server-requests.jsonl');accuracy=lines(d/'accuracy.jsonl')
    assert len(trials)==112 and sum(r['trial']>=0 for r in calls)==980
    assert sum(r.get('trial',-1)>=0 for r in native)==1330
    assert len(accuracy)==87*3*2 and sum(r.get('trial')==-3 for r in native)==len(accuracy)
    assert all(c['status']=='ok' for c in calls)
    for r in accuracy:
        assert r['correct']==(r['prediction']==r['label'])
        if r['api']=='decision':assert abs(sum(r['probabilities'].values())-1)<1e-5
    for r in lines(d/'answers-and-arrivals.jsonl'):
        if r['arm']=='decision':
            assert r['response']['usage']['completion_tokens']==0
            for a in r['response']['answers'].values():
                assert 'prompt_token_ids' not in a
                assert all(math.isfinite(v) and 0<=v<=1 for v in a['probabilities'].values())
                assert abs(sum(a['probabilities'].values())-1)<1e-5
    runtime=json.loads((d/'runtime.json').read_text());assert runtime['scheduler']['effective_max_running_requests_per_dp']==4
    snapshots=lines(d/'scheduler.jsonl.gz');assert max(len(s['requests']) for s in snapshots)==4
    result['arms'][arm]={'formal_http':980,'internal_questions':1330,'accuracy_http':len(accuracy),'scheduler_snapshots':len(snapshots)}
    repaired=E/'agent32k'/arm
    for a in json.loads((repaired/'isolation-audits.json').read_text()):
        assert a['workspaceAnonymous'] and not any(a[k] for k in ['evaluatorCanaryVisible','hostRootVisible','businessDataVisible','procMounted'])
    agent=json.loads((repaired/'agent-summary.json').read_text());assert len(agent)==6 and all(r['status']=='completed' for r in agent)
    result['arms'][arm]['repaired_agent_reports']=len(agent)
completion=json.loads((E/'agent32k/completion.json').read_text());assert completion['status']=='completed' and completion['restored']
local=(E.parents[1]/'scripts/localization_agent.py').read_text(encoding='utf-8').encode('utf-8')
frozen=json.loads((E/'agent32k/base/agent-source-sha256.json').read_text())
assert hashlib.sha256(local).hexdigest()==frozen['scripts/localization_agent.py'],'Published Agent differs from the tested client'
result['published_agent_matches_tested_source_after_newline_normalization']=True
print(json.dumps(result,indent=2))
(E/'verification.json').write_text(json.dumps(result,indent=2))
