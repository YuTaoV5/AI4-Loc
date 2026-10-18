"""Offline behavioural checks: label boundaries, split leakage, export and training plan."""
import pathlib,json,importlib.util,tempfile,subprocess,sys,copy,threading,http.server,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
data=ROOT/'skills/ai4loc-decision-data';train=ROOT/'skills/ai4loc-decision-finetune'
spec=importlib.util.spec_from_file_location('prepare_dataset',data/'scripts/prepare_dataset.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=[json.loads(x) for x in (data/'assets/reviewed-example.jsonl').read_text(encoding='utf-8').splitlines()]
records,counts=m.validate(rows,m.CLASSES);assert counts=={'train':1,'dev':1,'test':1}
checks=['reviewed_format_accepted']
for name,mutate in [('circular_not_rcu',lambda x:x[1].update(label='rcu_progress')),('group_split_leakage',lambda x:x[1].update(group=x[0]['group'])),('duplicate_input',lambda x:x[1].update(input=x[0]['input'],evidence=x[0]['evidence'],label=x[0]['label'])),('injection_metadata',lambda x:x[0].update(input=x[0]['input']+'\nSCENARIO=UAF'))]:
    bad=copy.deepcopy(rows);mutate(bad)
    try:m.validate(bad,m.CLASSES)
    except ValueError:checks.append(name+'_rejected')
    else:raise AssertionError(name)
archive=ROOT/'data/local-archive';archive.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='decision-skill-check-',dir=archive) as tmp:
    tmp=pathlib.Path(tmp);run=tmp/'run'
    subprocess.run([sys.executable,str(data/'scripts/prepare_dataset.py'),'--input',str(data/'assets/reviewed-example.jsonl'),'--output',str(run)],check=True,capture_output=True)
    public=json.loads((run/'dataset-frozen.json').read_text(encoding='utf-8'));assert all(not {'input','evidence','reviewed_by'}&r.keys() for r in public['records']);checks.append('public_manifest_excludes_log_text')
    subprocess.run([sys.executable,str(train/'scripts/train.py'),'--project-root',str(ROOT),'--run-dir',str(run),'--base',str(tmp/'absent-base'),'--output',str(tmp/'new-model')],check=True,capture_output=True)
    plan=json.loads((run/'training-plan.json').read_text(encoding='utf-8'));assert plan['microsteps']==12 and plan['optimizer_updates']==3 and plan['execute_requested'] is False;assert not (tmp/'new-model').exists();checks.append('plan_does_not_download_load_or_train')
    assert plan['worker_source_validated']
    subprocess.run([sys.executable,str(train/'scripts/train.py'),'--project-root',str(ROOT),'--run-dir',str(run),'--base',str(tmp/'absent-base'),'--output',str(tmp/'new-model'),'--objective','ce'],check=True,capture_output=True)
    ceplan=json.loads((run/'training-plan.json').read_text(encoding='utf-8'));assert ceplan['worker_source_validated'] and ceplan['worker_source_sha256']!=plan['worker_source_sha256'];checks.append('both_ce_and_rlcd_workers_compile_without_torch')
    blocked=subprocess.run([sys.executable,str(train/'scripts/train.py'),'--project-root',str(ROOT),'--run-dir',str(run),'--base',str(tmp/'absent-base'),'--output',str(tmp/'new-model'),'--execute'],capture_output=True)
    assert blocked.returncode!=0 and b'Do not train format examples' in blocked.stderr;checks.append('synthetic_gpu_execution_refused_before_model_import')
    # Verify request schema and content timing on an HTTP stub, not an actual model.
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.send_response(200);self.send_header('Content-Type','application/json' if self.path.endswith('decisions') else 'text/event-stream');self.end_headers()
            if self.path.endswith('decisions'):
                assert all(isinstance(x,dict) and {'name','description'}<=x.keys() for x in body['questions'][0]['options'])
                names=[x['name'] for x in body['questions'][0]['options']];probs={n:(.9 if n=='memory_lifetime' else .1/(len(names)-1)) for n in names}
                self.wfile.write(json.dumps({'answers':{'family':{'choice':'memory_lifetime','probabilities':probs,'prompt_token_ids':[1,2,3]}}}).encode())
            else:
                assert body['chat_template_kwargs']['enable_thinking'] is False and body['max_tokens']==1
                self.wfile.write(b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\ndata: {"choices":[{"delta":{"content":"A"}}]}\n\ndata: [DONE]\n\n')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        subprocess.run([sys.executable,str(train/'scripts/probe.py'),'--base-url',f'http://127.0.0.1:{server.server_port}','--model','stub-only','--output',str(tmp/'probe.json')],check=True,capture_output=True)
        checks.append('probe_protocol_stub_passed_not_model_test')
        stub=tmp/'tokenizer-stub';stub.mkdir();(stub/'transformers.py').write_text('class AutoTokenizer:\n @classmethod\n def from_pretrained(cls,*a,**k):return cls()\n def apply_chat_template(self,*a,**k):return "stub prompt"\n def encode(self,*a,**k):return [1,2,3]\n',encoding='utf-8')
        env=os.environ.copy();env['PYTHONPATH']=str(stub)
        subprocess.run([sys.executable,str(train/'scripts/evaluate.py'),'--run-dir',str(run),'--tokenizer','stub-only','--base-url',f'http://127.0.0.1:{server.server_port}','--model','stub-only','--output',str(tmp/'eval')],check=True,capture_output=True,env=env)
        ev=json.loads((tmp/'eval/summary.json').read_text(encoding='utf-8'));assert all(r['cases']==1 and r['calls']==3 and r['failed_calls']==0 for r in ev['summary'])
        checks.append('evaluator_six_stub_requests_recorded_without_gold_payload')
    finally:server.shutdown();server.server_close()
for name in ['train.py','probe.py','evaluate.py']:
    subprocess.run([sys.executable,str(train/'scripts'/name),'--help'],check=True,capture_output=True)
result={'passed':True,'checks':checks,'gpu_training_executed':False,'real_model_api_calls':0,'scope':'Offline contracts/plan checks and eight local HTTP stub requests only; fake tokenizer for evaluator protocol checks'}
(ROOT/'skills/decision-skills-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
