"""Own-process lifecycle for a loopback-only PPLX service in non-systemd containers."""
import argparse,json,pathlib,subprocess,time,urllib.request,socket,os,signal,sys
p=argparse.ArgumentParser();p.add_argument('action',choices=['start','status','stop']);p.add_argument('--python',default=str(pathlib.Path(__file__).resolve().parent/'venv/bin/python'));p.add_argument('--checkpoint',default='/root/gpufree-data/systemone/models/PPLX-Decider-v1-27B');p.add_argument('--port',type=int,default=30002);p.add_argument('--gpu-weight-limit',default='10GiB');p.add_argument('--cpu-memory-limit',default='64GiB');p.add_argument('--gpu-wait-seconds',type=int,default=60);a=p.parse_args()
home=pathlib.Path(__file__).resolve().parent;state=home/'state';state.mkdir(exist_ok=True);pidfile=state/'process.json';script=home/'serve.py'
def owned():
 if not pidfile.exists():return None
 record=json.loads(pidfile.read_text());pid=record['pid'];proc=pathlib.Path(f'/proc/{pid}')
 if not proc.exists():return None
 stat=(proc/'stat').read_text().split()
 if stat[2]=='Z':return None
 cmd=(proc/'cmdline').read_bytes().split(b'\0');start=stat[21]
 if str(script).encode() not in cmd or start!=record['procStartTicks']:raise RuntimeError('PID identity mismatch; refusing process operation')
 return pid
def health():
 try:
  return json.load(urllib.request.urlopen(f'http://127.0.0.1:{a.port}/health',timeout=3))
 except Exception:return None
def same_process_alive(pid,ticks):
 try:
  stat=pathlib.Path(f'/proc/{pid}/stat').read_text().split()
  return stat[2]!='Z' and stat[21]==ticks
 except FileNotFoundError:return False
pid=owned()
if a.action=='status':print(json.dumps({'pid':pid,'healthy':health()}));sys.exit(0 if pid and health() else 1)
if a.action=='stop':
 if pid:
  ticks=json.loads(pidfile.read_text())['procStartTicks'];os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+45
  # Command line may disappear before /proc during CUDA teardown. After the
  # identity-checked SIGTERM, wait on this exact start time without signalling again.
  while same_process_alive(pid,ticks) and time.monotonic()<deadline:time.sleep(1)
  if same_process_alive(pid,ticks):raise RuntimeError('Graceful stop timed out; inspect log/process before retrying')
 pidfile.unlink(missing_ok=True);print('STOPPED');sys.exit()
if pid:raise RuntimeError('Already running; use status')
with socket.socket() as sock:
 if sock.connect_ex(('127.0.0.1',a.port))==0:raise RuntimeError('Port is occupied; refusing to replace another service')
gpu_wait_start=time.monotonic();assert 0<=a.gpu_wait_seconds<=600
while True:
 free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())
 if free>=16000:break
 if time.monotonic()-gpu_wait_start>=a.gpu_wait_seconds:raise RuntimeError('Need at least 16000 MiB free; bounded GPU wait expired, no process started')
 time.sleep(2)
gpu_wait=time.monotonic()-gpu_wait_start
args=[a.python,str(script),'--checkpoint',a.checkpoint,'--port',str(a.port),'--gpu-weight-limit',a.gpu_weight_limit,'--cpu-memory-limit',a.cpu_memory_limit,'--record',str(state/'runtime.json')]
with (state/'server.log').open('ab') as log:
 child=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 ticks=pathlib.Path(f'/proc/{child.pid}/stat').read_text().split()[21]
 pidfile.write_text(json.dumps({'pid':child.pid,'procStartTicks':ticks,'args':args},indent=2))
deadline=time.monotonic()+600
while time.monotonic()<deadline:
 if child.poll() is not None:raise RuntimeError('Service exited; inspect state/server.log')
 h=health()
 if h and h.get('ready'):print(json.dumps({'status':'ready','pid':child.pid,'gpuWaitSeconds':gpu_wait,'health':h}));break
 time.sleep(2)
else:raise RuntimeError('Startup wait timed out; service kept for inspection; use status/stop')
