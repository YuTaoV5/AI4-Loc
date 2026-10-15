"""Allowlisted Agent32k results; full tool/API evidence retained privately."""
import pathlib,json,gzip,csv,tarfile,hashlib,shutil
E=pathlib.Path(__file__).resolve().parent;P=E/'public';P.mkdir(exist_ok=False)
completion=json.loads((E/'completion.json').read_text());assert completion['status']=='completed' and completion['restored']
for n in ['completion.json','restoration.json']:shutil.copy2(E/n,P/n)
for model in ['base','trained']:
    src=E/model;dest=P/model;dest.mkdir()
    for n in ['agent-summary.json','agent-protocol.json','experimental-command.json','model-config.json','completion.json']:shutil.copy2(src/n,dest/n)
    info=json.loads((src/'server-info.private.json').read_text());keys=['version','dtype','context_length','mem_fraction_static','max_running_requests','max_mamba_cache_size','effective_max_running_requests_per_dp','memory_usage','tool_call_parser','reasoning_parser']
    (dest/'runtime.json').write_text(json.dumps({'frontend':{k:info[k] for k in keys if k in info},'scheduler':{k:info['internal_states'][0][k] for k in keys if k in info['internal_states'][0]}},indent=2))
    shutil.copy2(src/'gpu.log',dest/'gpu.csv')
    with gzip.open(dest/'scheduler.jsonl.gz','wt') as out:
        for f in src.glob('scheduler.*.jsonl'):
            for line in f.open():out.write(line)
    with gzip.open(dest/'server-requests.jsonl.gz','wt') as out:
        allowed=['id','finish_reason','prompt_tokens','completion_tokens','cached_tokens','cached_tokens_details',
                 'reasoning_tokens','num_retractions','forward_entry_time','prefill_finished_time','queue_time',
                 'e2e_latency','first_token_latency','request_received_ts','api_server_dispatch_finish_ts',
                 'request_finished_ts','response_sent_to_client_ts']
        for f in (src/'request-metrics').glob('*'):
            for line in f.open():
                r=json.loads(line);clean={k:r[k] for k in allowed if k in r}
                if 'request_parameters' in r:clean['parameters_sha256']=hashlib.sha256(r['request_parameters'].encode()).hexdigest()
                out.write(json.dumps(clean)+'\n')
    audits=[]
    for f in src.glob('agent-*/workspaces/*/isolation-audit.json'):
        r=json.loads(f.read_text());assert r['workspaceAnonymous']
        assert not any(r[k] for k in ['evaluatorCanaryVisible','hostRootVisible','businessDataVisible','procMounted'])
        audits.append({'workspace_id':f.parent.name,**r})
    assert len(audits)==6
    (dest/'isolation-audits.json').write_text(json.dumps(audits,indent=2))
    # No inputs/source/gold canary mounted; labels are loaded only after exit.
    source_hashes={str(f.relative_to(E/'project-frozen')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (E/'project-frozen').rglob('*.py')}
    (dest/'agent-source-sha256.json').write_text(json.dumps(source_hashes,indent=2))
old=E.with_name('jev-qwen35-9b-20261016-agent32k');(P/'initial-32k-failure').mkdir()
for n in ['manual-stop.json','completion.json','restoration.json']:shutil.copy2(old/n,P/'initial-32k-failure'/n)
partial=[]
for f in old.glob('base/agent-*/results.json'):
    for r in json.loads(f.read_text())['runs']:partial.append({'variant':f.parent.name,'case':r['caseId'],'status':r['status'],'error':r.get('error'),'model_requests':r['metrics']['modelRequests'],'seconds':r['metrics']['localizationSeconds']})
(P/'initial-32k-failure'/'partial-results.json').write_text(json.dumps(partial,indent=2))
manifest={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in P.rglob('*') if f.is_file()};(P/'SHA256.json').write_text(json.dumps(manifest,indent=2))
with tarfile.open(E/'public.tgz','w:gz') as t:t.add(P,arcname='.')
print('AGENT32K_PUBLIC_READY',len(manifest),flush=True)
