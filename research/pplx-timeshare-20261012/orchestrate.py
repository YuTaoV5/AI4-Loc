"""Time-share the sole A100, with original supervisor and sidecar restoration.

The platform's Go supervisor has no configured control/RPC socket. Its monitor is
paused briefly (other services keep running), then resumed to restore its original
systemone program. A separate watchdog restores services if this controller dies.
Private saved process environments never enter reports or archives for publication.
"""
import pathlib,json,subprocess,os,signal,time,urllib.request,sys,hashlib,socket
E=pathlib.Path('/opt/kernel-insight/experiments/pplx-timeshare-20261012');S=pathlib.Path('/opt/kernel-insight/services/pplx-decider-v1');PY=str(S/'venv/bin/python');WORKER='/opt/kernel-insight/runtime/venv/bin/python';leasefile=E/'lease.private.json'
read=lambda p:json.loads(p.read_text())
def write(p,data):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(data,indent=2));t.replace(p)
def stat(pid):
 try:return pathlib.Path(f'/proc/{pid}/stat').read_text().split()
 except FileNotFoundError:return None
def identity(pid):
 x=stat(pid);return x[21] if x else None
def health(port,path):
 try:return json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=3))
 except Exception:return None
def wait_for(check,seconds,message):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  value=check()
  if value:return value
  time.sleep(2)
 raise TimeoutError(message)
def gpu():return int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())
def group_live(pgid):
 found=[]
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  x=stat(int(p.name))
  if x and int(x[4])==pgid and x[2]!='Z':found.append(int(p.name))
 return found
def stop(record):
 pid=record['pid'];ticks=record['ticks']
 if identity(pid)!=ticks:return
 if group_live(pid):os.killpg(pid,signal.SIGTERM)
 try:wait_for(lambda:not group_live(pid),45,'Group termination')
 except TimeoutError:
  if group_live(pid):os.killpg(pid,signal.SIGKILL)
  wait_for(lambda:not group_live(pid),15,'Group termination after KILL')
