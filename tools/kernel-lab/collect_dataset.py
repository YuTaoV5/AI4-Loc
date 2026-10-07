#!/usr/bin/env python3
"""Collect real guest faults. Run only on the Linux lab host, never host kernel."""
import argparse,base64,concurrent.futures,hashlib,json,pathlib,re,shutil,struct,subprocess,time
from dataset_contract import SCHEMA,PROFILES,record,agent_log,validate

def command(*args,**kw):return subprocess.check_output(args,**kw)
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def build_id(data):
    offset=0
    while offset+12<=len(data):
        namesz,descsz,kind=struct.unpack_from('<III',data,offset);offset+=12
        name=data[offset:offset+namesz];offset+=(namesz+3)&~3
        desc=data[offset:offset+descsz];offset+=(descsz+3)&~3
        if name.rstrip(b'\0')==b'GNU' and kind==3:return desc.hex()
    return None

def describe(name,act,source):
    if name=='baseline':return 'healthy','baseline','guest_init.sh','',r'KI_BASELINE_DONE','Healthy boot and orderly shutdown; no injected fault.'
    if name=='pressure_oom':return 'oom','userspace-pressure','pressure.c','main',r'Out of memory:|out_of_memory|panic_on_oom','Userspace retains and touches 8 MiB allocations until guest memory is exhausted; panic_on_oom=2 converts the guest OOM into a captured panic.'
    if not name.startswith('lkdtm_'):
        mapping={
          'leak_kmalloc':('memory_leak','ki_leak_kmalloc',r'unreferenced object','Last reference to a kmalloc allocation is dropped without kfree.'),
          'leak_kmem_cache':('memory_leak','ki_leak_kmem_cache',r'unreferenced object','Last reference to a slab-cache allocation is dropped without kmem_cache_free.'),
          'leak_vmalloc':('memory_leak','ki_leak_vmalloc',r'unreferenced object','Last reference to a vmalloc allocation is dropped without vfree.'),
          'leak_ptr_overwrite':('memory_leak','ki_leak_ptr_overwrite',r'unreferenced object','The first allocated object loses its reference; the replacement reference is also cleared without freeing.'),
          'oob_kmalloc':('memory_oob','ki_oob_kmalloc',r'KASAN:.*out-of-bounds','A loop writes 128 bytes into a 64-byte allocation.'),
          'uaf_kmalloc':('memory_uaf','ki_uaf_kmalloc',r'KASAN:.*use-after-free','p[0] is written after kfree(p).'),
          'mutex_abba':('lock_order','ki_thr_mutex_abba',r'possible circular locking dependency','The same thread acquires mutex A then B and later B then A; lockdep detects a potential cycle, not an observed two-thread deadlock.'),
          'spin_abba':('lock_order','ki_thr_spin_abba',r'possible circular locking dependency','Spinlocks are acquired A then B and later B then A, creating a lockdep dependency cycle.'),
          'recursive_spin':('lock_order','ki_thr_recursive_spin',r'possible recursive locking','A thread acquires the same nonrecursive spinlock twice without releasing it.'),
          'sleep_atomic':('atomic_sleep','ki_thr_sleep_atomic',r'scheduling while atomic|sleeping function called from invalid context','msleep is called while a spinlock is held, in an atomic context.'),
          'rcu_stall':('rcu_stall','ki_thr_rcu_stall',r'rcu.*detected.*stall|rcu.*self-detected stall','An unbounded loop runs with preemption disabled and prevents an RCU quiescent state.')}
        fam,sym,pat,cause=mapping[act];return fam,fam,'external/ki_bench.c',sym,pat,cause
    action=name[6:];symbol='lkdtm_'+action
    path=next((p for p in source.glob('drivers/misc/lkdtm/*.c') if re.search(r'void\s+'+symbol+r'\s*\(',p.read_text())),None)
    if not path:return 'unsupported','unsupported','drivers/misc/lkdtm/core.c','',r'(?!)','The selected LKDTM action has no implementation in this source revision; excluded from scoring.'
    fam='protection';pattern=r'BUG:|WARNING:|Kernel panic|general protection fault|unable to handle|refcount_t:|usercopy:'
    if action in ['LOOP','SOFTLOCKUP','SPINLOCKUP']:fam='watchdog';pattern=r'watchdog:.*soft lockup|BUG: soft lockup'
    elif action=='HARDLOCKUP':fam='watchdog';pattern=r'Watchdog detected hard LOCKUP|hard LOCKUP'
    elif action=='HUNG_TASK':fam='hung_task';pattern=r'blocked for more than|hung_task: blocked tasks'
    elif 'AFTER_FREE' in action or action=='SLAB_FREE_DOUBLE':fam='memory_uaf';pattern=r'KASAN:.*(?:use-after-free|double-free|invalid-free)|double free'
    elif action=='OVERWRITE_ALLOCATION':fam='memory_oob';pattern=r'KASAN:.*out-of-bounds'
    elif action.startswith('REFCOUNT'):fam='refcount';pattern=r'refcount_t:'
    elif action.startswith('USERCOPY'):fam='usercopy';pattern=r'usercopy:|usercopy_abort'
    elif action=='ARRAY_BOUNDS':fam='memory_oob';pattern=r'UBSAN:.*bounds'
    # Explain causal implementation from the exact archived function, not a guessed bug category.
    cause='LKDTM deliberately executes '+symbol+'; the exact causal function is preserved in causal-source.c and the patched source archive. Its diagnostic is matched independently against the raw guest log.'
    group='lkdtm-'+('refcount' if fam=='refcount' else 'usercopy' if fam=='usercopy' else fam)
    return fam,group,path.relative_to(source).as_posix(),symbol,pattern,cause

