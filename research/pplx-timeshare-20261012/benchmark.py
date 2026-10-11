"""Frozen sequential full-GPU comparison, using anonymous evaluation workers."""
import argparse,pathlib,json,hashlib,random,shutil,sys,subprocess,time,uuid
p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--arm',choices=['pplx','generic']);a=p.parse_args()
B=pathlib.Path('/opt/kernel-insight');E=B/'experiments/pplx-timeshare-20261012';D=B/'data/evaluation-datasets/stability-v1';F=E/'frozen'
read=lambda x:json.loads(x.read_text());sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
mapping={'memory_uaf':'memory_lifetime','memory_oob':'memory_bounds','usercopy':'memory_bounds','memory_leak':'memory_leak','lock_order':'locking','atomic_sleep':'locking','hung_task':'blocked_task','watchdog':'watchdog_lockup','rcu_stall':'rcu_progress','oom':'oom','healthy':'other_or_no_fault'}
manifest=read(D/'manifest.json');cases=[c for c in manifest['cases'] if c['status']=='ready'];assert len(cases)==60
if a.action=='prepare':
 F.mkdir(exist_ok=False)
 for n in ['boundary_router.py','decision_plugin.py','localization_agent.py']:shutil.copy2((B/'app').resolve()/'scripts'/n,F/n)
 shutil.copy2(E/'boundary-worker.py',F/'boundary-worker.py')
 rng=random.Random(202610120);shared=[{'caseId':c['id'],'repeat':r,'scored':True} for c in cases if c['family'] in mapping for r in range(3 if c['split']=='test' else 1)];rng.shuffle(shared)
 extra=[{'caseId':c['id'],'repeat':0,'scored':False} for c in cases if c['family'] not in mapping];rng.shuffle(extra)
 schedule=[{**r,'arm':arm} for arm in ['pplx','generic'] for r in shared+(extra if arm=='pplx' else [])];assert len(schedule)==121
 protocol={'schema':'pplx-timeshare/v1','registeredAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'seed':202610120,'checkpointRevision':'b01a5cbaca5391f73bd55103d4f27e8982cd5e60','datasetSha256':sha(D/'manifest.json'),'taxonomy':mapping,'cases':[{'caseId':c['id'],'family':c['family'],'split':c['split']} for c in cases],'schedule':schedule,'formalCalls':121,'warmupsExcluded':2,'primary':'9 existing test cases, three dependent repeats per arm, family agreement','secondary':'16 additional mapped train cases, one repeat per arm; 35 PPLX-only unsupported cases unscored','gpuSharedBetweenArms':False,'precision':'BF16','clientConcurrency':1,'questionsPerCall':3,'contextPerQuestion':8192,'runtime':'PPLX official reference Transformers SDPA versus generic SGLang 0.5.21. No CPU offload; runtime/kernel/prompt differences remain. Deployment comparison, not pure weight causal comparison.','order':'PPLX then generic; same randomized shared case/repeat order in both; temporal confounding remains.','genericRadixCache':False,'timeoutSeconds':180,'retries':0,'blind':False,'labelCaveat':'Injection proxy differs from first diagnosis in LOOP/SOFTLOCKUP; stage/reporter/root truth unavailable; natural log symbols retained.','code':{x.name:sha(x) for x in F.glob('*.py')},'experimentCode':{x.name:sha(x) for x in E.glob('*.py')},'productionScoresWritten':False}
 (E/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2));(E/'workspaces').mkdir();(E/'results.json').write_text(json.dumps({'complete':False,'protocolSha256':sha(E/'protocol.json'),'rows':[]}));print('PROTOCOL_FROZEN',sha(E/'protocol.json'));sys.exit()
assert a.arm
protocol=read(E/'protocol.json');assert protocol['datasetSha256']==sha(D/'manifest.json');assert all(sha(F/n)==v for n,v in protocol['code'].items())
sys.path.insert(0,str(F));from localization_agent import Inspector
R=B/'runtime';work=E/'workspaces';prepare=E/('prepare-'+a.arm);prepare.mkdir()
def active():
 s=read(B/'data/state.json');return any(j.get('status') in ['running','queued'] for j in s.get('jobs',[])+s.get('agentBenchmarkRuns',[]))
def invoke(incident):
 w=work/str(uuid.uuid4());w.mkdir();(w/'input.json').write_text(json.dumps({'base':'http://127.0.0.1:'+('30002' if a.arm=='pplx' else '30003'),'incident':incident}))
 cmd=['bwrap','--unshare-user','--unshare-pid','--die-with-parent','--new-session','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/bin','/bin','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--ro-bind','/etc','/etc','--ro-bind',str(R),str(R),'--ro-bind',str(F),'/agent','--bind',str(w),'/work','--dev','/dev','--tmpfs','/tmp','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1','--chdir','/work',str(R/'venv/bin/python'),'/agent/boundary-worker.py']
 with (w/'worker.log').open('w') as log:
  try:
   r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=200);out=read(w/'response.json') if (w/'response.json').exists() else {'status':'failed','error':'worker exit '+str(r.returncode)}
  except subprocess.TimeoutExpired:out={'status':'failed','error':'worker timeout'}
 return w.name,out
warm={'firstDiagnosticLine':1,'lines':[{'line':1,'text':'BUG: KASAN: use-after-free in synthetic_probe'}],'lifetimeEvidence':[],'available':{'log':True,'source':False,'artifacts':False},'evidenceId':'T1'}
wid,out=invoke(warm);(E/('warmup-'+a.arm+'.json')).write_text(json.dumps({'workspaceId':wid,**out}));assert out['status']=='completed'
data=read(E/'results.json');assert not any(r['arm']==a.arm for r in data['rows'])
for ordinal,item in enumerate(protocol['schedule']):
 if item['arm']!=a.arm:continue
 assert not active(),'New task appeared during maintenance; abort and restore'
 c=next(c for c in cases if c['id']==item['caseId']);f=c['files']['agentLog'];raw=(D/f['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==f['sha256'];(prepare/'input.log').write_bytes(raw);incident=Inspector(prepare)._execute('incident',{});incident['evidenceId']='T1';wid,out=invoke(incident);gold=mapping.get(c['family']);family=out.get('answers',{}).get('family',{}).get('choice')
 row={**item,'ordinal':ordinal,'split':c['split'],'injectionFamily':c['family'],'workspaceId':wid,'inputLogSha256':f['sha256'],**out,'gold':gold,'family':family,'correct':out['status']=='completed' and family==gold if item['scored'] else None};data['rows'].append(row);data['complete']=len(data['rows'])==121
 temp=E/'results.tmp';temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));temp.replace(E/'results.json');print(json.dumps({'done':len(data['rows']),'arm':a.arm,'seconds':out.get('seconds'),'status':out['status'],'correct':row['correct']}),flush=True)
 if len(data['rows'])>=4 and all(r['status']=='failed' for r in data['rows'][-4:]):raise RuntimeError('Four consecutive failures; retained and aborting')
