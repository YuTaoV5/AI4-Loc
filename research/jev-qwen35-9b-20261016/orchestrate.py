"""Train and evaluate with bounded, independently guarded GPU time sharing."""
import pathlib,json,os,sys,time,signal,subprocess,socket,urllib.request,hashlib,shutil
E=pathlib.Path(__file__).resolve().parent;PY='/root/systemone-venv/bin/python';LEASE=E/'lease.private.json'
BASE=pathlib.Path('/root/gpufree-data/systemone/models/Qwen3.5-9B')
TRAINED=BASE.parent/'AI4Loc-Jev-Qwen3.5-9B'
def read(p):return json.loads(pathlib.Path(p).read_text())
def write(p,x):
    p=pathlib.Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(x,indent=2));tmp.replace(p)
def stat(pid):
    try:return pathlib.Path(f'/proc/{pid}/stat').read_text().split()
    except FileNotFoundError:return None
def ticks(pid):
    s=stat(pid);return s[21] if s else None
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
        wait(lambda:not group(pid),30)
def restore():
    lease=read(LEASE)
    for child in reversed(lease['children']):stop(child)
    manager=lease['manager'];assert ticks(manager['pid'])==manager['ticks']
    if lease.get('paused'):os.kill(manager['pid'],signal.SIGCONT)
    wait(lambda:health(30000),900)
    result={'restored':True,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'models':health(30000),
            'supervisor_state':stat(manager['pid'])[2],'experimental_server_responding':bool(health(30003)),
            'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader'],text=True).strip()}
    # Actual post-restore Decision + streaming Chat requests, separate from trials.
    probes=[]
    for path,payload in [('/v1/decisions',{'input':'BUG: KASAN: use-after-free in worker','questions':[{'id':'x','type':'choice','question':'Which fault is reported?','options':[{'name':'use_after_free'},{'name':'out_of_memory'}]}],'temperature':1,'prompt_format_version':1}),
                         ('/v1/chat/completions',{'messages':[{'role':'user','content':'Reply OK only.'}],'max_tokens':8,'temperature':0,'chat_template_kwargs':{'enable_thinking':False}})]:
        req=urllib.request.Request('http://127.0.0.1:30000'+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=90) as r:obj=json.load(r);probes.append({'path':path,'status':r.status,'response':obj})
    result['synthetic_probes']=probes
    lease['restored']=True;write(LEASE,lease);write(E/'restoration.json',result)
if '--guard' in sys.argv:
    pid=int(sys.argv[2]);identity=sys.argv[3];deadline=time.monotonic()+14400
    while time.monotonic()<deadline:
        if read(LEASE).get('restored'):sys.exit()
        s=stat(pid)
        if not s or s[2]=='Z' or s[21]!=identity:break
        time.sleep(5)
    if ticks(pid)==identity:os.kill(pid,signal.SIGKILL)
    restore();sys.exit()
def spawn(args,path,env=None):
    with pathlib.Path(path).open('w') as f:p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=env)
    l=read(LEASE);l['children'].append({'pid':p.pid,'ticks':ticks(p.pid),'name':str(path)});write(LEASE,l);return p
def job(args,name,env,timeout):
    p=spawn(args,E/(name+'.log'),env);code=p.wait(timeout=timeout);assert code==0,f'{name} exited {code}'
def freegpu():return int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())>76000
def active():
    s=read('/opt/kernel-insight/data/state.json')
    return any(x.get('status') in ['queued','running'] for k in ['jobs','agentBenchmarkRuns'] for x in s.get(k,[]))
