"""Small frozen end-to-end check using the deployed localization agent.

Exploratory three-case check, not a new root-cause-accuracy benchmark. The
evaluator loads gold AFTER each bubblewrap-isolated worker has exited.
"""
import pathlib,os,json,subprocess,sys,hashlib,time,shutil,urllib.request,urllib.error
E=pathlib.Path(__file__).resolve().parent;RUN=pathlib.Path(os.environ['AI4LOC_RUN_DIR'])
APP=pathlib.Path('/opt/kernel-insight/app').resolve()
CASES=['corrupt_uaf_kmalloc','lock_mutex_abba','lkdtm_HUNG_TASK']
def main():
    original=APP;frozen=E/'project-frozen'
    if not frozen.exists():
        (frozen/'scripts').mkdir(parents=True)
        for p in (original/'scripts').glob('*.py'):shutil.copy2(p,frozen/'scripts'/p.name)
        (frozen/'tools/kernel-lab').mkdir(parents=True)
        shutil.copy2(original/'tools/kernel-lab/dataset_contract.py',frozen/'tools/kernel-lab/dataset_contract.py')
        p=frozen/'scripts/localization_agent.py';s=p.read_text()
        old="'messages':messages,'temperature':0,'max_tokens':2400}"
        assert s.count(old)==1
        s=s.replace(old,"'messages':messages,'temperature':0,'max_tokens':2400,'chat_template_kwargs':{'enable_thinking':False}}")
        before="calls=message.get('tool_calls',[])"
        assert s.count(before)==1
        s=s.replace(before,"calls=message.get('tool_calls') or []")
        p.write_text(s)
    # Preserve a detailed HTTP rejection body (the deployed agent retains only
    # HTTPError's summary). An explicitly separate diagnostic, never a trial.
    previous=E/'base/agent-chat-only/workspaces'
    samples=list(previous.glob('*/model-requests.jsonl')) if previous.exists() else []
    if samples and os.environ.get('AI4LOC_CHECKPOINT_ARM')=='trained':
        payload=json.loads(samples[0].read_text().splitlines()[0])['payload']
        req=urllib.request.Request('http://127.0.0.1:30003/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=90) as response:body=response.read().decode();status=response.status
        except urllib.error.HTTPError as error:status=error.code;body=error.read().decode()
        (RUN/'agent-compatibility-probe.private.json').write_text(json.dumps({'status':status,'body':body,'counting':'one separate diagnostic request, excluded from performance and accuracy'},indent=2))
    freeze={'cases':CASES,'profile':'log+source','max_model_calls':6,'timeout_seconds':150,
            'purpose':'exploratory end-to-end source-location check; not independent mechanism/introducing-commit gold',
            'variants':['chat-only','decision-boundary-chat-root'],
            'project_release':str(original),'compatibility_change':'Frozen copy: explicit enable_thinking=false; normalize OpenAI tool_calls:null to empty list. Both checkpoint/agent arms use identical changes; original failed 8k and 32k checks preserved separately.',
            'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (frozen/'scripts').glob('*.py')}}
    (RUN/'agent-protocol.json').write_text(json.dumps(freeze,indent=2))
    summary=[]
    for variant in freeze['variants']:
        env=os.environ.copy()
        for name in ['KERNEL_DECISION_BASE_URL','KERNEL_DECISION_POLICY','KERNEL_BOUNDARY_ROUTER','KERNEL_DECISION_API']:env.pop(name,None)
        if variant!='chat-only':env.update(KERNEL_BOUNDARY_ROUTER='decision',KERNEL_DECISION_BASE_URL='http://127.0.0.1:30003')
        out=RUN/('agent-'+variant)
        command=['/opt/kernel-insight/runtime/venv/bin/python',str(frozen/'scripts/run-localization-benchmark.py'),
                 '--dataset','/opt/kernel-insight/data/evaluation-datasets/stability-v1','--output',str(out),
                 '--cases',','.join(CASES),'--profiles','log+source','--model','AI4Loc-Qwen9B',
                 '--base','http://127.0.0.1:30003/v1','--transport','openai','--eager-boundary','--source-triage','--max-calls','6','--timeout','150']
        with (RUN/('agent-'+variant+'.log')).open('w') as log:
            p=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=660)
        assert p.returncode==0,'Agent evaluator failed; preserve logs'
        result=json.loads((out/'results.json').read_text())
        for r in result['runs']:
            # Model messages, source windows, and natural-language evidence remain private.
            metrics=r['metrics'];counts={k:v for k,v in metrics.items() if k!='requests'}
            counts['usage']=[x.get('usage') for x in metrics.get('requests',[]) if x.get('usage')]
            summary.append({'variant':variant,'case':r['caseId'],'status':r['status'],'scores':r['scores'],'metrics':counts,'error':r.get('error')})
    (RUN/'agent-summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    print('AGENT_CHECK_COMPLETE',len(summary),flush=True)
if __name__=='__main__':main()
