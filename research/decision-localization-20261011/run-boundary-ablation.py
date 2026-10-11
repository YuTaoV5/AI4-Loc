"""Frozen, randomized paired interface/window/question-count ablation. No production writes."""
import pathlib,json,sys,os,shutil,hashlib,random,subprocess,time,uuid,platform
BASE=pathlib.Path('/opt/kernel-insight');EXP=BASE/'experiments/paper-20261011';DATA=BASE/'data/evaluation-datasets/stability-v1';APP=(BASE/'app').resolve();EXP.mkdir(mode=0o700,exist_ok=False)
FROZEN=EXP/'frozen';FROZEN.mkdir();
for n in ['boundary_router.py','decision_plugin.py','localization_agent.py']:
 shutil.copy2(APP/'scripts'/n,FROZEN/n)
shutil.copy2(pathlib.Path(__file__).with_name('boundary-worker.py'),FROZEN/'boundary-worker.py')
sys.path.insert(0,str(FROZEN));from boundary_router import QUESTIONS;from localization_agent import Inspector
manifest=json.loads((DATA/'manifest.json').read_text());cases=[c for c in manifest['cases'] if c['status']=='ready' and c['split']=='test'];assert len(cases)==9
variants=[{'id':'D3-first','mode':'decision','window':'first','questions':3},{'id':'C3-first','mode':'chat','window':'first','questions':3},{'id':'D1-first','mode':'decision','window':'first','questions':1},{'id':'D3-tail','mode':'decision','window':'tail','questions':3},{'id':'C3-tail','mode':'chat','window':'tail','questions':3}]
seed=20261011;rng=random.Random(seed);schedule=[]
blocks=[(c['id'],r) for c in cases for r in range(3)];rng.shuffle(blocks)
for cid,r in blocks:
 order=variants.copy();rng.shuffle(order)
 schedule.extend({'caseId':cid,'repeat':r,'variant':v['id']} for v in order)