def source_range(text,symbol):
    if not symbol:return 1,len(text.splitlines())
    match=re.search(r'\b'+re.escape(symbol)+r'\s*\([^;{}]*\)\s*\{',text)
    if not match:raise ValueError('Missing function '+symbol)
    start=text.count('\n',0,match.start())+1;depth=1;end=match.end()
    while end<len(text) and depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return start,text.count('\n',0,end)+1

def prepare(lab,root):
    shared=root/'shared';shared.mkdir(parents=True,exist_ok=True)
    copies={'vmlinux':lab/'build/vmlinux','bzImage':lab/'build/arch/x86/boot/bzImage','config':lab/'build/.config','module':lab/'scenarios/ki_bench.ko','systemMap':lab/'build/System.map','sourcePatch':lab/'evidence/kasan_backport_fix.patch','guestInit':pathlib.Path(__file__).with_name('guest_dataset_init.sh'),'collector':pathlib.Path(__file__)}
    for key,p in copies.items():
        dest=shared/({'config':'kernel.config','sourcePatch':'source.patch'}.get(key,p.name))
        if not dest.exists() or key=='collector':shutil.copy2(p,dest)
        copies[key]=dest
    shutil.copy2(pathlib.Path(__file__).with_name('dataset_contract.py'),shared/'dataset_contract.py')
    source=shared/'source-tree'
    if not source.exists():
        source.mkdir();archive=command('git','-C',str(lab/'source'),'archive','HEAD')
        subprocess.run(['tar','-x','-C',str(source)],input=archive,check=True)
        subprocess.run(['git','apply',str(copies['sourcePatch'])],cwd=source,check=True)
        (source/'external').mkdir(exist_ok=True);shutil.copy2(lab/'scenarios/ki_bench.c',source/'external/ki_bench.c')
        shutil.copy2(pathlib.Path(__file__).with_name('pressure.c'),source/'pressure.c');shutil.copy2(copies['guestInit'],source/'guest_init.sh')
    dest=shared/'source.tar.gz'
    if not dest.exists():subprocess.run(['tar','-czf',str(dest),'-C',str(source),'.'],check=True)
    copies['sourceArchive']=dest
    for key,args in [('compiler',['gcc','--version']),('qemuVersion',['qemu-system-x86_64','--version'])]:
        dest=shared/(key+'.txt');dest.write_bytes(command(*args));copies[key]=dest
    dest=shared/'build.log';dest.write_bytes(b'\n'.join((lab/('evidence/'+f)).read_bytes() for f in ['build_v2.log','build_v3.log']));copies['buildLog']=dest
    ir=root/'initramfs';ir.mkdir(exist_ok=True)
    for name in ['bin','sbin','proc','sys','dev','tmp']:(ir/name).mkdir(exist_ok=True)
    shutil.copy2('/usr/bin/busybox',ir/'bin/busybox');shutil.copy2(copies['guestInit'],ir/'init');(ir/'init').chmod(0o755);shutil.copy2(copies['module'],ir/'ki_bench.ko')
    subprocess.run(['gcc','-static','-O0','-g','-Wl,--build-id','-o',str(ir/'pressure'),str(source/'pressure.c')],check=True)
    with (shared/'initramfs.cpio.gz').open('wb') as out:
        subprocess.run(['bash','-o','pipefail','-c','find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -9'],cwd=ir,stdout=out,check=True)
    copies['initramfs']=shared/'initramfs.cpio.gz';copies['pressure']=ir/'pressure';copies['contract']=shared/'dataset_contract.py'
    build={'commit':command('git','-C',str(lab/'source'),'rev-parse','HEAD').decode().strip(),'release':(lab/'build/include/config/kernel.release').read_text().strip(),'buildId':re.search(r'Build ID: (\w+)',command('readelf','-n',str(copies['vmlinux'])).decode()).group(1),'sourceState':'commit plus shared/source.patch; external/ki_bench.c and pressure.c added'}
    return copies,source,build