result={'status':'failed'}
try:
    assert not LEASE.exists(),'Use a fresh experiment directory'
    # Download is allowed to finish while production keeps running.
    wait(lambda:(BASE/'verified-checkpoint.json').exists(),1800)
    assert read(BASE/'verified-checkpoint.json')['revision']==read(E/'official-model-metadata.json')['sha']
    assert not active(),'Live user jobs pending'
    pids=[]
    for p in pathlib.Path('/proc').iterdir():
        if p.name.isdigit():
            try:args=(p/'cmdline').read_bytes().split(b'\0')[:-1]
            except FileNotFoundError:continue
            if b'sglang.launch_server' in args and b'30000' in args:pids.append(int(p.name))
    assert len(pids)==1;pid=pids[0];s=stat(pid);manager=int(s[3]);assert int(s[4])==pid
    assert b'/data/supervisord' in pathlib.Path(f'/proc/{manager}/cmdline').read_bytes()
    for port in [30002,30003]:
        with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',port))!=0,port
    original={'pid':pid,'ticks':ticks(pid),'args':[x.decode() for x in pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')[:-1]],
              'env':dict(x.decode().split('=',1) for x in pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in x)}
    write(E/'original-process.private.json',original);os.chmod(E/'original-process.private.json',0o600)
    write(LEASE,{'manager':{'pid':manager,'ticks':ticks(manager)},'children':[],'paused':False,'restored':False})
    with (E/'guard.log').open('w') as f:subprocess.Popen([PY,str(E/'orchestrate.py'),'--guard',str(os.getpid()),ticks(os.getpid())],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    os.kill(manager,signal.SIGSTOP);wait(lambda:stat(manager)[2]=='T',5);l=read(LEASE);l['paused']=True;write(LEASE,l)
    stop(original);wait(freegpu,120)
    env=original['env'].copy();env['PYTHONPATH']=str(E/'deps');env['OMP_NUM_THREADS']='8';env['TOKENIZERS_PARALLELISM']='false'
    gpu=spawn(['nvidia-smi','--query-gpu=timestamp,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw,clocks.sm,clocks.mem','--format=csv,noheader,nounits','--loop-ms=100'],E/'training-gpu.log')
    print('TRAINING_START',flush=True);job([PY,str(E/'train.py')],'training',env,7200)
    stop({'pid':gpu.pid,'ticks':ticks(gpu.pid)});wait(freegpu,120)
    for name,modelpath in [('base',BASE),('trained',TRAINED)]:
        assert not active()
        run=E/name;run.mkdir(exist_ok=False)
        for f in ['benchmark.py','sitecustomize.py']:shutil.copy2(E/f,run/f)
        args=[PY,'-m','sglang.launch_server','--model-path',str(modelpath),'--served-model-name','AI4Loc-Qwen9B','--host','127.0.0.1','--port','30003',
              '--dtype','bfloat16','--context-length','8192','--mem-fraction-static','0.55','--max-running-requests','4',
              '--mamba-full-memory-ratio','0.6','--max-mamba-cache-size','32','--enable-metrics','--decode-log-interval','1',
              '--enable-request-time-stats-logging','--export-metrics-to-file','--export-metrics-to-file-dir',str(run/'request-metrics')]
        serving=original['env'].copy();serving['PYTHONPATH']=str(run);serving['AI4LOC_KV_TRACE']=str(run/'scheduler');serving['AI4LOC_KV_TRACE_DISABLE_FILE']=str(run/'trace-disabled')
        write(run/'experimental-command.json',{'args':args,'hook':'isolated sitecustomize, installed sources unchanged'})
        server=spawn(args,run/'server.log',serving)
        def loaded():
            if server.poll() is not None:raise RuntimeError(name+' SGLang exited')
            return health(30003)
        wait(loaded,900)
        actual=json.load(urllib.request.urlopen('http://127.0.0.1:30003/get_server_info'));write(run/'server-info.private.json',actual)
        assert actual['internal_states'][0]['effective_max_running_requests_per_dp']==4
        write(run/'model-config.json',read(modelpath/'config.json'))
        monitor=spawn(['nvidia-smi','--query-gpu=timestamp,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw,clocks.sm,clocks.mem','--format=csv,noheader,nounits','--loop-ms=100'],run/'gpu.log')
        bench=original['env'].copy();bench['AI4LOC_RUN_DIR']=str(run);bench['AI4LOC_CHECKPOINT_ARM']=name
        print('BENCHMARK_START',name,flush=True)
        job([PY,str(run/'benchmark.py')],name+'-benchmark',bench,2400)
        job([PY,str(E/'accuracy.py')],name+'-accuracy',bench,1200)
        assert not (run/'scheduler.errors').exists()
        write(run/'completion.json',{'status':'completed','arm':name})
        for child in [server,monitor]:stop({'pid':child.pid,'ticks':ticks(child.pid)})
        wait(freegpu,120)
    result={'status':'completed','training':read(E/'training-complete.json')}
except BaseException as error:result={'status':'failed','error':repr(error)};print('ERROR',repr(error),flush=True)
finally:
    if LEASE.exists():
        try:restore();result['restored']=True
        except Exception as error:result['restoration_error']=repr(error)
    write(E/'completion.json',result);print(json.dumps(result),flush=True)
