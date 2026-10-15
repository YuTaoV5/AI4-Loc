"""Reversible GPU time sharing, exact process identities, independent watchdog."""
import pathlib, json, os, sys, time, signal, subprocess, urllib.request, socket
E=pathlib.Path(__file__).resolve().parent
PY='/root/systemone-venv/bin/python'
LEASE=E/'lease.private.json'
def read(p):return json.loads(p.read_text())
def write(p,x):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(x,indent=2));tmp.replace(p)
def stat(pid):
    try:return pathlib.Path(f'/proc/{pid}/stat').read_text().split()
    except FileNotFoundError:return None
def ticks(pid):
    x=stat(pid);return x[21] if x else None
def health(port):
    try:return json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models',timeout=3))
    except Exception:return None
def wait(check,seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if check():return
        time.sleep(2)
    raise TimeoutError('Condition timeout')
def group(pid):
    return [p.name for p in pathlib.Path('/proc').iterdir() if p.name.isdigit() and (s:=stat(int(p.name))) and s[2]!='Z' and int(s[4])==pid]
def stop(record):
    pid=record['pid']
    if ticks(pid)!=record['ticks']:return
    assert int(stat(pid)[4])==pid
    os.killpg(pid,signal.SIGTERM)
    try:wait(lambda:not group(pid),45)
    except TimeoutError:
        if group(pid):os.killpg(pid,signal.SIGKILL)
        wait(lambda:not group(pid),15)
def restore():
    lease=read(LEASE)
    for child in reversed(lease['children']):stop(child)
    manager=lease['manager']
    assert ticks(manager['pid'])==manager['ticks'],'Supervisor changed'
    if lease.get('paused'):os.kill(manager['pid'],signal.SIGCONT)
    wait(lambda:health(30000),900)
    result={'restored':True,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'models':health(30000),
            'supervisor_state':stat(manager['pid'])[2],'experimental_server_responding':bool(health(30003)),
            'sidecar_originally_running':False,
            'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader'],text=True).strip()}
    lease['restored']=True;write(LEASE,lease);write(E/'restoration.json',result)
if '--guard' in sys.argv:
    pid=int(sys.argv[2]);identity=sys.argv[3];deadline=time.monotonic()+3600
    while time.monotonic()<deadline:
        if read(LEASE).get('restored'):sys.exit()
        s=stat(pid)
        if not s or s[2]=='Z' or s[21]!=identity:break
        time.sleep(5)
    if ticks(pid)==identity:os.kill(pid,signal.SIGKILL)
    restore();sys.exit()
def spawn(args,name,env=None):
    with (E/(name+'.log')).open('w') as f:
        p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=env)
    lease=read(LEASE);lease['children'].append({'pid':p.pid,'ticks':ticks(p.pid),'name':name});write(LEASE,lease);return p
result={'status':'failed'}
try:
    assert not LEASE.exists(),'Never reuse an experiment directory'
    pids=[]
    for p in pathlib.Path('/proc').iterdir():
        if p.name.isdigit():
            try:args=p.joinpath('cmdline').read_bytes().split(b'\0')[:-1]
            except FileNotFoundError:continue
            if b'sglang.launch_server' in args and b'30000' in args:pids.append(int(p.name))
    assert len(pids)==1
    pid=pids[0];s=stat(pid);manager=int(s[3]);assert int(s[4])==pid
    assert b'/data/supervisord' in pathlib.Path(f'/proc/{manager}/cmdline').read_bytes()
    with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',30002))!=0,'Sidecar is active; revise protocol first'
    with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',30003))!=0
    state=read(pathlib.Path('/opt/kernel-insight/data/state.json'))
    assert not any(x.get('status') in ['queued','running'] for k in ['jobs','agentBenchmarkRuns'] for x in state.get(k,[]))
    original={'pid':pid,'ticks':ticks(pid),'args':[x.decode() for x in pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')[:-1]],
              'env':dict(x.decode().split('=',1) for x in pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in x)}
    write(E/'original-process.private.json',original);os.chmod(E/'original-process.private.json',0o600)
    info=json.load(urllib.request.urlopen('http://127.0.0.1:30000/get_server_info'))
    write(E/'production-before.private.json',info)
    write(LEASE,{'manager':{'pid':manager,'ticks':ticks(manager)},'children':[],'paused':False,'restored':False})
    with (E/'guard.log').open('w') as f:
        subprocess.Popen([PY,str(E/'orchestrate.py'),'--guard',str(os.getpid()),ticks(os.getpid())],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    os.kill(manager,signal.SIGSTOP);wait(lambda:stat(manager)[2]=='T',5)
    lease=read(LEASE);lease['paused']=True;write(LEASE,lease)
    stop(original);wait(lambda:int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())>76000,90)
    args=original['args'].copy();args[args.index('--port')+1]='30003'
    args+=['--enable-metrics','--decode-log-interval','1','--enable-request-time-stats-logging',
           '--export-metrics-to-file','--export-metrics-to-file-dir',str(E/'request-metrics')]
    env=original['env'].copy();env['PYTHONPATH']=str(E)+(':'+env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    env['AI4LOC_KV_TRACE']=str(E/'scheduler');env['AI4LOC_KV_TRACE_DISABLE_FILE']=str(E/'trace-disabled')
    write(E/'experimental-command.json',{'args':args,'environment_values_published':False,'hook':'sitecustomize.py; no installed source modification'})
    model=spawn(args,'server',env)
    def loaded():
        if model.poll() is not None:raise RuntimeError('Experimental server exited')
        return health(30003)
    wait(loaded,600)
    write(E/'server-info.private.json',json.load(urllib.request.urlopen('http://127.0.0.1:30003/get_server_info')))
    write(E/'model-config.json',read(pathlib.Path('/root/gpufree-data/systemone/models/Qwen3.8-27B/config.json')))
    spawn(['nvidia-smi','--query-gpu=timestamp,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw,clocks.sm,clocks.mem','--format=csv,noheader,nounits','--loop-ms=100'],'gpu')
    print('EXPERIMENT_READY',flush=True)
    with (E/'benchmark.log').open('w') as f:
        p=subprocess.run([PY,str(E/'benchmark.py')],stdout=f,stderr=subprocess.STDOUT,timeout=2400)
    assert p.returncode==0,'Benchmark failed; see benchmark.log'
    assert not (E/'scheduler.errors').exists(),'Scheduler observation failed'
    assert list(E.glob('scheduler.*.jsonl')),'No scheduler observations'
    result={'status':'completed'}
except BaseException as e:result={'status':'failed','error':repr(e)};print('ERROR',repr(e),flush=True)
finally:
    if LEASE.exists():
        try:restore();result['restored']=True
        except Exception as e:result['restoration_error']=repr(e)
    write(E/'completion.json',result);print(json.dumps(result),flush=True)