def collect(row,root,shared,source,build):
    name,scn,act,_=row;folder=root/'cases'/name;folder.mkdir(parents=True,exist_ok=True)
    fam,group,path,symbol,pattern,cause=describe(name,act,source)
    rawfile=folder/'serial.log';errfile=folder/'qemu.stderr';start=time.monotonic()
    cmd=['qemu-system-x86_64','-accel','tcg,thread=multi','-machine','q35','-cpu','max','-m','2048','-smp','2','-nic','none','-kernel',str(shared['bzImage']),'-initrd',str(shared['initramfs']),'-append','console=ttyS0,115200 ignore_loglevel nokaslr oops=panic panic=-1 panic_on_oops=1 log_buf_len=16M ki.scn='+scn+' ki.act='+act,'-display','none','-serial','file:'+str(rawfile),'-monitor','none','-no-reboot','-sandbox','on,obsolete=deny,elevateprivileges=deny,spawn=deny,resourcecontrol=deny']
    reason='guest_exit';timedout=False
    with errfile.open('wb') as err:
        process=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=err)
        panic_seen=None
        while process.poll() is None:
            time.sleep(.3);text=rawfile.read_text(errors='replace') if rawfile.exists() else ''
            if 'Kernel panic - not syncing:' in text:
                if panic_seen is None:panic_seen=time.monotonic()
                if time.monotonic()-panic_seen>2:reason='captured_panic';process.terminate();break
            if time.monotonic()-start>120:reason='wall_timeout';timedout=True;process.terminate();break
        try:code=process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();code=process.wait()
    raw=rawfile.read_bytes() if rawfile.exists() else b'';rawfile.write_bytes(raw);text=raw.decode('utf-8','replace');lines=text.splitlines()
    notes=re.search(r'KI_RUNTIME_NOTES_BEGIN\r?\n(.*?)KI_RUNTIME_NOTES_END',text,re.S)
    try:runtime_id=build_id(base64.b64decode(notes.group(1))) if notes else None
    except Exception:runtime_id=None
    release=re.search(r'KI_RUNTIME_RELEASE=([^\r\n]+)',text)
    evidence=[{'line':i+1,'text':line} for i,line in enumerate(lines) if re.search(r'\b(?:'+pattern+r')',line,re.I)]
    causal=source/path;causaltext=causal.read_text();lo,hi=source_range(causaltext,symbol)
    (folder/'causal-source.c').write_text(causaltext);(folder/'agent.log').write_bytes(agent_log(raw))
    # Matching the detector alone is insufficient: a relevant causal symbol must also occur.
    causal_symbols=[symbol] if symbol else ['KI_BASELINE_DONE']
    if fam=='memory_leak':causal_symbols+=['ki_alloc_','ki_trigger_write']
    if name=='pressure_oom':causal_symbols=['pressure','out_of_memory']
    causal_seen=any(s in text for s in causal_symbols)
    issues=[]
    if not evidence:issues.append('expected diagnostic absent')
    if not causal_seen:issues.append('causal trace/trigger evidence absent')
    if timedout:issues.append('wall-clock timeout')
    if runtime_id!=build['buildId']:issues.append('runtime Build ID mismatch')
    if not release or release.group(1)!=build['release']:issues.append('runtime release mismatch')
    if 'KI_TRIGGER_FAILED' in text or 'KI_MODULE_FAILED' in text:issues.append('trigger/module failed')
    run={'command':cmd,'returnCode':code,'timedOut':timedout,'stopReason':reason,'elapsedSeconds':round(time.monotonic()-start,3),'networkDisabled':True,'noHostSharing':True,'accelerator':'tcg','memoryMiB':2048,'vcpus':2,'runtimeBuildId':runtime_id,'runtimeRelease':release.group(1) if release else None}
    label={'status':'evidence_verified' if not issues else 'excluded','rootCause':cause,'rootLocation':{'path':path,'symbol':symbol or 'baseline','startLine':lo,'endLine':hi},'diagnosticEvidence':evidence,'causalTraceSymbols':causal_symbols,'issues':issues,'annotationMethod':'deterministic injector source plus expected detector and causal trace; synthetic, not independently discovered production bugs'}
    write(folder/'run.json',run);write(folder/'ground-truth.json',label)
    split='test' if int(hashlib.sha256(group.encode()).hexdigest(),16)%5==0 else 'train'
    result={'id':name,'family':fam,'mechanismGroup':group,'split':split,'status':'ready' if not issues else 'excluded','exclusionReasons':issues,'files':{k:record(root,folder/f) for k,f in {'rawLog':'serial.log','agentLog':'agent.log','stderr':'qemu.stderr','run':'run.json','groundTruth':'ground-truth.json','causalSource':'causal-source.c'}.items()}}
    write(folder/'case.json',result);print(name,result['status'],issues,flush=True);return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--lab',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--only');args=ap.parse_args()
    if not 1<=args.workers<=4:ap.error('workers must be 1..4')
    root=args.output.resolve()
    if (root/'manifest.json').exists():raise ValueError('Dataset is finalized; use a new output version. Only unfinished collection directories can resume.')
    root.mkdir(parents=True,exist_ok=True)
    shared,source,build=prepare(args.lab,root)
    rows=[s.split('|') for s in (args.lab/'scenarios.tsv').read_text().splitlines()[1:] if s];rows.append(['pressure_oom','pressure_oom','','120'])
    if args.only:rows=[r for r in rows if re.search(args.only,r[0])]
    cases=[];pending=[]
    for row in rows:
        previous=root/'cases'/row[0]/'case.json'
        if previous.exists():cases.append(json.loads(previous.read_text()))
        else:pending.append(row)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks=[pool.submit(collect,r,root,shared,source,build) for r in pending]
        for task in concurrent.futures.as_completed(tasks):cases.append(task.result())
    write(root/'manifest.json',{'schema':SCHEMA,'build':build,'shared':{k:record(root,p) for k,p in shared.items()},'cases':sorted(cases,key=lambda c:c['id']),'inputProfiles':PROFILES,'optionalArtifacts':{'vmcore':'not collected; vmlinux and matching module/debug symbols are present'},'scope':'synthetic injected x86_64 OpenHarmony 5.10 kernel stability cases; not production bug distribution'})
    report=validate(root);write(root/'validation.json',report);print(json.dumps(report,indent=2),flush=True)
    return 0 if report['complete'] else 2
if __name__=='__main__':raise SystemExit(main())