protocol={'schema':'paper-boundary-ablation/v1','registeredAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'evaluatorSha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'seed':seed,'repeats':3,'cases':[c['id'] for c in cases],'variants':variants,'schedule':schedule,'datasetSha256':hashlib.sha256((DATA/'manifest.json').read_bytes()).hexdigest(),'frozenCode':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FROZEN.iterdir() if p.is_file()},'primaryContrasts':['C3-first minus D3-first latency','D3-first minus D1-first latency','C3-tail minus D3-tail latency'],'secondaryContrasts':['first versus tail accuracy by interface'],'inferenceUnit':'unique case, averaged over 3 repeats; 9 cases, not 27 independent cases','tests':'two-sided exact sign-flip on case means; Holm correction across 3 latency contrasts; paired cluster bootstrap 95% percentile intervals, seed 20261011','accuracy':'family only; exact paired McNemar on majority outcome; no claim of equivalence or mechanism correctness','warmup':'synthetic non-benchmark incident, each variant once, excluded','p95':'nearest rank, descriptive only (27 observations/variant)','concurrency':1,'timeoutsSeconds':60,'retry':0,'productionWrites':False,'labelIsolation':'worker sees anonymous log-derived state, fixed question schema and endpoints only; bwrap excludes dataset, business state and proc; evaluator scores after worker exit','cache':'existing server cache policy unchanged; block order randomized, no cache flush; not a cache-cold experiment','nonBlind':True}
(EXP/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2))
(EXP/'protocol.sha256').write_text(hashlib.sha256((EXP/'protocol.json').read_bytes()).hexdigest())
(EXP/'environment.json').write_text(json.dumps({'platform':platform.platform(),'python':sys.version,'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],text=True).strip(),'sglang':json.load(__import__('urllib.request',fromlist=['urlopen']).urlopen('http://127.0.0.1:30000/v1/models'))},indent=2))
workroot=EXP/'workspaces';workroot.mkdir();rows=[]
mapgold={'kasan':'memory_lifetime','memory_lifetime':'memory_lifetime','memory_bounds':'memory_bounds','leak':'memory_leak','kmemleak':'memory_leak','lockdep':'locking','locking':'locking','rcu':'rcu_progress','rcu_progress':'rcu_progress','oom':'oom','hung_task':'blocked_task','watchdog':'watchdog_lockup','healthy':'other_or_no_fault','usercopy':'memory_bounds'}
# Match the frozen legacy evaluator's explicit taxonomy, not case-name inference.
old=json.loads((BASE/'experiments/decision-hybrid-20261008/boundary-v2-results/results.json').read_text());golds={r['caseId']:r['gold'] for r in old['rows']};assert set(golds)=={c['id'] for c in cases}
def active():
 s=json.loads((BASE/'data/state.json').read_text());return any(j.get('status') in ['queued','running'] for j in s.get('jobs',[])+s.get('agentBenchmarkRuns',[]))
def invoke(incident,v):
 w=workroot/str(uuid.uuid4());w.mkdir();request={'mode':v['mode'],'base':'http://127.0.0.1:30000','model':'Qwen3.8-27B-SystemOne','incident':incident,'questions':QUESTIONS[:v['questions']]};(w/'input.json').write_text(json.dumps(request,ensure_ascii=False))
 runtime=BASE/'runtime';cmd=['bwrap','--unshare-user','--unshare-pid','--die-with-parent','--new-session','--clearenv','--ro-bind','/usr','/usr','--ro-bind','/bin','/bin','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--ro-bind','/etc','/etc','--ro-bind',str(runtime),str(runtime),'--ro-bind',str(FROZEN),'/agent','--bind',str(w),'/work','--dev','/dev','--tmpfs','/tmp','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1','--chdir','/work',str(runtime/'venv/bin/python'),'/agent/boundary-worker.py']
 try:
  p=subprocess.run(cmd,stdout=(w/'worker.log').open('w'),stderr=subprocess.STDOUT,timeout=80);result=json.loads((w/'response.json').read_text()) if (w/'response.json').exists() else {'status':'failed','error':'worker exit '+str(p.returncode),'seconds':None}
 except Exception as e:result={'status':'failed','error':str(e),'seconds':None}
 return w.name,result
warm={'firstDiagnosticLine':1,'lines':[{'line':1,'text':'BUG: KASAN: use-after-free in synthetic_probe'}],'lifetimeEvidence':[],'available':{'log':True,'source':False,'artifacts':False},'evidenceId':'T1'}
for v in variants:invoke(warm,v)
for i,item in enumerate(schedule):
 while active():time.sleep(5)
 c=next(c for c in cases if c['id']==item['caseId']);f=c['files']['agentLog'];raw=(DATA/f['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==f['sha256'];v=next(v for v in variants if v['id']==item['variant'])
 # Inspector workspace contains only a raw agentLog; labels stay in the evaluator.
 temp=EXP/'prepare-input';temp.mkdir(exist_ok=True);(temp/'input.log').write_bytes(raw);inspector=Inspector(temp);incident=inspector._execute('incident',{});incident['evidenceId']='T1'
 if v['window']=='tail':incident={**incident,'lines':inspector.lines(inspector.log,max(1,len(inspector.log)-79),80),'lifetimeEvidence':[]}
 wid,response=invoke(incident,v);row={**item,'ordinal':i,'workspaceId':wid,'agentLogSha256':hashlib.sha256(raw).hexdigest(),**response,'gold':golds[c['id']],'correct':response.get('family')==golds[c['id']] and response.get('status')=='completed'};rows.append(row)
 (EXP/'results.json').write_text(json.dumps({'schema':'paper-boundary-ablation-results/v1','protocolSha256':hashlib.sha256((EXP/'protocol.json').read_bytes()).hexdigest(),'complete':len(rows)==len(schedule),'rows':rows},ensure_ascii=False,indent=2))
 print(json.dumps({'completed':len(rows),'total':len(schedule),'variant':v['id'],'seconds':response.get('seconds'),'status':response['status']}),flush=True)
 if len(rows)>=5 and all(x['status']=='failed' for x in rows[-5:]):raise RuntimeError('Five consecutive failures: stopping rather than silently retrying')
print('COMPLETE',len(rows),flush=True)
