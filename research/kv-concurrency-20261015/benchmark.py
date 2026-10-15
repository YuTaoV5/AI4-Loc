"""Same rendered prompts: native Decision probability scoring vs streaming Chat.

Run on the loopback-only experimental server. Dataset labels are never read.
Raw evidence stays private; public exports are created separately.
"""
import asyncio, pathlib, json, time, random, hashlib, itertools, sys, subprocess
import aiohttp
E = pathlib.Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:30003'
MODEL = 'Qwen3.8-27B-SystemOne'
sha = lambda b: hashlib.sha256(b).hexdigest()
def write(name, obj): (E/name).write_text(json.dumps(obj, indent=2, ensure_ascii=False))
def active():
    s = json.load(open('/opt/kernel-insight/data/state.json'))
    return any(x.get('status') in ['queued','running'] for k in ['jobs','agentBenchmarkRuns'] for x in s.get(k, []))
OPTIONS = ['memory_lifetime','memory_bounds','locking','blocked_task','watchdog_lockup','rcu_progress','oom','other_or_no_fault','driver_io','filesystem','network','scheduler']
QUESTION = 'Which fault family best describes the FIRST diagnostic in the supplied kernel log?'
def question(step):
    # Eight distinct ordered sets; the diagnostic question and log stay unchanged.
    names = [OPTIONS[(step+j) % len(OPTIONS)] for j in range(5)]
    return {'id': 'family'+str(step), 'type':'choice', 'question':QUESTION,
            'options':[{'name':n,'description':n.replace('_',' ')} for n in names]}
def rendered(text, q):
    return text+'\n\nQuestion: '+q['question']+'\n'+'\n'.join(chr(65+i)+': '+o['name']+' - '+o['description'] for i,o in enumerate(q['options']))+'\nAnswer with the letter of one option only.'
