"""Server-side allowlist export. Never publishes logs, prompts, env or accounts."""
import pathlib,json,hashlib,time,gzip,shutil,collections,os
from transformers import AutoTokenizer
from benchmark import rendered
ROOT=pathlib.Path(__file__).resolve().parent
E=pathlib.Path(os.environ['AI4LOC_RUN_DIR']);P=E/'public';P.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(n,x):(P/n).write_text(json.dumps(x,indent=2,ensure_ascii=False))
def lines(p):
    with p.open() as f:
        for line in f:yield json.loads(line)
def jsonl(n,rows):
    op=gzip.open if n.endswith('.gz') else open
    with op(P/n,'wt',encoding='utf-8') as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False)+'\n')
for n in ['protocol.json','provenance.json','prompt-equivalence.json','experimental-command.json','completion.json','restoration.json','model-config.json']:
    if (E/n).exists():shutil.copy2(E/n,P/n)
shutil.copy2(E/'accuracy.jsonl',P/'accuracy.jsonl')
for name in ['agent-summary.json','agent-protocol.json']:
    shutil.copy2(E/name,P/name)
s=json.load(open(E/'server-info.private.json'));inner=s['internal_states'][0]
keys=['version','dtype','kv_cache_dtype','mem_fraction_static','max_running_requests','max_mamba_cache_size','mamba_full_memory_ratio','mamba_ssm_dtype','mamba_radix_cache_strategy','mamba_track_interval','mamba_max_states_per_path','context_length','disable_radix_cache','chunked_prefill_size','max_prefill_tokens','attention_backend','linear_attn_backend','disable_overlap_schedule','enable_metrics','max_total_num_tokens','memory_usage','effective_max_running_requests_per_dp','startup_time']
save('runtime.json',{'frontend':{k:s[k] for k in keys if k in s},'scheduler':{k:inner[k] for k in keys if k in inner}})
calls=list(lines(E/'calls.jsonl'));trials=list(lines(E/'trials.jsonl'))
jsonl('calls.jsonl',calls);jsonl('trials.jsonl',trials)
tok=AutoTokenizer.from_pretrained('/root/gpufree-data/systemone/models/Qwen3.5-9B',local_files_only=True)
cache={}
def tokenhash(text,templated=False):
    key=(text,templated)
    if key not in cache:
        if not templated:text=tok.apply_chat_template([{'role':'user','content':text}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        ids=tok.encode(text,add_special_tokens=False);cache[key]=sha(json.dumps(ids).encode())
    return cache[key]
lookup=collections.defaultdict(list);responses=[]
for call in calls:
    raw=json.load(open(E/'raw'/(call['rid']+'.json')));p=raw['payload']
    if call['arm']=='decision':
        items=[(q['id'],rendered(p['input'],q)) for q in p['questions']]
    else:items=[('family'+str(call['steps'][0]),p['messages'][0]['content'])]
    for qid,text in items:lookup[tokenhash(text)].append((call,qid))
    # Only finite answer distributions or one-letter Chat output, no source text.
    responses.append({'rid':call['rid'],'trial':call['trial'],'arm':call['arm'],'response':raw['response'],
                      'arrivals':[{'mono_ns':v['mono_ns'],'bytes':v.get('bytes'),
                                   'content': ''.join(c.get('delta',{}).get('content','') or '' for c in v.get('data',{}).get('choices',[])),
                                   'done':v.get('done',False)} for v in raw['events']]})
jsonl('answers-and-arrivals.jsonl',responses)
accuracy=list(lines(E/'accuracy.jsonl'))
for r in accuracy:
    raw=json.load(open(E/'accuracy-raw'/(r['rid']+'.json')));payload=raw['request']
    prompt=rendered(payload['input'],payload['questions'][0]) if r['api']=='decision' else payload['messages'][0]['content']
    call={'rid':r['rid'],'trial':-3,'task':None,'start_wall_ns':r['start_wall_ns'],'end_wall_ns':r['end_wall_ns']}
    lookup[tokenhash(prompt)].append((call,'family'))
keep=['id','finish_reason','prompt_tokens','completion_tokens','cached_tokens','cached_tokens_details','reasoning_tokens','num_retractions','forward_entry_time','prefill_finished_time','queue_time','e2e_latency','first_token_latency','request_received_ts','api_server_dispatch_finish_ts','request_finished_ts','response_sent_to_client_ts']
native=[];mapping={};unmatched=[]
for file in sorted((E/'request-metrics').glob('*')):
    for obj in lines(file):
        params=json.loads(obj['request_parameters']);ids=params.get('input_ids')
        key=sha(json.dumps(ids).encode()) if ids is not None else tokenhash(params['text'],True)
        at=obj.get('request_received_ts',0)*1e9
        choices=[(c,q) for c,q in lookup.get(key,[]) if c['start_wall_ns']<=at<=c['end_wall_ns']]
        match_rule='strict_client_interval'
        if not choices:
            choices=[(c,q) for c,q in lookup.get(key,[]) if c['start_wall_ns']-2e6<=at<=c['end_wall_ns']+2e6]
            match_rule='2ms_clock_tolerance'
        row={k:obj[k] for k in keep if k in obj};row['prompt_token_sha256']=key
        if len(choices)==1:
            c,q=choices[0];row.update(client_rid=c['rid'],trial=c['trial'],task=c['task'],question_id=q,matching_rule=match_rule)
            mapping[obj['id']]={'client_rid':c['rid'],'trial':c['trial'],'task':c['task'],'question_id':q}
        else:row['matching_candidates']=len(choices);unmatched.append({'id':obj['id'],'candidates':len(choices)})
        native.append(row)
jsonl('server-requests.jsonl',native)
def scheduler():
    for file in sorted(E.glob('scheduler.*.jsonl')):
        for row in lines(file):
            for req in row['requests']:req.update(mapping.get(req['rid'],{}))
            yield row
jsonl('scheduler.jsonl.gz',scheduler())
shutil.copy2(E/'gpu.log',P/'gpu.csv')
def metrics():
    for row in lines(E/'metrics.jsonl'):
        values={}
        for line in row.get('text','').splitlines():
            if line.startswith('sglang:') and not any(suffix in line.split('{')[0] for suffix in ['_bucket','_created']):
                name,value=line.rsplit(' ',1)
                try:values[name]=float(value)
                except ValueError:pass
        yield {k:v for k,v in row.items() if k!='text'}|{'values':values}
jsonl('prometheus.jsonl.gz',metrics())
formal=[c for c in calls if c['trial']>=0];formal_native=[r for r in native if r.get('trial',-1)>=0]
expected=sum(t['questions'] for t in trials)
audit={'formal_http_calls':len(formal),'formal_question_evaluations':expected,'matched_formal_server_requests':len(formal_native),
       'all_server_requests':len(native),'unmatched_server_requests':unmatched,'excluded_client_calls':len(calls)-len(formal),
       'trial_count':len(trials),'all_http_ok':all(c['status']=='ok' for c in calls),
       'chat_valid_letters':sum(c.get('valid_letter',False) for c in formal if c['arm']=='chat'),
       'formal_chat_calls':sum(c['arm']=='chat' for c in formal),
       'exact_link_rule':'SHA256 of complete prompt token IDs + strict client interval; only if no candidate allow +/-2ms; exactly one candidate required. Strict first prevents adjacent identical Decision/Chat prompts being falsely ambiguous.',
       'full_input_logs_or_env_exported':False}
assert len(trials)==112 and len(formal_native)==expected and audit['all_http_ok'],audit
audit['accuracy_http_calls']=len(accuracy)
audit['matched_accuracy_requests']=sum(r.get('trial')==-3 for r in native)
assert audit['matched_accuracy_requests']==len(accuracy),audit
save('audit.json',audit)
files={str(p.relative_to(P)):sha(p.read_bytes()) for p in P.rglob('*') if p.is_file()};save('SHA256.json',files)
print(json.dumps(audit,indent=2),flush=True)