def restore():
 lease=read(leasefile);events=[]
 for child in reversed(lease.get('children',[])):
  try:stop(child);events.append({'stoppedOwnedGroup':child['pid']})
  except Exception as error:events.append({'stopError':str(error),'pid':child['pid']})
 if identity(50)!=lease['managerTicks']:raise RuntimeError('Supervisor identity changed; refusing signal')
 os.kill(50,signal.SIGCONT);events.append({'supervisorResumed':50})
 prod=wait_for(lambda:health(30000,'/v1/models'),900,'Original managed model failed to recover')
 side=health(30002,'/health')
 if not side:
  r=subprocess.run([PY,str(S/'service.py'),'start'],capture_output=True,text=True,timeout=180);events.append({'sidecarStartExit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
  side=wait_for(lambda:health(30002,'/health'),60,'Sidecar recovery')
 result={'restored':True,'checkedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'events':events,'productionModel':prod,'sidecar':side,'supervisorState':stat(50)[2],'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader'],text=True).strip()}
 write(E/'restoration.json',result);lease['restored']=True;write(leasefile,lease);print('RESTORED',flush=True);return result
if len(sys.argv)>1 and sys.argv[1]=='--guard':
 controller=int(sys.argv[2]);ticks=sys.argv[3];deadline=time.monotonic()+3600
 while time.monotonic()<deadline:
  if read(leasefile).get('restored'):sys.exit()
  x=stat(controller)
  if not x or x[2]=='Z' or x[21]!=ticks:break
  time.sleep(5)
 x=stat(controller)
 if x and x[2]!='Z' and x[21]==ticks:os.kill(controller,signal.SIGTERM)
 restore();sys.exit()
def spawn(args,name,env=None):
 with (E/(name+'.log')).open('w') as log:child=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
 lease=read(leasefile);lease['children'].append({'pid':child.pid,'ticks':identity(child.pid),'name':name});write(leasefile,lease);return child
def phase(arm,child):
 port=30002 if arm=='pplx' else 30003;path='/health' if arm=='pplx' else '/v1/models'
 def loaded():
  if child.poll() is not None:raise RuntimeError(arm+' server exited during loading; see server log')
  return health(port,path)
 wait_for(loaded,600,arm+' load timeout')
 if arm=='pplx':
  runtime=read(E/'pplx-runtime.json');assert runtime['parameterDevices']==['cuda:0'] and runtime['placement']=='full-gpu'
 snap={'arm':arm,'checkedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader'],text=True).strip(),'production30000Responding':bool(health(30000,'/v1/models')),'otherExperimentalArmResponding':bool(health(30003 if arm=='pplx' else 30002,'/v1/models' if arm=='pplx' else '/health'))}
 assert not snap['production30000Responding'] and not snap['otherExperimentalArmResponding'];write(E/(arm+'-phase.json'),snap)
 print('PHASE_READY',arm,flush=True)
 with (E/(arm+'-benchmark.log')).open('w') as log:r=subprocess.run([WORKER,str(E/'benchmark.py'),'run','--arm',arm],stdout=log,stderr=subprocess.STDOUT,timeout=2100)
 assert r.returncode==0,arm+' benchmark failed'
 stop({'pid':child.pid,'ticks':identity(child.pid)});child.wait(timeout=20);wait_for(lambda:gpu()>=76000,90,'GPU not released after '+arm)
 print('PHASE_COMPLETE',arm,flush=True)
finish={'status':'failed'};started=time.monotonic()
try:
 subprocess.run([WORKER,str(E/'benchmark.py'),'prepare'],check=True)
 s=read(pathlib.Path('/opt/kernel-insight/data/state.json'));assert not any(j.get('status') in ['queued','running'] for j in s.get('jobs',[])+s.get('agentBenchmarkRuns',[]))
 original=read(E/'original-process.private.json');original_pid=original['pid']
 assert identity(original_pid)==original['stat'].split()[21]
 assert stat(original_pid)[3]=='50' and int(stat(original_pid)[4])==original_pid;assert health(30000,'/v1/models');assert identity(50)
 with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',30003))!=0
 write(leasefile,{'managerTicks':identity(50),'children':[],'restored':False})
 with (E/'guard.log').open('w') as log:subprocess.Popen([PY,str(E/'orchestrate.py'),'--guard',str(os.getpid()),identity(os.getpid())],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 r=subprocess.run([PY,str(S/'service.py'),'stop'],capture_output=True,text=True,timeout=60);write(E/'sidecar-stop.json',{'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
 os.kill(50,signal.SIGSTOP);assert wait_for(lambda:stat(50)[2]=='T',5,'Supervisor pause')
 stop({'pid':original_pid,'ticks':identity(original_pid)});wait_for(lambda:gpu()>=76000,90,'Production GPU not released');print('ORIGINAL_MODEL_UNLOADED',flush=True)
 pplx=spawn([PY,str(E/'serve.py'),'--checkpoint','/root/gpufree-data/systemone/models/PPLX-Decider-v1-27B','--placement','full-gpu','--port','30002','--record',str(E/'pplx-runtime.json')],'pplx-server');phase('pplx',pplx)
 args=original['args'].copy();args[args.index('--port')+1]='30003';args+=['--disable-radix-cache'];write(E/'generic-command.json',{'args':args,'envPublished':False,'radixCache':False})
 generic=spawn(args,'generic-server',env=original['env']);phase('generic',generic)
 assert read(E/'results.json')['complete'];finish={'status':'completed'}
except BaseException as error:
 finish={'status':'failed','error':type(error).__name__+': '+str(error)};print('EXPERIMENT_ERROR',finish['error'],flush=True)
finally:
 if leasefile.exists():
  try:finish['restoration']=restore()
  except Exception as error:finish['restorationError']=str(error);print('RESTORE_ERROR',str(error),flush=True)
 finish['elapsedSeconds']=time.monotonic()-started;write(E/'completion.json',finish)