async def call(session, arm, text, steps, rid, trial, task):
    qs = [question(s) for s in steps]
    if arm == 'decision':
        path = '/v1/decisions'
        payload = {'model':MODEL,'input':text,'questions':qs,'temperature':1,'prompt_format_version':1}
    else:
        assert len(qs)==1
        path = '/v1/chat/completions'
        payload = {'model':MODEL, 'messages':[{'role':'user','content':rendered(text,qs[0])}],
                   'temperature':0, 'max_tokens':1, 'stream':True,
                   'stream_options':{'include_usage':True}, 'chat_template_kwargs':{'enable_thinking':False}}
    row = {'rid':rid,'trial':trial,'task':task,'arm':arm,'steps':steps,'payload_sha256':sha(json.dumps(payload,sort_keys=True).encode()),
           'start_wall_ns':time.time_ns(),'start_mono_ns':time.monotonic_ns()}
    events=[]; chunks=[]; usage={}; response=None; first_content=None; first_body=None
    try:
        async with session.post(BASE+path,json=payload,headers={'X-Request-ID':rid}) as r:
            row['headers_mono_ns']=time.monotonic_ns();row['http_status']=r.status
            if arm=='decision':
                async for chunk in r.content.iter_any():
                    t=time.monotonic_ns()
                    if first_body is None:first_body=t
                    chunks.append(chunk);events.append({'mono_ns':t,'bytes':len(chunk)})
                response=json.loads(b''.join(chunks)); usage=response.get('usage',{})
                assert r.status==200,response
                assert len(response['answers'])==len(qs)
                for q in qs:
                    ans=response['answers'][q['id']];assert abs(sum(ans['probabilities'].values())-1)<1e-5
                    assert ans['choice'] in [o['name'] for o in q['options']]
                assert usage.get('completion_tokens',0)==0
            else:
                async for line in r.content:
                    t=time.monotonic_ns()
                    if first_body is None:first_body=t
                    line=line.decode().strip()
                    if not line.startswith('data: '):continue
                    data=line[6:]
                    if data=='[DONE]':events.append({'mono_ns':t,'done':True});continue
                    obj=json.loads(data);events.append({'mono_ns':t,'data':obj})
                    if obj.get('usage'):usage=obj['usage']
                    for c in obj.get('choices',[]):
                        content=c.get('delta',{}).get('content')
                        if content:
                            if first_content is None:first_content=t
                            chunks.append(content)
                response={'text':''.join(chunks)}
                assert r.status==200 and first_content is not None,(r.status,response)
                row['valid_letter']=response['text'].strip() in list('ABCDE')
        row['status']='ok'
    except Exception as error: row['status']='error';row['error']=repr(error)
    row.update(end_mono_ns=time.monotonic_ns(),end_wall_ns=time.time_ns(),first_body_mono_ns=first_body,first_content_mono_ns=first_content,usage=usage)
    row['seconds']=(row['end_mono_ns']-row['start_mono_ns'])/1e9
    row['ttft_seconds']=(first_content-row['start_mono_ns'])/1e9 if first_content else None
    row['first_body_seconds']=(first_body-row['start_mono_ns'])/1e9 if first_body else None
    with (E/'calls.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    (E/'raw'/f'{rid}.json').write_text(json.dumps({'payload':payload,'response':response,'events':events}))
    if row['status']!='ok':raise RuntimeError(row)
    return row
async def monitor(session, stop, trial):
    # Gauges are scheduler-update snapshots, not a synchronous allocator query.
    with (E/'metrics.jsonl').open('a') as f:
        while not stop.is_set():
            a=time.monotonic_ns()
            try:
                async with session.get(BASE+'/metrics') as r:text=await r.text()
                f.write(json.dumps({'trial':trial,'start_mono_ns':a,'end_mono_ns':time.monotonic_ns(),'wall_ns':time.time_ns(),'text':text})+'\n');f.flush()
            except Exception as e:f.write(json.dumps({'trial':trial,'error':repr(e)})+'\n')
            try:await asyncio.wait_for(stop.wait(),timeout=.05)
            except asyncio.TimeoutError:pass
async def main():
    assert not active()
    (E/'raw').mkdir(exist_ok=True)
    manifest=json.load(open('/opt/kernel-insight/data/evaluation-datasets/stability-v1/manifest.json'))
    # Use only input paths/hashes, without labels, splits, case names or answers.
    inputs=[]
    for c in manifest['cases']:
        if c.get('status')!='ready':continue
        f=c['files']['agentLog'];p=pathlib.Path('/opt/kernel-insight/data/evaluation-datasets/stability-v1')/f['path']
        b=p.read_bytes();assert sha(b)==f['sha256']
        if len(b)>3000:inputs.append({'source_sha256':sha(b),'text':b.decode('utf-8','replace')[:6000]})
        if len(inputs)==4:break
    assert len(inputs)==4
    write('inputs.private.json',inputs)
    cells=[{'arm':arm,'concurrency':c,'decisions':d,'cache':cache,'mode':'sequential','repeat':r,'instrumented':True}
           for r,arm,c,d,cache in itertools.product(range(5),['decision','chat'],[1,4],[1,8],['cold','warm'])]
    cells += [{'arm':'decision','concurrency':c,'decisions':8,'cache':cache,'mode':'batch8','repeat':r,'instrumented':True}
              for r,c,cache in itertools.product(range(5),[1,4],['cold','warm'])]
    # Matched instrumentation sensitivity subset, same payloads, hooks/polling off.
    cells += [{'arm':arm,'concurrency':c,'decisions':1,'cache':'cold','mode':'sequential','repeat':r,'instrumented':False}
              for r,arm,c in itertools.product(range(3),['decision','chat'],[1,4])]
    rng=random.Random(20261015);rng.shuffle(cells)
    protocol={'schema':'ai4loc-kv-concurrency/v1','frozen_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'seed':20261015,
              'schedule':cells,'model':MODEL,'port':30003,'input_sha256':[sha(x['text'].encode()) for x in inputs],
              'data_source':'four existing agent logs; first eligible manifest order; first 6000 Unicode characters; no labels passed',
              'question':QUESTION,'options':[question(i) for i in range(8)],'warm_step':11,
              'cold':'flush once before trial, sequential calls may reuse prefix within trial',
              'warm':'flush then prime each task stem with different option set step11, excluded from formal results',
              'chat':'exact Decision v1 user prompt, thinking=false, max_tokens=1, temperature=0; actual first nonempty content arrival',
              'decision':'temperature1 next-token label normalization; full probability response latency, TTFT not applicable',
              'sampling':'Prometheus requested 50ms plus HTTP cost; scheduler snapshots every run/result boundary; NVML requested100ms',
              'accuracy':'not an accuracy study; option sets may omit correct class; no accuracy claims',
              'code_sha256':{p.name:sha(p.read_bytes()) for p in E.glob('*.py')}}
    write('protocol.json',protocol);print('FROZEN',sha((E/'protocol.json').read_bytes()),len(cells),flush=True)
    timeout=aiohttp.ClientTimeout(total=180)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        from transformers import AutoTokenizer
        tok=AutoTokenizer.from_pretrained('/root/gpufree-data/systemone/models/Qwen3.8-27B',local_files_only=True)
        checks=[]
        for task in range(4):
            q=question(0)
            async with session.post(BASE+'/v1/decisions',json={'input':inputs[task]['text'],'questions':[q],
                                    'temperature':1,'return_prompt_token_ids':True}) as r:
                obj=await r.json();assert r.status==200,obj
            ids=obj['answers'][q['id']]['prompt_token_ids']
            chat=tok.apply_chat_template([{'role':'user','content':rendered(inputs[task]['text'],q)}],
                                         tokenize=False,add_generation_prompt=True,enable_thinking=False)
            expected=tok.encode(chat,add_special_tokens=False)
            assert ids==expected,'Decision and Chat prompt token sequences differ'
            checks.append({'task':task,'prompt_tokens':len(ids),'exact_token_match':True,
                           'token_ids_sha256':sha(json.dumps(ids).encode())})
        write('prompt-equivalence.json',checks)
        assert list(E.glob('scheduler.*.jsonl')) and not (E/'scheduler.errors').exists(),'Missing/failed scheduler hook'
        for arm in ['decision','chat']:
            await call(session,arm,inputs[0]['text'],[0],'warmup-'+arm,-1,0)
        for idx,cell in enumerate(cells):
            assert not active(),'Live user task appeared; stop and restore'
            async with session.post(BASE+'/flush_cache') as r:
                flush_text=await r.text();assert r.status==200,flush_text
            if cell['instrumented']:(E/'trace-disabled').unlink(missing_ok=True)
            else:(E/'trace-disabled').touch()
            if cell['cache']=='warm':
                for task in range(cell['concurrency']):await call(session,cell['arm'],inputs[task]['text'],[11],f'prime-{idx}-{task}',-2,task)
            stop=asyncio.Event();mon=asyncio.create_task(monitor(session,stop,idx)) if cell['instrumented'] else None
            await asyncio.sleep(.15)
            gate=asyncio.Event()
            async def taskrun(task):
                await gate.wait(); rows=[]
                chunks=[list(range(8))] if cell['mode']=='batch8' else [[i] for i in range(cell['decisions'])]
                for step,steps in enumerate(chunks):
                    rows.append(await call(session,cell['arm'],inputs[task]['text'],steps,f'r{idx}-t{task}-s{step}',idx,task))
                return rows
            tasks=[asyncio.create_task(taskrun(t)) for t in range(cell['concurrency'])]
            started=time.monotonic_ns();gate.set();results=await asyncio.gather(*tasks);ended=time.monotonic_ns()
            await asyncio.sleep(.15);stop.set()
            if mon:await mon
            row={**cell,'trial':idx,'start_mono_ns':started,'end_mono_ns':ended,'makespan_seconds':(ended-started)/1e9,
                 'task_seconds':[sum(x['seconds'] for x in rs) for rs in results],
                 'calls':sum(len(rs) for rs in results),'questions':cell['concurrency']*cell['decisions']}
            with (E/'trials.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            print(json.dumps({'done':idx+1,'total':len(cells),**cell,'seconds':row['makespan_seconds']}),flush=True)
    write('benchmark-complete.json',{'complete':True,'trials':len(cells)})
if __name__=='__main__':asyncio.run(main())
