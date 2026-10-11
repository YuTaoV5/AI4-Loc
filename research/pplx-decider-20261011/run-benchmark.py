"""Frozen, isolated public-weight test; never writes production configuration or scores."""
import pathlib,json,hashlib,random,shutil,sys,subprocess,time,uuid,urllib.request
BASE=pathlib.Path('/opt/kernel-insight');EXP=BASE/'experiments/pplx-decider-20261011';DATA=BASE/'data/evaluation-datasets/stability-v1';APP=(BASE/'app').resolve();FROZEN=EXP/'frozen';FROZEN.mkdir(exist_ok=False)
for n in ['boundary_router.py','decision_plugin.py','localization_agent.py']:shutil.copy2(APP/'scripts'/n,FROZEN/n)
shutil.copy2(pathlib.Path(__file__).with_name('boundary-worker.py'),FROZEN/'boundary-worker.py')
sys.path.insert(0,str(FROZEN));from localization_agent import Inspector
manifest=json.loads((DATA/'manifest.json').read_text());cases=[c for c in manifest['cases'] if c['status']=='ready'];assert len(cases)==60
mapping={'memory_uaf':'memory_lifetime','memory_oob':'memory_bounds','usercopy':'memory_bounds','memory_leak':'memory_leak','lock_order':'locking','atomic_sleep':'locking','hung_task':'blocked_task','watchdog':'watchdog_lockup','rcu_stall':'rcu_progress','oom':'oom','healthy':'other_or_no_fault'}
test=[c for c in cases if c['split']=='test'];scored=[c for c in cases if c['family'] in mapping];assert len(test)==9 and len(scored)==25
rng=random.Random(20261011);blocks=[(c['id'],r) for c in scored for r in range(3 if c['split']=='test' else 1)];rng.shuffle(blocks);schedule=[]
for cid,r in blocks:
 arms=['generic','pplx'];rng.shuffle(arms);schedule.extend({'caseId':cid,'repeat':r,'arm':arm,'scored':True} for arm in arms)
extra=[c['id'] for c in cases if c['family'] not in mapping];rng.shuffle(extra);schedule.extend({'caseId':cid,'repeat':0,'arm':'pplx','scored':False} for cid in extra)
protocol={'schema':'pplx-weight-test/v1','registeredAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'model':'perplexity-ai/pplx-decider-v1-27b','revision':'b01a5cbaca5391f73bd55103d4f27e8982cd5e60','seed':20261011,'datasetSha256':hashlib.sha256((DATA/'manifest.json').read_bytes()).hexdigest(),'code':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in FROZEN.iterdir() if f.is_file()},'evaluatorSha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'cases':[{'caseId':c['id'],'family':c['family'],'split':c['split']} for c in cases],'taxonomy':mapping,'schedule':schedule,'primary':'9 existing test cases x 3 repeats x 2 arms, family accuracy; paired case means for descriptive latency','secondary':'16 additional train cases x 1 x 2 arms; 35 protection/refcount cases x 1 PPLX without accuracy scoring','formalCalls':121,'warmupsExcluded':2,'blind':False,'runtime':'generic SGLang BF16 versus PPLX official-reference BF16 with CPU offload; speed cannot isolate weights or represent native SGLang PPLX','gpuShared':True,'input':'same first-diagnostic state and three questions; anonymous worker only','timeoutSeconds':180,'retries':0,'noGroundTruth':'No independent stage/reporter/root-mechanism/introducing-commit labels. Unsupported family mappings remain null.','productionWrites':False}
(EXP/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2));protocolsha=hashlib.sha256((EXP/'protocol.json').read_bytes()).hexdigest();workroot=EXP/'workspaces';workroot.mkdir(exist_ok=False)
def active():
 s=json.loads((BASE/'data/state.json').read_text());return any(j.get('status') in ['running','queued'] for j in s.get('jobs',[])+s.get('agentBenchmarkRuns',[]))
def invoke(incident,arm):
 w=workroot/str(uuid.uuid4());w.mkdir();(w/'input.json').write_text(json.dumps({'base':'http://127.0.0.1:'+('30000' if arm=='generic' else '30002'),'incident':incident}),encoding='utf-8');runtime=BASE/'runtime'
 cmd=['bwrap','--unshare-user','--unshare-pid','--die-with-parent','--new-session','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/bin','/bin','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--ro-bind','/etc','/etc','--ro-bind',str(runtime),str(runtime),'--ro-bind',str(FROZEN),'/agent','--bind',str(w),'/work','--dev','/dev','--tmpfs','/tmp','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1','--chdir','/work',str(runtime/'venv/bin/python'),'/agent/boundary-worker.py']
 with (w/'worker.log').open('w') as f:
  try:
   r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=200);out=json.loads((w/'response.json').read_text()) if (w/'response.json').exists() else {'status':'failed','error':'worker exit '+str(r.returncode)}
  except subprocess.TimeoutExpired:out={'status':'failed','error':'worker timeout'}
 return w.name,out
health=json.load(urllib.request.urlopen('http://127.0.0.1:30002/health'));assert health['ready'] and health['revision']==protocol['revision']
warm={'firstDiagnosticLine':1,'lines':[{'line':1,'text':'BUG: KASAN: use-after-free in synthetic_probe'}],'lifetimeEvidence':[],'available':{'log':True,'source':False,'artifacts':False},'evidenceId':'T1'}
for arm in ['generic','pplx']:
 wid,out=invoke(warm,arm);(EXP/('warmup-'+arm+'.json')).write_text(json.dumps(out));assert out['status']=='completed',(arm,out)
rows=[];prepare=EXP/'prepare-input';prepare.mkdir()
for ordinal,item in enumerate(schedule):
 while active():time.sleep(5)
 case=next(c for c in cases if c['id']==item['caseId']);f=case['files']['agentLog'];raw=(DATA/f['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==f['sha256'];(prepare/'input.log').write_bytes(raw);incident=Inspector(prepare)._execute('incident',{});incident['evidenceId']='T1'
 wid,out=invoke(incident,item['arm']);gold=mapping.get(case['family']);family=out.get('answers',{}).get('family',{}).get('choice');row={**item,'ordinal':ordinal,'split':case['split'],'injectionFamily':case['family'],'workspaceId':wid,'inputLogSha256':f['sha256'],**out,'gold':gold,'family':family,'correct':(out['status']=='completed' and family==gold) if item['scored'] else None};rows.append(row)
 (EXP/'results.json').write_text(json.dumps({'protocolSha256':protocolsha,'complete':len(rows)==len(schedule),'rows':rows},ensure_ascii=False,indent=2));print(json.dumps({'completed':len(rows),'total':len(schedule),'arm':item['arm'],'seconds':out.get('seconds'),'status':out['status'],'correct':row['correct']}),flush=True)
 if len(rows)>=4 and all(r['status']=='failed' for r in rows[-4:]):raise RuntimeError('Four consecutive failures; preserving failures and stopping')
print('BENCHMARK_COMPLETE',len(rows),flush=True)
