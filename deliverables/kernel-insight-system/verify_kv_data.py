"""Check source ledgers independently of the canvas rendering and scene builder."""
import pathlib,json,hashlib,gzip,math
HERE=pathlib.Path(__file__).resolve().parent;R=HERE.parents[1]/'research/kv-concurrency-20261016'
read=lambda n:json.load(open(HERE/n,encoding='utf-8'))
data=read('media/kv/animation-data.json')
for name,expected in data['sources'].items():assert hashlib.sha256((R/'data'/name).read_bytes()).hexdigest()==expected
trials={r['trial']:r for r in map(json.loads,(R/'data/trials.jsonl').read_text().splitlines())}
native=[json.loads(x) for x in (R/'data/server-requests.jsonl').read_text().splitlines()]
calls={c['rid']:c for c in map(json.loads,(R/'data/calls.jsonl').read_text().splitlines())}
checked=[]
for scene in data['scenes'].values():
    assert len(scene['arms'])==2 and len({a['repeat'] for a in scene['arms']})==1
    for a in scene['arms']:
        t=trials[a['trial']];ns=[n for n in native if n.get('trial')==a['trial']]
        assert a['duration']==t['makespan_seconds'] and a['questions']==t['questions']
        assert len(a['prefills'])==len(ns)==a['questions']
        assert sum(p['new'] for p in a['prefills'])==sum(n['prompt_tokens']-n['cached_tokens'] for n in ns)==a['new_tokens']
        assert sum(p['cached'] for p in a['prefills'])==sum(n['cached_tokens'] for n in ns)==a['cached_tokens']
        assert all(0<=p['t']<=a['duration']+.002 for p in a['prefills'])
        for c in a['calls']:
            raw=calls[c['client_id']]
            expected=raw['first_content_mono_ns'] if raw['arm']=='chat' else raw['end_mono_ns']
            actual=expected-t['start_mono_ns']
            assert math.isclose(c['ready'],actual/1e9,abs_tol=1e-9)
            assert c['output_tokens']==raw['usage'].get('completion_tokens',0)
        assert sum(c['questions'] for c in a['calls'])==a['questions']
        assert max(o['kv'] for o in a['samples'])==a['peak_kv']
        assert max(o['states'] for o in a['samples'])==a['peak_states']
        assert all(o['t']>=0 and o['kv']>=0 and 0<=o['states']<=32 for o in a['samples'])
    checked.append({'scene':scene['id'],'repeat':scene['repeat'],'trials':[a['trial'] for a in scene['arms']],
                    'timing_matches':True,'prefill_ledger_matches':True,'result_and_output_tokens_match':True})
for gif in read('media/kv/gif-manifest.json'):
    p=HERE/'media/kv'/gif['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==gif['sha256']
    from PIL import Image
    with Image.open(p) as im:
        duration=0
        for i in range(im.n_frames):im.seek(i);duration+=im.info['duration']
        assert im.n_frames==gif['frames']==81 and duration==gif['display_ms']==10000
html=(HERE/'deck.html').read_text(encoding='utf-8')
assert (HERE/'kv_replay.js').read_text(encoding='utf-8') in html
import re
embedded=re.search(r'<script id="kv-replay-data" type="application/json">(.*?)</script>',html,re.S)
assert json.loads(embedded[1])==data
result={'passed':True,'source_hashes_checked':len(data['sources']),'scenes':checked,'gifs_verified':5,
        'embedded_and_external_data_identical':True,'new_model_calls':0}
(HERE/'kv-data-qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
