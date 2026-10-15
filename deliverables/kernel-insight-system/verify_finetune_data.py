"""Audit replay aggregates, native request coverage, measurement units and hashes."""
import pathlib,json,hashlib,math
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
D=json.loads((HERE/'media/finetune/animation-data.json').read_text(encoding='utf-8'))
P=json.loads((HERE/'media/finetune/provenance.json').read_text(encoding='utf-8'))
for s in P['sources']:assert hashlib.sha256((ROOT/s['path']).read_bytes()).hexdigest()==s['sha256'],s['path']
assert len(D['training'])==396 and [r['step'] for r in D['training']]==list(range(1,397))
assert len(D['cases'])==87 and sum(c['before'] for c in D['cases'])==66 and sum(c['after'] for c in D['cases'])==78
assert len(D['scenes'])==16
requests=0
for key,s in D['scenes'].items():
    cp,cross,cache=key.split('-');c,d=map(int,cross.split('x'))
    assert len(s['arms'])==2 and s['points'][0]==0
    for arm in s['arms']:
        assert len(arm['prefills'])==len(arm['calls'])==c*d
        assert all(p['new']>=0 and p['cached']>=0 for p in arm['prefills'])
        assert all(0<=call['start']<=call['ready']<=call['end']<=arm['duration'] for call in arm['calls'])
        assert all(0<=x['t']<=arm['duration'] and x['kv']>=0 for x in arm['samples'])
        row=next(r for r in D['summary'] if r['checkpoint']==cp and r['mode']=='sequential' and r['cache']==cache and int(r['concurrency'])==c and int(r['decisions'])==d and r['arm']==arm['api'] and r['instrumented']=='True')
        assert int(row['trials'])==5 and float(row['makespan_seconds'])==arm['mean']
        requests+=len(arm['calls'])
assert len(D['agent'])==4 and all(int(x['completed'])==3 and int(x['code_location_hits'])==2 for x in D['agent'])
result={'passed':True,'source_hashes_verified':len(P['sources']),'training_steps':396,'paired_cases':87,'accuracy_before':66,'accuracy_after':78,'runtime_conditions':16,'replayed_http_requests':requests,'kv_token_bytes':32768,'new_model_calls':0,'full_agent_runs':12}
(HERE/'finetune-data-qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
