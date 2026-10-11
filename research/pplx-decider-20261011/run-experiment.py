"""Own only the isolated reference process; production model services stay untouched."""
import pathlib,subprocess,time,json,urllib.request,signal,sys,hashlib
P=pathlib.Path(__file__).resolve().parent;MODEL=pathlib.Path('/root/gpufree-data/systemone/models/PPLX-Decider-v1-27B');child=None
def stop(signum,frame):raise SystemExit(128+signum)
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def ready():
 try:return json.load(urllib.request.urlopen('http://127.0.0.1:30002/health',timeout=3)).get('ready') is True
 except Exception:return False
def active():
 s=json.loads(pathlib.Path('/opt/kernel-insight/data/state.json').read_text());return any(j.get('status') in ['running','queued'] for j in s.get('jobs',[])+s.get('agentBenchmarkRuns',[]))
started=time.monotonic();finish={}
try:
 while not (MODEL/'verified-checkpoint.json').exists():
  if time.monotonic()-started>2400:raise TimeoutError('Checkpoint did not finish in 40 minutes')
  time.sleep(5)
 while active():time.sleep(5)
 assert not ready(),'Reference port already in use'
 free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip());assert free>=16000,'Need 16GB free GPU headroom'
 py=P/'reference-venv/bin/python'
 with (P/'server.log').open('w') as log:
  child=subprocess.Popen([str(py),str(P/'serve-reference.py'),'--checkpoint',str(MODEL),'--gpu-weight-limit','10GiB','--record',str(P/'runtime.json')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  (P/'reference.pid').write_text(str(child.pid));deadline=time.monotonic()+600
  while not ready():
   if child.poll() is not None:raise RuntimeError('Reference server startup failed; see server.log')
   if time.monotonic()>deadline:raise TimeoutError('Reference startup timeout')
   time.sleep(3)
  with (P/'benchmark.log').open('w') as b:
   result=subprocess.run(['/opt/kernel-insight/runtime/venv/bin/python',str(P/'run-benchmark.py')],stdout=b,stderr=subprocess.STDOUT,timeout=5400)
  assert result.returncode==0,'Benchmark failed; preserve logs'
  finish={'status':'completed'}
except BaseException as e:
 finish={'status':'failed','error':type(e).__name__+': '+str(e)};raise
finally:
 if child and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=30)
  except subprocess.TimeoutExpired:child.kill();child.wait()
 finish['elapsedSeconds']=time.monotonic()-started
 try:finish['productionModel']=json.load(urllib.request.urlopen('http://127.0.0.1:30000/v1/models',timeout=10))
 except Exception as e:finish['productionHealthError']=type(e).__name__
 (P/'completion.json').write_text(json.dumps(finish,indent=2));print(json.dumps(finish),flush=True)
