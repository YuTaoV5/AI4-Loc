"""Independent checks of frozen code, accounting, probabilities and raw archive."""
import pathlib,json,hashlib,gzip,tarfile,sys
E=pathlib.Path(__file__).resolve().parent
ROOT=E.parents[1]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def lines(path):return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
results=[]
for date in ['20261015','20261016']:
    B=E.parent/('kv-concurrency-'+date);D=B/'data'
    manifest=json.load(open(D/'SHA256.json'))
    assert all(sha(D/n)==v for n,v in manifest.items()),'Public source data checksum'
    protocol=json.load(open(D/'protocol.json'))
    assert all(sha(B/n)==v for n,v in protocol['code_sha256'].items()),'Frozen executed code mismatch'
    calls=lines(D/'calls.jsonl');trials=lines(D/'trials.jsonl');native=lines(D/'server-requests.jsonl')
    formal=[c for c in calls if c['trial']>=0]
    assert len(trials)==112 and len(formal)==980 and sum(t['questions'] for t in trials)==1330
    assert len([r for r in native if r.get('trial',-1)>=0])==1330
    assert len({r['id'] for r in native})==len(native)
    assert all(c['status']=='ok' and c['http_status']==200 for c in calls)
    answers=lines(D/'answers-and-arrivals.jsonl')
    for r in answers:
        if r['arm']=='decision':
            assert r['response']['usage'].get('completion_tokens',0)==0
            for a in r['response']['answers'].values():
                probs=a['probabilities'];assert len(probs)==5 and abs(sum(probs.values())-1)<1e-6
                assert a['choice'] in probs and 'prompt_token_ids' not in a
        else:assert r['response']['text'].strip() in 'ABCDE'
    with gzip.open(D/'scheduler.jsonl.gz','rt') as f:
        observations=[json.loads(x) for x in f]
    assert all(r['pool']['full_num_used']>=0 and r['pool']['full_available_size']>=0 and r['pool']['full_evictable_size']>=0 for r in observations)
    assert all(r['pool']['full_num_used']+r['pool']['full_available_size']+r['pool']['full_evictable_size']==r['kv_capacity'] for r in observations)
    archive=json.load(open(B/'archive.json'));raw=ROOT/'data/local-archive'/('kv-concurrency-'+date)/archive['file']
    checked=False
    if raw.exists():
        assert raw.stat().st_size==archive['bytes'] and sha(raw)==archive['sha256']
        actual={}
        with tarfile.open(raw,'r:gz') as tar:
            expected=json.load(tar.extractfile('retained-files.json'))
            for member in tar:
                if not member.isfile() or member.name=='retained-files.json':continue
                assert pathlib.PurePosixPath(member.name).name not in ['original-process.private.json','lease.private.json']
                f=tar.extractfile(member);h=hashlib.sha256()
                for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
                actual[member.name]=h.hexdigest()
        assert actual==expected and len(actual)+1==archive['files_including_manifest'];checked=True
    results.append({'date':date,'public_source_files':len(manifest),'formal_http_calls':980,'formal_server_questions':1330,
                    'frozen_code_matches':True,'all_probabilities_and_answers_valid':True,'allocator_accounting_valid':True,
                    'private_archive_verified':checked,'private_files_checked':archive['files_including_manifest'] if checked else None})
(E/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
