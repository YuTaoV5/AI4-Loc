"""One-command regression + isolated business checks + live benchmark smoke.

Results and exit status are evidence, never a claim of exhaustive GUI coverage.
No credentials are written to reports. Production writes are benchmark trials only.
"""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,sys,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--base',default='http://127.0.0.1:8787');p.add_argument('--analysis-case');p.add_argument('--verified-log');p.add_argument('--source-version');p.add_argument('--repair',action='store_true');p.add_argument('--skip-unit',action='store_true');p.add_argument('--skip-live',action='store_true');a=p.parse_args()
    root=pathlib.Path(__file__).resolve().parents[1];a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    report={'schema':'kernel-website-acceptance/v1','startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'steps':[],'limits':['Browser layout requires separate visual inspection.','Real vmcore and introducing-commit causality are not verified.'],'sourceHashes':{str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [root/'server/index.js',root/'server/analyzer.js',root/'server/agent.js',root/'scripts/localization_agent.py',root/'scripts/website-selfcheck.js']}}
    def run(name,command,timeout=180):
        start=time.monotonic()
        try:
            env={**os.environ,'PYTHONIOENCODING':'utf-8'}
            if name in ['node-regression','python-regression','isolated-business']:
                for key in ['KERNEL_AGENT_MODE','KERNEL_ROUTER_BASE_URL','KERNEL_VERIFIED_SOURCE_REGISTRY']:env.pop(key,None)
            r=subprocess.run(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
            text=r.stdout.decode('utf-8',errors='replace');(a.output/(name+'.log')).write_text(text,encoding='utf-8');row={'name':name,'exitCode':r.returncode,'seconds':round(time.monotonic()-start,3),'log':name+'.log'}
        except subprocess.TimeoutExpired:row={'name':name,'exitCode':124,'seconds':round(time.monotonic()-start,3),'error':'Check timed out'}
        report['steps'].append(row);print(json.dumps(row),flush=True)
    if a.repair:run('service-recovery',[sys.executable,str(root/'scripts/manage-supervisor.py')],90)
    if not a.skip_unit:
        tests=[str(q.relative_to(root)) for q in sorted((root/'tests').glob('*.test.js'))]
        run('node-regression',['node','--test','--experimental-test-isolation=none',*tests])
        run('python-regression',[sys.executable,'-m','unittest','discover','-s','tests','-p','*_test.py'])
    run('isolated-business',['node','scripts/website-selfcheck.js','--isolated','--output',str(a.output/'isolated.json')])
    if not a.skip_live:
        command=['node','scripts/website-selfcheck.js','--base',a.base,'--output',str(a.output/'live.json')]
        if a.analysis_case:command+=['--analysis-case',a.analysis_case]
        if a.source_version:command+=['--source-version',a.source_version]
        run('live-website',command,720)
    if a.verified_log:run('verified-model',['node','scripts/website-selfcheck.js','--isolated','--model-log',a.verified_log,'--output',str(a.output/'verified-model.json')],720)
    for name in ['isolated','live','verified-model']:
        file=a.output/(name+'.json')
        if file.exists():report[name]=json.loads(file.read_text(encoding='utf-8'))
    report['completedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();report['passed']=all(x['exitCode']==0 for x in report['steps'])
    (a.output/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'passed':report['passed'],'report':str(a.output/'acceptance.json')}));return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
